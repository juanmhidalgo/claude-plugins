---
name: branch-review
description: |
  Use when reviewing branch changes or PRs for merge readiness.
  Provides severity classification, feedback format, and review anti-patterns.
  Do NOT use for general code quality advice or linting - use dedicated linters instead.
keywords:
  - code-review
  - branch-comparison
  - diff-analysis
  - pr-preparation
  - security-checklist
triggers:
  - "review branch changes"
  - "compare branches"
  - "analyze diff"
  - "prepare PR for merge"
  - "check code before merge"
allowed-tools:
  - Bash(git *)
  - Read
  - Grep
agent: code-review:branch-reviewer
user-invocable: true
---

# Branch Review

## Severity Classification

| Level | Block Merge? | Examples |
|-------|--------------|----------|
| CRITICAL | Yes | Security vulnerabilities, data loss risks, breaking changes without migration |
| HIGH | Should fix | Bugs affecting users, performance regressions, missing error handling |
| MEDIUM | Recommend | Code smells, minor perf issues, missing non-critical tests |
| LOW | Optional | Style issues, refactoring opportunities, docs |

## Feedback Format

```markdown
**[SEVERITY]** Brief title

📍 `path/to/file.py:42`

**Issue:** Clear description of the problem

**Risk:** What could go wrong

**Suggestion:**
```python
# Recommended fix
```
```

## Focus Areas (Non-Obvious)

**Security** - Hardcoded secrets, missing input validation, SQL injection, auth gaps

**Bugs** - Race conditions in concurrent code, resource leaks (connections, file handles)

**Performance** - N+1 queries, blocking calls in async contexts, missing pagination

## Review Anti-Patterns

1. **Nitpicking** - Don't block on minor style issues
2. **Rubber stamping** - Actually read the code
3. **Bike-shedding** - Focus on important issues
4. **No context** - Understand the "why" before criticizing

## Request Changes vs Comment

**Request Changes:** Security issues, bugs affecting users, breaking changes, missing critical tests

**Comment Only:** Suggestions, questions about approach, style preferences, future considerations
