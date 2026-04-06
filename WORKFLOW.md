# Development Workflow Guide

How to use these plugins together across the development lifecycle.

## The Development Lifecycle

```
  Discuss ──→ Specify ──→ Explore & Plan ──→ Build ──→ Review ──→ Ship
     │                                         │         │
     │                              Debug ◄────┘         │
     │                                                   │
     └──────────── Refactor (anytime) ◄──────────────────┘
```

## Phase 1: Discuss & Refine

Before writing any code, pressure-test the idea.

| When | Command |
|------|---------|
| Analyze a feature or spec for gaps | `/discuss:feature <feature>` |
| Generate alternative approaches | `/discuss:brainstorm <problem>` |
| Stress-test a specific proposal | `/discuss:challenge <proposal>` |
| Compare 2-4 concrete options | `/discuss:tradeoffs <A vs B>` |

**Typical flow**: Start with `/discuss:feature` to identify risks, then `/discuss:brainstorm` if you need alternatives, then `/discuss:tradeoffs` to pick one.

## Phase 2: Specify

Write a structured spec before coding. Surfaces assumptions and defines success criteria.

| When | Command |
|------|---------|
| Starting a new feature | `/feature-dev:spec <feature>` |

The spec command follows a gated workflow: **Specify → Plan → Tasks → Implement**. Each gate requires your review before advancing. Saves a `SPEC-<feature>.md` file.

**Skip this phase** for single-file fixes or changes where requirements are unambiguous.

## Phase 3: Explore & Plan

Understand the codebase before making changes.

| When | Command |
|------|---------|
| Plan a feature implementation | `/feature-dev:explore-plan <feature>` |
| Understand project architecture | `/onboard:architecture` |
| Deep-dive into a specific area | `/onboard:explore <topic>` |

`explore-plan` spawns 4 parallel agents (backend, frontend, tests, git history) and produces an implementation plan saved to `PLAN-<feature>.md`.

## Phase 4: Build

Implement with test-driven development.

| When | Command |
|------|---------|
| Implement a feature with TDD | `/feature-dev:tdd <spec>` |

Follows the RED → GREEN → REFACTOR cycle with coverage gates. If a `PLAN-*.md` exists from Phase 3, it loads it automatically instead of re-exploring.

## Phase 5: Debug

When something breaks during development.

| When | Command |
|------|---------|
| Systematic debugging | `/debug:debug <error or failing test>` |
| Quick error classification | `/debug:triage <error message>` |

`debug` follows the 6-step triage: **Reproduce → Localize → Reduce → Root Cause → Guard → Verify**. Always writes a regression test before moving on.

`triage` is a lighter-weight classification — use it to quickly understand what kind of error you're dealing with before committing to a full debug session.

## Phase 6: Review

Quality gates before shipping.

| When | Command |
|------|---------|
| Review branch changes | `/code-review:branch` |
| Review staged changes | `/code-review:staged` |
| Full PR review (multi-agent) | `/code-review:pr <PR#>` |
| Triage AI reviewer feedback | `/code-review:triage <PR#>` |
| Security audit | `/security:audit [path]` |
| Security checklist | `/security:checklist [area]` |
| Performance audit | `/performance:audit [path]` |
| Profile specific code | `/performance:profile <target>` |
| Check coverage thresholds | `/code-review:coverage-gate` |

**Recommended review order**:
1. `/code-review:branch` — catch bugs and code quality issues
2. `/security:audit` — check for vulnerabilities (especially if touching auth, input handling, or external data)
3. `/performance:audit` — check for N+1 queries, missing pagination, bundle size (especially if touching data fetching or frontend)

Not every change needs all three. Use judgment:
- **Auth/input changes** → always run security audit
- **Data fetching/rendering** → always run performance audit
- **Everything** → always run code review

## Phase 7: Ship

Commit, test, push, and optionally create a PR.

| When | Command |
|------|---------|
| Full ship workflow | `/ship` |
| Ship without tests | `/ship --skip-tests` |
| Ship without PR prompt | `/ship --no-pr` |
| Ship as draft PR | `/ship --draft` |

Handles smart staging (groups cohesive changes), conventional commit generation, test execution, push, and PR creation.

## Cross-Cutting Workflows

These apply at any point in the lifecycle.

### Refactoring

| When | Command |
|------|---------|
| Analyze code for refactoring opportunities | `/refactor:analyze <path>` |
| Create a refactoring plan | `/refactor:plan <path>` |
| Extract code into new function/module | `/refactor:extract <path>` |

### Cross-Team Handoffs

| When | Command |
|------|---------|
| Generate prompt for another repo | `/handoff:prompt` |
| After backend API changes → tell frontend | `/handoff:backend-to-frontend [file]` |
| Frontend needs new APIs → tell backend | `/handoff:frontend-to-backend [feature]` |
| Process a received handoff | `/handoff:receive <prompt>` |

### Second Opinions

| When | Command |
|------|---------|
| External AI review of staged changes | `/second-opinion review staged` |
| External AI review of a file | `/second-opinion review <file>` |
| External AI review of branch | `/second-opinion review branch` |

### Code Review Fix Pipeline

When a PR has review feedback:

```
/code-review:triage <PR#>        → Separate valid issues from false positives
/code-review:fixes-plan          → Generate tracking document
/code-review:implement-fix       → Fix issues one by one
/code-review:mark-fixed          → Verify fixes
/code-review:resolve-fixed <PR#> → Resolve GitHub threads
```

### Onboarding

When joining a new project:

```
/onboard:start                   → Full onboarding guide
/onboard:architecture            → Architecture overview
/onboard:explore <topic>         → Deep-dive into specific area
```

## Common Chains

### New Feature (Full Lifecycle)
```
/discuss:feature "user dashboard with activity feed"
/feature-dev:spec "user dashboard with activity feed"
/feature-dev:explore-plan "user dashboard"
/feature-dev:tdd
/code-review:branch
/security:audit
/ship
```

### Bug Fix
```
/debug:triage "TypeError in auth middleware"
/debug:debug "TypeError in auth middleware"
/code-review:staged
/ship
```

### Performance Issue
```
/performance:audit src/api/
/performance:profile src/api/tasks.py:list_tasks
/code-review:staged
/ship
```

### Security Hardening
```
/security:audit
/security:checklist auth
/code-review:branch
/ship
```
