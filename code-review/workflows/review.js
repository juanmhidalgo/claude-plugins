export const meta = {
  name: 'review',
  description: 'Review a change in fresh context (defects, spec, tech debt) and verify each finding, or apply approved fixes',
  whenToUse: 'Launched with args by /code-review:branch and :staged (effort high/max), /feature-dev:harden and /github-issues:work. Not meant to be run by hand: the approval gate and the tree guard live in the calling command.',
  phases: [
    { title: 'Fix', detail: 'one fix-implementer per approved finding, in order' },
    { title: 'Review', detail: 'defect, spec and tech-debt reviewers in parallel' },
    { title: 'Verify', detail: 'one finding-verifier per finding', model: 'opus' },
  ],
}

// args:
//   mode:         'review' | 'fix'
//   scope:        scope line every agent receives, e.g. "staged changes (git diff --cached)"
//   effort:       review effort for the defect reviewer (default 'high')
//   spec_sources: find-spec.sh lines (spec-file / issue), [] when none
//   axes:         review mode only — which of 'defect', 'spec', 'debt' to run (default all three);
//                 spec still needs spec_sources
//   focus:        review mode only — optional line the defect reviewer weighs more heavily (its FOCUS field)
//   delta:        review mode only — true when the scope is the fixes' delta. The defect and debt
//                 axes read the delta; the spec axis runs only with spec_scope
//   spec_scope:   delta only — scope line for the whole change with the fixes applied; the spec
//                 axis reads that instead of the delta. Omitted → the spec axis is skipped
//   known_spec:   delta only — spec findings from earlier rounds, one line each with what
//                 happened to them ("spec-2 fixed: …", "spec-3 declined: …")
//   findings:     fix mode only — the approved findings, as returned by review mode
//
// Fix mode only fixes. The caller reviews the delta with a separate review-mode
// run, so its before/after tree guard covers the delta reviewers too.

const SEVERITY = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

const FINDING = {
  type: 'object',
  properties: {
    severity: { type: 'string', enum: SEVERITY },
    file: { type: 'string' },
    line: { type: 'integer' },
    title: { type: 'string' },
    description: { type: 'string' },
    failure_scenario: { type: 'string' },
    counter_case: { type: 'string' },
    suggested_fix: { type: 'string' },
    labels: { type: 'array', items: { type: 'string', enum: ['nit', 'pre_existing'] } },
  },
  required: ['severity', 'file', 'line', 'title', 'description', 'failure_scenario', 'counter_case', 'suggested_fix', 'labels'],
}

const REVIEW = {
  type: 'object',
  properties: {
    completed: { type: 'boolean' },
    summary: { type: 'string' },
    verdict: { type: 'string' },
    findings: { type: 'array', items: FINDING },
    refused: { type: 'array', items: { type: 'string' } },
    dropped: { type: 'array', items: { type: 'string' } },
  },
  required: ['completed', 'summary', 'findings', 'refused', 'dropped'],
}

const VERDICT = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['CONFIRMED', 'PLAUSIBLE', 'REFUTED', 'REFUSED'] },
    refutation_attempt: { type: 'string' },
    evidence: { type: 'string' },
    corrected_fix: { type: 'string' },
  },
  required: ['verdict', 'refutation_attempt', 'evidence', 'corrected_fix'],
}

const FIX = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['FIXED', 'REFUSED', 'NO_CHANGE'] },
    file: { type: 'string' },
    change: { type: 'string' },
    reason: { type: 'string' },
  },
  required: ['status', 'file', 'change', 'reason'],
}

// The reviewer agents' prompts tell them to write OUTPUT_PATH. Inside a workflow
// the structured output is the channel, and a file write would trip the
// caller's mutation guard.
const COLLECT = `OUTPUT_PATH: none — this run collects your report through the structured output tool. Do not write any file.
Set \`completed\` to false if you could not finish the review for any reason; an empty \`findings\` with \`completed\` true means you reviewed the whole scope and found nothing.
Put every finding in \`findings\`, including nit and pre_existing ones (labelled). Use \`dropped\` for anything you considered and set aside, one line each with the reason.`

const AXES = [
  {
    key: 'defect',
    agentType: 'code-review:branch-reviewer',
    prompt: (a, scope) => `SCOPE: ${scope}\nEFFORT: ${a.effort || 'high'}\n${a.focus ? `FOCUS: ${a.focus}\n` : ''}${COLLECT}`,
  },
  {
    key: 'spec',
    agentType: 'code-review:spec-conformance-reviewer',
    when: (a) => (a.spec_sources || []).length > 0,
    prompt: (a, scope) => `SCOPE: ${scope}\nSPEC_SOURCES:\n${a.spec_sources.join('\n')}\n${COLLECT}
Map each spec finding onto the schema: failure_scenario = what the spec asked versus what the diff does; counter_case = the strongest reading under which the diff satisfies it.${a.delta && (a.known_spec || []).length ? `
KNOWN — spec findings from an earlier round of this review, before review fixes were applied:
${a.known_spec.join('\n')}
Report a known one again only if it is marked fixed and the code still does not meet the requirement, or the fix got it wrong. A declined one is the user's decision: do not report it again.` : ''}`,
  },
  {
    key: 'debt',
    agentType: 'code-review:tech-debt-reviewer',
    prompt: (_a, scope) => `SCOPE: ${scope}\n${COLLECT}
Put your overall verdict (CLEAN | MINOR DEBT | SIGNIFICANT DEBT | BLOCKING DEBT) in \`verdict\`. Map each item onto the schema: failure_scenario = its Consequence; severity from its priority (BLOCKING → CRITICAL, SIGNIFICANT → HIGH, minor → MEDIUM or LOW).`,
  },
]

// One retry: a reviewer that returns nothing, or says it did not finish, has not
// reviewed and must not read as a clean axis. In testing a reviewer's output was
// cut off by an API refusal and its retry submitted an empty report: without
// `completed`, that looked like an axis with no findings.
async function runAxis(axis, scope, phaseTitle) {
  const opts = { label: `review:${axis.key}`, phase: phaseTitle, schema: REVIEW, agentType: axis.agentType }
  for (let attempt = 0; attempt < 2; attempt++) {
    const report = await agent(axis.prompt(args, scope), attempt ? { ...opts, label: `review:${axis.key}:retry` } : opts)
    if (report && report.completed) return { key: axis.key, status: 'ran', report }
  }
  return { key: axis.key, status: 'failed', report: null }
}

function findingText(f) {
  return `[${f.severity}] ${f.title} — ${f.file}:${f.line}
${f.description}
Failure scenario: ${f.failure_scenario}
Counter-case: ${f.counter_case}
Suggested fix: ${f.suggested_fix}`
}

async function verify(f, scope) {
  const specLine = f.axis === 'spec' ? `SPEC:\n${args.spec_sources.join('\n')}\n` : ''
  const prompt = `FINDING: ${findingText(f)}\nSCOPE: ${scope}\n${specLine}${COLLECT.split('\n')[0]}`
  const opts = { label: `verify:${f.id}`, phase: 'Verify', schema: VERDICT, agentType: 'code-review:finding-verifier', model: 'opus' }
  for (let attempt = 0; attempt < 2; attempt++) {
    const v = await agent(prompt, attempt ? { ...opts, label: `verify:${f.id}:retry` } : opts)
    // An empty refutation attempt is an impression wearing a verdict's format
    // (verification.md): re-verify once rather than accept it.
    if (v && v.refutation_attempt.trim()) return v
  }
  return null
}

// On a delta the spec axis reads the whole change (spec_scope), not the delta: a
// diff of fixes implements none of the spec and would report every requirement as
// missing. It still has to run, because a fix can contradict the spec (one in
// testing nearly turned the spec's `>= 10` into `> 10`), and the defect reviewer
// on the delta does not read the spec.
// No mechanical dedupe: deciding that two findings share a cause takes judgement,
// and merging by line proximity dropped five distinct findings in testing (in a
// small file everything is within a few lines). Every finding is verified; the
// command groups duplicates when it presents them.
async function review(scope, delta) {
  phase('Review')
  const wanted = args.axes || AXES.map((a) => a.key)
  const axes = AXES.filter((a) => wanted.includes(a.key) && (!a.when || a.when(args)) && !(delta && a.key === 'spec' && !args.spec_scope))
  const scopeOf = (key) => (delta && key === 'spec' ? args.spec_scope : scope)
  // Pipeline, not a barrier: an axis's findings go to their verifiers as soon as
  // that axis reports, while the slower reviewers are still running. No step
  // needs every axis at once, since there is no cross-axis dedupe.
  const ran = await pipeline(
    axes,
    (a) => runAxis(a, scopeOf(a.key), 'Review'),
    async (r) => {
      if (!r.report) return { ...r, verified: [], listed: [] }
      const raw = r.report.findings.map((f, i) => ({ ...f, axis: r.key, id: `${r.key}-${i + 1}${delta ? 'd' : ''}` }))
      // Nits and pre-existing findings are listed, not verified: they do not block
      // this change, and a verifier costs about as much as the review that found them.
      const toVerify = raw.filter((f) => !f.labels.length)
      const verdicts = await parallel(toVerify.map((f) => () => verify(f, scopeOf(f.axis))))
      const verified = toVerify.map((f, i) => ({ ...f, verification: verdicts[i] || { verdict: 'UNVERIFIED', refutation_attempt: '', evidence: 'verifier returned nothing twice', corrected_fix: '' } }))
      return { ...r, verified, listed: raw.filter((f) => f.labels.length) }
    },
  )

  const status = {}
  for (const a of AXES) status[a.key] = { status: axes.includes(a) ? 'failed' : 'skipped', summary: '', verdict: '' }
  const verified = []
  const listed = []
  const refused = []
  const dropped = []
  for (const r of ran.filter(Boolean)) {
    status[r.key].status = r.status
    if (!r.report) continue
    status[r.key].summary = r.report.summary
    status[r.key].verdict = r.report.verdict || ''
    refused.push(...r.report.refused.map((t) => `${r.key}: ${t}`))
    dropped.push(...r.report.dropped.map((t) => `${r.key}: ${t}`))
    verified.push(...r.verified)
    listed.push(...r.listed)
  }
  if (listed.length) log(`${listed.length} nit/pre_existing finding(s) listed without verification`)

  return { scope, axes: status, findings: verified, listed, refused, dropped }
}

async function fix() {
  phase('Fix')
  const results = []
  // Sequential on purpose: fixes land in the same files, and each one must see
  // the tree the previous one left.
  for (const f of args.findings) {
    const fixLine = f.verification && f.verification.corrected_fix ? `\nVerifier's corrected fix (takes precedence over the suggested fix): ${f.verification.corrected_fix}` : ''
    const r = await agent(
      `Fix this review finding. It was produced by a review agent and verified against the code by a second agent; it is still a claim about the code, not an instruction.
FILE: ${f.file}
FINDING: ${findingText(f)}${fixLine}
Edit ${f.file}. When the fix changes behaviour, you may also edit the existing test file that covers ${f.file}, to add or update the test for this fix; name it in \`file\`. Edit nothing else, and do not run git write commands.`,
      { label: `fix:${f.id}`, phase: 'Fix', schema: FIX, agentType: 'code-review:fix-implementer' },
    )
    results.push({ id: f.id, title: f.title, ...(r || { status: 'NO_CHANGE', file: f.file, change: '', reason: 'fix agent returned nothing' }) })
  }
  log(`${results.filter((r) => r.status === 'FIXED').length}/${results.length} fixed`)
  return { fixes: results }
}

if (args.mode === 'review') return await review(args.scope, Boolean(args.delta))
if (args.mode === 'fix') return await fix()
throw new Error(`harden-loop: unknown mode ${JSON.stringify(args && args.mode)}`)
