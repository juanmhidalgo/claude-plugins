---
name: coverage-gate
description: |
  Use when checking code coverage against CI-configured thresholds before pushing or during pipeline execution.
  Do NOT use for general test writing or coverage tool configuration.
user-invocable: false
keywords:
  - coverage
  - coverage-gate
  - threshold
  - ci-coverage
  - orgoro-coverage
---

## GHA Threshold Detection

Search `.github/workflows/*.yml` for coverage actions and extract thresholds.

### Supported Actions

| Action | Threshold Fields | Format |
|--------|-----------------|--------|
| `orgoro/coverage` | `thresholdAll`, `thresholdNew`, `thresholdModified` | Decimal 0-1 (multiply by 100) |
| `irongut/CodeCoverageReport` | `thresholds` | `'60 80'` (warning failure) — use failure value |
| `5monkeys/cobertura-action` | `minimum_coverage` | Integer 0-100 |
| `codecov/codecov-action` | None inline — check `codecov.yml` at repo root | `target: 80%` |

### Detection Steps

1. Glob for `.github/workflows/*.yml`
2. Grep for coverage action patterns
3. Read the matching workflow file
4. Extract threshold values from `with:` block
5. Normalize all thresholds to percentages (0-100 scale)

**If no coverage config found**: Skip the coverage gate entirely with a note.

**Default thresholds** (when action exists but thresholds are partially configured):
- `thresholdAll`: 55%
- `thresholdNew`: 80%
- `thresholdModified`: 65%

## File Categorization

Map GHA categories to git state:

| Category | PR Context | Staged Context |
|----------|-----------|----------------|
| New files | `git diff --name-only --diff-filter=A <base>...HEAD` | `git diff --cached --name-only --diff-filter=A` |
| Modified files | `git diff --name-only --diff-filter=M <base>...HEAD` | `git diff --cached --name-only --diff-filter=M` |
| All files | Overall coverage report | Overall coverage report |

**Filter to source files only** — exclude test files, configs, docs, migrations, `__init__.py`.

## Coverage Tool Detection

Detect the project's coverage tool. **Check the GHA workflow first** — it reveals the exact command and flags.

| Ecosystem | Config Files | Coverage Command | Report |
|-----------|-------------|-----------------|--------|
| Python (pytest-cov) | `pyproject.toml`, `setup.cfg` | `pytest --cov --cov-report=xml` | `coverage.xml` |
| Python (coverage.py) | `.coveragerc` | `coverage run -m pytest && coverage xml` | `coverage.xml` |
| Node (jest) | `package.json` | `npx jest --coverage --coverageReporters=cobertura` | `coverage/cobertura-coverage.xml` |
| Node (vitest) | `vitest.config.*` | `npx vitest run --coverage` | `coverage/cobertura-coverage.xml` |
| Go | `go.mod` | `go test -coverprofile=coverage.out ./...` | `coverage.out` |

Also check `Makefile` / `package.json` scripts for existing coverage targets.

## Coverage Verification Workflow

1. **Run test suite with coverage** using the project's tool
2. **Parse coverage report** — extract per-file line coverage percentages
3. **Categorize changed files** — new vs modified via git diff
4. **Check thresholds** per category
5. **Report failures** — list each file below threshold with current % and required %

## Below-Threshold Response

1. Identify specific uncovered lines per failing file
2. Write tests targeting meaningful uncovered paths — skip trivial getters/setters, `__str__`, `__repr__`
3. Re-run coverage to verify improvement
4. Maximum **2 additional coverage cycles**
5. If still below after 2 cycles: report remaining gaps, let user (or pipeline) decide

## Rationalization Defenses

If you catch yourself thinking any of these, STOP — you are about to skip the coverage gate:

| Rationalization | Why It's Wrong |
|----------------|----------------|
| "Coverage looks okay overall, I don't need to check per-file" | Overall coverage masks individual file gaps. CI checks per-category thresholds, so must you. |
| "I can't find a coverage config so I'll skip this" | Check all four supported action types in GHA workflows. Only skip if genuinely no coverage action exists. |
| "The uncovered lines are just boilerplate" | Only trivial getters/setters/`__str__` are exempt. Business logic boilerplate still needs coverage. |
| "I'll write one more cycle of tests to push it over" | Maximum 2 additional cycles. After that, report gaps and let the user decide. Don't keep trying. |
| "The tests pass, coverage is probably fine" | Passing tests and sufficient coverage are independent. A file can have 100% passing tests and 30% line coverage. |
| "This threshold seems too strict for this file" | The threshold comes from the CI config — it's the project's standard, not yours to override. |

For detailed GHA action patterns, see [gha-patterns.md](references/gha-patterns.md).
