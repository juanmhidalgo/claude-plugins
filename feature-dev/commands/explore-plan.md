---
disable-model-invocation: true
model: opus
allowed-tools:
  - Read
  - Write
  - Agent
  - Glob
  - Bash(gh auth status)
  - Bash(gh repo view --json nameWithOwner*)
  - Bash(gh issue view *)
  - Bash(git branch --show-current)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/issue_spec.py *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py snapshot *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py artifacts *)
argument-hint: "[SPEC-*.md path or feature description — optional; auto-discovers SPEC-*.md if omitted]"
description: |
  Use when starting a feature that touches multiple parts of the codebase and you need a
  structured implementation plan before coding.
  Do NOT use for simple bug fixes or single-file changes.
keywords:
  - exploration
  - planning
  - parallel-agents
  - implementation-plan
  - architecture
triggers:
  - "explore and plan"
  - "plan this feature"
  - "parallel exploration"
  - "implementation plan for"
  - "understand the codebase for"
---

## Context
- **Repository**: !`git remote get-url origin`
- **Current branch**: !`git branch --show-current`
- **Feature**: $ARGUMENTS
- **Artifacts folder**: `${user_config.artifacts_dir}` (a literal `${user_config...}` here means `.feature-dev`). Where specs are found and plans written: [artifact-locations.md](../skills/spec-driven-development/references/artifact-locations.md).

## Phase 0: Resolve Feature and Validate

1. **Resolve the feature:**
   - **If `$ARGUMENTS` is the path of an existing `SPEC-*.md`** → use that spec as if it had been auto-selected below (the closing lines of `/feature-dev:spec` and `/feature-dev:spec-review` print this form).
   - **If `$ARGUMENTS` is `#N`, `owner/repo#N`, or an issue URL** → resolve it per [issue-store.md's Argument parsing](../skills/spec-driven-development/references/issue-store.md#argument-parsing), then run [issue-store.md's Import algorithm](../skills/spec-driven-development/references/issue-store.md#import-ac-8-ac-9-ac-10-ac-11-ac-12) against it, start to finish. Do not restate Import's steps here — follow the reference. A failed `gh` preflight, or a failed `gh issue view` call, stops here and names the issue that could not be read. On success, continue as if `$ARGUMENTS` had been the resulting `SPEC-<slug>.md` path (the reference's own step 6).
   - **If `$ARGUMENTS` is any other text** → use it as the feature description. Record `source_spec: null`.
   - **If `$ARGUMENTS` is empty** → auto-discover spec files. List them with `${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py artifacts --dir "<artifacts folder>" --kind spec` (the folder first, then legacy specs at the root), then read each file's frontmatter and **filter out any spec with `status: implemented`** (those features are already shipped). From the remaining candidates:
     - **0 specs** → **STOP** and ask the user for a feature description.
     - **1 spec** → use it. Read its frontmatter, use `feature:` as the feature description, record the spec path as `source_spec`. Inform the user: "Auto-selected spec: `<spec path>` (feature: <name>, status: <status>)". If `status: draft`, also warn: "This spec is still in draft — the user may not have approved it yet. Proceed anyway?" and wait for confirmation.
     - **2+ specs** → use AskUserQuestion to let the user pick (label = `feature:` value, description = `<filename> — status: <status>`). Use the chosen spec's `feature:` as the feature description and record its path as `source_spec`.
2. Parse the feature into a one-line summary for agent prompts.
3. Generate a plan filename: `PLAN-<slug>.md` (slug = lowercase, hyphenated, max 4 words from the feature name. E.g., `PLAN-scheduled-notifications.md`). If `source_spec` is set, reuse its `slug:` value for consistency. The **plan path** is where that name lives: if `artifacts --kind plan` already lists it, that path (a legacy plan at the root is rewritten in place); otherwise what `${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py artifacts --dir "<artifacts folder>" --new PLAN-<slug>.md` prints (`<folder>/plans/PLAN-<slug>.md`). Every `PLAN-<slug>.md` below means this path.
4. **Select the explorers.** Four always run: `backend-explorer`, `frontend-explorer`, `test-explorer`, `history-explorer`. Add any of the four below whose signal is present in the feature description or, if `source_spec` is set, in the spec body (read it — the frontmatter alone is not enough signal).

   | Explorer | Add when the feature… |
   |---|---|
   | `schema-explorer` | touches persistence: a new/changed model, table, column, index, constraint, or migration; a data backfill; anything with a storage shape |
   | `config-explorer` | introduces or reads a setting, an environment variable, a credential, or a feature flag; behaves differently per environment; needs a rollout toggle |
   | `api-contract-explorer` | is consumed across a repo boundary: `source_spec` frontmatter has 2+ `repos:` entries, or the feature changes a declared contract (OpenAPI, GraphQL SDL, tRPC router, protobuf, JSON Schema) |
   | `observability-explorer` | ships something whose failure is silent: a background job, queue consumer, scheduled task, webhook handler, payment or auth path — anywhere post-ship visibility is how you learn it broke |

   These are cheap (read-only, parallel, `maxTurns: 30`) and the cost of omitting one is planning blind on the highest-risk layer. **When a signal is borderline, include the explorer.** Record the selected list; you pass it into the Phase 1 agent prompt.

   State the selection to the user in one line: "Explorers: backend, frontend, test, history + schema (new model), config (feature flag)."

## Phase 1: Explore and Generate Plan (Forked)

Launch a **single Agent** with `subagent_type: "general-purpose"` to do all exploration and plan generation in an isolated context.

**Do NOT pass `name` to this Agent call.** A named agent is spawned as a *teammate*, and a teammate cannot spawn the explorers in Step 1 — the harness refuses with "Teammates cannot spawn other teammates". The generator is a nested worker, not a roster member; leave it anonymous.

The generator's context is discarded when it finishes — only the plan file persists, which is why the prompt below has it write the file.

Agent prompt — include all of this:

```
You are generating an implementation plan for: [feature summary]

Repository: [repo URL]
Branch: [current branch]
Plan file: [plan path from Phase 0]
Source spec: [source_spec path from Phase 0, or "none"]

## Step 1: Parallel Exploration

Launch every agent below in a SINGLE response so they run concurrently. Do NOT use run_in_background, and do NOT pass `name` to any of them — a named spawn is a teammate, and the harness refuses teammates spawned from here.

Always:

Agent — subagent_type: "feature-dev:backend-explorer"
Prompt: "Explore the backend/API layer for: [feature summary]"

Agent — subagent_type: "feature-dev:frontend-explorer"
Prompt: "Explore the frontend/UI layer for: [feature summary]"

Agent — subagent_type: "feature-dev:test-explorer"
Prompt: "Explore the test suite for: [feature summary]"

Agent — subagent_type: "feature-dev:history-explorer"
Prompt: "Explore git history and open PRs for: [feature summary]"

Additionally, launch each explorer the caller selected in Phase 0 — [selected explorers from Phase 0, or "none"] — in the SAME response as the four above:

Agent (only if selected) — subagent_type: "feature-dev:schema-explorer"
Prompt: "Explore database schema and migration state for: [feature summary]"

Agent (only if selected) — subagent_type: "feature-dev:config-explorer"
Prompt: "Explore the configuration surface for: [feature summary]"

Agent (only if selected) — subagent_type: "feature-dev:api-contract-explorer"
Prompt: "Explore declared API contracts for: [feature summary]"

Agent (only if selected) — subagent_type: "feature-dev:observability-explorer"
Prompt: "Explore logging, metrics, tracing, error reporting and alerting conventions for: [feature summary]"

Do NOT launch an explorer the caller did not select, and do NOT skip one it did.

**If a spawn is refused:** retry that call once with `name` omitted. If it is refused again, do NOT abandon the layer and do NOT pretend it was covered — explore it yourself with Read/Grep/Glob, and make the degradation visible in the plan: put this line immediately under the `### Exploration Findings` heading, listing every explorer that could not run and the refusal verbatim.

> **Degraded exploration** — `<explorer>, <explorer>` could not be spawned (`<refusal message>`). Those sections were written by the generator reading the tree directly: single-reader, no cross-check, and scoped to the files the spec names plus their immediate dependencies.

## Step 2: Synthesize and Write Plan

After all agents complete, synthesize the findings and draft the Implementation Order against the Step 2b rules. Run the Step 2c baseline on the draft's commands, then write the plan to [plan path] using the Write tool. If that file already exists, first run `${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py snapshot <plan path>`, which copies it to `.feature-dev/history/<slug>/PLAN-<slug>.<n>.md` with the next n and the slug sanitized the way `/feature-dev:review` and `/feature-dev:cleanup` read it. If Bash is unavailable, make the copy by hand under the sanitized slug: every run of characters outside `A-Za-z0-9._-` replaced by `-`, leading and trailing `-`/`.` stripped (`artifact` if nothing is left), n one more than the highest already there (1 if none). `/feature-dev:review` diffs against the newest copy; without it nobody can see what changed between plan versions.

The plan MUST follow this template:

---
type: implementation-plan
feature: [Feature Name]
slug: [feature-slug]
date: [YYYY-MM-DD]
branch: [current branch]
source_spec: [source_spec path, or null if none]
run_status: not-started
completed_steps: []
---

## Implementation Plan: [Feature Name]

### Summary
[One paragraph: what this feature does, which layers it touches]

### Exploration Findings

#### Backend
[Key findings from backend-explorer]

#### Frontend
[Key findings from frontend-explorer]

#### Tests
[Key findings from test-explorer]

#### History & Conflicts
[Key findings from history-explorer — flag any potential conflicts]

<!-- One subsection per ADDITIONAL explorer that ran. Omit the heading entirely
     if that explorer was not selected — do not write "N/A". -->

#### Schema & Migrations
[Key findings from schema-explorer: migration tool, domain-touching migrations, current schema, indexes and constraints, pending migrations, naming conventions]

#### Configuration
[Key findings from config-explorer: settings modules, per-environment overrides, feature flags, how credentials are handled]

#### API Contracts
[Key findings from api-contract-explorer: operations in the domain, shared DTOs, versioning, contract testing, codegen, consumer repos]

#### Observability
[Key findings from observability-explorer: logging stack, metrics, tracing, error reporting, alerting, conventions for adding new signals]

### Baseline
Run on `<short sha>` at plan time. /tdd uses this to attribute failures.

| Command | Steps | Result on HEAD | Detail |
|---|---|---|---|
| `[command]` | [step numbers] | [pass / expected-red / pre-existing-fail / hollow / not-run] | [what the output showed; for `not-run`, start with `missing` / `slow` / `writes`] |

### Files to Modify
| File | Change | Layer |
|------|--------|-------|
| [path] | [what to change] | backend/frontend/test |

### Files to Create
| File | Purpose | Layer |
|------|---------|-------|
| [path] | [what it does] | backend/frontend/test |

### Implementation Order

<!-- Each step is ONE bounded, independently verifiable change. This is the unit
     /feature-dev:tdd dispatches to a tdd-runner and feature-implementer dispatches
     to a plan-step-executor. A step without Accept + Verify is not dispatchable.
     Optionally group steps under `#### Milestone N — <name>` headings; numbering
     stays global and continuous across milestones. -->

1. **[Step name]**
   - Kind: [behavior | characterization — optional, default behavior]
   - Accept: [one specific, testable acceptance criterion — observable behavior, not "implement X"]
   - Pins: [optional — existing behaviors this step's test file must also lock in; only on a step whose Test is a path it creates]
   - Covers: [spec AC ids this step makes true, e.g. AC-3, AC-5 — required on behavior and characterization steps when the source spec numbers its ACs (rule 8); may be omitted on non-behavioral steps]
   - Impl: [path to the production file this step changes]
   - Test: [path to the test file that proves it; add `(written by step N)` if an earlier step creates it; or `n/a — <reason>` for non-behavioral steps]
   - Verify: [exact runnable command scoped to this step]
   - Depends on: [step numbers, or `none`]
   - Rationale: [why this step sits here in the order]

2. **[Step name]**
   - ...

### Key Decisions
| Decision | Options | Recommendation | Rationale |
|----------|---------|----------------|-----------|
| [e.g., where to put validation] | [A, B] | [chosen] | [why] |

### Risks
- [Risk 1 — and mitigation]
- [Risk 2 — and mitigation]

### Parallelization Hints
<!-- Informational only. Flag steps from "Implementation Order" that are independent and could be worked on in parallel by humans or by a future executor. Do NOT include executable subagent prompts here — TDD requires sequential discipline, and concurrent edits to overlapping files will collide. -->
- Steps [X] and [Y]: independent — touch different files / different layers, no shared state
- Step [Z]: must complete before step [W] — [dependency reason]
- (If nothing to parallelize, write exactly: "All steps are sequentially dependent — no parallelization opportunities.")

### Estimated Test Cases
- [Category]: [count] tests ([brief description])

<!-- run_status and completed_steps are owned by /feature-dev:tdd, which updates
     them as it dispatches steps. Write them exactly as shown above; do not
     populate them. -->

## Step 2b: Rules for Implementation Order (non-negotiable)

The downstream agents halt on a step that violates these. A plan that fails them is a TODO list, not a plan. Re-read your Implementation Order against this list before writing the file.

1. **`Verify` must be a real, runnable command** — built from the test runner, config, and path conventions the test-explorer reported. `pytest tests/test_booking.py::test_no_active_subjects`, `npm run test:run -- src/composables/useBooking.spec.ts`. Never a description (`run the tests`, `check it works`), never a command you did not confirm the project actually has.
2. **`Accept` is one criterion, testable in isolation.** If stating it needs an "and", split the step. "when contact has no active subjects, `start_booking` returns `NO_SUBJECTS`" — not "add the booking flow". The split applies to new behavior only. A test that merely locks in behavior that already exists (no production change) is a `Pins:` bullet on the step that creates its Test file, never a step of its own — each step costs a runner dispatch, and a pin-only step just passes at RED.
   A step that changes structure but not behavior (refactor, deprecation, removal behind a flag), whose tests are expected to pass on first run, is `Kind: characterization`. Never use it for new behavior: it skips the RED that proves the behavior was missing.
3. **`Impl` and `Test` are file paths, not layers.** Each must also appear in the Files to Modify / Files to Create tables above. If a step's impl spans two unrelated modules, split it.
4. **Non-behavioral steps still need `Verify`.** A migration, a config wiring, or a dependency bump has no test file — write `Test: n/a — <reason>` and give `Verify` a command that proves the step landed (`python manage.py migrate --check`, `npm run typecheck`, `make lint`). These steps route to `plan-step-executor` instead of `tdd-runner`.
5. **Order by dependency, not by layer.** A step consuming a symbol another step introduces comes after it, and names it in `Depends on`.
6. **Say who writes the test.** When one step writes a test file and a later step makes it pass, the later step's `Test:` must carry `(written by step N)`. Without that marker the executor cannot tell "write this test" from "make this existing test pass", and will try to write a test that already exists. A step whose `Test:` and `Impl:` are BOTH `n/a` is an environment precondition (rebase, migration check, dependency install) — legitimate, but it still needs a `Verify` command.
7. **Re-examine a plan over ~20 steps before writing it.** Fold pin-only steps into `Pins:` and structure-only steps into `Kind: characterization`; above 25 the plan review flags it. What remains large can be grouped under `#### Milestone N — <name>` headings. Milestones are for reading; they add no gate.
8. **Trace every acceptance criterion.** When the source spec numbers its ACs (`**AC-1**`…), every behavior and characterization step carries `Covers:` with the ids it makes true, and every AC is covered by at least one step. Steps with `Test: n/a` may omit it. Before writing, list the spec's AC ids and check each against the steps. An AC that no step covers gets a step, or a line in Risks that names its id and says why this plan leaves it out; the plan review accepts only that form. ACs were lost between spec and plan before: one was made unreachable by the code, and a docs step was dispatched only because the user asked for it.

## Step 2c: Baseline — run every gate once on HEAD

/feature-dev:tdd attributes each step's failures against this table. Without it, a command that was already red on HEAD halts the run mid-way and waits on the user; a gate that checks nothing passes a step that was never verified.

1. **Collect the distinct commands**: every step's `Verify`, plus any suite, lint, or migration gate a step names, plus the full-suite, lint and coverage commands /tdd's Phases 4–5 will run — those phases attribute against this table too. Run each exactly once on the current HEAD (`git rev-parse --short HEAD` for the sha), with a timeout (`timeout 300 <command>`).
2. **Classify each from its own output**, using exactly one of:
   - `pass`
   - `expected-red` — fails, or is empty, only because the plan has not run yet: the test file or symbol does not exist, or the selector matches a test this plan writes (`go test -run TestNew` reporting "no tests to run", a `--passWithNoTests` run over a file not yet created). Detail names the step that creates it.
   - `pre-existing-fail` — fails for reasons outside this plan. Detail lists the failing test ids; for a count-only gate (lint), the total count plus the per-file count for each file this plan touches (a touched file with no findings is omitted — /tdd reads an absent file as 0). /tdd matches on exactly these.
   - `hollow` — succeeds but its output shows it exercised nothing, and it would still exercise nothing after the plan runs (0 apps loaded without an env var, a target no step writes to).
   - `not-run` — could not run. Detail starts with the reason, one of: `missing` (a tool, service or env var is absent — the command cannot work as written), `slow` (would take over ~5 min — typically the full suite and coverage), or `writes` (would mutate state: files, migrations, a non-test database). /tdd gates only on `missing`; `slow` and `writes` rows dispatch normally and are verified at run time.
3. **Record only what the output shows.** A `hollow` comes from the output, never from suspicion; "probably pre-existing" is not a Detail.
4. **Mutate nothing.** Never install, start, or restart anything to make a command runnable, and never run one that writes to the tree — mark it `not-run` (`writes`). Compare `git status --short` before and after; if a run changed the tree anyway, say so in its Detail and in Risks rather than reverting it yourself.
5. **Leave gate-blocking rows standing** (`hollow`, and `not-run` for `missing`). If a different command you confirmed on HEAD is a real gate for the same step, use it as the `Verify` and baseline that one instead; otherwise keep the row as it is — /tdd asks the user about every such step before its first dispatch.

## Step 3: Update .gitignore

If `.feature-dev/` is not in the project's .gitignore, add it (review files, version history, and the default plans folder). If the artifacts folder is not under `.feature-dev/`, add that folder too.
```

## Phase 2: Plan Review (automatic)

The plan is validated before the user sees it. When plan review was a separate, optional command it ran in 2 of 6 features, and in one of those the user carried the result over by pasting a review run in another session.

1. Spawn `feature-dev:spec-plan-validator` with `artifact_type: plan` and `artifact_path: PLAN-<slug>.md`. Leave `name` unset, for the same reason as the generator: it is a nested worker, and its fresh context is what makes it a review rather than the generator re-reading its own work.
2. **If it returns Blocking findings**, re-dispatch the generator once: a new anonymous `general-purpose` Agent (no `name`) whose prompt gives the plan path, the Blocking findings verbatim, and these instructions — fix each finding in place with Edit, touching only what the finding names; read the code a fix needs, but do not re-run the explorers; a changed or new step still follows Step 2b and a changed or new `Verify` is baselined per Step 2c (include both sections of the Phase 1 prompt verbatim in this prompt); a finding that cannot be fixed without a user decision is left as it is and named in the reply; before the first Edit, snapshot the plan with `${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py snapshot PLAN-<slug>.md` as Step 2 does. Then spawn the validator again on the edited plan. There is no second re-dispatch: a Blocking finding that survives one fix needs the user, not another pass.
3. **Should Address and Nice to Have findings** are not re-dispatched; they go into the brief.

Keep the final validator report for Phase 3. Do not print it in full.

## Phase 3: Review Brief

Read `PLAN-<slug>.md` from disk and end with a review brief instead of re-printing the plan. Users approve from the chat; a plan printed in full gets approved unread, while a short numbered list gets answered item by item. Give the full plan only on request.

1. **If the plan carries a `Degraded exploration` line, lead with it** — say which layers had no explorer and that those findings had a single reader. A plan the user reviews as if eight agents cross-checked it, when one did not, is the failure mode worth a sentence at the top.
2. Then the brief: at most ~15 lines, numbering continuous across groups so the user can answer "2: no, 5: ok", empty groups omitted.

```markdown
### Review brief — PLAN-<slug>.md (<N> lines, <T> steps)
**Plan review** — <B> Blocking left (<F> fixed in one pass), <S> Should Address · AC coverage <c>/<t>
1. Blocking: <finding, section>
2. <Should Address finding, section>
- Nice to Have: <n> — <short list, one line>
**Decided** (review if you disagree)
3. <a Key Decision and its recommendation, one line>
**Assumed — confirm**
4. <an assumption a step relies on that exploration did not settle; a `pre-existing-fail` Baseline row /tdd will treat as baseline>
**Unverified claims about the code**
5. Step 9 `make run-api` — Baseline `not-run`: missing — pipenv not installed
**Out of scope**
- <what the plan deliberately leaves out>
Reply with the numbers you want changed, or "approved".
Or review it in the browser: /feature-dev:review <plan path>
```

The **Plan review** group leads because a remaining Blocking finding is the one thing that stalls /tdd. Blocking findings come first, then Should Address. A finding that restates a Baseline row already listed under Unverified is not repeated. When the validator found nothing, the group is one line: `**Plan review** — clean`. `AC coverage` is copied from the validator's summary; leave it out when the source spec has no numbered ACs. An uncovered AC is one of the Should Address findings in the group.

Every Baseline row that gates a step — `hollow`, or `not-run` for `missing` — goes under **Unverified**, with a note that /tdd will ask about it before its first dispatch (fix the environment, give a replacement `Verify`, or accept the step as unverifiable by its gate). `not-run` for `slow` or `writes` goes there too, without the note: it does not gate, but nothing checked it on HEAD.

3. End with the next commands, using the plan path from Phase 0, then stop:

   ```
   Next: answer the brief, then /clear and /feature-dev:tdd <plan path>   (a fresh context leaves /tdd's budget to the steps)
   /feature-dev:plan-review <plan path> only if you edit the plan by hand
   ```
