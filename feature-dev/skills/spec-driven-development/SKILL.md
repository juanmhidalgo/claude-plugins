---
name: spec-driven-development
description: |
  Use when starting a new feature or significant change and no specification exists yet.
  Provides gated workflow (Specify → Plan → Tasks → Implement) with assumption surfacing.
  Do NOT use for single-line fixes, typos, or unambiguous self-contained changes.
keywords:
  - spec
  - specification
  - requirements
  - planning
  - acceptance-criteria
triggers:
  - "write a spec"
  - "define requirements"
  - "what should we build"
  - "create a specification"
  - "spec-driven"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
---

# Spec-Driven Development

## When to Use

- Starting a new feature or project
- Requirements are ambiguous or incomplete
- Change touches multiple files or modules
- Task would take more than 30 minutes to implement
- About to make an architectural decision

## The Gated Workflow

Four phases. Do not advance until the current phase is validated by the user.

```
SPECIFY ──→ PLAN ──→ TASKS ──→ IMPLEMENT
   │          │        │          │
   ▼          ▼        ▼          ▼
 Review     Review   Review    Review
```

### Phase 1: Specify

Surface assumptions immediately before writing anything:

```
ASSUMPTIONS I'M MAKING:
1. This is a web application (not native mobile)
2. Authentication uses session-based cookies
3. The database is PostgreSQL
→ Correct me now or I'll proceed with these.
```

Write a spec covering six areas:
1. **Objective** — What, why, who, and what success looks like
2. **Commands** — Full executable commands (build, test, lint, dev)
3. **Project Structure** — Where source, tests, and docs live
4. **Code Style** — One real snippet showing conventions
5. **Testing Strategy** — Framework, location, coverage, test levels
6. **Boundaries** — Always do / Ask first / Never do

Reframe vague requirements as testable success criteria:
```
"Make the dashboard faster"
→ LCP < 2.5s on 4G, initial data load < 500ms, CLS < 0.1
→ Are these the right targets?
```

### Phase 2: Plan

With validated spec, generate a technical plan:
- Major components and dependencies
- Implementation order
- Risks and mitigations
- What can parallelize vs. must be sequential
- Verification checkpoints between phases

### Phase 3: Tasks

Break into discrete, implementable tasks:
- Completable in one focused session
- Explicit acceptance criteria and verification step
- Ordered by dependency, not importance
- No task changes more than ~5 files

```markdown
- [ ] Task: [Description]
  - Accept: [What must be true]
  - Verify: [Test command or check]
  - Files: [Which files]
```

### Phase 4: Implement

Execute tasks using `tdd` patterns. One task at a time, verify before advancing.

## Keeping the Spec Alive

- Update when decisions or scope change
- Commit alongside code
- Reference spec sections in PRs

## Anti-Rationalizations

| Excuse | Reality |
|--------|---------|
| "This is simple, no spec needed" | Simple tasks need short specs, not no specs. Two lines is fine. |
| "I'll write the spec after coding" | That's documentation, not specification. The value is clarity before code. |
| "The spec will slow us down" | A 15-minute spec prevents hours of rework. |
| "Requirements will change anyway" | That's why it's a living document. Outdated spec > no spec. |
| "The user knows what they want" | Even clear requests have implicit assumptions. Surface them. |

## Verification

Before proceeding to implementation:
- [ ] Spec covers all six core areas
- [ ] User has reviewed and approved the spec
- [ ] Success criteria are specific and testable
- [ ] Boundaries (Always / Ask First / Never) are defined
- [ ] Spec is saved to a file in the repository
