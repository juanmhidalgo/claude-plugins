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

**Review** — backend for `spec-review` and `plan-review`:

| Agent | Focus |
|-------|-------|
| `spec-plan-validator` | Structural gap detection on `SPEC-*.md` / `PLAN-*.md` |

**Implementation** — dispatched by the main agent (or each other) once a plan is approved:

| Agent | Focus |
|-------|-------|
| `plan-step-executor` | Executes ONE step of an approved plan in isolation; returns a fixed-format report (Files / Verification / Deviations / Carry-over / Blockers) |
| `feature-implementer` | Orchestrates an approved `PLAN-*.md` end-to-end by dispatching steps to `plan-step-executor`, threading carry-over forward, halting on blockers |
| `tdd-runner` | Strict red-green-refactor enforcer for one bounded behavior; caps at 5 cycles, validates RED failure mode, gates promotion on coverage. Stack-agnostic (pytest / vitest / jest) |

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

### Alternative implementation path (agent-driven)

Once a `PLAN-*.md` exists from `/feature-dev:explore-plan`, the main agent can dispatch implementation through agents instead of running `/feature-dev:tdd` interactively:

- **`feature-implementer`** drives the whole plan: dispatches each step to `plan-step-executor`, threads carry-over forward, halts on blockers.
- **`plan-step-executor`** can be dispatched directly for a single qualifying step (multi-file scope, own verification).
- **`tdd-runner`** enforces strict red-green-refactor for one bounded behavior (caps at 5 cycles).

Use the command path when you want interactive review gates between phases. Use the agent path when the plan is approved and you want a single delegate to drive execution end-to-end without polluting the main agent's context.

## Installation

```bash
/plugin install feature-dev@juanmhidalgo-plugins
```
