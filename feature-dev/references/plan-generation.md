# Plan generation rules

Read by the plan generator that `/feature-dev:explore-plan` dispatches, and by
the agent that fixes the plan review's Blocking findings. `<PLUGIN_ROOT>` is the
feature-dev plugin root your prompt gives you; the plan path, feature, branch
and source spec are in your prompt too.

## Step 2: Synthesize and Write Plan

After all agents complete, synthesize the findings and draft the Implementation Order against the Step 2b rules. Run the Step 2c baseline on the draft's commands, then write the plan to [plan path] using the Write tool. If that file already exists, first run `<PLUGIN_ROOT>/scripts/review_server.py snapshot <plan path>`, which copies it to `.feature-dev/features/<slug>/history/PLAN-<slug>.<n>.md` with the next n, `<slug>` being the feature folder the plan lives in. If Bash is unavailable, make the copy by hand at that same path, n one more than the highest already there (1 if none). `/feature-dev:review` diffs against the newest copy; without it nobody can see what changed between plan versions.

The plan MUST follow this template:

````markdown
---
type: implementation-plan
feature: [Feature Name]
slug: [feature-slug]
date: [YYYY-MM-DD]
branch: [current branch]
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

<!-- Plan-only feature (no spec in this repo): add a `## Decisions Log` section
     after Key Decisions for the decisions the spec would have held. -->

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

<!-- Run state lives in feature.json, owned by features.py. Do not write it into
     the plan. -->
````

## Step 2b: Rules for Implementation Order (non-negotiable)

The downstream agents halt on a step that violates these. A plan that fails them is a TODO list, not a plan. Re-read your Implementation Order against this list before writing the file.

1. **`Verify` must be a real, runnable command** — built from the test runner, config, and path conventions the test-explorer reported. `pytest tests/test_booking.py::test_no_active_subjects`, `npm run test:run -- src/composables/useBooking.spec.ts`. Never a description (`run the tests`, `check it works`), never a command you did not confirm the project actually has.
2. **`Accept` is one criterion, testable in isolation.** If stating it needs an "and", split the step. "when contact has no active subjects, `start_booking` returns `NO_SUBJECTS`" — not "add the booking flow". The split applies to new behavior only. A test that merely locks in behavior that already exists (no production change) is a `Pins:` bullet on the step that creates its Test file, never a step of its own — each step costs a runner dispatch, and a pin-only step just passes at RED.
   A step that changes structure but not behavior (refactor, deprecation, removal behind a flag), whose tests are expected to pass on first run, is `Kind: characterization`. Never use it for new behavior: it skips the RED that proves the behavior was missing.
3. **`Impl` and `Test` are file paths, not layers.** Each must also appear in the Files to Modify / Files to Create tables above. If a step's impl spans two unrelated modules, split it.
4. **Non-behavioral steps still need `Verify`.** A migration, a config wiring, or a dependency bump has no test file — write `Test: n/a — <reason>` and give `Verify` a command that proves the step landed (`python manage.py migrate --check`, `npm run typecheck`, `make lint`). These steps route to `plan-step-executor` instead of `tdd-runner`. A `Verify` that proves a removed path, option or name is gone (a docs or cleanup step) greps for **every** one the change retires, taken from this plan's own Exploration Findings and Files tables, not a sample of them: a pattern that misses one passes a step that left it behind.
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

If `.feature-dev/` is not in the project's .gitignore, add it (features, review files and version history).
