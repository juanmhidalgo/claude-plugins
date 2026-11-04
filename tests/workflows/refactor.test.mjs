import { test, describe } from 'node:test'
import assert from 'node:assert/strict'
import { loadWorkflow, labels, callsFor, sequence } from './harness.mjs'

const wf = await loadWorkflow('refactor/workflows/refactor.js')

const ANALYZE = { mode: 'analyze', target: 'src/service.py', targets: ['src/service.py'] }
const PLAN = { mode: 'plan', target: 'split the service module', targets: ['src/service.py', 'src/api/'], symbols: ['ServiceClient', 'build_payload'] }

const analysis = (over = {}) => ({
  completed: true, summary: 'shared, well covered', similar_code: [], abstractions: [], tests: { covered: [], untested: [] },
  consumers: [], conventions: { naming: 'snake', organization: 'by layer', style: 'ruff' }, uncertain: [], ...over,
})
const planContext = (over = {}) => ({
  completed: true, summary: 'medium scope', scope: { target: 'src/service.py', complexity: 'Medium', reason: 'two consumers' },
  coverage: { covered: [], gaps: [] }, dependencies: { imports: [], imported_by: [], transitive_risk: [] },
  past_patterns: [], risks: [], suggested_order: [], clarifications: [], ...over,
})
const scan = (over = {}) => ({
  completed: true, verdict: 'CLEAR', verdict_reason: 'nothing open touches the target', gh_available: true, data_gaps: [], base: 'master',
  textual: [], semantic: [], local: { uncommitted: [], stashes_worktrees: [], branches: [] }, freshness: { behind: 0, touching: [] },
  sequencing: { do_now: [], do_first: [], defer: [], coordinate: [] }, ...over,
})
const textual = (pr) => ({ target: 'src/service.py', pr, title: 't', author: 'alice', age: '2d', size: 'S', state: 'open', overlap: 'same lines' })
const semantic = (pr) => ({ symbol: 'ServiceClient', pr, title: 't', author: 'bob', calling_file: 'src/api/views.py:7' })

// Dispatch on the label: explore:<mode>[:retry] and scout[:retry]. Each handler gets (retry, prompt, opts).
function stub({ explore = () => analysis(), scout = () => scan() } = {}) {
  return (prompt, opts) => {
    const m = /^(explore:(?:analyze|plan)|scout)(:retry)?$/.exec(opts.label)
    if (!m) throw new Error(`unexpected label ${opts.label}`)
    return (m[1] === 'scout' ? scout : explore)(Boolean(m[2]), prompt, opts)
  }
}

describe('mode selection', () => {
  test('analyze runs the refactor-analyzer and the scout, in one barrier', async () => {
    const { result, calls, phases } = await wf.run(ANALYZE, stub())
    assert.deepEqual(labels(calls), ['explore:analyze', 'scout'])
    assert.equal(calls[0].opts.agentType, 'refactor:refactor-analyzer')
    assert.equal(calls[0].opts.phase, 'Explore')
    assert.ok(calls[0].opts.schema.required.includes('uncertain'))
    assert.match(calls[0].prompt, /^TARGET: src\/service\.py\nGather the context for a refactoring analysis of the target:\n1\. Similar code/)
    assert.match(calls[0].prompt, /OUTPUT_PATH: none — this run collects your report through the structured output tool/)
    assert.equal(calls[1].opts.agentType, 'refactor:conflict-scout')
    assert.equal(calls[1].opts.phase, 'Scout')
    assert.deepEqual(calls[1].opts.schema.properties.verdict.enum, ['CLEAR', 'CONTESTED', 'BLOCKED'])
    assert.deepEqual(phases, [])
    assert.deepEqual(result.stages, { explore: { status: 'ran' }, scout: { status: 'ran' } })
  })

  test('plan runs the refactor-planner with the plan prompt and schema', async () => {
    const { calls } = await wf.run(PLAN, stub({ explore: () => planContext() }))
    assert.deepEqual(labels(calls), ['explore:plan', 'scout'])
    assert.equal(calls[0].opts.agentType, 'refactor:refactor-planner')
    assert.ok(calls[0].opts.schema.required.includes('clarifications'))
    assert.match(calls[0].prompt, /^TARGET: split the service module\nGather the context for a safe, ordered refactoring plan of the target:\n1\. What needs to be refactored/)
  })

  test('an unknown mode or a missing target throws before any agent runs', async () => {
    await assert.rejects(wf.run({ mode: 'audit', target: 'x' }, stub()), /refactor: unknown mode "audit"/)
    await assert.rejects(wf.run({}, stub()), /refactor: unknown mode undefined/)
    await assert.rejects(wf.run(null, stub()), /refactor: unknown mode/)
    await assert.rejects(wf.run({ mode: 'analyze' }, stub()), /refactor: args\.target is required/)
  })
})

describe('skipping', () => {
  test('empty targets: the scout is skipped and the summary says UNSCANNED with a data gap', async () => {
    const { result, calls, logs } = await wf.run({ ...ANALYZE, targets: [] }, stub())
    assert.deepEqual(labels(calls), ['explore:analyze'])
    assert.equal(result.stages.scout.status, 'skipped')
    assert.equal(result.scout, null)
    assert.equal(result.summary.verdict, 'UNSCANNED')
    assert.equal(result.summary.gh_available, false)
    assert.deepEqual(result.summary.data_gaps, ['conflict scan did not run'])
    assert.equal(result.summary.contested, 0)
    assert.equal(result.summary.scout, 'skipped')
    assert.ok(logs.includes('scout: skipped, no targets given — the scan is not a repo-wide PR dump'))
  })

  test('targets made of empty entries count as no targets', async () => {
    const r1 = await wf.run({ ...ANALYZE, targets: ['', null] }, stub())
    assert.deepEqual(labels(r1.calls), ['explore:analyze'])
    const r2 = await wf.run({ ...ANALYZE, targets: undefined }, stub())
    assert.deepEqual(labels(r2.calls), ['explore:analyze'])
  })

  test('skip_explore in plan mode: only the scout runs and the explore stage is skipped', async () => {
    const { result, calls, logs } = await wf.run({ ...PLAN, skip_explore: true }, stub())
    assert.deepEqual(labels(calls), ['scout'])
    assert.deepEqual(result.stages, { explore: { status: 'skipped' }, scout: { status: 'ran' } })
    assert.equal(result.explore, null)
    assert.equal(result.summary.explore, 'skipped')
    assert.equal(result.summary.headline, '')
    assert.equal(result.summary.verdict, 'CLEAR')
    assert.ok(logs.includes('explore: skipped, a recent analysis covers the target'))
  })

  test('skip_explore is ignored in analyze mode', async () => {
    const { calls } = await wf.run({ ...ANALYZE, skip_explore: true }, stub())
    assert.deepEqual(labels(calls), ['explore:analyze', 'scout'])
  })

  test('skip_explore with no targets runs nothing and reports both stages skipped', async () => {
    const { result, calls } = await wf.run({ ...PLAN, targets: [], skip_explore: true }, stub())
    assert.equal(calls.length, 0)
    assert.deepEqual(result.stages, { explore: { status: 'skipped' }, scout: { status: 'skipped' } })
    assert.equal(result.summary.verdict, 'UNSCANNED')
  })
})

describe('retry and failure', () => {
  test('each stage is retried once with a :retry label when it returns nothing', async () => {
    const { result, calls } = await wf.run(ANALYZE, stub({ explore: sequence(null, analysis()), scout: sequence(null, scan()) }))
    assert.deepEqual(labels(calls), ['explore:analyze', 'scout', 'explore:analyze:retry', 'scout:retry'])
    assert.deepEqual(result.stages, { explore: { status: 'ran' }, scout: { status: 'ran' } })
    assert.equal(calls[2].opts.agentType, 'refactor:refactor-analyzer')
    assert.equal(calls[3].opts.agentType, 'refactor:conflict-scout')
  })

  test('completed: false is retried like a missing report', async () => {
    const { calls } = await wf.run(ANALYZE, stub({ explore: sequence(analysis({ completed: false }), analysis()), scout: sequence(scan({ completed: false }), scan()) }))
    assert.deepEqual(labels(calls), ['explore:analyze', 'scout', 'explore:analyze:retry', 'scout:retry'])
  })

  test('a scout that fails twice reports failed with a null scan, and the verdict is UNSCANNED, never CLEAR', async () => {
    const { result, calls, logs } = await wf.run(ANALYZE, stub({ scout: () => null }))
    assert.deepEqual(labels(calls).filter((l) => l.startsWith('scout')), ['scout', 'scout:retry'])
    assert.equal(result.stages.scout.status, 'failed')
    assert.equal(result.scout, null)
    assert.equal(result.summary.verdict, 'UNSCANNED')
    assert.equal(result.summary.gh_available, false)
    assert.deepEqual(result.summary.data_gaps, ['conflict scan did not run'])
    assert.equal(result.summary.scout, 'failed')
    assert.ok(logs.includes('scout: no usable report after two attempts'))
    assert.ok(logs.includes('scout UNSCANNED (0 overlap(s)), explore ran'))
  })

  test('an explorer that fails twice reports failed with a null report and an empty headline', async () => {
    const { result } = await wf.run(PLAN, stub({ explore: () => planContext({ completed: false }) }))
    assert.equal(result.stages.explore.status, 'failed')
    assert.equal(result.explore, null)
    assert.equal(result.summary.explore, 'failed')
    assert.equal(result.summary.headline, '')
    assert.equal(result.summary.verdict, 'CLEAR')
  })

  test('a stage whose thunk throws is failed (parallel resolves it to null)', async () => {
    const { result } = await wf.run(ANALYZE, stub({ explore: () => { throw new Error('boom') } }))
    assert.deepEqual(result.stages, { explore: { status: 'failed' }, scout: { status: 'ran' } })
    assert.equal(result.explore, null)
  })
})

describe('result', () => {
  test('summary comes first and carries mode, target, verdict, gh_available, data_gaps, contested, stage statuses and the headline', async () => {
    const report = scan({ verdict: 'CONTESTED', verdict_reason: 'two PRs', gh_available: true, data_gaps: ['PR 12 file list truncated'], textual: [textual(12), textual(13)], semantic: [semantic(14)] })
    const { result, logs } = await wf.run(ANALYZE, stub({ scout: () => report }))
    assert.deepEqual(Object.keys(result), ['summary', 'stages', 'explore', 'scout'])
    assert.deepEqual(result.summary, {
      mode: 'analyze', target: 'src/service.py', verdict: 'CONTESTED', gh_available: true, data_gaps: ['PR 12 file list truncated'],
      contested: 3, explore: 'ran', scout: 'ran', headline: 'shared, well covered',
    })
    assert.equal(result.scout, report)
    assert.equal(result.explore.summary, 'shared, well covered')
    assert.ok(logs.includes('scout CONTESTED (3 overlap(s)), explore ran'))
  })

  test('a scan without gh is passed through as is: gh_available false and its data gaps', async () => {
    const { result } = await wf.run(ANALYZE, stub({ scout: () => scan({ verdict: 'BLOCKED', gh_available: false, data_gaps: ['gh unauthenticated'] }) }))
    assert.equal(result.summary.verdict, 'BLOCKED')
    assert.equal(result.summary.gh_available, false)
    assert.deepEqual(result.summary.data_gaps, ['gh unauthenticated'])
  })
})

describe('scout prompt', () => {
  test('lists the targets, joins the symbols and names the base branch when given', async () => {
    const { calls } = await wf.run({ ...PLAN, base: 'develop' }, stub({ explore: () => planContext() }))
    const p = callsFor(calls, 'scout')[0].prompt
    assert.match(p, /^Targets:\n- src\/service\.py\n- src\/api\/\nSymbols: ServiceClient, build_payload\nBase branch: develop\nOUTPUT_PATH: none/)
    assert.match(p, /`base` is the base branch you compared against\.$/)
  })

  test('without symbols the semantic scan is waived; without base no base line appears; empty entries are dropped', async () => {
    const { calls } = await wf.run({ ...ANALYZE, targets: ['src/service.py', ''], symbols: ['', null] }, stub())
    const p = callsFor(calls, 'scout')[0].prompt
    assert.match(p, /^Targets:\n- src\/service\.py\nSymbols: none — nothing is named for renaming yet; skip the semantic scan and leave `semantic` empty\nOUTPUT_PATH: none/)
    assert.doesNotMatch(p, /Base branch:/)
    const plain = await wf.run(ANALYZE, stub())
    assert.match(callsFor(plain.calls, 'scout')[0].prompt, /Symbols: none — /)
  })
})

test('meta is extracted from the script', () => {
  assert.equal(wf.meta.name, 'refactor')
  assert.deepEqual(wf.meta.phases.map((p) => p.title), ['Explore', 'Scout'])
})
