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

### Alternative implementation path (non-TDD)

When a `PLAN-*.md` is approved but the work isn't test-first (migrations, config wiring, mechanical refactors), dispatch the plan agents directly instead of running `/feature-dev:tdd`:

- **`feature-implementer`** drives the whole plan: dispatches each step to `plan-step-executor`, threads carry-over forward, halts on blockers.
- **`plan-step-executor`** can be dispatched directly for a single qualifying step (multi-file scope, own verification).

Neither enforces red-green-refactor — that's `tdd-runner`'s job, and `/feature-dev:tdd` is how you reach it.

## Installation

```bash
/plugin install feature-dev@juanmhidalgo-plugins
```
