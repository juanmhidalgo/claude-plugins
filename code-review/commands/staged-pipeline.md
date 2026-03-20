---
disable-model-invocation: true
allowed-tools:
  - Bash(git *)
  - Bash(npm *)
  - Bash(npx *)
  - Bash(yarn *)
  - Bash(pnpm *)
  - Bash(pytest *)
  - Bash(python *)
  - Bash(make *)
  - Bash(cargo *)
  - Bash(go *)
  - Read
  - Write
  - Edit
  - Agent
  - Glob
  - Grep
  - EnterPlanMode
  - ExitPlanMode
argument-hint: "[focus area]"
description: |
  Review staged changes, verify findings, and fix confirmed issues — all in one session.
  Runs the review in a forked context to preserve main context for verification and fixes.
  Use when you want to review and fix staged changes before committing.
  Do NOT use for PR reviews (use /code-review:pipeline) or read-only reviews (use /code-review:staged).
keywords:
  - staged-pipeline
  - review-and-fix
  - pre-commit
  - staged-changes
  - autonomous-review
triggers:
  - "review and fix staged"
  - "staged pipeline"
  - "review fix commit"
  - "fix staged issues"
skills:
  - receiving-code-review
  - technical-decisions
  - coverage-gate
hooks:
  - event: Stop
    once: true
    command: |
      echo "Staged review pipeline complete."
      echo "  - /commit to commit the changes"
      echo "  - git diff to review what was changed"
---

## Context
- **Current branch**: !`git branch --show-current`
- **Staged files**: !`git diff --cached --name-only`
- **Focus area**: $ARGUMENTS

## Phase 0: Validate

1. Check staged changes exist: `git diff --cached --name-only` must return files. If empty, **STOP** and tell user to stage changes first.
2. Note the staged file list for later phases.

## Phase 1: Review (Forked)

Launch a **single Agent** with `subagent_type: "general-purpose"` to perform the full review in an isolated context.

The agent's review output returns as its result — **no files are written**.

Agent prompt — include all of this:

```
You are reviewing staged git changes. Run a thorough code review and return structured findings.

## Step 1: Get the Diff

Run: git diff --cached
For large diffs, review file by file: git diff --cached -- <file>
Read full files when needed for surrounding context.

## Step 2: Analyze

Focus on:
- Security vulnerabilities (injection, auth issues, secrets)
- Performance problems (N+1 queries, memory leaks, blocking calls)
- Bug risks (edge cases, null checks, race conditions)
- Code quality (readability, maintainability)
- Missing tests for new/changed functionality

[If focus area was provided]: Pay special attention to: [focus area]

## Step 3: Return Structured Findings

Return ONLY findings in this exact format. No preamble, no summary, just the findings list:

### FINDING 1
- **Severity**: CRITICAL | HIGH | MEDIUM | LOW
- **File**: <file path>
- **Line**: <line number or range>
- **Category**: security | performance | bug | code-quality | testing
- **Issue**: <what's wrong>
- **Suggested fix**: <concrete fix description>

### FINDING 2
...

If no issues found, return: "NO ISSUES FOUND"
```

## Phase 2: Verify Findings

After the forked agent returns, process its findings:

1. **If "NO ISSUES FOUND"** — report clean review and stop
2. **For each finding**, read the actual file and verify:

| Check | How |
|-------|-----|
| File and line match | Read the file, confirm the code exists at that location |
| Issue is real | Verify the finding is technically correct |
| Context was understood | Check surrounding code the reviewer may not have seen |
| Aligns with project conventions | Check existing patterns |

**Classify each finding:**
- **CONFIRMED** — issue exists and finding is correct
- **INCORRECT** — finding misunderstands the code or is technically wrong
- **DISPUTED** — debatable, needs user input

Drop INCORRECT findings silently.

## Phase 3: Present & Approve (Plan Mode)

Enter plan mode using the EnterPlanMode tool.

Present findings grouped by status:

```
## Staged Review Findings

### Confirmed ([count])
For each: severity, file:line, issue, proposed fix

### Disputed ([count])
For each: what the review says vs what the code does, your assessment

### Dropped ([count])
[count] findings rejected as incorrect (not shown)
```

**Wait for user to approve which findings to fix.** Do NOT proceed until the user confirms.

## Phase 4: Implement Fixes

After user approval, exit plan mode with ExitPlanMode tool.

### Parallel execution (different files)

For fixes touching **different files**, spawn parallel `fix-implementer` agents:

```
For each independent fix, use Agent tool with:
- subagent_type: "code-review:fix-implementer"
- prompt: "Fix: [issue]. File: [path:line]. Problem: [description]. Fix: [suggested fix]."
```

Launch all independent fix agents in a single response. Do NOT use run_in_background.

### Sequential execution (same file)

For fixes touching the **same file**, implement them sequentially to avoid conflicts.

### After all fixes

Read each modified file to verify no syntax errors were introduced.

## Phase 5: Test

Discover and run the project test suite:

1. Check for test commands: `package.json` scripts, `Makefile` targets, `pytest.ini`/`pyproject.toml`, `Cargo.toml`, `go.mod`
2. Run the test suite
3. If tests **pass** → continue to Phase 6
4. If tests **fail**:
   - Analyze failures, fix, re-run (up to 2 retries)
   - If still failing after retries: **STOP** and report which tests fail

## Phase 5b: Coverage Gate

After tests pass, check if the repository has CI coverage thresholds:

1. **Detect GHA coverage config**: Search `.github/workflows/*.yml` for coverage actions (`orgoro/coverage`, `CodeCoverageReport`, `cobertura-action`, `codecov`)
2. **If no coverage config found**: Skip this phase, note "Coverage: SKIPPED (no CI config)" in report
3. **If coverage config found**:
   a. Extract thresholds and normalize to 0-100 percentages
   b. Categorize staged files:
      - New: `git diff --cached --name-only --diff-filter=A` (source files only)
      - Modified: `git diff --cached --name-only --diff-filter=M` (source files only)
   c. Run test suite with coverage report generation
   d. Parse per-file coverage from the report
   e. Check each file against its category threshold
   f. **If all pass**: Continue to Phase 6
   g. **If below threshold**:
      - Identify uncovered lines in failing files
      - Write additional tests targeting those lines
      - Re-run coverage (up to 2 additional cycles)
      - If still failing after 2 cycles: report which files are below threshold, continue to Phase 6

## Phase 6: Stage and Report

1. Stage the fixed files: `git add <modified files>`
2. Output a summary:

```
## Staged Pipeline Results

### Reviewed: [count] staged files
### Findings: [count] confirmed, [count] disputed, [count] dropped
### Fixed: [count]
- [file:line] — [brief description of fix]

### Tests: PASS/FAIL

### Coverage: PASS/FAIL/SKIPPED
- [If applicable: files below threshold with current % vs required %]

### Ready to commit: Yes/No
```
