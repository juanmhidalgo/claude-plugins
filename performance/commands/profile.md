---
description: |
  Use to profile a specific function, endpoint, or component and identify bottlenecks with timing data.
  Do NOT use without a specific target — run /performance:audit for codebase-wide scans first.
argument-hint: "<file:function or endpoint>"
keywords:
  - profile
  - benchmark
  - timing
  - bottleneck
triggers:
  - "profile this function"
  - "benchmark this endpoint"
  - "why is this slow"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(npm run *)
  - Bash(npx jest *)
  - Bash(python -m cProfile *)
  - Bash(python -m timeit *)
  - Bash(node -e *)
  - Bash(git diff *)
  - Edit
  - Write
hooks:
  - event: Stop
    once: true
    command: |
      echo "Profiling complete."
      echo "  - /performance:audit for broader analysis"
---

## Context

- **Branch**: !`git branch --show-current`

## Focused Profiling

Target: **$ARGUMENTS**

### Step 1: Understand the Code

Read the target function/endpoint. Understand what it does, what it calls, and what data flows through it.

### Step 2: Identify Measurement Approach

Based on the language and context:

**Python:**
```bash
python -m cProfile -s cumulative script.py
python -m timeit -s "setup" "expression"
```

**Node.js:**
```javascript
console.time('operation');
// ... code ...
console.timeEnd('operation');
```

**Database queries:**
- Enable query logging to see actual SQL and timing
- Check for N+1 patterns in the query log
- Look for missing indexes on WHERE/JOIN columns

### Step 3: Profile

Run the profiling tool and collect baseline numbers. Record:
- Total execution time
- Hot spots (functions consuming the most time)
- Call counts (functions called most frequently)
- Memory allocation (if relevant)

### Step 4: Analyze & Recommend

For each hot spot:
1. Is it doing unnecessary work? (redundant computation, fetching unused data)
2. Is it doing work at the wrong time? (could be cached, deferred, or parallelized)
3. Is it using an inefficient algorithm? (O(n²) when O(n) is possible)

Provide specific fix recommendations with expected improvement.
