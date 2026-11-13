---
disable-model-invocation: true
allowed-tools:
  - Bash(git *)
  - Bash(npm *)
  - Bash(npx *)
  - Bash(yarn *)
  - Bash(pnpm *)
  - Bash(pytest *)
  - Bash(python *)
  - Bash(make *)
  - Bash(cargo *)
  - Bash(go *)
  - Bash(gh auth status)
  - Bash(gh repo view --json nameWithOwner*)
  - Bash(gh issue view *)
  - Bash(gh issue comment *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/issue_spec.py *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py snapshot *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/features.py *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/herdr-pane.sh *)
  - Read
  - Write
  - Edit
  - Agent
  - Glob
  - Grep
  - ListAgents
  - SendMessage
skills:
  - tdd-patterns
argument-hint: "[PLAN-*.md or SPEC-*.md path, or feature description — optional; auto-discovers a running or halted feature, then an unplanned one] [--coordinator <session-name>] [--pane|--no-pane]"
description: |
  Use when implementing a new feature or fixing a bug where you want tests to lead, not follow.
  Do NOT use for quick one-line fixes or refactors without behavioral change.
keywords:
  - tdd
  - test-driven
  - feature-development
  - coverage
  - red-green-refactor
triggers:
  - "implement with TDD"
  - "test-driven development"
  - "write tests first"
  - "implement feature with coverage"
---

## Context
- **Repository**: !`git remote get-url origin`
- **Current branch**: !`git branch --show-current`
- **Working tree clean**: !`git status --short`
- **Feature spec**: $ARGUMENTS
- **Arguments**: !`bash "${CLAUDE_PLUGIN_ROOT}/scripts/args.sh" '$ARGUMENTS'`
- **Feature store**: each feature lives in `.feature-dev/features/<slug>/`, managed by `${CLAUDE_PLUGIN_ROOT}/scripts/features.py` (every call below passes `--root <repo root>`). Run progress is recorded there with `step`, never by editing a file. Layout: [artifact-locations.md](../skills/spec-driven-development/references/artifact-locations.md).

## Phase 0: Resolve Spec and Validate

**First, read the flags from the Arguments JSON in Context.** `--coordinator <session-name>` is a flag the parser does not know: when `positional` holds `--coordinator`, the token after it is the session name; remove both. What remains of `positional`, joined with spaces, is the feature spec, and it may be empty, which is the normal auto-discovery path; `$ARGUMENTS` below means that remainder. Record the name. Do not resolve or validate it yet; a coordinator that turns out to be unreachable must not block a run that is otherwise fine. `pane` is the Herdr flag: `true` hands the run off (below), `false` or `null` runs here, and `false` wins when both flags were passed. If the Arguments line is a shell error instead of JSON (an apostrophe in a feature description does that), read the raw **Feature spec** line and strip the flags by hand. Run `${CLAUDE_PLUGIN_ROOT}/scripts/herdr-pane.sh status` once: it prints `inside` or `outside` (Herdr), and the checkpoint line below depends on it.

**`pane: true` hands the run to a fresh session.** The run moves to a sibling Herdr pane in **handoff** mode (`${CLAUDE_PLUGIN_ROOT}/references/herdr-pane.md`) and this session stops: the pane gets a full context budget instead of inheriting this one. Resolve the argument to a `PLAN-*.md` or `SPEC-*.md` path first (step 1 below), then send `/feature-dev:tdd <path> [--coordinator <name>] --no-pane` with agent name `tdd-<slug>`. The step loop's resume re-verifies any steps already done, so handing off mid-run loses nothing. Do not run any step here after the handoff: two runs on one checkout race. Outside Herdr, say so and run here.

1. **Resolve the feature spec:**
   - **If `$ARGUMENTS` is the path of an existing `PLAN-*.md`** → read it and use it exactly as a single auto-discovered plan below (the closing lines of `/feature-dev:explore-plan` and `/feature-dev:plan-review` print this form). Its feature slug is its folder name under `.feature-dev/features/`; refuse any other path (a root `PLAN-*.md`, or the layout older than 2.0.0) in one line and name `.feature-dev/features/<slug>/` as the only place plans live.
   - **If `$ARGUMENTS` is the path of an existing `SPEC-*.md`** → the feature slug is its folder name under `.feature-dev/features/` (refuse any other path the same way). Read its `feature:` frontmatter value and use it as the spec; the spec path is the **source spec**. Then read the feature's entry from `${CLAUDE_PLUGIN_ROOT}/scripts/features.py list --json --root <repo root>`:
     - If its `status` is `implemented`, say so and ask before continuing.
     - If the spec is still `draft`: ask once with AskUserQuestion "This spec is still a draft. Mark it approved and implement it?" (options: approve and continue / stop). **Yes** → run `${CLAUDE_PLUGIN_ROOT}/scripts/features.py approve <slug> --root <repo root>` and continue. **No** → **STOP** and point the user to `/feature-dev:review <spec path>` to approve it first. Never implement from a draft.
     - If the feature already has a PLAN artifact in its entry, use that plan as the **pre-selected plan** (as for a `PLAN-*.md` argument) — a spec with a plan is not a no-plan run.
     - Otherwise there is no plan: skip the plan search in Phase 1 and take the no-plan path. This is the small-feature fallback `/feature-dev:spec` mentions; the spec's ACs (or, in a spec written before 3.0.0, its Tasks) are the reviewed anchor, the decisions go to its Decisions Log, and Phase 6 closes it. Record the run in the feature store before the first step: with the spec `approved`, run `${CLAUDE_PLUGIN_ROOT}/scripts/features.py plan <slug> --steps <number of ACs> --from-spec --root <repo root>` (one step per AC, matching the criteria the step loop derives). A refusal (`refused: …`) names the state and the valid events; report it instead of editing `feature.json`.
   - **If `$ARGUMENTS` is `#N`, `owner/repo#N`, or an issue URL** → resolve it per [issue-store.md's Argument parsing](../skills/spec-driven-development/references/issue-store.md#argument-parsing), then run [issue-store.md's Import algorithm](../skills/spec-driven-development/references/issue-store.md#import-ac-8-ac-9-ac-10-ac-11-ac-12) against it, start to finish. Do not restate Import's steps here — follow the reference; its own step 3 is where a closed issue asks before continuing, the same shape as this command's `implemented` check above. A failed `gh` preflight, or a failed `gh issue view` call, stops here and names the issue that could not be read. On success, continue as if `$ARGUMENTS` had been the resulting `SPEC-<slug>.md` path (the `SPEC-*.md` bullet above applies; when the issue also carries a plan section, Import rebuilt `PLAN-<slug>.md` beside the spec, so the feature has a PLAN artifact and that bullet pre-selects it).
   - **If `$ARGUMENTS` is anything else** → use it as the feature spec. There is no feature in the store, so the run records no state. Continue to step 2.
   - **If `$ARGUMENTS` is empty** → run `${CLAUDE_PLUGIN_ROOT}/scripts/features.py list --json --root <repo root>` (a missing `.feature-dev/features/` is an empty list) and keep the features whose `status` is `planned`, `running` or `halted` and that have a PLAN artifact, plus the `running` or `halted` features with only a SPEC artifact (a run straight from the spec; for these the SPEC path stands in for the plan path below, and the run continues as for a `SPEC-*.md` argument):
     - **0 plans found** → **STOP** and ask the user for a feature description.
     - **1 plan found** → read its PLAN (path from `artifacts`), extract the `feature:` value from the spec when the feature has one (else the plan's title), and use that as the spec. Record the plan path as the **pre-selected plan** for Phase 1. Inform the user: "Auto-selected plan: `<plan path>` (feature: <name>, <status>)".
     - **2+ plans found** → use AskUserQuestion to let the user pick one (label = feature name or slug, description = `<slug> — <status>`). The chosen feature's plan path is the **pre-selected plan** for Phase 1.
2. **Check the working tree.** Use the `Working tree clean` field from the Context section above — it was captured before Phase 0 ran, so an issue import in step 1 (which writes a new, untracked `SPEC-<slug>.md` when no local copy exists) never trips this check on its own output.
   - **Clean** → proceed normally. If the resolved feature is `halted`, still resume (`resume: yes` in Phases 1b–3) after Phase 1: it records the restart, and `step done` is refused until it does.
   - **Dirty** → this may be a halted run, not stray edits. Take the feature's `status` and `plan.completed` from `list --json` (a run with no feature in the store cannot be a resumable run: apply the stop below). If `status` is `running` or `halted` (a halt at step 1 leaves `plan.completed` empty and is still this command's work), the dirty tree is *this command's own* unfinished work → resume (`resume: yes` in Phases 1b–3) after Phase 1.
   - **Dirty with no running or halted feature** → **STOP** and ask the user to commit or stash.

   A feature in `planned` has recorded no step, so a dirty tree there is not this command's work: apply the plain dirty-tree stop.

## Phase 1: Load Plan or Explore Codebase

**First, determine the plan:**

- **If a pre-selected plan was set in Phase 0** → use it directly; skip the search below.
- **If a `SPEC-*.md` argument has no plan** → no plan; go to "If no plan file exists" below. Also load that spec's `## Decisions Log`, if it has one, as binding prior decisions (see "Load prior decisions").
- **Otherwise** (spec came from `$ARGUMENTS` as text), look for plans in `${CLAUDE_PLUGIN_ROOT}/scripts/features.py list --json --root <repo root>` (plans are created by `/feature-dev:explore-plan`). If multiple exist, pick the one whose feature best matches the spec; if none clearly matches, ask the user which to use.

**If a plan file is in use:**
- Read it and use it as the source of truth for files to modify/create, implementation order, and key decisions
- **Drift check**: if the feature has a SPEC artifact in the same folder, compare modification times (`stat -c %Y <spec>` and `stat -c %Y <plan>`, or `git log -1 --format=%ct -- <file>` as a fallback). If the spec is newer than the plan, **warn the user**: "The source spec `<path>` was modified after the plan was generated. The plan may be stale. Proceed with the current plan, or re-run `/feature-dev:explore-plan` first?" and wait for confirmation.
- **Load prior decisions**: if the feature has a spec, read the spec's `## Decisions Log` section (if it has one); for a plan-only feature, read the PLAN's own `## Decisions Log`. Those are decisions taken during earlier runs — in this repo or in a sibling one — and they bind this run. Thread them into the initial carry-over for the step loop and list them back in the Phase 1 summary. A recorded decision is as binding as the plan: do not re-open one on your own judgment, and do not let a runner contradict it. If the PLAN's `Source spec:` line points outside this repo (`../<sibling>/.feature-dev/features/<slug>/SPEC-<slug>.md`), that is the expected multi-repo shape, not an error — read it there.
- **Load the Baseline**: if the plan has a `### Baseline` section, keep its table — the step loop attributes failures against it and gates dispatch on it. If HEAD is no longer the sha it was run on and no precondition step of this plan moved it, say so in the Phase 1 summary: after unexplained HEAD movement the rows are not attributable. (A precondition step that moves HEAD refreshes the rows itself — see Routing.) A plan without the section (pre-1.26.0) keeps the behaviour below unchanged.
- **Coordinator hint**: if the resolved spec has a `repos:` block and no `--coordinator` was passed, add exactly one line to the Phase 1 summary — "Multi-repo spec. If you have a coordinator session open, pass `--coordinator <name>` to route cross-repo questions to it." A line, not a question: do not block on it.

  **Do not call `ListAgents` to find a candidate.** The listing gives name, kind and status — not a working directory — so matching reduces to the session's name, and a coordinator session for a multi-repo feature has no single repo to derive a name from. Name-matching reliably finds the *implementer* sessions (named after their repos) and misses the coordinator (named by hand, precisely because it belongs to no one repo). The user names it or it does not get used.
- Only do a **minimal exploration** with the Agent tool (`subagent_type: "Explore"`) focused on:
  - Test framework and runner command
  - Coverage tool and current thresholds
  - Existing test patterns (naming, structure, fixtures)
- Skip general codebase exploration — the plan already has that context

**If no plan file exists:**
- Use the Agent tool with `subagent_type: "Explore"` to understand:
  1. **Existing patterns**: Test conventions, file structure, naming, frameworks (pytest/vitest/jest/etc.)
  2. **Related code**: Models, services, components, APIs relevant to the feature
  3. **Test infrastructure**: Fixtures, factories, mocks, helpers, config files

Summarize findings before proceeding. Include:
- Test framework and runner command
- Coverage tool and current thresholds (if configured)
- Key files to modify/create
- Existing patterns to follow

## Phases 1b–3: Resume, resolve criteria, execute (the step loop)

Follow `${CLAUDE_PLUGIN_ROOT}/references/step-loop.md` from here to the last step. It holds what used to be inline in this command: the resume re-verification (its section 1, "Phase 1b"), the step contract and the gate-blocked questions (section 2, "Phase 2"), and the gates, routing, loop, halt table, attribution rule and decision recording (section 3, "Phase 3"). Set its inputs as follows:

- **plan**: the plan resolved in Phase 1 (or the spec, for a spec-only run), the feature slug, the repo root; **scripts** = `${CLAUDE_PLUGIN_ROOT}/scripts`. A description-only run has no feature in the store: it records no state, and Phase 6 says so.
- **spec** and **baseline**: as loaded in Phase 1 (prior decisions from the `## Decisions Log`; the Baseline table and whether HEAD is still its sha).
- **gate policy**: `ask`. Gate-blocked steps are put to the user before the first dispatch, one AskUserQuestion per step, at most 4 per call, as the reference describes.
- **resume**: `yes` when Phase 0 detected a halted or running run (the dirty-tree branch, or a `halted` feature on a clean tree); else `no`.
- **after each step**: tell the user one line — `Step N/M — <name>: <outcome>` — in the user's language only; do not repeat it in a second language or recap earlier steps. When the next step opens a new `#### Milestone` heading, add one line naming it; it is not a prompt. Then the checkpoint line below when due. Do **not** commit between steps: the command's contract is one reviewable change set at the end; `/code-review:branch` and `/commit` come after, as Phase 6 tells the user.
- **decisions**: the reference's default (the SPEC's `## Decisions Log`, the PLAN's for a plan-only feature, and the issue comment when the feature has an `issue`), plus **log first, announce second** below when a coordinator is named.
- **cross-repo**: the coordinator routing below when `--coordinator <name>` was passed; otherwise a `halt: cross-repo-question` is handed to the user like any other halt, with the advisor's brief.

**Every halt** the reference returns is recorded with `${CLAUDE_PLUGIN_ROOT}/scripts/features.py step <slug> halt <n> --reason "<one line>" --root <repo root>` (the reference's section 3, item 4 says when the script refuses and what to do) and ends in Phase 6's halt message, with the diagnosis verbatim. Nothing else runs after a halt.

**Checkpoint line.** At each `#### Milestone` boundary, once the finished milestone's last step is recorded, print one line. In a plan without milestones, print it every ~8 completed steps:

```
Progress recorded in <plan path> (steps 1–<N> done). To free context: /clear, then /feature-dev:tdd <plan path>; resume re-verifies the completed steps.
```

When Phase 0's `herdr-pane.sh status` printed `inside`, end the line with: `Or interrupt and run /feature-dev:tdd <plan path> --pane to continue in a fresh pane.`

Then continue with the next step in the same turn. Do not ask, and do not pause for an answer. The line exists because this orchestrator's context only grows: one run went from 98k to 389k tokens. Resume already re-verifies every recorded step (the reference's section 1), so clearing between milestones costs one re-verification pass, not the run.

### Routing a cross-repo question to the coordinator session

**Only if `--coordinator <name>` was passed in Phase 0.** Without it, skip this section entirely — do not go looking for a session to talk to.

1. **Resolve the name once**, on the first halt that needs it. Call `ListAgents` and find the local session whose name matches. If `ListAgents` is unavailable (older Claude Code, or Bedrock/Vertex/Foundry), or no session matches, or several do — say so once, hand the halt to the user as normal, and do not retry on later steps. A coordinator you cannot reach is a downgrade to the normal flow, never a halt of its own.
2. **Send the question, not the run.** One plain-text `SendMessage`: the step number, the question in a sentence, and the `cross-repo-advisor` brief verbatim if one was produced. Set `notify_when_idle: true` so this session hears back when the coordinator finishes. The message must stand alone — a slash command inside it arrives as text and is not executed.
3. **Never send intermediate state.** Not per-step reports, not accumulated carry-over, not green verifications, not progress. The coordinator exists to answer a question; a step-by-step feed is the noise that makes it stop reading the messages that matter. One message per halt that needs one — nothing else, ever.

**Log first, announce second.** A *question* can go out immediately; there is nothing to store yet. A *decision* is written to the `## Decisions Log` **before** it is announced to anyone, and only after the user has accepted it. A decision that reached the coordinator session but not the log is exactly the split-brain the log exists to prevent: the session knows something the spec does not, and the session will not outlive the feature.

## Phase 4: Coverage Check

Each runner gates coverage on the lines it added, within its Verify scope. This phase checks the aggregate and owns the project-wide threshold — a runner cannot see it from one test file.

1. Run the project's coverage tool across the **changed files** from all runners
2. Compare against project thresholds (from config) or 80% minimum. If the project enforces a global threshold, run the Baseline's coverage command too: a drop versus its row is this run's; with no usable row (`not-run: slow`), a global threshold below its configured minimum is unattributable and handled as in the step loop (`references/step-loop.md`, section 3)
3. If below threshold: identify the uncovered paths and dispatch one more `tdd-runner` per meaningful gap, treating each as a new criterion. Do not write the tests inline
4. If no coverage tool is configured, skip with a note
5. **Numeric target → offer `/goal`.** When the spec or plan sets a numeric target this run did not meet (a coverage percentage above the project's threshold, a latency or size budget, a benchmark number), and one more `tdd-runner` per gap did not close it, do not loop on it here. In the Phase 6 report, offer the built-in `/goal` with the condition and the command that measures it, for example `/goal coverage of src/billing/ ≥ 90% as reported by pytest --cov=src/billing`. Claude Code then keeps working across turns until the condition holds. Only the user can start a goal, so offer it; never claim it is running.

## Phase 5: Lint and Format

Run the project's linter and formatter once, across everything the runners touched:

1. Detect tool: `ruff`/`black`/`eslint`/`prettier`/`rustfmt`/`gofmt`
2. Fix any issues — this is mechanical, handle it inline
3. Re-run the full test suite to confirm nothing broke — failures in the Baseline's `pre-existing-fail` rows are not breakage; anything else is. When the suite's row is `not-run: slow`, there is nothing to attribute against: a failure is unattributable, and the step loop's rule applies (`references/step-loop.md`, section 3)

## Phase 6: Report

Output a final summary:

```
## TDD Results

### Feature: [brief description]

### Criteria: [N] total — [N] met, [N] pinned, [N] already satisfied, [N] halted

### Acceptance criteria: [covered]/[total] covered by met steps — uncovered: [AC ids, or None] · halted: [AC ids on halted or never-run steps, or None]

| # | Criterion | Cycles | Outcome |
|---|-----------|--------|---------|
| 1 | [criterion] | 2/5 | met |

### Tests Written: [count] — pins: [n written, n proven falsifiable]
- [test file]: [count] tests ([brief categories])
- Unproven pins: [list, or None]

### Implementation Files Modified: [count]
- [file path] — [what was changed]

### Coverage: [percentage] on changed files (threshold: [threshold])

### Decisions Recorded: [count, or None]
- [decision] — binds: [who] ([recorded in SPEC-<slug>.md | recorded in PLAN decisions log | report only — no feature])

### Unposted decisions: [count, or None]
- [decision text, verbatim]

### Coordinator: [session name — N questions routed | not used | named but unreachable]

### Test Run: ALL PASSING | PASSING except Baseline pre-existing failures: [ids]

### Verified by runner tests only (gate accepted by user): [step numbers, or None]

### Blockers: [verbatim, or None]

### Ready to commit: Yes/No
```

**The Acceptance criteria line** traces the run back to the spec. Take the AC ids from the feature's spec (or the spec passed as the argument). An AC is *covered* when at least one step whose `Covers:` cites it ended `met`, `pinned` or `RED passed early`. It is *halted* when every step citing it halted or never ran. It is *uncovered* when no step cites it. Omit the line when there is no spec with numbered ACs. The line reports; it does not gate. An uncovered AC on an otherwise green run still gets named, because it is the criterion nobody built.

If every criterion was met and the suite is green (apart from failures listed in the Baseline's `pre-existing-fail` rows):
1. **Close the loop in the feature store (if the feature has one):** run `${CLAUDE_PLUGIN_ROOT}/scripts/features.py implemented <slug> --root <repo root>` once the last step is recorded `done`. This prevents auto-discovery from re-surfacing a completed feature on future runs. A refusal (`refused: …`) means a step was not recorded: report it, do not edit `feature.json`.
2. **Keep the `PLAN-*.md`.** It stays in the feature folder next to the spec; `/feature-dev:cleanup` removes finished features.
3. Suggest a commit message following the project's convention.
4. End with the next commands:

   ```
   Next: /feature-dev:harden to review, verify and fix in fresh context, then /ship
   ```

If any criterion halted, do **none** of the above. Leave the plan and spec on disk with the feature recorded as `halted` (`step … halt`), and tell the user verbatim:

> Halted at step `<N>`. Fix the blocker, then run `/feature-dev:tdd <plan path>` (the spec path for a run straight from the spec) — it will re-verify steps 1-`<N-1>` and resume from `<N>`. The dirty working tree is expected; do not stash it.

with the path of the plan this run used. A run with no feature in the store has no plan to resume from; tell the user instead that the steps landed so far are uncommitted in the tree, and that the next step is `/feature-dev:explore-plan <spec path>` against that tree or finishing by hand — re-running `/feature-dev:tdd` on the spec would stop on the dirty tree. (A spec-only run recorded in the store is resumable like any plan: its halt is recorded, so give the plan-resume message above.)

The stash instruction matters: stashing is the one action that makes the recorded progress unrecoverable.
