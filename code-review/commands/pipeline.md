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
  Autonomous PR review-fix-ship pipeline. Triages all bot/reviewer comments,
  implements valid fixes with parallel subagents, dismisses false positives,
  runs tests, commits, pushes, and resolves GitHub threads in one pass.
  Use when you want to resolve all PR feedback autonomously.
  Do NOT use for draft PRs or when you need manual control over each fix.
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
---

## Context
- **Repository**: !`git remote get-url origin 2>/dev/null | sed 's/.*github.com[:/]\(.*\)\.git/\1/' | sed 's/.*github.com[:/]\(.*\)/\1/'`
- **Current branch**: !`git branch --show-current`
- **PR Number**: $ARGUMENTS
- **Date**: !`date +%Y-%m-%d`
- **Working tree clean**: !`git status --porcelain | head -1 || echo "clean"`

## Phase 0: Validate

Before starting, verify:
1. PR number was provided (from $ARGUMENTS)
2. Working tree is clean (no uncommitted changes). If dirty, **STOP** and ask user to commit or stash first.
3. PR is open: `gh pr view $ARGUMENTS --json state -q '.state'` must be `OPEN`. If draft/closed/merged, **STOP**.

## Autonomous Mode Rules

This pipeline runs **without asking for input**. Follow these decision rules:

| Situation | Action |
|-----------|--------|
| Simple fix (typo, null check, import) | Implement directly |
| Multiple valid approaches | Choose the simplest, most consistent with codebase |
| Adding dependency | Prefer stdlib/existing deps over new ones |
| Architectural decision | Choose the approach matching existing patterns |
| Tests fail | Fix and retry (up to 2 attempts), then STOP |
| Unclear if issue is valid | Default to false positive (conservative) |
| No comments to triage | Report "no actionable feedback" and exit |
| All comments are false positives | Dismiss all, skip fix phases, report |
| No test suite found | Skip test phase, warn in report |

**NEVER ask for input.** Only stop if tests fail after 2 retry attempts or if validation fails.

## Phase 1: Triage

Fetch all PR comments:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/pr-triage-comments.sh OWNER REPO PR_NUMBER
```

For each comment, spawn a `comment-verifier` agent in parallel to verify it against actual code:

```
For each comment, use Agent tool with:
- subagent_type: "comment-verifier"
- prompt: "Verify this review comment:\n\nref_id: [ref_id]\nFile: [file:line]\nReviewer: @[author]\nComment: [body]"
```

Launch ALL verifier agents in a single response (parallel tool calls). Each returns a structured verdict: `VALID BUG` or `FALSE POSITIVE` with evidence.

Collect all verdicts into a running list with `ref_id` preserved.

## Phase 2: Dismiss False Positives

For each FALSE POSITIVE, dismiss immediately:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/pr-resolve-comment.sh OWNER REPO PR_NUMBER REF_ID dismiss "REASON"
```

Use concise reasons: "Already handled in [location]", "YAGNI", "Misunderstands context: [brief]", "Style preference", "Pre-existing, not introduced by this PR".

## Phase 3: Plan Fixes

For each VALID BUG, create a fix plan:
1. Read the affected code
2. Determine the minimal fix
3. Note which files are affected

Group fixes by file to detect conflicts. Fixes touching **different files** can run in parallel.

## Phase 4: Implement Fixes

### Parallel execution (different files)

For fixes that touch different files, spawn parallel subagents using the Agent tool with the `fix-implementer` agent type. Each agent runs in the background (`background: true`) with a 25-turn cap:

```
For each independent fix, use Agent tool with:
- subagent_type: "fix-implementer"
- prompt: "Fix: [issue title]. File: [path:line]. Problem: [description]. Expected fix: [solution from plan]."
```

Launch all independent fix agents in a single response (parallel tool calls). Wait for all to complete before proceeding.

### Sequential execution (same file)

For fixes touching the same file, implement them sequentially using the same `fix-implementer` agent to avoid conflicts.

### After all fixes

Read each modified file to verify no syntax errors were introduced.

## Phase 5: Run Tests

Discover and run the project test suite:

1. Check for test commands: `package.json` scripts (`test`), `Makefile` targets, `pytest.ini`/`pyproject.toml`, `Cargo.toml`, `go.mod`
2. Run the full test suite
3. If tests **pass** → continue to Phase 6
4. If tests **fail**:
   - Analyze failures
   - Fix the failing tests or the code causing failures
   - Re-run tests (attempt 2)
   - If still failing: fix again and re-run (attempt 3)
   - If still failing after attempt 3: **STOP** and report which tests fail and why

## Phase 6: Commit and Push

Create a structured commit:

```
fix: resolve PR #{PR_NUMBER} review feedback

Fixes applied:
- [Brief description of each fix]

Dismissed as false positives:
- [Count] comments dismissed

Reviewed-by: Claude Code
```

Then push:
```bash
git push
```

## Phase 7: Resolve GitHub Threads

For each VALID BUG that was fixed, resolve the thread:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/pr-resolve-comment.sh OWNER REPO PR_NUMBER REF_ID resolve
```

## Phase 8: Report

Output a final summary:

```
## Pipeline Results - PR #[number]

### Fixed ([count])
- [ref_id] [file:line] - [brief description of fix]

### Dismissed ([count])
- [ref_id] [file:line] - [reason]

### Threads Resolved ([count])

### Tests: PASS/FAIL

### Commits: [commit hash] pushed to [branch]
```
