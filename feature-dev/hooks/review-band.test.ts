import { describe, expect, mock, test } from 'claude-code/testing'
import type { Engine, MockClock } from 'claude-code/testing'
import type { On } from 'claude-code'

const ROOT = '/work/repo'
const REVIEWS = `${ROOT}/.feature-dev/reviews`
const HOUR = 60 * 60 * 1000

type File = { text: string; mtimeMs: number }
type World = {
  files: Record<string, File>
  alive?: Set<string>
  runs: { command: string; args: string }[]
  /** Where the mocked clock starts; 0 keeps every test mtime inside the window. */
  now?: number
}

const BAND = {
  plugin: 'feature-dev',
  surface: 'terminal',
  component: 'AbovePrompt',
  props: {
    hasSurvey: false,
    isWorking: false,
    maxRows: 12,
    bodyColumns: 120,
    scroll: { offset: 0, bodyRows: 11 },
    view: {},
  },
} as const

function review(artifact: string): string {
  return `---\nartifact: ${artifact}\nverdict: approve\n---\n\n# Review\n`
}

function spec(slug?: string): string {
  return slug ? `---\ntype: specification\nslug: ${slug}\n---\n# Spec\n` : '# Spec\n'
}

const DISMISSED = `${ROOT}/.feature-dev/band-dismissed.json`

/** What a previous session's Dismiss of SPEC-billing.md at mtime 1000 leaves on disk. */
const PERSISTED = { version: 1, dismissed: { 'SPEC-billing.md': 1000 } }

function dismissedOnDisk(w: World): unknown {
  const f = w.files[DISMISSED]
  return f === undefined ? undefined : JSON.parse(f.text)
}

/** The world beneath the plugin: a file system in memory, the network, commands. */
function world(on: On, w: World): MockClock {
  const clock = mock.clock(on, { now: w.now ?? 0 })
  const dirOf = (p: string) => p.slice(0, p.lastIndexOf('/'))
  on('session.root', () => ({ value: ROOT }))
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  on('turn.complete', () => ({ text: '' }))
  on('fs.list', ($, e) => ({
    value: Object.entries(w.files)
      .filter(([p]) => dirOf(p) === e.path)
      .map(([p, f]) => ({ name: p.slice(p.lastIndexOf('/') + 1), kind: 'file' as const, size: f.text.length, mtimeMs: f.mtimeMs, isLink: false })),
  }))
  on('fs.write', ($, e) => {
    w.files[e.path] = { text: e.text, mtimeMs: 0 }
    return { value: undefined }
  })
  on('fs.read', ($, e) => {
    const f = w.files[e.path]
    return f === undefined ? { deny: `ENOENT ${e.path}` } : { value: f.text }
  })
  on('http.fetch', ($, e) =>
    w.alive?.has(e.url) ? { value: { status: 204, ok: true, headers: {}, text: '' } } : { deny: 'ECONNREFUSED' },
  )
  on('command.list', () => ({
    value: [
      { name: 'feature-dev:spec', description: '', source: 'plugin' as const, plugin: 'feature-dev' },
      { name: 'feature-dev:review', description: '', source: 'plugin' as const, plugin: 'feature-dev' },
      { name: 'feature-dev:cleanup', description: '', source: 'plugin' as const, plugin: 'feature-dev' },
    ],
  }))
  on('command.run', ($, e) => {
    w.runs.push({ command: e.command, args: e.args })
    return { text: '' }
  })
  on('ui.render', { component: 'AbovePrompt' }, () => ({ type: 'Box', props: { key: 'engine-band' } }) as never)
  return clock
}

async function endTurn($: Engine, agentId?: string): Promise<void> {
  await $.turn.complete({ answer: '', durationMs: 1, isAborted: false, turnId: 't', reason: 'answer', ...(agentId ? { agentId } : {}) })
}

describe('review band', () => {
  test('flags an artifact changed after its latest review', async ($, on) => {
    const w: World = {
      runs: [],
      files: {
        [`${ROOT}/SPEC-billing.md`]: { text: spec(), mtimeMs: 2000 },
        [`${REVIEWS}/billing-20260101T000000Z.md`]: { text: review('SPEC-billing.md'), mtimeMs: 1000 },
      },
    }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    expect((await ui.find({ type: 'Text', text: 'not reviewed since last change' }))?.text).toContain('SPEC-billing.md')
    expect(await ui.find({ key: 'open:SPEC-billing.md' })).toBeDefined()
    expect(await ui.find({ key: 'dismiss:SPEC-billing.md' })).toBeDefined()
  })

  test('draws nothing when the latest review is newer than the artifact', async ($, on) => {
    const w: World = {
      runs: [],
      files: {
        [`${ROOT}/SPEC-billing.md`]: { text: spec(), mtimeMs: 1000 },
        [`${REVIEWS}/billing-20260101T000000Z.md`]: { text: review('SPEC-billing.md'), mtimeMs: 2000 },
      },
    }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    expect(await ui.find({ key: 'engine-band' })).toBeDefined()
    expect(await ui.find({ type: 'Button' })).toBeUndefined()
  })

  test('matches reviews on the full artifact name, not the shared slug', async ($, on) => {
    const w: World = {
      runs: [],
      files: {
        [`${ROOT}/SPEC-billing.md`]: { text: spec(), mtimeMs: 1000 },
        [`${ROOT}/PLAN-billing.md`]: { text: spec(), mtimeMs: 1000 },
        // A newer review of the SPEC says nothing about the PLAN.
        [`${REVIEWS}/billing-20260101T000000Z.md`]: { text: review('SPEC-billing.md'), mtimeMs: 2000 },
      },
    }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    expect(await ui.find({ key: 'open:PLAN-billing.md' })).toBeDefined()
    expect(await ui.find({ key: 'open:SPEC-billing.md' })).toBeUndefined()
  })

  test('ignores history copies and files that are not artifacts', async ($, on) => {
    const w: World = {
      runs: [],
      files: {
        [`${ROOT}/SPEC-billing.3.md`]: { text: spec(), mtimeMs: 1000 },
        [`${ROOT}/SPEC notes.md`]: { text: spec(), mtimeMs: 1000 },
        [`${ROOT}/README.md`]: { text: spec(), mtimeMs: 1000 },
      },
    }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    expect(await ui.find({ type: 'Button' })).toBeUndefined()
  })

  test('Dismiss hides the row until the artifact changes again', async ($, on) => {
    const w: World = { runs: [], files: { [`${ROOT}/SPEC-billing.md`]: { text: spec(), mtimeMs: 1000 } } }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    await ui.press({ key: 'dismiss:SPEC-billing.md' })
    expect(await ui.find({ key: 'open:SPEC-billing.md' })).toBeUndefined()
    await endTurn($)
    expect(await ui.find({ key: 'open:SPEC-billing.md' })).toBeUndefined()
    w.files[`${ROOT}/SPEC-billing.md`] = { text: spec(), mtimeMs: 3000 }
    await endTurn($)
    expect(await ui.find({ key: 'open:SPEC-billing.md' })).toBeDefined()
  })

  test('Open review runs /feature-dev:review on the artifact', async ($, on) => {
    const w: World = { runs: [], files: { [`${ROOT}/PLAN-billing.md`]: { text: spec(), mtimeMs: 1000 } } }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    await ui.press({ key: 'open:PLAN-billing.md' })
    expect(w.runs).toEqual([{ command: 'feature-dev:review', args: 'PLAN-billing.md' }])
  })

  test('finds artifacts in .feature-dev/specs and /plans, and a name in both places once', async ($, on) => {
    const w: World = {
      runs: [],
      files: {
        [`${ROOT}/.feature-dev/specs/SPEC-billing.md`]: { text: spec(), mtimeMs: 1000 },
        [`${ROOT}/.feature-dev/plans/PLAN-billing.md`]: { text: spec(), mtimeMs: 1000 },
        [`${ROOT}/SPEC-billing.md`]: { text: spec(), mtimeMs: 5000 },
      },
    }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    await ui.press({ key: 'show-all' })
    expect(await ui.findAll({ type: 'Button', text: 'Open review' })).toHaveLength(2)
    await ui.press({ key: 'open:SPEC-billing.md' })
    await ui.press({ key: 'open:PLAN-billing.md' })
    expect(w.runs.map(r => r.args)).toEqual(['.feature-dev/specs/SPEC-billing.md', '.feature-dev/plans/PLAN-billing.md'])
  })

  test('artifacts_dir moves the folder the band reads', { options: { artifacts_dir: 'docs/fd' } }, async ($, on) => {
    const w: World = {
      runs: [],
      files: {
        [`${ROOT}/docs/fd/specs/SPEC-billing.md`]: { text: spec(), mtimeMs: 1000 },
        [`${ROOT}/.feature-dev/specs/SPEC-other.md`]: { text: spec(), mtimeMs: 1000 },
      },
    }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    expect(await ui.find({ key: 'open:SPEC-billing.md' })).toBeDefined()
    expect(await ui.find({ key: 'open:SPEC-other.md' })).toBeUndefined()
  })

  test('a live review server turns Open into a link to its page', async ($, on) => {
    const w: World = {
      runs: [],
      alive: new Set(['http://127.0.0.1:43123/alive']),
      files: {
        [`${ROOT}/SPEC-billing.md`]: { text: spec('billing-v2'), mtimeMs: 1000 },
        [`${REVIEWS}/.billing-v2.url`]: { text: 'http://127.0.0.1:43123/\n', mtimeMs: 1000 },
      },
    }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    const link = await ui.find({ type: 'Link' })
    expect(link?.props.href).toBe('http://localhost:43123/')
    expect(await ui.find({ key: 'open:SPEC-billing.md' })).toBeUndefined()
  })

  test('a stale pointer whose server is gone keeps the Open button', async ($, on) => {
    const w: World = {
      runs: [],
      files: {
        [`${ROOT}/SPEC-billing.md`]: { text: spec(), mtimeMs: 1000 },
        [`${REVIEWS}/.billing.url`]: { text: 'http://127.0.0.1:43123/\n', mtimeMs: 1000 },
      },
    }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    expect(await ui.find({ type: 'Link' })).toBeUndefined()
    expect(await ui.find({ key: 'open:SPEC-billing.md' })).toBeDefined()
  })

  test("a subagent's turn does not rescan", async ($, on) => {
    const w: World = { runs: [], files: { [`${ROOT}/SPEC-billing.md`]: { text: spec(), mtimeMs: 1000 } } }
    world(on, w)
    await endTurn($, 'agent-1')
    const ui = await $.ui.mount(BAND)
    expect(await ui.find({ type: 'Button' })).toBeUndefined()
  })

  test('review_band: false turns the band off', { options: { review_band: false } }, async ($, on) => {
    const w: World = { runs: [], files: { [`${ROOT}/SPEC-billing.md`]: { text: spec(), mtimeMs: 1000 } } }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    expect(await ui.find({ type: 'Button' })).toBeUndefined()
  })

  test('yields to a survey', async ($, on) => {
    const w: World = { runs: [], files: { [`${ROOT}/SPEC-billing.md`]: { text: spec(), mtimeMs: 1000 } } }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount({ ...BAND, props: { ...BAND.props, hasSurvey: true } })
    expect(await ui.find({ type: 'Button' })).toBeUndefined()
  })

  test('hides an unreviewed artifact older than the window, shows a recent one', async ($, on) => {
    const now = 100 * HOUR
    const w: World = {
      runs: [],
      now,
      files: {
        [`${ROOT}/SPEC-old.md`]: { text: spec(), mtimeMs: now - 48 * HOUR },
        [`${ROOT}/SPEC-new.md`]: { text: spec(), mtimeMs: now - 1 * HOUR },
      },
    }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    expect(await ui.find({ key: 'open:SPEC-new.md' })).toBeDefined()
    expect(await ui.find({ key: 'open:SPEC-old.md' })).toBeUndefined()
    expect(await ui.find({ key: 'show-all' })).toBeUndefined()
  })

  test('review_band_window_hours widens the window', { options: { review_band_window_hours: 72 } }, async ($, on) => {
    const now = 100 * HOUR
    const w: World = { runs: [], now, files: { [`${ROOT}/SPEC-old.md`]: { text: spec(), mtimeMs: now - 48 * HOUR } } }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    expect(await ui.find({ key: 'open:SPEC-old.md' })).toBeDefined()
  })

  test('shows an artifact modified this session even past the window', async ($, on) => {
    const w: World = {
      runs: [],
      now: 10 * HOUR,
      files: {
        [`${ROOT}/SPEC-before.md`]: { text: spec(), mtimeMs: 5 * HOUR },
        [`${ROOT}/SPEC-during.md`]: { text: spec(), mtimeMs: 20 * HOUR },
      },
    }
    const clock = world(on, w)
    await $.session.start({ cwd: ROOT, surface: 'terminal', isInteractive: true })
    await clock.set(100 * HOUR)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    expect(await ui.find({ key: 'open:SPEC-during.md' })).toBeDefined()
    expect(await ui.find({ key: 'open:SPEC-before.md' })).toBeUndefined()
  })

  test('two or more pending collapse into one row that opens the latest', async ($, on) => {
    const w: World = {
      runs: [],
      files: {
        [`${ROOT}/SPEC-a.md`]: { text: spec(), mtimeMs: 1000 },
        [`${ROOT}/.feature-dev/plans/PLAN-b.md`]: { text: spec(), mtimeMs: 3000 },
        [`${ROOT}/SPEC-c.md`]: { text: spec(), mtimeMs: 2000 },
      },
    }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    expect((await ui.find({ type: 'Text', text: 'not reviewed' }))?.text).toContain('3 not reviewed')
    expect((await ui.find({ key: 'open:latest' }))?.props.label).toBe('Open PLAN-b.md')
    expect(await ui.find({ key: 'open:SPEC-a.md' })).toBeUndefined()
    await ui.press({ key: 'open:latest' })
    expect(w.runs).toEqual([{ command: 'feature-dev:review', args: '.feature-dev/plans/PLAN-b.md' }])
  })

  test('Show all expands to one row each, Collapse folds it back', async ($, on) => {
    const w: World = {
      runs: [],
      files: {
        [`${ROOT}/SPEC-a.md`]: { text: spec(), mtimeMs: 1000 },
        [`${ROOT}/SPEC-b.md`]: { text: spec(), mtimeMs: 2000 },
      },
    }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    await ui.press({ key: 'show-all' })
    expect(await ui.find({ key: 'open:SPEC-a.md' })).toBeDefined()
    expect(await ui.find({ key: 'dismiss:SPEC-b.md' })).toBeDefined()
    expect(await ui.find({ key: 'show-all' })).toBeUndefined()
    await ui.press({ key: 'collapse' })
    expect(await ui.find({ key: 'open:SPEC-a.md' })).toBeUndefined()
    expect(await ui.find({ key: 'show-all' })).toBeDefined()
  })

  test('Dismiss all hides every pending artifact until one changes again', async ($, on) => {
    const w: World = {
      runs: [],
      files: {
        [`${ROOT}/SPEC-a.md`]: { text: spec(), mtimeMs: 1000 },
        [`${ROOT}/SPEC-b.md`]: { text: spec(), mtimeMs: 2000 },
      },
    }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    await ui.press({ key: 'dismiss-all' })
    expect(await ui.find({ type: 'Button' })).toBeUndefined()
    w.files[`${ROOT}/SPEC-a.md`] = { text: spec(), mtimeMs: 4000 }
    await endTurn($)
    expect(await ui.find({ key: 'open:SPEC-a.md' })).toBeDefined()
    expect(await ui.find({ key: 'open:SPEC-b.md' })).toBeUndefined()
  })

  test('Dismiss writes the artifact and its mtime to .feature-dev/band-dismissed.json', async ($, on) => {
    const w: World = { runs: [], files: { [`${ROOT}/SPEC-billing.md`]: { text: spec(), mtimeMs: 1000 } } }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    await ui.press({ key: 'dismiss:SPEC-billing.md' })
    // The exact state the next test starts a fresh session from.
    expect(dismissedOnDisk(w)).toEqual(PERSISTED)
  })

  test('a dismissal persisted by an earlier session hides the row in a fresh one', async ($, on) => {
    // A fresh engine and module: only the file on disk carries the dismissal over.
    const w: World = {
      runs: [],
      files: {
        [`${ROOT}/SPEC-billing.md`]: { text: spec(), mtimeMs: 1000 },
        [DISMISSED]: { text: JSON.stringify(PERSISTED), mtimeMs: 0 },
      },
    }
    world(on, w)
    await $.session.start({ cwd: ROOT, surface: 'terminal', isInteractive: true })
    const ui = await $.ui.mount(BAND)
    expect(await ui.find({ key: 'open:SPEC-billing.md' })).toBeUndefined()
    // Changed since: it comes back, and the stale entry is pruned from disk.
    w.files[`${ROOT}/SPEC-billing.md`] = { text: spec(), mtimeMs: 3000 }
    await endTurn($)
    expect(await ui.find({ key: 'open:SPEC-billing.md' })).toBeDefined()
    expect(dismissedOnDisk(w)).toEqual({ version: 1, dismissed: {} })
  })

  test('prunes dismissals whose artifact no longer exists, keeps the rest', async ($, on) => {
    const stored = { version: 1, dismissed: { 'SPEC-billing.md': 1000, 'SPEC-gone.md': 500 } }
    const w: World = {
      runs: [],
      files: {
        [`${ROOT}/SPEC-billing.md`]: { text: spec(), mtimeMs: 1000 },
        [DISMISSED]: { text: JSON.stringify(stored), mtimeMs: 0 },
      },
    }
    world(on, w)
    await endTurn($)
    expect(dismissedOnDisk(w)).toEqual(PERSISTED)
    const ui = await $.ui.mount(BAND)
    expect(await ui.find({ type: 'Button' })).toBeUndefined()
  })

  test('a malformed dismiss file reads as nothing dismissed', async ($, on) => {
    const w: World = {
      runs: [],
      files: {
        [`${ROOT}/SPEC-billing.md`]: { text: spec(), mtimeMs: 1000 },
        [DISMISSED]: { text: '{"version": 1, "dismis', mtimeMs: 0 },
      },
    }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    expect(await ui.find({ key: 'open:SPEC-billing.md' })).toBeDefined()
  })

  test('Dismiss merges with what another session wrote meanwhile', async ($, on) => {
    const w: World = {
      runs: [],
      files: {
        [`${ROOT}/SPEC-billing.md`]: { text: spec(), mtimeMs: 1000 },
        [`${ROOT}/SPEC-other.md`]: { text: spec(), mtimeMs: 700 },
      },
    }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    await ui.press({ key: 'show-all' })
    w.files[DISMISSED] = { text: JSON.stringify({ version: 1, dismissed: { 'SPEC-other.md': 700 } }), mtimeMs: 0 }
    await ui.press({ key: 'dismiss:SPEC-billing.md' })
    expect(dismissedOnDisk(w)).toEqual({ version: 1, dismissed: { 'SPEC-other.md': 700, 'SPEC-billing.md': 1000 } })
  })

  test('Dismiss all persists every listed artifact', async ($, on) => {
    const w: World = {
      runs: [],
      files: {
        [`${ROOT}/SPEC-a.md`]: { text: spec(), mtimeMs: 1000 },
        [`${ROOT}/.feature-dev/plans/PLAN-b.md`]: { text: spec(), mtimeMs: 2000 },
      },
    }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    await ui.press({ key: 'dismiss-all' })
    expect(dismissedOnDisk(w)).toEqual({ version: 1, dismissed: { 'SPEC-a.md': 1000, 'PLAN-b.md': 2000 } })
  })

  test('Clean up runs /feature-dev:cleanup from the collapsed row and the expanded view', async ($, on) => {
    const w: World = {
      runs: [],
      files: {
        [`${ROOT}/SPEC-a.md`]: { text: spec(), mtimeMs: 1000 },
        [`${ROOT}/SPEC-b.md`]: { text: spec(), mtimeMs: 2000 },
      },
    }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    await ui.press({ key: 'cleanup' })
    await ui.press({ key: 'show-all' })
    await ui.press({ key: 'cleanup' })
    expect(w.runs).toEqual([
      { command: 'feature-dev:cleanup', args: '' },
      { command: 'feature-dev:cleanup', args: '' },
    ])
    // Nothing is deleted by the band itself.
    expect(Object.keys(w.files)).toEqual([`${ROOT}/SPEC-a.md`, `${ROOT}/SPEC-b.md`])
  })

  test('hides a spec whose frontmatter says status: approved', async ($, on) => {
    const approved = '---\ntype: specification\nstatus: approved\n---\n# Spec\n'
    const draft = '---\ntype: specification\nstatus: draft\n---\n# Spec\n'
    const w: World = {
      runs: [],
      files: {
        [`${ROOT}/SPEC-done.md`]: { text: approved, mtimeMs: 2000 },
        [`${ROOT}/SPEC-wip.md`]: { text: draft, mtimeMs: 1000 },
        // `status: approved` past the frontmatter is body text, not an approval.
        [`${ROOT}/SPEC-body.md`]: { text: `${draft}\nstatus: approved\n`, mtimeMs: 1000 },
      },
    }
    world(on, w)
    await endTurn($)
    const ui = await $.ui.mount(BAND)
    await ui.press({ key: 'show-all' })
    expect(await ui.find({ key: 'open:SPEC-wip.md' })).toBeDefined()
    expect(await ui.find({ key: 'open:SPEC-body.md' })).toBeDefined()
    expect(await ui.find({ key: 'open:SPEC-done.md' })).toBeUndefined()
  })
})
