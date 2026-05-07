---
disable-model-invocation: true
allowed-tools:
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/*)
  - Bash(git *)
  - Bash(gh *)
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
argument-hint: PR#
description: |
  Use when you want to resolve all PR feedback autonomously in a single pass.
  Do NOT use for draft PRs or when you need manual control over individual fixes.
keywords:
  - autonomous-pipeline
  - review-fix-ship
  - pr-pipeline
  - auto-fix
  - batch-review
triggers:
  - "run the full review pipeline"
  - "autonomous PR review"
  - "fix all PR comments"
  - "review fix and ship"
  - "resolve all PR feedback"
skills:
  - technical-decisions
  - receiving-code-review
  - coverage-gate
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this command and proceed with your assigned task.
</SUBAGENT-STOP>

## Context
- **Repository**: !`git remote get-url origin`
- **Current branch**: !`git branch --show-current`
- **PR Number**: $ARGUMENTS
- **Date**: !`date +%Y-%m-%d`
- **Working tree clean**: !`git status --short`

## Phase 0: Validate

1. PR number was provided (from `$ARGUMENTS`)
2. Working tree is clean. If dirty, **STOP** and ask user to commit or stash.
3. PR is open: `gh pr view $ARGUMENTS --json state -q '.state'` must be `OPEN`. If draft/closed/merged, **STOP**.

## Autonomous mode

This pipeline runs **without asking for input**. For the full decision-rules table covering simple fixes, ambiguous cases, test failures, coverage misses, and scope leaks from auto-formatters, see `@pipeline.references/phase-details.md` (Autonomous mode rules section).

**NEVER ask for input.** Only stop if tests fail after 2 retry attempts or if validation fails.

## Phase 1: Triage

Fetch all PR comments and verify each in parallel using the `comment-verifier` agent. Collect `VALID BUG` / `FALSE POSITIVE` verdicts with `ref_id` preserved.

For the exact script invocation and verifier-prompt format, see `@pipeline.references/phase-details.md` (Phase 1 detail).

## Phase 2: Dismiss false positives

For each `FALSE POSITIVE`, run `pr-resolve-comment.sh ... dismiss "REASON"`. For canonical reason phrases, see `@pipeline.references/phase-details.md` (Phase 2 detail).

## Phase 3: Plan fixes

For each `VALID BUG`:
1. Read affected code
2. Determine the minimal fix
3. Note which files are affected

Group fixes by file. Fixes touching **different files** can run in parallel; fixes touching the **same file** run sequentially.

## Phase 4: Implement fixes

- **Parallel** (different files) — spawn `fix-implementer` agents in parallel.
- **Sequential** (same file) — run `fix-implementer` one at a time to avoid conflicts.
- **After all fixes** — read each modified file to verify no syntax errors.
- **Scope check** — discard auto-formatter-induced changes to files NOT in the fix plan via `git checkout -- <file>`; log the count.

For agent prompts, parallel-launch instructions, and the full scope-check procedure, see `@pipeline.references/phase-details.md` (Phase 4 detail).

## Phase 5: Run tests

Skip if no code changes were made (go to Phase 8). Discover the project's test runner, run the suite, fix-and-retry on failure (up to 3 attempts, then STOP).

For runner-discovery order and the failure handling sequence, see `@pipeline.references/phase-details.md` (Phase 5 detail).

## Phase 5b: Coverage gate

Detect CI coverage config in `.github/workflows/*.yml`. If none, skip and note in report. If present, extract thresholds, categorize new/modified files by diff against the PR base, run coverage, gate per-file, and write additional tests for uncovered lines (up to 2 cycles).

For threshold parsing, file categorization, and the cycle-limit behavior, see `@pipeline.references/phase-details.md` (Phase 5b detail).

## Phase 6: Commit and push

Skip if no code changes were made. Otherwise create a structured commit and `git push`.

For the commit-message template, see `@pipeline.references/phase-details.md` (Phase 6 detail).

## Phase 7: Resolve GitHub threads

For each `VALID BUG` that was fixed, run `pr-resolve-comment.sh ... resolve`.

## Phase 8: Report

Print a final summary covering Fixed, Dismissed, Threads Resolved, Tests, Coverage, and Commits. For the report template, see `@pipeline.references/phase-details.md` (Phase 8 detail).
