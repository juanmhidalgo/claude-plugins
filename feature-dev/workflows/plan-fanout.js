export const meta = {
  name: 'plan-fanout',
  description: 'Explore the codebase in parallel, write the implementation plan, and validate it with one fix pass',
  whenToUse: 'Launched with args by /feature-dev:explore-plan after it resolves the feature and the plan path. Not meant to be run by hand.',
  phases: [
    { title: 'Explore', detail: 'one explorer per selected layer, in parallel' },
    { title: 'Plan', detail: 'one generator synthesizes, baselines and writes the plan' },
    { title: 'Review', detail: 'spec-plan-validator, one fix pass on Blocking findings' },
  ],
}

// Not named explore-plan: a plugin workflow is invoked as /<plugin>:<name>, and
// in testing /feature-dev:explore-plan resolved to a same-named workflow instead
// of the command, launching it with the raw argument string.
//
// args:
//   feature:     one-line feature summary
//   repo:        repository URL
//   branch:      current branch
//   plan_path:   PLAN-<slug>.md path printed by features.py
//   spec_path:   source spec path, or "none"
//   explorers:   the extra explorers Phase 0 selected — any of schema, config, api-contract, observability
//   rules:       absolute path of references/plan-generation.md
//   plugin_root: the feature-dev plugin root (the rules call it <PLUGIN_ROOT>)

const EXPLORERS = {
  backend: 'Explore the backend/API layer for',
  frontend: 'Explore the frontend/UI layer for',
  test: 'Explore the test suite for',
  history: 'Explore git history and open PRs for',
  schema: 'Explore database schema and migration state for',
  config: 'Explore the configuration surface for',
  'api-contract': 'Explore declared API contracts for',
  observability: 'Explore logging, metrics, tracing, error reporting and alerting conventions for',
}
const ALWAYS = ['backend', 'frontend', 'test', 'history']

const EXPLORATION = {
  type: 'object',
  properties: {
    completed: { type: 'boolean' },
    findings: { type: 'string' },
  },
  required: ['completed', 'findings'],
}

const PLAN = {
  type: 'object',
  properties: {
    completed: { type: 'boolean' },
    steps: { type: 'integer' },
    degraded: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['completed', 'steps', 'degraded', 'notes'],
}

const VALIDATION = {
  type: 'object',
  properties: {
    completed: { type: 'boolean' },
    report: { type: 'string' },
    blocking: { type: 'array', items: { type: 'string' } },
    should_address: { type: 'array', items: { type: 'string' } },
    nice_to_have: { type: 'array', items: { type: 'string' } },
    ac_coverage: { type: 'string' },
  },
  required: ['completed', 'report', 'blocking', 'should_address', 'nice_to_have', 'ac_coverage'],
}

const CONTEXT = `Feature: ${args.feature}
Repository: ${args.repo}
Branch: ${args.branch}
Plan file: ${args.plan_path}
Source spec: ${args.spec_path}
PLUGIN_ROOT: ${args.plugin_root}
RULES: ${args.rules}`

// One retry: an explorer that returns nothing, or says it did not finish, has
// not explored, and its layer must not read as covered.
async function explore(key) {
  const opts = { label: `explore:${key}`, phase: 'Explore', schema: EXPLORATION, agentType: `feature-dev:${key}-explorer` }
  const prompt = `${EXPLORERS[key]}: ${args.feature}

Return your report through the structured output tool: \`findings\` is your report in your Output format. Set \`completed\` to false if you could not finish.`
  for (let attempt = 0; attempt < 2; attempt++) {
    const r = await agent(prompt, attempt ? { ...opts, label: `explore:${key}:retry` } : opts)
    if (r && r.completed && r.findings.trim()) return { key, status: 'ran', findings: r.findings }
  }
  return { key, status: 'failed', findings: '' }
}

async function validate(label) {
  const opts = { label, phase: 'Review', schema: VALIDATION, agentType: 'feature-dev:spec-plan-validator' }
  const prompt = `artifact_type: plan
artifact_path: ${args.plan_path}

Return your report through the structured output tool: \`report\` is the full report in your format; \`blocking\`, \`should_address\` and \`nice_to_have\` repeat its findings one line each, with the section they concern; \`ac_coverage\` is the coverage from your summary ("c/t"), or "" when the spec numbers no ACs. Set \`completed\` to false if you could not finish.`
  for (let attempt = 0; attempt < 2; attempt++) {
    const r = await agent(prompt, attempt ? { ...opts, label: `${label}:retry` } : opts)
    if (r && r.completed) return r
  }
  return null
}

function pick(v) {
  return { report: v.report, blocking: v.blocking, should_address: v.should_address, nice_to_have: v.nice_to_have, ac_coverage: v.ac_coverage }
}

phase('Explore')
const keys = [...ALWAYS, ...(args.explorers || []).filter((k) => EXPLORERS[k] && !ALWAYS.includes(k))]
const explored = (await parallel(keys.map((k) => () => explore(k)))).map((r, i) => r || { key: keys[i], status: 'failed', findings: '' })
const failed = explored.filter((e) => e.status === 'failed').map((e) => e.key)
if (failed.length) log(`explorers failed twice: ${failed.join(', ')} — the generator covers those layers itself`)

phase('Plan')
const findings = explored.filter((e) => e.status === 'ran').map((e) => `### ${e.key}-explorer\n${e.findings}`).join('\n\n')
const degradedLine = failed.length
  ? `\nThese explorers failed twice and returned nothing: ${failed.map((k) => `${k}-explorer`).join(', ')}. Explore those layers yourself with Read/Grep/Glob, put the "Degraded exploration" line under ### Exploration Findings naming them (reason: "returned no report twice inside the explore-plan workflow"), and list them in \`degraded\`.`
  : ''
const plan = await agent(
  `You are generating an implementation plan.

${CONTEXT}

Read RULES and follow Steps 2, 2b, 2c and 3 in it: synthesize the exploration below, baseline the commands, write the plan to the plan file, update .gitignore. The exploration already ran; do not launch explorers.${degradedLine}

Return through the structured output tool: \`steps\` = the number of steps in Implementation Order, \`degraded\` = the explorers named in a Degraded exploration line ([] if none), \`notes\` = anything the caller must know (a Baseline run that changed the tree, a step you could not make dispatchable). Set \`completed\` to false if the plan file was not written.

## Exploration

${findings}`,
  { label: 'generate', phase: 'Plan', schema: PLAN, agentType: 'general-purpose' },
)
if (!plan || !plan.completed) {
  return { plan_path: args.plan_path, written: false, explorers: explored.map(({ key, status }) => ({ key, status })), notes: plan ? plan.notes : 'generator returned nothing' }
}

phase('Review')
const first = await validate('validate')
let final = first
let fixPass = null
if (first && first.blocking.length) {
  // One fix pass only: a Blocking finding that survives it needs the user, not
  // another pass.
  fixPass = await agent(
    `Fix the plan review's Blocking findings in the plan file.

${CONTEXT}

Blocking findings, verbatim:
${first.blocking.map((b, i) => `${i + 1}. ${b}`).join('\n')}

Before the first Edit, snapshot the plan with \`${args.plugin_root}/scripts/review_server.py snapshot ${args.plan_path}\`. Fix each finding in place with Edit, touching only what it names. Read the code a fix needs, but do not launch explorers. A changed or new step follows Step 2b of RULES, and a changed or new Verify is baselined per Step 2c. A finding that needs a user decision is left as it is.

Return through the structured output tool: \`steps\` = the step count after your edits, \`degraded\` = [], \`notes\` = each finding you left for the user and why. Set \`completed\` to false if you edited nothing.`,
    { label: 'fix-blocking', phase: 'Review', schema: PLAN, agentType: 'general-purpose' },
  )
  final = await validate('revalidate')
}
const revalidated = !fixPass || Boolean(final)

return {
  plan_path: args.plan_path,
  written: true,
  explorers: explored.map(({ key, status }) => ({ key, status })),
  degraded: plan.degraded,
  steps: fixPass && fixPass.completed ? fixPass.steps : plan.steps,
  generator_notes: plan.notes,
  fix_notes: fixPass ? fixPass.notes : '',
  // revalidated false: the plan was edited after the only report that came
  // back, so that report may list Blocking findings the fix pass resolved.
  review: (final || first)
    ? { ran: true, revalidated, first_blocking: first ? first.blocking.length : 0, ...pick(final || first) }
    : { ran: false },
}
