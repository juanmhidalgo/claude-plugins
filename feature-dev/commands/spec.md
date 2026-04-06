---
description: Create a structured specification before coding — surfaces assumptions, defines success criteria, and produces an implementation-ready spec
argument-hint: "<feature or project description>"
keywords:
  - spec
  - specification
  - requirements
  - planning
triggers:
  - "write a spec"
  - "create specification"
  - "define requirements first"
  - "spec-driven development"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - Agent
hooks:
  - event: Stop
    once: true
    command: |
      echo "Spec complete. Next steps:"
      echo "  - /feature-dev:explore-plan to explore the codebase"
      echo "  - /feature-dev:tdd to start test-driven implementation"
---

## Context

- **Branch**: !`git branch --show-current`
- **Recent commits**: !`git log --oneline -5`

<best_practices>
@feature-dev/skills/spec-driven-development/SKILL.md
</best_practices>

## Spec-Driven Development Workflow

You are creating a structured specification for: **$ARGUMENTS**

Follow the gated workflow. Each phase requires user review before advancing.

### Phase 1: Specify

1. **Surface assumptions first.** Before writing anything, list 3-5 assumptions you're making about the tech stack, architecture, and scope. Ask the user to confirm or correct.

2. **Reframe vague requirements.** If the input is vague, translate it into concrete, testable success criteria. Present these to the user for validation.

3. **Write the spec** covering these six areas:
   - **Objective**: What we're building, why, who it's for, what success looks like
   - **Commands**: Full executable commands (build, test, lint, dev)
   - **Project Structure**: Where code, tests, and docs live (explore the repo first)
   - **Code Style**: One real snippet from the codebase showing conventions
   - **Testing Strategy**: Framework, test location, coverage expectations
   - **Boundaries**: Always do / Ask first / Never do

4. **Save the spec** to `SPEC-<feature-slug>.md` in the project root.

5. **Present to user** for review. Do NOT proceed until they approve.

### Phase 2: Plan

With the approved spec:
1. Identify major components and their dependencies
2. Determine implementation order
3. Note risks and mitigations
4. Define verification checkpoints

Present the plan for review.

### Phase 3: Tasks

Break the plan into discrete tasks:
- Each completable in one session
- Explicit acceptance criteria
- Verification step (test command, build, manual check)
- Ordered by dependency
- No task changes more than ~5 files

```markdown
- [ ] Task: [Description]
  - Accept: [What must be true]
  - Verify: [How to confirm]
  - Files: [Which files]
```

Add tasks to the spec file. Present for review.

### Phase 4: Handoff

After all phases are approved:
- Spec file is committed to the repo
- User can proceed with `/feature-dev:tdd` or `/feature-dev:explore-plan`

## Rules

- **Never skip assumption surfacing.** Silent assumptions are the most dangerous form of misunderstanding.
- **Never advance phases without user approval.** Each gate exists to catch misalignment early.
- **Reframe, don't accept vagueness.** Convert "make it better" into measurable criteria.
- **The spec is a living document.** Update it when decisions change, don't abandon it.
