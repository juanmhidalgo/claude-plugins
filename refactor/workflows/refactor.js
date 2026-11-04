export const meta = {
  name: 'refactor',
  description: 'Gather the context for a refactoring analysis or plan: the codebase explorer and the conflict scout in parallel, as structured data',
  whenToUse: 'Launched with args by /refactor:analyze (mode analyze) and /refactor:plan (mode plan). Not meant to be run by hand: the metrics, the report and the clarifying questions live in the calling command.',
  phases: [
    { title: 'Explore', detail: 'refactor-analyzer (analyze) or refactor-planner (plan) over the target' },
    { title: 'Scout', detail: 'conflict-scout over the targets and symbols: open PRs, branches, local work' },
  ],
}

// args:
//   mode:         'analyze' | 'plan'
//   target:       what the command was given — a file, a directory, or (plan) a topic line
//   targets:      paths for the conflict scout, one per entry. analyze passes [target];
//                 plan passes every file and directory the refactor will touch, including
//                 the consumers a rename would reach. Empty → the scout is skipped and
//                 `summary.verdict` is UNSCANNED
//   symbols:      plan only — names expected to be renamed, moved or deleted ([] when the
//                 refactor renames nothing; analyze always passes none)
//   base:         optional base branch for the scout's freshness check. Omitted → the scout
//                 reads it from origin/HEAD
//   skip_explore: plan only — true when a recent /refactor:analyze already covers the target;
//                 the planner stage is skipped and only the scout runs
//
// Returns { summary, stages, explore, scout }. `summary` comes first so it survives a
// result cut off at the end; `explore` and `scout` are the agents' reports or null.

const REF = { type: 'string', description: 'file:line' }

const COVERED = {
  type: 'object',
  properties: { where: REF, covers: { type: 'string' } },
  required: ['where', 'covers'],
}

// refactor-analyzer: the five sections of its text format, one field each.
const ANALYSIS = {
  type: 'object',
  properties: {
    completed: { type: 'boolean' },
    summary: { type: 'string' },
    similar_code: { type: 'array', items: { type: 'object', properties: { where: REF, description: { type: 'string' } }, required: ['where', 'description'] } },
    abstractions: { type: 'array', items: { type: 'object', properties: { where: { type: 'string' }, provides: { type: 'string' }, reuse: { type: 'string' } }, required: ['where', 'provides', 'reuse'] } },
    tests: {
      type: 'object',
      properties: { covered: { type: 'array', items: COVERED }, untested: { type: 'array', items: { type: 'string' } } },
      required: ['covered', 'untested'],
    },
    consumers: { type: 'array', items: { type: 'object', properties: { where: REF, uses: { type: 'string' } }, required: ['where', 'uses'] } },
    conventions: {
      type: 'object',
      properties: { naming: { type: 'string' }, organization: { type: 'string' }, style: { type: 'string' } },
      required: ['naming', 'organization', 'style'],
    },
    uncertain: { type: 'array', items: { type: 'string' } },
  },
  required: ['completed', 'summary', 'similar_code', 'abstractions', 'tests', 'consumers', 'conventions', 'uncertain'],
}

// refactor-planner: the six sections of its text format, one field each.
const PLAN_CONTEXT = {
  type: 'object',
  properties: {
    completed: { type: 'boolean' },
    summary: { type: 'string' },
    scope: {
      type: 'object',
      properties: { target: { type: 'string' }, complexity: { type: 'string', enum: ['Low', 'Medium', 'High'] }, reason: { type: 'string' } },
      required: ['target', 'complexity', 'reason'],
    },
    coverage: {
      type: 'object',
      properties: { covered: { type: 'array', items: COVERED }, gaps: { type: 'array', items: { type: 'string' } } },
      required: ['covered', 'gaps'],
    },
    dependencies: {
      type: 'object',
      properties: {
        imports: { type: 'array', items: { type: 'string' } },
        imported_by: { type: 'array', items: { type: 'string' } },
        transitive_risk: { type: 'array', items: { type: 'string' } },
      },
      required: ['imports', 'imported_by', 'transitive_risk'],
    },
    past_patterns: { type: 'array', items: { type: 'object', properties: { where: REF, pattern: { type: 'string' } }, required: ['where', 'pattern'] } },
    risks: { type: 'array', items: { type: 'object', properties: { where: REF, why: { type: 'string' } }, required: ['where', 'why'] } },
    suggested_order: { type: 'array', items: { type: 'object', properties: { step: { type: 'string' }, why: { type: 'string' } }, required: ['step', 'why'] } },
    clarifications: { type: 'array', items: { type: 'string' } },
  },
  required: ['completed', 'summary', 'scope', 'coverage', 'dependencies', 'past_patterns', 'risks', 'suggested_order', 'clarifications'],
}

const PR_REF = {
  pr: { type: 'integer' },
  title: { type: 'string' },
  author: { type: 'string' },
}

// conflict-scout: its verdict and the five tables. `gh_available` and `data_gaps`
// carry what the text format puts under the verdict: a scan on missing data is
// never CLEAR, and the caller must be able to see why.
const SCAN = {
  type: 'object',
  properties: {
    completed: { type: 'boolean' },
    verdict: { type: 'string', enum: ['CLEAR', 'CONTESTED', 'BLOCKED'] },
    verdict_reason: { type: 'string' },
    gh_available: { type: 'boolean' },
    data_gaps: { type: 'array', items: { type: 'string' }, description: 'gh unavailable, a truncated PR file list, an inconclusive symbol grep — one line each' },
    base: { type: 'string' },
    textual: {
      type: 'array',
      items: {
        type: 'object',
        properties: { target: { type: 'string' }, ...PR_REF, age: { type: 'string' }, size: { type: 'string' }, state: { type: 'string', enum: ['open', 'draft'] }, overlap: { type: 'string' } },
        required: ['target', 'pr', 'title', 'author', 'age', 'size', 'state', 'overlap'],
      },
    },
    semantic: {
      type: 'array',
      items: {
        type: 'object',
        properties: { symbol: { type: 'string' }, ...PR_REF, calling_file: REF },
        required: ['symbol', 'pr', 'title', 'author', 'calling_file'],
      },
    },
    local: {
      type: 'object',
      properties: {
        uncommitted: { type: 'array', items: { type: 'string' } },
        stashes_worktrees: { type: 'array', items: { type: 'string' } },
        branches: { type: 'array', items: { type: 'object', properties: { branch: { type: 'string' }, paths: { type: 'array', items: { type: 'string' } } }, required: ['branch', 'paths'] } },
      },
      required: ['uncommitted', 'stashes_worktrees', 'branches'],
    },
    freshness: {
      type: 'object',
      properties: { behind: { type: 'integer' }, touching: { type: 'array', items: { type: 'string' } } },
      required: ['behind', 'touching'],
    },
    sequencing: {
      type: 'object',
      properties: {
        do_now: { type: 'array', items: { type: 'string' } },
        do_first: { type: 'array', items: { type: 'string' } },
        defer: { type: 'array', items: { type: 'string' } },
        coordinate: { type: 'array', items: { type: 'string' } },
      },
      required: ['do_now', 'do_first', 'defer', 'coordinate'],
    },
  },
  required: ['completed', 'verdict', 'verdict_reason', 'gh_available', 'data_gaps', 'base', 'textual', 'semantic', 'local', 'freshness', 'sequencing'],
}

// The agents' prompts describe a text block to return. Inside a workflow the
// structured output is the channel: same sections, one field each, no file.
const COLLECT = `OUTPUT_PATH: none — this run collects your report through the structured output tool. Do not write any file.
Fill every field; an empty array means you looked and found nothing. Set \`completed\` to false if you could not finish for any reason.`

const EXPLORE = {
  analyze: {
    agentType: 'refactor:refactor-analyzer',
    schema: ANALYSIS,
    prompt: (a) => `TARGET: ${a.target}
Gather the context for a refactoring analysis of the target:
1. Similar code — other files with similar patterns, for comparison
2. Existing abstractions — utilities, helpers, base classes already in the project
3. Tests — what test coverage exists for this code
4. Consumers — what depends on this code
${COLLECT}
\`summary\` is one line on what the target looks like from outside: how shared, how covered, how conventional. Put a finding you are not sure of in \`uncertain\` as well as in its section.`,
  },
  plan: {
    agentType: 'refactor:refactor-planner',
    schema: PLAN_CONTEXT,
    prompt: (a) => `TARGET: ${a.target}
Gather the context for a safe, ordered refactoring plan of the target:
1. What needs to be refactored and why
2. Current test coverage
3. Dependencies that could break
4. Similar refactorings done in this project
${COLLECT}
\`summary\` is one line on scope and complexity. \`clarifications\` holds what you would need to ask before planning, one question each; empty when the scope is clear.`,
  },
}

function scoutPrompt(a) {
  const symbols = (a.symbols || []).filter(Boolean)
  return `Targets:
${a.targets.map((t) => `- ${t}`).join('\n')}
Symbols: ${symbols.length ? symbols.join(', ') : 'none — nothing is named for renaming yet; skip the semantic scan and leave \`semantic\` empty'}
${a.base ? `Base branch: ${a.base}\n` : ''}${COLLECT}
\`verdict_reason\` is the one sentence after the verdict. \`gh_available\` is false when \`gh\` was missing or unauthenticated, and every reason the scan rests on missing data goes in \`data_gaps\`, one line each. \`base\` is the base branch you compared against.`
}

// One retry: an agent that returns nothing, or says it did not finish, has not
// explored, and a missing scan must not read as a clean one.
async function run(key, prompt, opts) {
  for (let attempt = 0; attempt < 2; attempt++) {
    const report = await agent(prompt, attempt ? { ...opts, label: `${opts.label}:retry` } : opts)
    if (report && report.completed) return { key, status: 'ran', report }
  }
  log(`${key}: no usable report after two attempts`)
  return { key, status: 'failed', report: null }
}

if (!['analyze', 'plan'].includes(args && args.mode)) throw new Error(`refactor: unknown mode ${JSON.stringify(args && args.mode)}`)
if (!args.target) throw new Error('refactor: args.target is required')

const targets = (args.targets || []).filter(Boolean)
const explore = EXPLORE[args.mode]
const skipExplore = args.mode === 'plan' && Boolean(args.skip_explore)
if (skipExplore) log('explore: skipped, a recent analysis covers the target')
if (!targets.length) log('scout: skipped, no targets given — the scan is not a repo-wide PR dump')

// Both agents read the same target and neither needs the other: one barrier,
// since the result wants them together and there is no stage after it.
const tasks = []
if (!skipExplore) tasks.push(() => run('explore', explore.prompt(args), { label: `explore:${args.mode}`, phase: 'Explore', schema: explore.schema, agentType: explore.agentType }))
if (targets.length) tasks.push(() => run('scout', scoutPrompt({ ...args, targets }), { label: 'scout', phase: 'Scout', schema: SCAN, agentType: 'refactor:conflict-scout' }))
const ran = (await parallel(tasks)).filter(Boolean)

const stages = {
  explore: { status: skipExplore ? 'skipped' : 'failed' },
  scout: { status: targets.length ? 'failed' : 'skipped' },
}
let exploreReport = null
let scan = null
for (const r of ran) {
  stages[r.key].status = r.status
  if (r.key === 'explore') exploreReport = r.report
  if (r.key === 'scout') scan = r.report
}

const contested = scan ? scan.textual.length + scan.semantic.length : 0
const summary = {
  mode: args.mode,
  target: args.target,
  // UNSCANNED covers a skipped and a failed scout alike: the caller has no scan
  // and must say so instead of presenting a clean ordering.
  verdict: scan ? scan.verdict : 'UNSCANNED',
  gh_available: scan ? scan.gh_available : false,
  data_gaps: scan ? scan.data_gaps : ['conflict scan did not run'],
  contested,
  explore: stages.explore.status,
  scout: stages.scout.status,
  headline: exploreReport ? exploreReport.summary : '',
}
log(`scout ${summary.verdict} (${contested} overlap(s)), explore ${stages.explore.status}`)

return { summary, stages, explore: exploreReport, scout: scan }
