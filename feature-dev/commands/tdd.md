---
disable-model-invocation: true
allowed-tools:
  - Bash(git *)
  - Bash(npm *)
  - Bash(npx *)
  - Bash(yarn *)
  - Bash(pnpm *)
  - Bash(pytest *)
  - Bash(python *)
  - Bash(make *)
  - Bash(cargo *)
  - Bash(go *)
  - Read
  - Write
  - Edit
  - Agent
  - Glob
  - Grep
skills:
  - tdd-patterns
argument-hint: "<feature spec or description>"
description: |
  Use when implementing a new feature or fixing a bug where you want tests to lead, not follow.
  Do NOT use for quick one-line fixes or refactors without behavioral change.
keywords:
  - tdd
  - test-driven
  - feature-development
  - coverage
  - red-green-refactor
triggers:
  - "implement with TDD"
  - "test-driven development"
  - "write tests first"
  - "implement feature with coverage"
hooks:
  - event: Stop
    once: true
    command: |
      echo "TDD cycle complete."
      echo "  - /code-review:branch to review before merge"
      echo "  - /commit to commit changes"
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this command and proceed with your assigned task.
</SUBAGENT-STOP>

## Context
- **Repository**: !`git remote get-url origin`
- **Current branch**: !`git branch --show-current`
- **Working tree clean**: !`git status --short`
- **Feature spec**: $ARGUMENTS

## Phase 0: Validate

1. Feature spec was provided (from $ARGUMENTS). If empty, **STOP** and ask user for a feature description.
2. Working tree is clean. If dirty, **STOP** and ask user to commit or stash.

## Phase 1: Load Plan or Explore Codebase

**First, check for an existing implementation plan:**

Look for `PLAN-*.md` files in the repository root (created by `/feature-dev:explore-plan`). If multiple exist, pick the one most relevant to the feature spec.

**If the plan file exists:**
- Read it and use it as the source of truth for files to modify/create, implementation order, and key decisions
- Only do a **minimal exploration** with the Agent tool (`subagent_type: "Explore"`) focused on:
  - Test framework and runner command
  - Coverage tool and current thresholds
  - Existing test patterns (naming, structure, fixtures)
- Skip general codebase exploration — the plan already has that context

**If no plan file exists:**
- Use the Agent tool with `subagent_type: "Explore"` to understand:
  1. **Existing patterns**: Test conventions, file structure, naming, frameworks (pytest/vitest/jest/etc.)
  2. **Related code**: Models, services, components, APIs relevant to the feature
  3. **Test infrastructure**: Fixtures, factories, mocks, helpers, config files

Summarize findings before proceeding. Include:
- Test framework and runner command
- Coverage tool and current thresholds (if configured)
- Key files to modify/create
- Existing patterns to follow

## Phase 2: Write Failing Tests (RED)

Based on the spec and codebase exploration:

1. Write **comprehensive tests** covering:
   - Happy path (core behavior)
   - Edge cases
   - Error paths
   - Integration points
2. Follow existing test patterns exactly (naming, structure, fixtures)
3. Place tests next to source files or in the project's test directory (match convention)

Run the tests — they should **ALL FAIL**. If any pass, they're testing existing behavior, not new behavior. Review and adjust.

Report: "X tests written, all failing as expected."

## Phase 3: Implement Feature (GREEN)

Implement the minimum code to make tests pass:

1. Make changes incrementally — run tests after each meaningful change
2. Focus on making tests green, not on code elegance
3. If a test failure reveals a gap in understanding, fix the implementation, not the test

### Iteration loop (max 5 cycles):
```
1. Implement/modify code
2. Run tests
3. If all pass → move to Phase 4
4. If some fail → analyze failures, fix implementation, go to step 2
5. If stuck after 3 cycles on same failure → STOP and report the issue
```

## Phase 4: Coverage Check

Run the project's coverage tool:

1. Check coverage on the **changed files** specifically
2. Compare against project thresholds (from config) or 80% minimum
3. If below threshold:
   - Identify uncovered lines
   - Write additional tests for meaningful uncovered paths
   - Re-run until coverage meets threshold
4. If no coverage tool configured, skip with a note

## Phase 5: Refactor (REFACTOR)

With all tests green and coverage met:

1. Review the implementation for:
   - Code duplication
   - Naming clarity
   - Unnecessary complexity
2. Make small refactoring changes, running tests after each
3. Do NOT over-engineer — keep changes minimal

## Phase 6: Lint and Format

Run the project's linter and formatter:

1. Detect tool: `ruff`/`black`/`eslint`/`prettier`/`rustfmt`/`gofmt`
2. Fix any issues
3. Re-run tests to confirm nothing broke

## Phase 7: Report

Output a final summary:

```
## TDD Results

### Feature: [brief description]

### Tests Written: [count]
- [test file]: [count] tests ([brief categories])

### Implementation Files Modified: [count]
- [file path] — [what was changed]

### Coverage: [percentage] on changed files (threshold: [threshold])

### Test Run: ALL PASSING

### Ready to commit: Yes/No
```

If all phases passed:
1. **Delete the `PLAN-*.md` file** that was used (it has served its purpose — the implementation is done)
2. Suggest a commit message following the project's convention
