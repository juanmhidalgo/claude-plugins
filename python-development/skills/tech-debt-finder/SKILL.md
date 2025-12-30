---
name: tech-debt-finder
description: Find technical debt in Python projects. Scans for debt markers (TODO/FIXME/HACK), code smells, complexity issues, and framework anti-patterns (Django, Flask, FastAPI). Outputs prioritized P1/P2/P3 markdown reports. Use when asked to audit code quality, find refactoring opportunities, identify legacy code issues, or generate a tech debt report.
---

# Tech Debt Finder

Analyze Python codebases to identify and document technical debt. Generates actionable reports for tracking improvements in existing or legacy projects.

## Workflow

1. **Discover project structure** — Identify Python files, framework in use, and available analysis tools
2. **Scan for debt indicators** — Search for patterns in [references/patterns.md](references/patterns.md)
3. **Run optional tools** — If radon/flake8/pylint available, incorporate output
4. **Generate report** — Produce prioritized markdown report

## Quick Start

```bash
# Find Python files (exclude migrations, cache, venv)
find . -name "*.py" -not -path "*/\.*" -not -path "*/migrations/*" -not -path "*/__pycache__/*" -not -path "*/venv/*" -not -path "*/.venv/*"

# Search for debt markers
grep -rn "TODO\|FIXME\|HACK\|XXX" --include="*.py" .

# Find broad exception handlers
grep -rn "except:\|except Exception:" --include="*.py" .
```

## Tool Integration (Optional)

Use only if already installed—do not install unless requested:

```bash
# Complexity analysis
which radon &>/dev/null && radon cc . -a -s -n C

# Linting summary
which flake8 &>/dev/null && flake8 . --statistics --count -q

# Refactoring suggestions
which pylint &>/dev/null && pylint --disable=all --enable=R --score=n .
```

## Report Format

```markdown
# Technical Debt Report: [Project Name]

**Generated:** [Date]  
**Files Analyzed:** [Count]  
**Framework:** [Django/Flask/FastAPI/None]

## Summary

| Category | Count | Priority |
|----------|-------|----------|
| Debt Markers | X | P2 |
| Complex Functions | X | P1 |
| Code Smells | X | P1-P2 |

## P1 - High Priority
[Items impacting maintainability or likely to cause bugs]

## P2 - Medium Priority
[Address in normal development cycle]

## P3 - Low Priority
[Track in backlog]

## Detailed Findings
[Organized by category with file:line references]

## Recommendations
[Top 3-5 actionable improvements]
```

## Priority Definitions

**P1 - High**
- Cyclomatic complexity > 15
- Files > 500 lines
- Deep nesting > 4 levels
- Broad exception handling
- Security-related TODOs

**P2 - Medium**
- Functions > 50 lines
- TODO/FIXME comments
- Hardcoded secrets/config
- Missing type hints in public APIs

**P3 - Low**
- HACK/XXX comments
- `# noqa` / `# type: ignore`
- Minor style issues

## References

See [references/patterns.md](references/patterns.md) for complete scanning patterns by category.
