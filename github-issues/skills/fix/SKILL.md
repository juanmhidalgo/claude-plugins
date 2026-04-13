---
name: fix
description: |
  Use when the user provides a GitHub Issue URL and wants to fix it in the current repo.
  Provides phased workflow: fetch issue, create branch, explore codebase, plan fix, implement, and multi-repo handoff.
  Do NOT use for feature requests without a clear bug, issues in repos the user hasn't cloned,
  or PRs (use /code-review instead).
argument-hint: "<github-issue-url>"
disable-model-invocation: true
keywords:
  - github
  - issue
  - bug
  - fix
  - pull-request
triggers:
  - "fix this issue"
  - "work on this issue"
  - "fix this bug from github"
  - "implement this github issue"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Edit
  - Write
  - Agent
  - Bash(gh issue view *)
  - Bash(gh issue comment *)
  - Bash(gh pr create *)
  - Bash(gh pr view *)
  - Bash(git checkout *)
  - Bash(git branch *)
  - Bash(git log *)
  - Bash(git diff *)
  - Bash(git status)
  - Bash(git stash *)
  - Bash(npm test *)
  - Bash(npx jest *)
  - Bash(pytest *)
  - Bash(python -m pytest *)
  - Bash(make *)
  - Bash(cargo test *)
  - Bash(go test *)
hooks:
  - event: Stop
    once: true
    command: |
      echo "Fix complete. Next steps:"
      echo "  - Run your test suite to verify no regressions"
      echo "  - /ship to commit, push, and open a PR"
      echo "  - If this fix requires changes in another repo, check the handoff prompt above"
---

## Context

- **Repository**: !`git remote get-url origin 2>/dev/null || echo "no remote"`
- **Current branch**: !`git branch --show-current`
- **Working tree clean**: !`git status --porcelain | head -5 | wc -l | xargs -I{} sh -c 'if [ {} -eq 0 ]; then echo "yes"; else echo "no — {} uncommitted changes"; fi'`

## Issue to Fix

**URL**: $ARGUMENTS

## Workflow

Follow these phases in order. Do NOT skip phases or advance without user approval.

### Phase 1: Fetch Issue

1. **Validate the argument.** It must be a GitHub Issue URL matching `https://github.com/{owner}/{repo}/issues/{number}`. If invalid, **STOP** and ask for a valid URL.
2. **Extract** `owner`, `repo`, and `issue number` from the URL.
3. **Fetch the issue:**
   ```bash
   gh issue view {number} --repo {owner}/{repo} --json title,body,labels,comments,assignees,milestone,state
   ```
   If the issue is closed, warn the user and ask whether to proceed.
4. **Summarize** to the user: title, labels, reproduction steps, expected vs actual behavior, error messages, and relevant comments. Flag any mentions of other repositories.
5. **Check for linked PRs or duplicates** referenced in the body or comments.

### Phase 2: Branch

1. If there are uncommitted changes, warn and suggest stashing.
2. Create a fix branch: `git checkout -b fix/issue-{number}-{slug}` (slug: 3-4 lowercase hyphenated words from the title).
3. Confirm branch creation.

### Phase 3: Explore

1. **Start from clues** in the issue: error messages, file paths, function names, stack traces.
2. **Widen** if needed: keyword search, `git log --oneline -20 -- {path}`, related test files.
3. **Build the picture**: which files, what's wrong, what's correct, localized or cross-cutting.

If exploration exceeds 10 minutes without a clear picture, **STOP** and present findings. This limit is intentionally tighter than the global 15-minute limit — a single issue should converge faster or needs user guidance.

### Phase 4: Plan

**Enter plan mode.** Present a structured fix proposal using the [plan template](references/plan-template.md). Wait for user approval before proceeding.

### Phase 5: Implement

1. Implement the fix following the approved plan, file by file.
2. Write regression tests that fail without the fix and pass with it.
3. Run the project's test suite. Do NOT proceed with failing tests.

### Phase 6: Multi-Repo Check

1. Ask: "Does this fix require changes in other repositories?"
2. If yes, generate a self-contained handoff prompt (see [critical rules](references/critical-rules.md) for format).
3. If no, skip this phase.

For safety guidelines that apply across all phases, see [critical rules](references/critical-rules.md).
