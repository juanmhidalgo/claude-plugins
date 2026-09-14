# feature-dev

Feature development workflows with structured phases and quality gates.

## Commands

| Command | Purpose |
|---------|---------|
| `/feature-dev:spec <feature>` | Create a structured specification before coding with gated review workflow |
| `/feature-dev:tdd <spec>` | Test-driven feature development: write failing tests, implement, coverage gate, refactor |
| `/feature-dev:explore-plan <feature>` | Parallel codebase exploration with 4 agents, synthesized implementation plan |
| `/feature-dev:spec-review [file]` | Validate a `SPEC-*.md` for structural gaps; emits Blocking / Should Address / Nice to Have checklist |
| `/feature-dev:plan-review [file]` | Validate a `PLAN-*.md` for structural gaps; emits Blocking / Should Address / Nice to Have checklist |
| `/feature-dev:cleanup` | Bulk-delete implemented `SPEC-*.md` and stale `PLAN-*.md` artifacts; explicit Y/N confirmation required |

## Agents

**Exploration** — spawned by `explore-plan` for parallel codebase analysis:

| Agent | Focus |
|-------|-------|
| `backend-explorer` | Models, views, serializers, endpoints, services, database patterns |
| `frontend-explorer` | Components, hooks, API clients, routing, state management, UI patterns |
| `test-explorer` | Test files, fixtures, factories, coverage config, test patterns |
| `history-explorer` | Git history, open PRs, recent changes, conflict risk assessment |

**Conditional explorers** — `explore-plan` selects these in Phase 0 from signals in the feature description and spec body, and dispatches them in the same parallel batch as the four above. Also invocable directly via `subagent_type: "feature-dev:<name>"` from any skill in any repo:

| Agent | Focus |
|-------|-------|
| `config-explorer` | Settings modules, environment variables, feature flags, credential handling, per-environment overrides — selected when the feature reads or introduces any of them |
| `schema-explorer` | DB migrations, current schema, indexes/constraints, naming conventions, pending migrations — selected when the feature touches persistence |
| `api-contract-explorer` | OpenAPI, GraphQL, tRPC, protobuf, JSON Schema contracts, distinct from endpoint code — selected for multi-repo features or declared-contract changes |
| `observability-explorer` | Logging, metrics, tracing, error reporting, alerting, dashboards — selected when the feature can fail silently (jobs, consumers, webhooks, auth/payment paths) |

**Review** — backend for `spec-review` and `plan-review`:

| Agent | Focus |
|-------|-------|
| `spec-plan-validator` | Structural gap detection on `SPEC-*.md` / `PLAN-*.md` |

**Implementation** — dispatched by the main agent (or each other) once a plan is approved:

| Agent | Focus |
|-------|-------|
| `plan-step-executor` | Executes ONE step of an approved plan in isolation; returns a fixed-format report (Files / Verification / Deviations / Carry-over / Blockers) |
| `feature-implementer` | Orchestrates an approved `PLAN-*.md` end-to-end by dispatching steps to `plan-step-executor`, threading carry-over forward, halting on blockers |
| `tdd-runner` | Strict red-green-refactor enforcer for one bounded behavior; caps at 5 cycles, validates RED failure mode, gates promotion on coverage. Stack-agnostic (pytest / vitest / jest). **Dispatched per acceptance criterion by `/feature-dev:tdd`** |
| `cross-repo-advisor` | Read-only decision brief for ONE bounded cross-repo question (who owns a field, does this break the contract). Recommends with cited evidence; never edits and never decides. Spawned by `/feature-dev:tdd` when a halt is a question rather than a defect, or invocable directly |

## Skills

| Skill | Purpose |
|-------|---------|
| `spec-driven-development` | Gated specification workflow: assumption surfacing, success criteria, six-area spec template |
| `tdd-patterns` | Institutional TDD knowledge: iteration limits, coverage gates, phase constraints |

## Workflow

The commands are designed to chain:

1. **`/feature-dev:spec`** — Define requirements and create a specification
2. **`/feature-dev:explore-plan`** — Understand the codebase and create a plan
3. **`/feature-dev:tdd`** — Execute the plan with test-driven development

Each command can also be used independently.

### How `/feature-dev:tdd` executes

The command is an **orchestrator, not an implementer**. After loading the plan it decomposes the feature into ordered acceptance criteria and dispatches one **`tdd-runner`** per criterion, sequentially, threading carry-over forward and halting on the first blocker. Test bodies and implementation diffs stay in the runners' contexts; the main agent keeps the criteria list, the reports, and the final lint/coverage pass.

Dispatch is sequential by design — later criteria depend on symbols earlier ones introduce, and concurrent runners collide on overlapping files.

Steps whose `Test:` is `n/a` (migrations, config wiring, dependency bumps) route to **`plan-step-executor`** instead — nothing to drive test-first, but the step's `Verify` command still gates it.

### Resuming a halted run

`/feature-dev:tdd` records progress in the plan's frontmatter (`run_status`, `completed_steps`) as it goes. When a step halts, the plan and spec stay on disk and the working tree keeps the finished steps.

Re-running `/feature-dev:tdd` picks it up: it re-runs the `Verify` command of each recorded step, skips the ones that are still green, re-dispatches any that regressed, and resumes from the halt point. A dirty working tree is only a hard stop when there is no in-progress plan to explain it.

**Do not `git stash` a halted run** — the recorded progress points at work that would no longer be in the tree. `/feature-dev:cleanup` will not offer an `in-progress` or `halted` plan for deletion, for the same reason.

### Alternative implementation path (non-TDD)

When a `PLAN-*.md` is approved but the work isn't test-first (migrations, config wiring, mechanical refactors), dispatch the plan agents directly instead of running `/feature-dev:tdd`:

- **`feature-implementer`** drives the whole plan: dispatches each step to `plan-step-executor`, threads carry-over forward, halts on blockers.
- **`plan-step-executor`** can be dispatched directly for a single qualifying step (multi-file scope, own verification).

Neither enforces red-green-refactor — that's `tdd-runner`'s job, and `/feature-dev:tdd` is how you reach it.

### Decisions Log

Decisions taken *during* implementation land in a `## Decisions Log` section of the `SPEC-*.md`, not in the plan — the plan is deleted when it completes, the spec is not. `/feature-dev:tdd` appends to it in Phase 3 and reads it back in Phase 1, so a run in the consuming repo starts already knowing what the contract-owning repo decided. Each entry carries a `Binds:` field naming who has to obey it.

This is what removes the need to keep a second session open as the feature's memory across repos. For the *judgement* half of that role — a bounded question you want a second read on — spawn `cross-repo-advisor`; it produces a brief, the decision stays yours, and once you take it `/feature-dev:tdd` records it.

### Coordinator session

If you keep a session open as the feature's coordinator, name it at invocation:

```
/feature-dev:tdd --coordinator <session-name>
```

On a halt that is a cross-repo *question* (not a defect), the run sends that session one message — the step, the question, and the `cross-repo-advisor` brief if one was produced — with `notify_when_idle: true`, and carries on handing the halt to you. Never per-step progress: one message per halt that needs one.

**The command does not go looking for a session, by design.** `ListAgents` reports name, kind and status but no working directory, so matching falls back to the name — and a coordinator for a multi-repo feature has no single repo to be named after. Name-matching finds the implementer sessions and misses the coordinator. You name it or it is not used.

**The log is the record; the message is a notification.** A decision is written to the spec's Decisions Log before it is announced, and only after you accept it. A session can be compacted, restarted or closed; the spec cannot.

## Installation

```bash
/plugin install feature-dev@juanmhidalgo-plugins
```
