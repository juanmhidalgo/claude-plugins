import { describe, expect, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { On } from 'claude-code'

const ROOT = '/work/repo'
const REVIEWS = `${ROOT}/.feature-dev/reviews`

type File = { text: string; mtimeMs: number }
type World = {
  files: Record<string, File>
  alive?: Set<string>
  runs: { command: string; args: string }[]
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

/** The world beneath the plugin: a file system in memory, the network, commands. */
function world(on: On, w: World): void {
  const dirOf = (p: string) => p.slice(0, p.lastIndexOf('/'))
  on('session.root', () => ({ value: ROOT }))
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  on('turn.complete', () => ({ text: '' }))
  on('fs.list', ($, e) => ({
    value: Object.entries(w.files)
      .filter(([p]) => dirOf(p) === e.path)
      .map(([p, f]) => ({ name: p.slice(p.lastIndexOf('/') + 1), kind: 'file' as const, size: f.text.length, mtimeMs: f.mtimeMs, isLink: false })),
  }))
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
    ],
  }))
  on('command.run', ($, e) => {
    w.runs.push({ command: e.command, args: e.args })
    return { text: '' }
  })
  on('ui.render', { component: 'AbovePrompt' }, () => ({ type: 'Box', props: { key: 'engine-band' } }) as never)
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
})
