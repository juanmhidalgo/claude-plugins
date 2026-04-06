---
description: Performance audit with measure-first approach — identifies bottlenecks, anti-patterns, and recommends targeted fixes
argument-hint: "[path, endpoint, or scope]"
keywords:
  - performance
  - optimization
  - profiling
  - bottleneck
triggers:
  - "check performance"
  - "find bottlenecks"
  - "performance audit"
  - "optimize this"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(npm run *)
  - Bash(npx lighthouse *)
  - Bash(npx bundlesize *)
  - Bash(npx webpack-bundle-analyzer *)
  - Bash(python -m cProfile *)
  - Bash(python -m timeit *)
  - Bash(git diff *)
  - Bash(git log *)
  - Bash(du *)
  - Bash(wc *)
  - Agent
hooks:
  - event: Stop
    once: true
    command: |
      echo "Performance audit complete. Next steps:"
      echo "  - Fix identified bottlenecks (highest impact first)"
      echo "  - Re-measure after each fix to verify improvement"
      echo "  - /code-review:branch to review changes"
---

## Context

- **Branch**: !`git branch --show-current`
- **Recent commits**: !`git log --oneline -5`

<best_practices>
@performance/skills/performance-optimization/SKILL.md
</best_practices>

## Performance Audit Workflow

Audit scope: **$ARGUMENTS** (if empty, audit the full codebase for anti-patterns).

**Rule: NEVER optimize without measurement. Measure → Identify → Fix → Verify → Guard.**

### Phase 1: Scope & Stack Detection

1. Determine audit scope from argument (specific path, endpoint, or full app)
2. Detect the stack: frontend (React, Vue, etc.), backend (Node, Python, etc.), or both
3. Identify build tools, test frameworks, and available profiling commands

### Phase 2: Anti-Pattern Scan

Search the codebase for common performance anti-patterns:

**Backend:**
- N+1 queries: nested loops with database calls, missing `include`/`select_related`
- Unbounded fetches: `findMany()` / `SELECT *` without `LIMIT` or pagination
- Blocking operations in async contexts
- Missing database indexes for frequently queried columns

**Frontend:**
- Large bundle: importing entire libraries instead of specific functions
- Missing code splitting: no `lazy()` / dynamic `import()`
- Unnecessary re-renders: inline object/function creation in JSX
- Images without dimensions, lazy loading, or responsive sources
- Render-blocking CSS/JS in the head

### Phase 3: Measurement

Run appropriate profiling tools:
- **Frontend**: Bundle size analysis, Lighthouse (if available)
- **Backend**: Query logging, endpoint response times
- **Both**: Build time, test suite duration

### Phase 4: Report

For each finding:
1. **What**: The specific anti-pattern or bottleneck
2. **Where**: File path and line number
3. **Impact**: Estimated performance effect (high/medium/low)
4. **Fix**: Concrete code change with before/after
5. **Verify**: How to measure the improvement

Organize findings by impact (highest first).
