# Error Patterns Reference

## Test Failure Patterns

### Changed covered code
```
Test fails after modifying code the test covers:
├── Is the test outdated? → Update the test to match new behavior
└── Is the code buggy? → Fix the code, keep the test
```

### Changed unrelated code
```
Test fails after modifying code the test does NOT cover:
├── Shared state? → Check globals, singletons, module-level vars
├── Import side effects? → Check module initialization order
├── Test pollution? → Run the test in isolation to confirm
└── Transitive dependency? → Check if changed module is imported indirectly
```

### Flaky tests
```
Test passes sometimes, fails sometimes:
├── Timing-dependent? → setTimeout, race conditions, async not awaited
├── Order-dependent? → Run in isolation vs. in full suite
├── External dependency? → Network, database, file system, clock
└── Non-deterministic data? → Random values, timestamps, UUIDs in assertions
```

## Build Failure Patterns

### Type errors
- Read the error message carefully — it usually points to the exact location
- Check if a function signature changed but callers weren't updated
- Check if a type was narrowed or widened unexpectedly
- Search for the type name to find all usages

### Import errors
- Does the module exist at the path specified?
- Do the exports match what's being imported? (default vs. named)
- Is the tsconfig/webpack alias configured correctly?
- Circular imports? Check the dependency chain.

### Dependency errors
- Run `npm install` / `pip install -r requirements.txt`
- Check lockfile for conflicts
- Check Node/Python version compatibility
- Peer dependency mismatches?

## Runtime Error Patterns

### TypeError: Cannot read property 'x' of undefined
Most common runtime error. Trace the data flow:
1. Where is the variable defined?
2. Where is it assigned a value?
3. What conditions could make it undefined at the point of access?
4. Is there an async timing issue (value not yet loaded)?

### Network / CORS errors
1. Is the URL correct? (typos, wrong port, wrong protocol)
2. Is the server running?
3. Are CORS headers configured for the requesting origin?
4. Are credentials included when needed?
5. Is there a proxy misconfiguration?

### Unhandled promise rejection
1. Find the async operation that's failing
2. Check if `.catch()` or try/catch is missing
3. Check what error the promise rejects with
4. Is the error handler itself throwing?

## Non-Reproducible Bug Patterns

### Timing-dependent
- Add timestamps to logs around the suspected area
- Insert artificial delays to widen race windows
- Run under load or concurrency to increase collision probability
- Check for missing `await` on async operations

### Environment-dependent
- Compare runtime versions (Node, Python, browser)
- Compare environment variables
- Check for differences in data (empty vs. populated database)
- Try reproducing in CI where the environment is clean

### State-dependent
- Check for leaked state between tests or requests
- Look for global variables, singletons, or shared caches
- Run the failing scenario in isolation vs. after other operations
- Check if database state affects the outcome

### Truly random
- Add defensive logging at the suspected location
- Set up an alert for the specific error signature
- Document the conditions observed and revisit when it recurs
- Check for uninitialized variables or undefined behavior

## Git Bisect for Regressions

When something worked before and stopped working:

```bash
# Start bisecting
git bisect start
git bisect bad                    # Current commit is broken
git bisect good <known-good-sha> # This commit worked

# Automated: run a test at each bisect point
git bisect run npm test -- --grep "failing test"

# Manual: git checks out midpoints, you test each one
# Mark as: git bisect good / git bisect bad

# When done
git bisect reset
```

## Safe Fallback Patterns

When under time pressure, use safe fallbacks while investigating the root cause:

```typescript
// Safe default + warning (instead of crashing)
function getConfig(key: string): string {
  const value = process.env[key];
  if (!value) {
    console.warn(`Missing config: ${key}, using default`);
    return DEFAULTS[key] ?? '';
  }
  return value;
}

// Graceful degradation (instead of broken feature)
function renderChart(data: ChartData[]) {
  if (data.length === 0) {
    return <EmptyState message="No data available" />;
  }
  try {
    return <Chart data={data} />;
  } catch (error) {
    console.error('Chart render failed:', error);
    return <ErrorState message="Unable to display chart" />;
  }
}
```

These are **temporary mitigations**, not fixes. Always follow up with proper root cause analysis.
