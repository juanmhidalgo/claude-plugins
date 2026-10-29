import { describe, expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { On } from 'claude-code'

import { needsReviewCount, newlyApproved } from './register'

const ROOT = '/work/repo'

type Feature = {
  slug: string
  status: string
  plan: null
  issue: null
  artifacts: { kind: 'spec' | 'plan'; path: string; needs_review: boolean }[]
}

type World = {
  /** What `features.py list --json` prints. */
  features: Feature[]
  /** Every process.run the mod made. */
  runs: { argv: readonly string[] }[]
  /** Every ui.open the mod made. */
  opens: { id: string; title?: string; focus?: boolean; columns?: number }[]
  /** What ui.open answers: false when the terminal is too narrow to place the pane. */
  isPlaced?: boolean
  /** Every command.run the mod made. */
  commands: { command: string; args: string }[]
  /** How `list --json` fails: rejects, exits non-zero, or prints invalid JSON. */
  listFails?: 'reject' | 'exit' | 'json'
  /** Make `delete` exit non-zero with this stderr. */
  deleteStderr?: string
  /** Every toast the mod raised. */
  toasts?: string[]
}

const BAND = {
  plugin: 'feature-dev',
  surface: 'terminal',
  component: 'AbovePrompt',
  props: { hasSurvey: false, isWorking: false, maxRows: 12, bodyColumns: 120, scroll: { offset: 0, bodyRows: 11 }, view: {} },
} as const

const PANE = {
  plugin: 'feature-dev',
  surface: 'terminal',
  component: 'Pane',
  requestId: 'features',
  props: {
    title: 'Features',
    isFocused: false,
    bodyColumns: 60,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 20 },
    view: {},
  },
} as const

function feature(slug: string, status: string, needsReview = false): Feature {
  return {
    slug,
    status,
    plan: null,
    issue: null,
    artifacts: [{ kind: 'spec', path: `.feature-dev/features/${slug}/SPEC-${slug}.md`, needs_review: needsReview }],
  }
}

/**
 * The world beneath the mod: a fake features.py and a pane placement answer.
 * No fs.read handler is registered, so any read the mod makes throws.
 */
function world(on: On, w: World): void {
  on('session.root', () => ({ value: ROOT }))
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  on('turn.complete', () => ({ text: '' }))
  on('ui.open', (_$, e) => {
    w.opens.push(e)
    return { value: w.isPlaced === false ? { isPlaced: false as const, reason: 'too-narrow' as never } : { isPlaced: true as const } }
  })
  on('command.list', () => ({
    value: [
      { name: 'feature-dev:review', description: '', source: 'plugin' as const, plugin: 'feature-dev' },
      { name: 'feature-dev:tdd', description: '', source: 'plugin' as const, plugin: 'feature-dev' },
      { name: 'feature-dev:explore-plan', description: '', source: 'plugin' as const, plugin: 'feature-dev' },
    ],
  }))
  on('command.run', (_$, e) => {
    w.commands.push({ command: e.command, args: e.args })
    return { text: '' }
  })
  on('ui.toast', (_$, e) => {
    ;(w.toasts ??= []).push(e.text)
    return { value: undefined } as never
  })
  on('ui.render', { component: 'Pane' }, () => ({ type: 'Box', props: {} }) as never)
  on('ui.render', { component: 'AbovePrompt' }, () => ({ type: 'Box', props: {} }) as never)
  on('process.run', (_$, e) => {
    w.runs.push({ argv: e.argv })
    if (e.argv[2] === 'list' && w.listFails === 'reject') throw new Error('python3: not found')
    if (e.argv[2] === 'list' && w.listFails === 'exit')
      return { value: { exitCode: 2, stdout: '', stderr: 'boom', isStdoutTruncated: false, isStderrTruncated: false } }
    if (e.argv[2] === 'list' && w.listFails === 'json')
      return { value: { exitCode: 0, stdout: 'not json', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
    if (e.argv[2] === 'delete' && w.deleteStderr !== undefined)
      return { value: { exitCode: 1, stdout: '', stderr: w.deleteStderr, isStdoutTruncated: false, isStderrTruncated: false } }
    if (e.argv[2] === 'delete') w.features = w.features.filter(f => f.slug !== e.argv[3])
    return {
      value: { exitCode: 0, stdout: JSON.stringify(w.features), stderr: '', isStdoutTruncated: false, isStderrTruncated: false },
    }
  })
}

function threeFeatures(): World {
  return {
    runs: [],
    opens: [],
    commands: [],
    features: [feature('billing', 'running', true), feature('auth', 'implemented'), feature('search', 'draft')],
  }
}

async function start($: Engine): Promise<void> {
  await $.session.start({ cwd: ROOT, surface: 'terminal', isInteractive: true })
}

async function endTurn($: Engine, agentId?: string, reason: 'answer' | 'aborted' = 'answer'): Promise<void> {
  await $.turn.complete({ answer: '', durationMs: 1, isAborted: reason === 'aborted', turnId: 't', reason, ...(agentId ? { agentId } : {}) })
}

function withPlan(f: Feature): Feature {
  return {
    ...f,
    artifacts: [
      ...f.artifacts,
      { kind: 'plan', path: `.feature-dev/features/${f.slug}/PLAN-${f.slug}.md`, needs_review: false },
    ],
  }
}

async function buttons(ui: Awaited<ReturnType<Engine['ui']['mount']>>): Promise<string[]> {
  return (await ui.findAll({ type: 'Button' })).map(b => String(b.key ?? ''))
}

async function rows(ui: Awaited<ReturnType<Engine['ui']['mount']>>): Promise<string[]> {
  return (await ui.findAll({ type: 'Text' })).map(t => t.text ?? '')
}

describe('feature sidebar', () => {
  test('session.start opens the Features pane and lists active features, then Done', async ($, on) => {
    const w = threeFeatures()
    world(on, w)
    await start($)
    expect(w.opens).toEqual([{ id: 'features', title: 'Features', columns: 56 }])
    expect(w.runs).toHaveLength(1)
    const argv = w.runs[0]!.argv
    expect(argv[0]).toBe('python3')
    expect(argv.slice(2)).toEqual(['list', '--json', '--root', ROOT])
    expect(argv[1]).toMatch(/\/scripts\/features\.py$/)

    const ui = await $.ui.mount(PANE)
    const text = await rows(ui)
    const at = (needle: string) => text.findIndex(t => t.includes(needle))
    expect(at('billing')).toBeGreaterThanOrEqual(0)
    expect(text[at('billing')]).toContain('running')
    expect(text[at('billing')]).toContain('needs review')
    expect(text[at('search')]).toContain('draft')
    expect(text[at('search')]).not.toContain('needs review')
    expect(text[at('Done')]).toBeDefined()
    expect(at('billing')).toBeLessThan(at('Done'))
    expect(at('search')).toBeLessThan(at('Done'))
    expect(at('Done')).toBeLessThan(at('auth'))
    expect(text[at('auth')]).toContain('implemented')
  })

  test('ac22: an empty list opens no pane; a hand-mounted Pane names /feature-dev:spec', async ($, on) => {
    const w = threeFeatures()
    w.features = []
    world(on, w)
    await start($)
    expect(w.runs).toHaveLength(1)
    expect(w.opens).toEqual([])

    const ui = await $.ui.mount(PANE)
    const text = await rows(ui)
    expect(text).toHaveLength(1)
    expect(text[0]).toMatch(/no features/i)
    expect(text[0]).toContain('/feature-dev:spec')
  })

  test('turn.complete refreshes the list for the main agent only', async ($, on) => {
    const w = threeFeatures()
    world(on, w)
    await start($)
    const ui = await $.ui.mount(PANE)
    w.features = [feature('newcomer', 'draft')]

    await endTurn($, 'agent-1')
    expect(w.runs).toHaveLength(1)
    expect((await rows(ui)).some(t => t.includes('newcomer'))).toBe(false)

    await endTurn($)
    expect(w.runs).toHaveLength(2)
    expect((await rows(ui)).some(t => t.includes('newcomer'))).toBe(true)
  })

  test('ac16: selecting a feature shows exactly its valid actions', async ($, on) => {
    const w = threeFeatures()
    w.features = [
      withPlan(feature('billing', 'running')),
      feature('search', 'draft'),
      withPlan(feature('auth', 'implemented')),
    ]
    world(on, w)
    await start($)
    const ui = await $.ui.mount(PANE)
    expect(await buttons(ui)).toEqual(['select:billing', 'select:search', 'select:auth'])

    await ui.press({ key: 'select:billing' })
    expect(await buttons(ui)).toEqual(
      expect.arrayContaining(['review-spec', 'review-plan', 'continue', 'dismiss', 'delete']),
    )

    await ui.press({ key: 'select:search' })
    const draft = await buttons(ui)
    expect(draft).toEqual(expect.arrayContaining(['review-spec', 'dismiss', 'delete']))
    expect(draft).not.toContain('review-plan')
    expect(draft).not.toContain('continue')

    await ui.press({ key: 'select:auth' })
    const done = await buttons(ui)
    expect(done).toContain('review-plan')
    expect(done).not.toContain('continue')
  })

  test('ac16: Review spec, Review plan and Continue run through command.run', async ($, on) => {
    const w = threeFeatures()
    w.features = [withPlan(feature('billing', 'planned')), feature('search', 'running')]
    world(on, w)
    await start($)
    const ui = await $.ui.mount(PANE)

    await ui.press({ key: 'select:billing' })
    await ui.press({ key: 'review-spec' })
    await ui.press({ key: 'review-plan' })
    await ui.press({ key: 'continue' })
    // No PLAN artifact: Continue falls back to the spec path.
    await ui.press({ key: 'select:search' })
    await ui.press({ key: 'continue' })
    expect(w.commands).toEqual([
      { command: 'feature-dev:review', args: '.feature-dev/features/billing/SPEC-billing.md' },
      { command: 'feature-dev:review', args: '.feature-dev/features/billing/PLAN-billing.md' },
      { command: 'feature-dev:tdd', args: '.feature-dev/features/billing/PLAN-billing.md' },
      { command: 'feature-dev:tdd', args: '.feature-dev/features/search/SPEC-search.md' },
    ])
  })
  test('ac17: Dismiss hides the mark and the band count until a fresh session', async ($, on) => {
    const w = threeFeatures()
    w.features = [feature('a', 'running', true), feature('b', 'draft', true)]
    // No fs.write handler is registered: any write the mod made would throw.
    world(on, w)
    await start($)
    const ui = await $.ui.mount(PANE)
    const marked = async () => (await rows(ui)).filter(t => t.includes('needs review')).length
    expect(await marked()).toBe(2)

    await ui.press({ key: 'select:a' })
    await ui.press({ key: 'dismiss' })
    expect(await marked()).toBe(1)

    // A later turn reports `a` with a newer artifact, still needing review.
    w.features = [
      {
        ...feature('a', 'running', true),
        artifacts: [{ kind: 'spec', path: '.feature-dev/features/a/SPEC-a-v2.md', needs_review: true }],
      },
      feature('b', 'draft', true),
    ]
    await endTurn($)
    const text = await rows(ui)
    expect(text.find(t => t.startsWith('a '))).not.toContain('needs review')
    expect(await marked()).toBe(1)
    expect(needsReviewCount(w.features as never, ['a'])).toBe(1)
    expect(needsReviewCount(w.features as never, [])).toBe(2)
  })

  test('ac17: a fresh session (new engine) shows the dismissed mark again', async ($, on) => {
    const w = threeFeatures()
    w.features = [feature('a', 'running', true)]
    world(on, w)
    await start($)
    const ui = await $.ui.mount(PANE)
    expect((await rows(ui)).find(t => t.startsWith('a '))).toContain('needs review')
  })

  test('ac18: Delete asks first, then runs features.py delete (--force unless implemented)', async ($, on) => {
    const w = threeFeatures()
    world(on, w)
    await start($)
    const ui = await $.ui.mount(PANE)
    const deletes = () => w.runs.filter(r => r.argv[2] === 'delete').map(r => r.argv)
    const deleteLabel = async () => String((await ui.findAll({ type: 'Button' })).find(b => b.key === 'delete')?.props?.label)

    await ui.press({ key: 'select:search' })
    expect(await deleteLabel()).toBe('Delete')
    await ui.press({ key: 'delete' })
    expect(deletes()).toEqual([])
    expect(await deleteLabel()).toMatch(/not implemented/i)
    await ui.press({ key: 'delete' })
    expect(deletes()).toHaveLength(1)
    expect(deletes()[0]!.slice(2)).toEqual(['delete', 'search', '--root', ROOT, '--force'])
    expect((await rows(ui)).some(t => t.startsWith('search '))).toBe(false)

    await ui.press({ key: 'select:auth' })
    await ui.press({ key: 'delete' })
    expect(await deleteLabel()).not.toMatch(/not implemented/i)
    expect(await deleteLabel()).not.toBe('Delete')
    await ui.press({ key: 'delete' })
    expect(deletes()[1]!.slice(2)).toEqual(['delete', 'auth', '--root', ROOT])
  })

  test('ac18: Delete never deletes a running or halted feature; it toasts the cleanup pointer', async ($, on) => {
    const w = threeFeatures()
    w.features.push(feature('stuck', 'halted'))
    world(on, w)
    await start($)
    const ui = await $.ui.mount(PANE)
    for (const slug of ['billing', 'stuck']) {
      await ui.press({ key: `select:${slug}` })
      await ui.press({ key: 'delete' })
      await ui.press({ key: 'delete' })
      expect((await rows(ui)).some(t => t.startsWith(`${slug} `))).toBe(true)
    }
    expect(w.runs.filter(r => r.argv[2] === 'delete')).toEqual([])
    expect(w.toasts?.length).toBeGreaterThanOrEqual(2)
    expect(w.toasts!.every(t => t.includes('/feature-dev:cleanup'))).toBe(true)
  })

  test('ac18: changing the selection resets the delete confirmation', async ($, on) => {
    const w = threeFeatures()
    world(on, w)
    await start($)
    const ui = await $.ui.mount(PANE)
    await ui.press({ key: 'select:search' })
    await ui.press({ key: 'delete' })
    await ui.press({ key: 'select:billing' })
    await ui.press({ key: 'select:search' })
    await ui.press({ key: 'delete' })
    expect(w.runs.filter(r => r.argv[2] === 'delete')).toEqual([])
  })

  test('ac19: with the pane not shown, the band is one row that opens the pane', async ($, on) => {
    const w = threeFeatures()
    w.isPlaced = false
    w.features = [feature('a', 'running', true), feature('b', 'draft', true), feature('c', 'draft')]
    world(on, w)
    await start($)
    const ui = await $.ui.mount(BAND)
    const found = await ui.findAll({ type: 'Button' })
    expect(found).toHaveLength(1)
    expect(String(found[0]!.props?.label)).toBe('2 need review · Features')

    w.opens.length = 0
    await ui.press({ key: String(found[0]!.key) })
    expect(w.opens).toEqual([{ id: 'features', focus: true, columns: 56 }])
  })

  test('an implemented feature is never marked: no band, no row mark, not counted', async ($, on) => {
    const w = threeFeatures()
    w.isPlaced = false
    w.features = [feature('shipped', 'implemented', true)]
    world(on, w)
    await start($)
    const band = await $.ui.mount(BAND)
    expect(await band.find({ type: 'Button' })).toBeUndefined()
    const pane = await $.ui.mount(PANE)
    const row = (await rows(pane)).find(t => t.startsWith('shipped '))
    expect(row).toContain('implemented')
    expect(row).not.toContain('needs review')
    const mixed = [feature('shipped', 'implemented', true), feature('active', 'running', true)]
    expect(needsReviewCount(mixed as never, [])).toBe(1)
  })

  test('ac19: the band hides while the pane is open', async ($, on) => {
    const w = threeFeatures()
    w.features = [feature('a', 'running', true)]
    world(on, w)
    await start($)
    expect(w.opens).toHaveLength(1)
    const ui = await $.ui.mount(BAND)
    expect(await ui.find({ type: 'Button' })).toBeUndefined()
  })

  test('ac19: no band when nothing needs review', async ($, on) => {
    const w = threeFeatures()
    w.isPlaced = false
    w.features = [feature('a', 'running'), feature('b', 'draft')]
    world(on, w)
    await start($)
    const ui = await $.ui.mount(BAND)
    expect(await ui.find({ type: 'Button' })).toBeUndefined()
  })

  test('ac22: an empty list renders no band', async ($, on) => {
    const w = threeFeatures()
    w.features = []
    world(on, w)
    await start($)
    const ui = await $.ui.mount(BAND)
    expect(await ui.find({ type: 'Button' })).toBeUndefined()
  })

  test('ac23: review_band false draws neither the pane nor the band', { options: { review_band: false } }, async ($, on) => {
    const w = threeFeatures()
    w.isPlaced = false
    w.features = [feature('a', 'running', true)]
    world(on, w)
    await start($)
    expect(w.opens).toEqual([])
    const band = await $.ui.mount(BAND)
    expect(await band.find({ type: 'Button' })).toBeUndefined()
    const pane = await $.ui.mount(PANE)
    expect(await pane.find({ type: 'Text' })).toBeUndefined()
  })

  test('review_band and plan_after_approve both false register nothing', { options: { review_band: false, plan_after_approve: false } }, async ($, on) => {
    const w = threeFeatures()
    world(on, w)
    await start($)
    expect(w.runs).toEqual([])
    expect(w.opens).toEqual([])
  })

  test('the band yields to a survey and to an agent view', async ($, on) => {
    const w = threeFeatures()
    w.isPlaced = false
    w.features = [feature('a', 'running', true)]
    world(on, w)
    await start($)
    const shown = await $.ui.mount(BAND)
    expect(await shown.find({ type: 'Button' })).toBeDefined()
    const survey = await $.ui.mount({ ...BAND, props: { ...BAND.props, hasSurvey: true } })
    expect(await survey.find({ type: 'Button' })).toBeUndefined()
    const agent = await $.ui.mount({ ...BAND, props: { ...BAND.props, view: { agentId: 'agent-1' } } })
    expect(await agent.find({ type: 'Button' })).toBeUndefined()
  })

  for (const mode of ['reject', 'exit', 'json'] as const) {
    test(`ac21: a list that ${mode === 'reject' ? 'rejects' : mode === 'exit' ? 'exits non-zero' : 'prints invalid JSON'} shows one error line and Retry, no band`, async ($, on) => {
      const w = threeFeatures()
      w.features = [feature('a', 'running', true)]
      w.listFails = mode
      w.isPlaced = false
      world(on, w)
      await start($)
      expect(w.opens).toEqual([{ id: 'features', title: 'Features', columns: 56 }])
      const ui = await $.ui.mount(PANE)
      expect(await rows(ui)).toHaveLength(1)
      expect(await buttons(ui)).toEqual(['retry'])
      const band = await $.ui.mount(BAND)
      expect(await band.find({ type: 'Button' })).toBeUndefined()

      w.listFails = undefined
      await ui.press({ key: 'retry' })
      expect(w.runs.at(-1)!.argv.slice(2)).toEqual(['list', '--json', '--root', ROOT])
      expect((await rows(ui)).some(t => t.startsWith('a '))).toBe(true)
      expect(await buttons(ui)).not.toContain('retry')
    })
  }

  test('ac21: a failed delete toasts the stderr and leaves the list unchanged', async ($, on) => {
    const w = threeFeatures()
    w.deleteStderr = 'cannot delete: locked'
    world(on, w)
    await start($)
    const ui = await $.ui.mount(PANE)
    await ui.press({ key: 'select:search' })
    await ui.press({ key: 'delete' })
    await ui.press({ key: 'delete' })
    expect(w.toasts).toEqual(['cannot delete: locked'])
    expect((await rows(ui)).some(t => t.startsWith('search '))).toBe(true)
  })

  test('ac21: a refresh that fails after a good list hides the band and shows the error', async ($, on) => {
    const w = threeFeatures()
    w.isPlaced = false
    w.features = [feature('a', 'running', true)]
    world(on, w)
    await start($)
    const band = await $.ui.mount(BAND)
    expect(await band.find({ type: 'Button' })).toBeDefined()
    w.listFails = 'exit'
    await endTurn($)
    expect(await band.find({ type: 'Button' })).toBeUndefined()
    const ui = await $.ui.mount(PANE)
    expect(await rows(ui)).toHaveLength(1)
    expect(await buttons(ui)).toEqual(['retry'])
  })

  test('Plan shows only for an approved feature without a plan, and runs explore-plan on its spec', async ($, on) => {
    const w = threeFeatures()
    w.features = [feature('fresh', 'approved'), withPlan(feature('planned', 'approved')), feature('search', 'draft')]
    world(on, w)
    await start($)
    const ui = await $.ui.mount(PANE)
    await ui.press({ key: 'select:planned' })
    expect(await buttons(ui)).not.toContain('plan')
    await ui.press({ key: 'select:search' })
    expect(await buttons(ui)).not.toContain('plan')
    await ui.press({ key: 'select:fresh' })
    expect(await buttons(ui)).toContain('plan')
    await ui.press({ key: 'plan' })
    expect(w.commands).toEqual([
      { command: 'feature-dev:explore-plan', args: '.feature-dev/features/fresh/SPEC-fresh.md' },
    ])
  })

  test('pressing the selected row again collapses its actions', async ($, on) => {
    const w = threeFeatures()
    world(on, w)
    await start($)
    const ui = await $.ui.mount(PANE)
    await ui.press({ key: 'select:search' })
    expect(await buttons(ui)).toContain('dismiss')
    await ui.press({ key: 'select:search' })
    expect(await buttons(ui)).not.toContain('dismiss')
  })
})

describe('plan after approve', () => {
  test('newlyApproved needs draft before, approved after, and no plan', () => {
    const before = [feature('a', 'draft'), feature('b', 'approved'), feature('c', 'draft')]
    expect(newlyApproved(before as never, [feature('a', 'approved')] as never)?.slug).toBe('a')
    expect(newlyApproved(before as never, [feature('b', 'approved')] as never)).toBeUndefined()
    expect(newlyApproved(before as never, [withPlan(feature('c', 'approved'))] as never)).toBeUndefined()
    expect(newlyApproved([] as never, [feature('new', 'approved')] as never)).toBeUndefined()
  })

  test('a turn that approves a draft spec queues explore-plan on it once the turn is over', async ($, on) => {
    const clock = mock.clock(on)
    const w = threeFeatures()
    world(on, w)
    await start($)
    w.features = w.features.map(f => (f.slug === 'search' ? feature('search', 'approved') : f))
    await endTurn($)
    expect(w.commands).toEqual([])
    await clock.advance(1)
    expect(w.commands).toEqual([
      { command: 'feature-dev:explore-plan', args: '.feature-dev/features/search/SPEC-search.md' },
    ])
    expect(w.toasts?.some(t => t.includes('search approved'))).toBe(true)

    // The next turn sees it approved already: nothing is queued again.
    await endTurn($)
    await clock.advance(1)
    expect(w.commands).toHaveLength(1)
  })

  test('the turn explore-plan ran in does not queue a second run', async ($, on) => {
    const clock = mock.clock(on)
    const w = threeFeatures()
    world(on, w)
    await start($)
    await $.command.run({ command: 'feature-dev:explore-plan', args: '.feature-dev/features/search/SPEC-search.md' } as never)
    w.features = w.features.map(f => (f.slug === 'search' ? feature('search', 'approved') : f))
    await endTurn($)
    await clock.advance(1)
    expect(w.commands).toHaveLength(1)
  })

  test('an aborted turn and a subagent turn queue nothing', async ($, on) => {
    const clock = mock.clock(on)
    const w = threeFeatures()
    world(on, w)
    await start($)
    w.features = w.features.map(f => (f.slug === 'search' ? feature('search', 'approved') : f))
    await endTurn($, 'agent-1')
    await endTurn($, undefined, 'aborted')
    await clock.advance(1)
    expect(w.commands).toEqual([])
  })

  test('plan_after_approve false keeps the pane but queues nothing', { options: { plan_after_approve: false } }, async ($, on) => {
    const clock = mock.clock(on)
    const w = threeFeatures()
    world(on, w)
    await start($)
    expect(w.opens).toHaveLength(1)
    w.features = w.features.map(f => (f.slug === 'search' ? feature('search', 'approved') : f))
    await endTurn($)
    await clock.advance(1)
    expect(w.commands).toEqual([])
  })
})
