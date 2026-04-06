---
name: performance-optimization
description: |
  Use when performance requirements exist, profiling reveals bottlenecks, or Core Web Vitals need improvement.
  Provides measure-first workflow, bottleneck identification patterns, and performance budgets.
  Do NOT use without evidence of a problem — premature optimization adds complexity.
keywords:
  - performance
  - optimization
  - profiling
  - web-vitals
  - n-plus-one
triggers:
  - "optimize performance"
  - "make this faster"
  - "Core Web Vitals"
  - "page load too slow"
code-triggers:
  - "findMany"
  - "SELECT *"
  - "React.memo"
  - "useMemo"
  - "useCallback"
  - "lazy("
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Performance Optimization

Measure before optimizing. Performance work without measurement is guessing. Profile first, identify the actual bottleneck, fix it, measure again.

## The Optimization Workflow

```
1. MEASURE  → Establish baseline with real data
2. IDENTIFY → Find the actual bottleneck (not assumed)
3. FIX      → Address the specific bottleneck
4. VERIFY   → Measure again, confirm improvement
5. GUARD    → Add monitoring or tests to prevent regression
```

## Core Web Vitals Targets

| Metric | Good | Needs Work | Poor |
|--------|------|------------|------|
| **LCP** (Largest Contentful Paint) | ≤ 2.5s | ≤ 4.0s | > 4.0s |
| **INP** (Interaction to Next Paint) | ≤ 200ms | ≤ 500ms | > 500ms |
| **CLS** (Cumulative Layout Shift) | ≤ 0.1 | ≤ 0.25 | > 0.25 |

## Symptom-Based Decision Tree

```
What is slow?
├── First page load
│   ├── Large bundle? → Measure bundle size, check code splitting
│   ├── Slow server response? → Measure TTFB, check API/database
│   └── Render-blocking resources? → Check waterfall for CSS/JS blocking
├── Interaction feels sluggish
│   ├── UI freezes? → Profile main thread, look for long tasks (>50ms)
│   ├── Form input lag? → Check re-renders, controlled component overhead
│   └── Animation jank? → Check layout thrashing, forced reflows
├── Page after navigation
│   ├── Data loading? → Measure API times, check for fetch waterfalls
│   └── Client rendering? → Profile component render, check N+1 fetches
└── Backend / API
    ├── Single endpoint slow? → Profile queries, check indexes
    ├── All endpoints slow? → Check connection pool, memory, CPU
    └── Intermittent? → Check lock contention, GC pauses, external deps
```

## Performance Budget

| Target | Threshold |
|--------|-----------|
| JavaScript bundle (initial, gzipped) | < 200KB |
| CSS (gzipped) | < 50KB |
| Images (above the fold) | < 200KB each |
| API response time (p95) | < 200ms |
| Lighthouse Performance score | ≥ 90 |

## Anti-Rationalizations

| Excuse | Reality |
|--------|---------|
| "We'll optimize later" | Performance debt compounds. Fix obvious anti-patterns now, defer micro-optimizations. |
| "It's fast on my machine" | Your machine isn't the user's. Profile on representative hardware and networks. |
| "This optimization is obvious" | If you didn't measure, you don't know. Profile first. |
| "Users won't notice 100ms" | Research shows 100ms delays impact conversion rates. Users notice more than you think. |
| "The framework handles performance" | Frameworks can't fix N+1 queries, oversized bundles, or missing indexes. |

## Red Flags

- Optimization without profiling data to justify it
- N+1 query patterns in data fetching
- List endpoints without pagination
- Images without dimensions, lazy loading, or responsive sizes
- Bundle size growing without review
- No performance monitoring in production
- `React.memo` / `useMemo` everywhere (overusing is as bad as underusing)

## Verification

After any performance change:

- [ ] Before and after measurements exist (specific numbers)
- [ ] The specific bottleneck is identified and addressed
- [ ] Core Web Vitals within "Good" thresholds (if applicable)
- [ ] Bundle size hasn't increased significantly
- [ ] No N+1 queries in new data fetching code
- [ ] Existing tests still pass (optimization didn't break behavior)

For the full checklist, see [performance-checklist.md](references/performance-checklist.md).
