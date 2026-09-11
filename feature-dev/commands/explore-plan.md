---
disable-model-invocation: true
model: opus
allowed-tools:
  - Read
  - Agent
  - Glob
argument-hint: "[feature description — optional; auto-discovers SPEC-*.md if omitted]"
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
hooks:
  - event: Stop
    once: true
    command: |
      echo "Exploration complete."
      echo "  - /feature-dev:plan-review to validate the plan for structural gaps (optional)"
      echo "  - Review the plan above, then run /feature-dev:tdd to implement"
      echo "  - Or start a NEW conversation and run /feature-dev:tdd (maximizes context)"
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this command and proceed with your assigned task.
</SUBAGENT-STOP>

## Context
- **Repository**: !`git remote get-url origin`
- **Current branch**: !`git branch --show-current`
- **Feature**: $ARGUMENTS

## Phase 0: Resolve Feature and Validate

1. **Resolve the feature:**
   - **If `$ARGUMENTS` is provided** → use it as the feature description. Record `source_spec: null`.
   - **If `$ARGUMENTS` is empty** → auto-discover spec files. Use Glob with pattern `SPEC-*.md` in the repo root, then read each file's frontmatter and **filter out any spec with `status: implemented`** (those features are already shipped). From the remaining candidates:
     - **0 specs** → **STOP** and ask the user for a feature description.
     - **1 spec** → use it. Read its frontmatter, use `feature:` as the feature description, record the spec path as `source_spec`. Inform the user: "Auto-selected spec: `SPEC-<slug>.md` (feature: <name>, status: <status>)". If `status: draft`, also warn: "This spec is still in draft — the user may not have approved it yet. Proceed anyway?" and wait for confirmation.
     - **2+ specs** → use AskUserQuestion to let the user pick (label = `feature:` value, description = `<filename> — status: <status>`). Use the chosen spec's `feature:` as the feature description and record its path as `source_spec`.
2. Parse the feature into a one-line summary for agent prompts.
3. Generate a plan filename: `PLAN-<slug>.md` (slug = lowercase, hyphenated, max 4 words from the feature name. E.g., `PLAN-scheduled-notifications.md`). If `source_spec` is set, reuse its `slug:` value for consistency.
4. **Select the explorers.** Four always run: `backend-explorer`, `frontend-explorer`, `test-explorer`, `history-explorer`. Add any of the four below whose signal is present in the feature description or, if `source_spec` is set, in the spec body (read it — the frontmatter alone is not enough signal).

   | Explorer | Add when the feature… |
   |---|---|
   | `schema-explorer` | touches persistence: a new/changed model, table, column, index, constraint, or migration; a data backfill; anything with a storage shape |
   | `config-explorer` | introduces or reads a setting, an environment variable, a credential, or a feature flag; behaves differently per environment; needs a rollout toggle |
   | `api-contract-explorer` | is consumed across a repo boundary: `source_spec` frontmatter has 2+ `repos:` entries, or the feature changes a declared contract (OpenAPI, GraphQL SDL, tRPC router, protobuf, JSON Schema) |
   | `observability-explorer` | ships something whose failure is silent: a background job, queue consumer, scheduled task, webhook handler, payment or auth path — anywhere post-ship visibility is how you learn it broke |

   These are cheap (read-only, parallel, `maxTurns: 15`) and the cost of omitting one is planning blind on the highest-risk layer. **When a signal is borderline, include the explorer.** Record the selected list; you pass it into the Phase 1 agent prompt.

   State the selection to the user in one line: "Explorers: backend, frontend, test, history + schema (new model), config (feature flag)."

## Phase 1: Explore and Generate Plan (Forked)

Launch a **single Agent** with `subagent_type: "general-purpose"` to do all exploration and plan generation in an isolated context.

**CRITICAL: The agent MUST write the plan file to disk.** The agent's context is discarded after it completes — only the file persists.

Agent prompt — include all of this:

```
You are generating an implementation plan for: [feature summary]

Repository: [repo URL]
Branch: [current branch]
Plan file: [PLAN-<slug>.md filename from Phase 0]
Source spec: [source_spec path from Phase 0, or "none"]

## Step 1: Parallel Exploration

Launch every agent below in a SINGLE response so they run concurrently. Do NOT use run_in_background.

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

## Step 2: Synthesize and Write Plan

After all agents complete, synthesize findings into a plan and write it to [PLAN-<slug>.md] using the Write tool.

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
     to a plan-step-executor. A step without Accept + Verify is not dispatchable. -->

1. **[Step name]**
   - Accept: [one specific, testable acceptance criterion — observable behavior, not "implement X"]
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
2. **`Accept` is one criterion, testable in isolation.** If stating it needs an "and", split the step. "when contact has no active subjects, `start_booking` returns `NO_SUBJECTS`" — not "add the booking flow".
3. **`Impl` and `Test` are file paths, not layers.** Each must also appear in the Files to Modify / Files to Create tables above. If a step's impl spans two unrelated modules, split it.
4. **Non-behavioral steps still need `Verify`.** A migration, a config wiring, or a dependency bump has no test file — write `Test: n/a — <reason>` and give `Verify` a command that proves the step landed (`python manage.py migrate --check`, `npm run typecheck`, `make lint`). These steps route to `plan-step-executor` instead of `tdd-runner`.
5. **Order by dependency, not by layer.** A step consuming a symbol another step introduces comes after it, and names it in `Depends on`.
6. **Say who writes the test.** When one step writes a test file and a later step makes it pass, the later step's `Test:` must carry `(written by step N)`. Without that marker the executor cannot tell "write this test" from "make this existing test pass", and will try to write a test that already exists. A step whose `Test:` and `Impl:` are BOTH `n/a` is an environment precondition (rebase, migration check, dependency install) — legitimate, but it still needs a `Verify` command.

## Step 3: Update .gitignore

If PLAN-*.md is not in the project's .gitignore, add it.
```

## Phase 2: Present Plan for Review

After the agent completes:

1. Read the `PLAN-<slug>.md` file from disk
2. Present the full plan to the user
3. Ask:
   - Does this look correct? Any files or areas I missed?
   - Any decisions you'd like to override?
   - Ready to implement? (Suggest `/feature-dev:tdd` to start)
