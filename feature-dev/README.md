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

Dedicated exploration agents spawned by `explore-plan` for parallel codebase analysis:

| Agent | Focus |
|-------|-------|
| `backend-explorer` | Models, views, serializers, endpoints, services, database patterns |
| `frontend-explorer` | Components, hooks, API clients, routing, state management, UI patterns |
| `test-explorer` | Test files, fixtures, factories, coverage config, test patterns |
| `history-explorer` | Git history, open PRs, recent changes, conflict risk assessment |
| `spec-plan-validator` | Shared backend for `spec-review` and `plan-review`: structural gap detection on `SPEC-*.md` / `PLAN-*.md` |

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

## Installation

```bash
/plugin install feature-dev@juanmhidalgo-plugins
```
