---
name: tdd-patterns
description: |
  Institutional patterns for test-driven development workflows.
  Use when executing TDD cycles with coverage gates and quality checks.
  Do NOT use for general testing advice or test writing without the full TDD cycle.
user-invocable: false
keywords:
  - tdd
  - red-green-refactor
  - coverage-gate
---

## TDD Cycle Constraints

### Iteration Limits

- **Maximum 5 RED-GREEN cycles** per feature. If tests still fail after 5 cycles, STOP and report the blocking issue to the user.
- **Stuck-after-3 rule**: If the same test failure persists after 3 consecutive cycles with different fix attempts, STOP immediately. Do not keep trying the same approach.

### Phase Ordering

Phases are strictly sequential. Never skip or reorder:

1. **RED**: Write tests that MUST fail. If any test passes immediately, it is testing existing behavior — remove or rewrite it.
2. **GREEN**: Write the minimum code to make tests pass. No refactoring, no optimization, no "while I'm here" changes.
3. **REFACTOR**: Only after all tests are green. Run tests after every refactoring change. If a test breaks during refactor, undo the refactoring change.

### Fix Implementation, Not Tests

When a test fails during the GREEN phase:

- Default action: fix the **implementation**, not the test.
- Only modify a test if the test itself has a bug (wrong assertion, incorrect setup) — never weaken a test to make it pass.
- If the spec is ambiguous, ask the user rather than adjusting the test.

## Coverage Gate Workflow

### Check Changed Files Only

1. Run coverage on the full test suite but report coverage for **changed/new files only**.
2. Use the project's configured coverage tool and thresholds first.
3. If no coverage configuration exists, apply **80% line coverage minimum** on changed files.

### Below-Threshold Response

1. Identify specific uncovered lines (not just percentages).
2. Write tests for meaningful uncovered paths — skip trivial getters/setters and `__str__` methods.
3. Re-run coverage after adding tests. Maximum 2 additional coverage cycles.

## Lint and Format Detection

Detect the project's lint/format tools in this order:

1. Check `package.json` scripts for `lint`/`format` keys.
2. Check for config files: `pyproject.toml` (ruff/black), `.eslintrc*`, `prettier.config*`, `rustfmt.toml`, `.golangci.yml`.
3. Check `Makefile` / `justfile` for lint/format targets.
4. If no tool found, skip lint phase with a note — do not install tools.

Run lint/format **after** all tests pass and coverage is met. Fix lint issues, then re-run tests to confirm nothing broke.
