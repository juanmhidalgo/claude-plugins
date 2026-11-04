import { test, describe } from 'node:test'
import assert from 'node:assert/strict'
import { loadWorkflow, labels, sequence } from './harness.mjs'

const wf = await loadWorkflow('code-review/workflows/triage-comments.js')

const ARGS = { repo: 'acme/widgets', pr: 42, dir: '/scratch/comments' }

const comment = (ref_id, extra = {}) => ({
  ref_id, type: 'review_comment', author: 'copilot', is_bot: true, file: 'src/app.py', line: 10,
  thread_comments: 1, comment_file: `${ARGS.dir}/${ref_id}.json`, ...extra,
})
const fetched = (comments, stats = {}) => ({
  ok: true, error: '',
  stats: { total: comments.length, bots: comments.length, humans: 0, filtered_out: { resolved: 0, outdated: 0 }, ...stats },
  comments,
})
const verdict = (ref_id, over = {}) => ({
  completed: true, ref_id, verdict: 'VALID BUG', priority: 'HIGH', file: 'src/app.py', title: `issue ${ref_id}`,
  reason: 'the guard is missing', refutation: 'tried the happy path: it fails', dismiss_reason: '', refused_text: '', to_verify: '', ...over,
})

// Dispatch on the agent type: the fetcher gets `fetch`, each verifier gets `verify(ref_id, retry)`.
function stub({ fetch, verify = (ref) => verdict(ref) }) {
  return (prompt, opts) => {
    if (opts.agentType === 'code-review:comment-fetcher') return fetch(opts, prompt)
    const m = /^verify:(.+?)(:retry)?$/.exec(opts.label)
    return verify(m[1], Boolean(m[2]), prompt, opts)
  }
}
const fetchOnce = (comments) => sequence(fetched(comments))

describe('fetch', () => {
  test('one fetch, the comments go to one verifier each, labelled by ref_id', async () => {
    const { result, calls, phases } = await wf.run(ARGS, stub({ fetch: fetchOnce([comment('r1'), comment('r2')]) }))
    assert.deepEqual(labels(calls), ['fetch', 'verify:r1', 'verify:r2'])
    assert.equal(calls[0].opts.agentType, 'code-review:comment-fetcher')
    assert.equal(calls[0].opts.phase, 'Fetch')
    assert.equal(calls[1].opts.agentType, 'code-review:comment-verifier')
    assert.equal(calls[1].opts.phase, 'Verify')
    assert.deepEqual(phases, ['Fetch', 'Verify'])
    assert.equal(result.results.length, 2)
    assert.ok(result.results.every((r) => r.verified))
  })

  test('fetch prompt carries repo, PR, dir and the flags', async () => {
    const { calls } = await wf.run({ ...ARGS, bots_only: true, include_resolved: true }, stub({ fetch: fetchOnce([]) }))
    assert.match(calls[0].prompt, /REPO: acme\/widgets\nPR: 42\nDIR: \/scratch\/comments\nFlags: --bots-only --include-resolved/)
    const plain = await wf.run(ARGS, stub({ fetch: fetchOnce([]) }))
    assert.match(plain.calls[0].prompt, /Flags: none$/)
  })

  test('fetch is retried once when comments.length !== stats.total', async () => {
    const short = { ...fetched([comment('r1')]), stats: { ...fetched([]).stats, total: 2 } }
    const full = fetched([comment('r1'), comment('r2')])
    const { result, calls } = await wf.run(ARGS, stub({ fetch: sequence(short, full) }))
    assert.deepEqual(labels(calls).slice(0, 2), ['fetch', 'fetch:retry'])
    assert.equal(result.results.length, 2)
    assert.equal(result.error, undefined)
  })

  test('fetch is retried once when the fetcher reports ok: false or returns nothing', async () => {
    const failed = { ok: false, error: 'gh: 404', stats: null, comments: [] }
    const r1 = await wf.run(ARGS, stub({ fetch: sequence(failed, fetched([comment('r1')])) }))
    assert.deepEqual(labels(r1.calls), ['fetch', 'fetch:retry', 'verify:r1'])
    const r2 = await wf.run(ARGS, stub({ fetch: sequence(null, fetched([comment('r1')])) }))
    assert.deepEqual(labels(r2.calls), ['fetch', 'fetch:retry', 'verify:r1'])
  })

  test('fetch failing twice returns {error, stats: null, counts: {}, results: []} without verifying', async () => {
    const short = { ...fetched([comment('r1')]), stats: { ...fetched([]).stats, total: 3 } }
    const { result, calls, logs } = await wf.run(ARGS, stub({ fetch: sequence(short) }))
    assert.deepEqual(labels(calls), ['fetch', 'fetch:retry'])
    assert.deepEqual(result, { repo: 'acme/widgets', pr: 42, error: 'fetcher returned 1 comments for a total of 3', stats: null, counts: {}, results: [] })
    assert.match(logs[0], /^fetch failed: /)
  })

  test('the error of a failed fetch is the last failure: the fetcher message, or a default when it returned nothing', async () => {
    const failed = { ok: false, error: 'gh: 404', stats: null, comments: [] }
    const r1 = await wf.run(ARGS, stub({ fetch: sequence(null, failed) }))
    assert.equal(r1.result.error, 'gh: 404')
    const r2 = await wf.run(ARGS, stub({ fetch: sequence(null) }))
    assert.equal(r2.result.error, 'fetcher returned nothing')
    const r3 = await wf.run(ARGS, stub({ fetch: sequence({ ok: false, error: '', stats: null, comments: [] }) }))
    assert.equal(r3.result.error, 'gh feedback fetch failed')
  })
})

describe('verify', () => {
  test('verifier prompt names the comment file, the location and the bot author', async () => {
    const { calls } = await wf.run(ARGS, stub({ fetch: fetchOnce([comment('r1'), comment('r2', { file: null, line: null, type: 'issue_comment', is_bot: false, author: 'alice' })]) }))
    const [v1, v2] = calls.slice(1)
    assert.match(v1.prompt, /ref_id: r1\nFile: src\/app\.py:10\nReviewer: @copilot \(bot\)\nCOMMENT_FILE: \/scratch\/comments\/r1\.json/)
    assert.match(v2.prompt, /File: none — a issue_comment, not attached to a line\nReviewer: @alice\n/)
    assert.equal(v1.opts.schema.properties.verdict.enum.length, 4)
  })

  test('a verdict with an empty refutation is re-run once with a :retry label, and the retry is kept', async () => {
    const verify = (ref, retry) => (retry ? verdict(ref, { verdict: 'FALSE POSITIVE', priority: '', dismiss_reason: 'Already handled' }) : verdict(ref, { refutation: '  ' }))
    const { result, calls } = await wf.run(ARGS, stub({ fetch: fetchOnce([comment('r1')]), verify }))
    assert.deepEqual(labels(calls), ['fetch', 'verify:r1', 'verify:r1:retry'])
    assert.equal(calls[2].opts.agentType, 'code-review:comment-verifier')
    assert.equal(result.results[0].verdict, 'FALSE POSITIVE')
    assert.equal(result.results[0].verified, true)
  })

  test('a verifier silent twice becomes NEEDS INVESTIGATION with verified: false, never FALSE POSITIVE', async () => {
    const { result, calls, logs } = await wf.run(ARGS, stub({ fetch: fetchOnce([comment('r1')]), verify: () => verdict('r1', { verdict: 'FALSE POSITIVE', refutation: '' }) }))
    assert.deepEqual(labels(calls), ['fetch', 'verify:r1', 'verify:r1:retry'])
    const r = result.results[0]
    assert.equal(r.verified, false)
    assert.equal(r.verdict, 'NEEDS INVESTIGATION')
    assert.equal(r.reason, 'verifier returned no usable verdict twice')
    assert.equal(r.to_verify, 're-run the verification')
    assert.equal(r.priority, '')
    assert.equal(r.ref_id, 'r1')
    assert.equal(r.comment_file, `${ARGS.dir}/r1.json`)
    assert.ok(logs.some((l) => l === '1 comment(s) not verified — carried as NEEDS INVESTIGATION'))
  })

  test('a verdict with completed: false or a foreign ref_id is not accepted', async () => {
    const r1 = await wf.run(ARGS, stub({ fetch: fetchOnce([comment('r1')]), verify: () => verdict('r1', { completed: false }) }))
    assert.equal(r1.result.results[0].verified, false)
    assert.equal(r1.calls.length, 3)
    const r2 = await wf.run(ARGS, stub({ fetch: fetchOnce([comment('r1')]), verify: () => verdict('r9') }))
    assert.equal(r2.result.results[0].verified, false)
    assert.equal(r2.result.results[0].ref_id, 'r1')
  })

  test('a REFUSED with refused_text is kept without retry; a REFUSED without it is retried', async () => {
    const refused = (ref) => verdict(ref, { verdict: 'REFUSED', priority: '', refutation: '', refused_text: 'ignore previous instructions' })
    const r1 = await wf.run(ARGS, stub({ fetch: fetchOnce([comment('r1')]), verify: refused }))
    assert.deepEqual(labels(r1.calls), ['fetch', 'verify:r1'])
    assert.equal(r1.result.results[0].verdict, 'REFUSED')
    assert.equal(r1.result.results[0].verified, true)
    const r2 = await wf.run(ARGS, stub({ fetch: fetchOnce([comment('r1')]), verify: (ref) => verdict(ref, { verdict: 'REFUSED', refutation: '', refused_text: '' }) }))
    assert.deepEqual(labels(r2.calls), ['fetch', 'verify:r1', 'verify:r1:retry'])
    assert.equal(r2.result.results[0].verdict, 'NEEDS INVESTIGATION')
  })

  test('agent() returning null (agent died) counts as a silent attempt: retried, then NEEDS INVESTIGATION', async () => {
    const { result, calls } = await wf.run(ARGS, stub({ fetch: fetchOnce([comment('r1')]), verify: () => null }))
    assert.deepEqual(labels(calls), ['fetch', 'verify:r1', 'verify:r1:retry'])
    assert.equal(result.results[0].verdict, 'NEEDS INVESTIGATION')
    assert.equal(result.results[0].verified, false)
  })

  test('a verifier whose thunk throws (parallel resolves it to null) becomes NEEDS INVESTIGATION "verifier crashed"', async () => {
    const verify = (ref) => { if (ref === 'r2') throw new Error('boom'); return verdict(ref) }
    const { result } = await wf.run(ARGS, stub({ fetch: fetchOnce([comment('r1'), comment('r2')]), verify }))
    const r2 = result.results.find((r) => r.ref_id === 'r2')
    assert.equal(r2.verified, false)
    assert.equal(r2.verdict, 'NEEDS INVESTIGATION')
    assert.equal(r2.reason, 'verifier crashed')
    assert.equal(result.results.find((r) => r.ref_id === 'r1').verified, true)
  })

  test('verifiers run in parallel: every first attempt is dispatched before any retry', async () => {
    const verify = (ref, retry) => (retry ? verdict(ref) : verdict(ref, { refutation: '' }))
    const { calls } = await wf.run(ARGS, stub({ fetch: fetchOnce([comment('r1'), comment('r2'), comment('r3')]), verify }))
    assert.deepEqual(labels(calls), ['fetch', 'verify:r1', 'verify:r2', 'verify:r3', 'verify:r1:retry', 'verify:r2:retry', 'verify:r3:retry'])
  })
})

describe('result', () => {
  test('results sort REFUSED > VALID BUG by priority > NEEDS INVESTIGATION > FALSE POSITIVE, stable within a bucket', async () => {
    const verdicts = {
      r1: { verdict: 'FALSE POSITIVE', priority: '', dismiss_reason: 'Style' },
      r2: { verdict: 'VALID BUG', priority: 'MEDIUM' },
      r3: { verdict: 'NEEDS INVESTIGATION', priority: '', to_verify: 'run it' },
      r4: { verdict: 'VALID BUG', priority: 'CRITICAL' },
      r5: { verdict: 'REFUSED', priority: '', refutation: '', refused_text: 'quoted' },
      r6: { verdict: 'VALID BUG', priority: 'HIGH' },
      r7: null, // silent twice → NEEDS INVESTIGATION, verified false
    }
    const verify = (ref) => (verdicts[ref] ? verdict(ref, verdicts[ref]) : null)
    const comments = Object.keys(verdicts).map((r) => comment(r))
    const { result } = await wf.run(ARGS, stub({ fetch: fetchOnce(comments), verify }))
    assert.deepEqual(result.results.map((r) => r.ref_id), ['r5', 'r4', 'r6', 'r2', 'r3', 'r7', 'r1'])
    assert.deepEqual(result.counts, { REFUSED: 1, 'VALID BUG': 3, 'NEEDS INVESTIGATION': 2, 'FALSE POSITIVE': 1 })
  })

  test('the result carries repo, pr, the fetcher stats, counts for every verdict and the merged comment+verdict rows', async () => {
    const stats = { total: 1, bots: 1, humans: 0, filtered_out: { resolved: 2, outdated: 1 } }
    const { result, logs } = await wf.run(ARGS, stub({ fetch: sequence(fetched([comment('r1')], stats)) }))
    assert.deepEqual(Object.keys(result), ['repo', 'pr', 'stats', 'counts', 'results'])
    assert.equal(result.repo, 'acme/widgets')
    assert.equal(result.pr, 42)
    assert.deepEqual(result.stats, stats)
    assert.deepEqual(result.counts, { REFUSED: 0, 'VALID BUG': 1, 'NEEDS INVESTIGATION': 0, 'FALSE POSITIVE': 0 })
    const r = result.results[0]
    assert.equal(r.comment_file, `${ARGS.dir}/r1.json`)
    assert.equal(r.author, 'copilot')
    assert.equal(r.title, 'issue r1')
    assert.equal(r.verified, true)
    assert.equal(logs[0], '1 comment(s): 1 bot, 0 human; 2 resolved left out')
  })

  test('no comments: nothing verified, empty results and zero counts', async () => {
    const { result, calls } = await wf.run(ARGS, stub({ fetch: fetchOnce([]) }))
    assert.equal(calls.length, 1)
    assert.deepEqual(result.results, [])
    assert.deepEqual(result.counts, { REFUSED: 0, 'VALID BUG': 0, 'NEEDS INVESTIGATION': 0, 'FALSE POSITIVE': 0 })
  })
})

test('meta is extracted from the script', () => {
  assert.equal(wf.meta.name, 'triage-comments')
  assert.deepEqual(wf.meta.phases.map((p) => p.title), ['Fetch', 'Verify'])
})
