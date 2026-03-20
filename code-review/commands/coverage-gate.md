---
disable-model-invocation: true
allowed-tools:
  - Bash(git *)
  - Bash(pytest *)
  - Bash(python *)
  - Bash(coverage *)
  - Bash(npm *)
  - Bash(npx *)
  - Bash(yarn *)
  - Bash(pnpm *)
  - Bash(make *)
  - Bash(cargo *)
  - Bash(go *)
  - Read
  - Write
  - Edit
  - Agent
  - Glob
  - Grep
argument-hint: "[base-branch]"
description: |
  Check code coverage against CI-configured thresholds locally before pushing.
  Detects coverage thresholds from GitHub Actions workflows and verifies
  changed files meet the required coverage levels. Writes tests to fix gaps.
  Use to prevent CI coverage failures before pushing.
  Do NOT use as a replacement for running tests (use your test command directly).
keywords:
  - coverage
  - coverage-gate
  - threshold
  - pre-push
  - ci-coverage
triggers:
  - "check coverage"
  - "coverage gate"
  - "will coverage pass"
  - "check coverage thresholds"
  - "coverage before push"
skills:
  - coverage-gate
hooks:
  - event: Stop
    once: true
    command: |
      echo "Coverage gate complete."
      echo "  - /commit to commit changes"
      echo "  - /code-review:pipeline PR# for full pipeline"
---

## Context
- **Current branch**: !`git branch --show-current`
- **Base branch argument**: $ARGUMENTS
- **Working tree**: !`git status --short`

## Phase 1: Detect CI Coverage Configuration

1. Search for `.github/workflows/*.yml` files using Glob
2. Grep for coverage action patterns: `orgoro/coverage`, `CodeCoverageReport`, `cobertura-action`, `codecov`
3. If found, read the workflow file and extract thresholds from the `with:` block
4. Normalize thresholds to 0-100 percentage scale
5. If `codecov/codecov-action` found, also check for `codecov.yml` at repo root

**If NO coverage config found**: Report "No CI coverage configuration detected" and **STOP**.

Report detected thresholds:

```
## Detected Coverage Thresholds

Source: [workflow file] ([action name])
- All files: [X]%
- New files: [X]%
- Modified files: [X]%
```

## Phase 2: Determine Base Branch and Categorize Files

1. Determine base branch:
   - Use `$ARGUMENTS` if provided
   - Otherwise detect: `git symbolic-ref refs/remotes/origin/HEAD --short` (strips `origin/` prefix)
2. Categorize changed source files (exclude test files, `__init__.py`, configs, docs, migrations):
   - **New files**: `git diff --name-only --diff-filter=A <base>...HEAD`
   - **Modified files**: `git diff --name-only --diff-filter=M <base>...HEAD`

Report file categorization:

```
## Changed Files

### New ([count])
- [file paths]

### Modified ([count])
- [file paths]
```

## Phase 3: Run Coverage

1. Detect coverage tool — check GHA workflow for the coverage command, then fall back to project config
2. Run the test suite with coverage report generation
3. Parse per-file coverage from the report

## Phase 4: Check Thresholds

For each changed source file, check coverage against its category threshold.

Report results:

```
## Coverage Gate Results

### Overall: [X]% (threshold: [X]%) — PASS/FAIL

### New Files
| File | Coverage | Threshold | Status |
|------|----------|-----------|--------|
| path/to/file.py | 53% | 80% | FAIL |

### Modified Files
| File | Coverage | Threshold | Status |
|------|----------|-----------|--------|
| path/to/file.py | 77% | 65% | PASS |
```

**If all PASS**: Report success and stop.

## Phase 5: Fix Coverage Gaps

If any files are below threshold:

1. For each failing file, identify specific uncovered lines
2. Write targeted tests for meaningful uncovered paths — skip trivial getters/setters, `__str__`, `__repr__`
3. Re-run test suite with coverage to verify improvement
4. Maximum **2 additional coverage cycles**
5. After each cycle, re-report the updated coverage table

If still below threshold after 2 cycles: report remaining gaps and what would be needed to reach the threshold.

```
## Final Coverage Status

### Fixed ([count] files now passing)
- [file]: [old]% → [new]% (threshold: [X]%)

### Remaining Gaps ([count] files still below)
- [file]: [current]% (threshold: [X]%, needs [Y] more lines covered)
```
