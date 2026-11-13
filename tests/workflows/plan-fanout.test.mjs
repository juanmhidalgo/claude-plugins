import { test, describe } from 'node:test'
import assert from 'node:assert/strict'
import { loadWorkflow, labels, callsFor } from './harness.mjs'

const wf = await loadWorkflow('feature-dev/workflows/plan-fanout.js')

const ARGS = {
  feature: 'Add an export button', repo: 'https://example.com/acme/widgets', branch: 'feat/export',
  plan_path: 'agent-os/plans/PLAN-0007-export.md', spec_path: 'none', explorers: [],
  rules: 'plugins/feature-dev/references/plan-generation.md', plugin_root: 'plugins/feature-dev',
}
const ALWAYS = ['backend', 'frontend', 'test', 'history']

const exploration = (findings = 'found things') => ({ completed: true, findings })
const plan = (over = {}) => ({ completed: true, steps: 4, degraded: [], notes: '', ...over })
const validation = (over = {}) => ({ completed: true, report: 'looks fine', blocking: [], should_address: [], nice_to_have: [], ac_coverage: '3/3', ...over })

// Dispatch on the label: explore:<key>[:retry], generate, validate[:retry], revalidate[:retry], fix-blocking.
function stub({ explore = () => exploration(), generate = () => plan(), validate = () => validation(), fix = () => plan({ steps: 5 }) } = {}) {
  return (prompt, opts) => {
    const [kind, key, retry] = opts.label.split(':')
    if (kind === 'explore') return explore(key, Boolean(retry), prompt, opts)
    if (kind === 'generate') return generate(prompt, opts)
    if (kind === 'validate' || kind === 'revalidate') return validate(kind, key === 'retry', prompt, opts)
    if (kind === 'fix-blocking') return fix(prompt, opts)
    throw new Error(`unexpected label ${opts.label}`)
  }
}

describe('explore', () => {
  test('the four always-on explorers run in parallel, one agent type each', async () => {
    const { calls, phases } = await wf.run(ARGS, stub())
    assert.deepEqual(labels(calls).slice(0, 4), ALWAYS.map((k) => `explore:${k}`))
    assert.deepEqual(calls.slice(0, 4).map((c) => c.opts.agentType), ALWAYS.map((k) => `feature-dev:${k}-explorer`))
    assert.ok(calls.slice(0, 4).every((c) => c.opts.phase === 'Explore'))
    assert.match(calls[0].prompt, /^Explore the backend\/API layer for: Add an export button\n/)
    assert.deepEqual(phases, ['Explore', 'Plan', 'Review'])
  })

  test('extra explorers are added once each; unknown keys and duplicates of the always-on set are ignored', async () => {
    const { result, calls } = await wf.run({ ...ARGS, explorers: ['schema', 'backend', 'bogus', 'observability', 'schema'] }, stub())
    const explored = labels(calls).filter((l) => l.startsWith('explore:'))
    assert.deepEqual(explored, ['explore:backend', 'explore:frontend', 'explore:test', 'explore:history', 'explore:schema', 'explore:observability', 'explore:schema'])
    assert.equal(calls.find((c) => c.opts.label === 'explore:schema').opts.agentType, 'feature-dev:schema-explorer')
    assert.match(calls.find((c) => c.opts.label === 'explore:observability').prompt, /^Explore logging, metrics, tracing, error reporting and alerting conventions for: /)
    assert.deepEqual(result.explorers.map((e) => e.key), [...ALWAYS, 'schema', 'observability', 'schema'])
  })

  test('an explorer with empty findings or completed: false is retried once with a :retry label', async () => {
    const explore = (key, retry) => (key === 'backend' && !retry ? exploration('   ') : key === 'test' && !retry ? { completed: false, findings: 'partial' } : exploration(`${key} report`))
    const { result, calls } = await wf.run(ARGS, stub({ explore }))
    assert.deepEqual(labels(calls).filter((l) => l.startsWith('explore:')), ['explore:backend', 'explore:frontend', 'explore:test', 'explore:history', 'explore:backend:retry', 'explore:test:retry'])
    assert.ok(result.explorers.every((e) => e.status === 'ran'))
  })

  test('an explorer silent twice is failed, its layer is handed to the generator, and the others feed the prompt', async () => {
    const explore = (key) => (key === 'history' ? null : exploration(`${key} report`))
    const { result, calls, logs } = await wf.run(ARGS, stub({ explore }))
    assert.deepEqual(result.explorers, [{ key: 'backend', status: 'ran' }, { key: 'frontend', status: 'ran' }, { key: 'test', status: 'ran' }, { key: 'history', status: 'failed' }])
    assert.ok(logs.includes('explorers failed twice: history — the generator covers those layers itself'))
    const gen = callsFor(calls, 'generate')[0].prompt
    assert.match(gen, /These explorers failed twice and returned nothing: history-explorer\. Explore those layers yourself/)
    assert.match(gen, /## Exploration\n\n### backend-explorer\nbackend report\n\n### frontend-explorer\nfrontend report\n\n### test-explorer\ntest report$/)
    assert.doesNotMatch(gen, /### history-explorer/)
  })

  test('an explorer whose thunk throws is failed too (parallel resolves it to null)', async () => {
    const explore = (key) => { if (key === 'frontend') throw new Error('boom'); return exploration() }
    const { result } = await wf.run(ARGS, stub({ explore }))
    assert.equal(result.explorers.find((e) => e.key === 'frontend').status, 'failed')
    assert.equal(result.written, true)
  })

  test('all explorers fine: no degraded line in the generator prompt', async () => {
    const { calls, logs } = await wf.run(ARGS, stub())
    assert.doesNotMatch(callsFor(calls, 'generate')[0].prompt, /failed twice/)
    assert.equal(logs.length, 0)
  })
})

describe('plan', () => {
  test('the generator gets the context block, the rules pointer and the structured-output contract', async () => {
    const { calls } = await wf.run(ARGS, stub())
    const gen = callsFor(calls, 'generate')[0]
    assert.equal(gen.opts.agentType, 'general-purpose')
    assert.equal(gen.opts.phase, 'Plan')
    assert.match(gen.prompt, /Feature: Add an export button\nRepository: https:\/\/example\.com\/acme\/widgets\nBranch: feat\/export\nPlan file: agent-os\/plans\/PLAN-0007-export\.md\nSource spec: none\nPLUGIN_ROOT: plugins\/feature-dev\nRULES: plugins\/feature-dev\/references\/plan-generation\.md/)
    assert.match(gen.prompt, /The exploration already ran; do not launch explorers\./)
    assert.deepEqual(gen.opts.schema.required, ['completed', 'steps', 'degraded', 'notes'])
  })

  test('generator returning nothing: written false, no review, explorers reported', async () => {
    const { result, calls } = await wf.run(ARGS, stub({ generate: () => null }))
    assert.deepEqual(result, { plan_path: ARGS.plan_path, written: false, explorers: ALWAYS.map((key) => ({ key, status: 'ran' })), notes: 'generator returned nothing' })
    assert.deepEqual(labels(calls).filter((l) => !l.startsWith('explore:')), ['generate'])
  })

  test('generator with completed: false: written false and its notes are passed on', async () => {
    const { result } = await wf.run(ARGS, stub({ generate: () => plan({ completed: false, notes: 'baseline changed the tree' }) }))
    assert.equal(result.written, false)
    assert.equal(result.notes, 'baseline changed the tree')
  })

  test('the generator is not retried', async () => {
    const { calls } = await wf.run(ARGS, stub({ generate: () => null }))
    assert.equal(callsFor(calls, 'generate').length, 1)
  })
})

describe('review', () => {
  test('no Blocking findings: one validation, no fix pass, review reported as revalidated', async () => {
    const { result, calls } = await wf.run(ARGS, stub({ generate: () => plan({ steps: 3, degraded: ['history'], notes: 'n' }) }))
    assert.deepEqual(labels(calls).filter((l) => !l.startsWith('explore:')), ['generate', 'validate'])
    const v = callsFor(calls, 'validate')[0]
    assert.equal(v.opts.agentType, 'feature-dev:spec-plan-validator')
    assert.equal(v.opts.phase, 'Review')
    assert.match(v.prompt, /^artifact_type: plan\nartifact_path: agent-os\/plans\/PLAN-0007-export\.md\nplugin_root: plugins\/feature-dev\n/)
    assert.deepEqual(result, {
      plan_path: ARGS.plan_path, written: true, explorers: ALWAYS.map((key) => ({ key, status: 'ran' })),
      degraded: ['history'], steps: 3, generator_notes: 'n', fix_notes: '',
      review: { ran: true, revalidated: true, first_blocking: 0, report: 'looks fine', blocking: [], should_address: [], nice_to_have: [], ac_coverage: '3/3' },
    })
  })

  test('a validator that returns nothing or completed: false is retried once, then the review is reported as not run', async () => {
    const r1 = await wf.run(ARGS, stub({ validate: () => null }))
    assert.deepEqual(labels(r1.calls).filter((l) => l.startsWith('validate')), ['validate', 'validate:retry'])
    assert.deepEqual(r1.result.review, { ran: false })
    assert.equal(r1.result.written, true)
    assert.equal(callsFor(r1.calls, 'fix-blocking').length, 0)
    const r2 = await wf.run(ARGS, stub({ validate: () => validation({ completed: false }) }))
    assert.deepEqual(r2.result.review, { ran: false })
  })

  test('Blocking findings: one fix pass with the findings verbatim, then a revalidation that becomes the report', async () => {
    const first = validation({ blocking: ['Step 2 has no Verify', 'AC-3 uncovered'], report: 'first' })
    const second = validation({ blocking: [], report: 'second', should_address: ['naming'] })
    const validate = (kind) => (kind === 'validate' ? first : second)
    const { result, calls } = await wf.run(ARGS, stub({ validate, fix: () => plan({ steps: 6, notes: 'left AC-3 for the user' }) }))
    assert.deepEqual(labels(calls).filter((l) => !l.startsWith('explore:')), ['generate', 'validate', 'fix-blocking', 'revalidate'])
    const fix = callsFor(calls, 'fix-blocking')[0]
    assert.equal(fix.opts.agentType, 'general-purpose')
    assert.equal(fix.opts.phase, 'Review')
    assert.match(fix.prompt, /Blocking findings, verbatim:\n1\. Step 2 has no Verify\n2\. AC-3 uncovered\n/)
    assert.match(fix.prompt, /snapshot the plan with `plugins\/feature-dev\/scripts\/review_server\.py snapshot agent-os\/plans\/PLAN-0007-export\.md`/)
    assert.equal(result.steps, 6)
    assert.equal(result.fix_notes, 'left AC-3 for the user')
    assert.deepEqual(result.review, { ran: true, revalidated: true, first_blocking: 2, report: 'second', blocking: [], should_address: ['naming'], nice_to_have: [], ac_coverage: '3/3' })
  })

  test('only one fix pass: Blocking findings that survive the revalidation are reported, not fixed again', async () => {
    const validate = () => validation({ blocking: ['needs a decision'] })
    const { result, calls } = await wf.run(ARGS, stub({ validate }))
    assert.equal(callsFor(calls, 'fix-blocking').length, 1)
    assert.deepEqual(result.review.blocking, ['needs a decision'])
    assert.equal(result.review.revalidated, true)
  })

  test('revalidation silent twice: revalidated false and the first report is kept', async () => {
    const validate = (kind) => (kind === 'validate' ? validation({ blocking: ['B1'], report: 'first' }) : null)
    const { result, calls } = await wf.run(ARGS, stub({ validate }))
    assert.deepEqual(labels(calls).filter((l) => l.startsWith('revalidate')), ['revalidate', 'revalidate:retry'])
    assert.equal(result.review.ran, true)
    assert.equal(result.review.revalidated, false)
    assert.equal(result.review.report, 'first')
    assert.deepEqual(result.review.blocking, ['B1'])
    assert.equal(result.review.first_blocking, 1)
  })

  test('fix pass that returns nothing or edited nothing: steps and notes fall back to the generator', async () => {
    const validate = (kind) => (kind === 'validate' ? validation({ blocking: ['B1'] }) : validation({ blocking: [] }))
    const r1 = await wf.run(ARGS, stub({ validate, fix: () => null }))
    assert.equal(r1.result.steps, 4)
    assert.equal(r1.result.fix_notes, '')
    assert.equal(r1.result.review.revalidated, true)
    const r2 = await wf.run(ARGS, stub({ validate, fix: () => plan({ completed: false, steps: 9, notes: 'needs the user' }) }))
    assert.equal(r2.result.steps, 4)
    assert.equal(r2.result.fix_notes, 'needs the user')
  })

  test('the fix pass is not retried', async () => {
    const validate = (kind) => (kind === 'validate' ? validation({ blocking: ['B1'] }) : validation())
    const { calls } = await wf.run(ARGS, stub({ validate, fix: () => null }))
    assert.equal(callsFor(calls, 'fix-blocking').length, 1)
  })
})

test('meta is extracted from the script', () => {
  assert.equal(wf.meta.name, 'plan-fanout')
  assert.deepEqual(wf.meta.phases.map((p) => p.title), ['Explore', 'Plan', 'Review'])
})
