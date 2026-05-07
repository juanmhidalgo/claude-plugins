---
description: |
  Use for quick error classification and diagnosis of test failures, build errors, or runtime issues.
  Do NOT use for systematic debugging — use /debug:debug for the full reproduce→fix cycle.
argument-hint: "<error message or context>"
keywords:
  - triage
  - error
  - diagnosis
  - classify
triggers:
  - "triage this error"
  - "what kind of error is this"
  - "classify this failure"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(npm test *)
  - Bash(npx jest *)
  - Bash(pytest *)
  - Bash(git log *)
  - Bash(git diff *)
hooks:
  - event: Stop
    once: true
    command: |
      echo "Triage complete."
      echo "  - /debug:debug to start systematic debugging"
---

## Context

- **Branch**: !`git branch --show-current`
- **Recent commits**: !`git log --oneline -5`

## Quick Error Triage

Error to classify: **$ARGUMENTS**

Classify the error and provide targeted investigation steps.

### Test Failure

```
Test fails after code change:
├── Did you change code the test covers?
│   └── YES → Is the test or the code wrong?
│       ├── Test is outdated → Update the test
│       └── Code has a bug → Fix the code
├── Did you change unrelated code?
│   └── YES → Likely a side effect
│       → Check shared state, imports, globals, singletons
└── Test was already flaky?
    └── Check for timing issues, order dependence, external deps
```

### Build Failure

```
Build fails:
├── Type error → Read the error, check types at the cited location
├── Import error → Module exists? Exports match? Paths correct?
├── Config error → Build config syntax/schema issues
├── Dependency error → Check package.json/requirements.txt, run install
└── Environment error → Check runtime version, OS compatibility
```

### Runtime Error

```
Runtime error:
├── TypeError: Cannot read property of undefined
│   → Something is null/undefined that shouldn't be
│   → Trace the data flow: where does this value come from?
├── Network error / CORS
│   → Check URLs, headers, server CORS config
├── Render error / White screen
│   → Check error boundary, console, component tree
├── Permission / Auth error
│   → Check tokens, session, middleware, role checks
└── Unexpected behavior (no error thrown)
    → Add logging at key points, verify data at each step
```

### Output

For each error:
1. **Classification**: Error type and layer
2. **Likely cause**: Most probable root cause based on the pattern
3. **Investigation steps**: 2-3 specific things to check, with commands
4. **Quick fix vs. proper fix**: If there's a tempting shortcut, explain why the proper fix is better
