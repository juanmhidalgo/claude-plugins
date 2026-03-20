# GHA Coverage Action Patterns

Detailed detection patterns for extracting coverage thresholds from GitHub Actions workflows.

## orgoro/coverage

Most common for Python projects using Cobertura XML.

```yaml
- name: Post Coverage Comment
  uses: orgoro/coverage@v3.2
  with:
    coverageFile: ./coverage.xml
    token: ${{ secrets.GITHUB_TOKEN }}
    thresholdAll: 0.55        # Overall: 55%
    thresholdNew: 0.8         # New files: 80%
    thresholdModified: 0.65   # Modified files: 65%
```

**Threshold format**: Decimal 0-1. Multiply by 100 for percentage.
**Coverage file**: Check `coverageFile` field — usually `coverage.xml` (Cobertura format).
**Grep pattern**: `orgoro/coverage`

### Threshold categories

- `thresholdAll` — applies to overall project coverage
- `thresholdNew` — applies to files added in the PR (not in base branch)
- `thresholdModified` — applies to files that exist in base branch but were changed

## irongut/CodeCoverageReport

```yaml
- name: Code Coverage Report
  uses: irongut/CodeCoverageReport@v1.3.0
  with:
    filename: coverage.xml
    thresholds: '60 80'    # 60% warning, 80% failure
```

**Threshold format**: Space-separated string — first is warning, second is failure. Use the **failure** threshold.
**Grep pattern**: `CodeCoverageReport`

## 5monkeys/cobertura-action

```yaml
- name: Cobertura Coverage
  uses: 5monkeys/cobertura-action@master
  with:
    minimum_coverage: 75    # 75% minimum
```

**Threshold format**: Integer percentage. Applies as overall threshold.
**Grep pattern**: `cobertura-action`

## codecov/codecov-action

Does NOT have inline thresholds. Thresholds live in `codecov.yml` at repo root:

```yaml
# codecov.yml
coverage:
  status:
    project:
      default:
        target: 80%
    patch:
      default:
        target: 90%
```

- `project.default.target` → maps to `thresholdAll`
- `patch.default.target` → maps to `thresholdNew` and `thresholdModified`

**Grep pattern**: `codecov/codecov-action` (then look for `codecov.yml`)

## Detection Priority

When multiple coverage actions exist in the same workflow:
1. Prefer the action that runs on `pull_request` events (not just `push`)
2. Prefer the action with per-category thresholds (new/modified) over single threshold
3. If equal, use the stricter thresholds

## Parsing Coverage Reports

### Cobertura XML (most common)

Per-file coverage can be extracted from `coverage.xml`:

```xml
<package name="apps.interviews.services">
  <classes>
    <class name="scorecard_suggestion.py" filename="apps/interviews/services/scorecard_suggestion.py"
           line-rate="0.53" branch-rate="0" complexity="0">
```

`line-rate` is a decimal 0-1 representing line coverage percentage.

### Reading per-file coverage

For Python projects with `coverage.py`:
```bash
coverage report --show-missing --include="<file-pattern>"
```

For the full JSON report:
```bash
coverage json -o coverage.json
```

The JSON report has per-file details under `files.<path>.summary.percent_covered`.
