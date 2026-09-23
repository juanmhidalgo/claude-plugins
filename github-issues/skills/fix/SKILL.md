---
name: fix
description: |
  Deprecated alias of /github-issues:work, kept until 2.0. Use /github-issues:work.
argument-hint: "<issue-url | #number> [--part N[,M]]"
disable-model-invocation: true
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
  - Bash(gh pr list *)
  - Bash(gh repo view *)
  - Bash(git checkout *)
  - Bash(git branch *)
  - Bash(git log *)
  - Bash(git diff *)
  - Bash(git show *)
  - Bash(git blame *)
  - Bash(git status)
  - Bash(git stash *)
  - Bash(npm test *)
  - Bash(npx jest *)
  - Bash(npx vitest *)
  - Bash(pytest *)
  - Bash(python -m pytest *)
  - Bash(make *)
  - Bash(cargo test *)
  - Bash(go test *)
  - Bash(uv run *)
  - Bash(pipenv run *)
  - Bash(poetry run *)
  - mcp__clickup-local__link_pr_to_task
hooks:
  - event: Stop
    once: true
    command: |
      echo "If the run stopped at the verification gate: decide on the verdict, or post the ledger's corrections to the issue."
      echo "If it implemented the plan:"
      echo "  - Run your test suite to verify no regressions"
      echo "  - Commit, push, and open a PR (Closes #N only if the whole issue is resolved; Refs #N otherwise)"
      echo "  - If this work requires changes in another repo, check the handoff prompt above"
---

## Context

- **Repository**: !`git remote get-url origin 2>/dev/null || echo "no remote"`
- **Current branch**: !`git branch --show-current`
- **HEAD**: !`git log -1 --format='%h %cs' 2>/dev/null`
- **Working tree clean**: !`git status --porcelain | head -5 | wc -l | xargs -I{} sh -c 'if [ {} -eq 0 ]; then echo "yes"; else echo "no — {} uncommitted changes"; fi'`

## Deprecated

`/github-issues:fix` was renamed to `/github-issues:work`: the skill covers tech debt,
refactors, and follow-ups as well as bugs. This alias is removed in 2.0.

1. Tell the user that once, in one line.
2. Read `../work/SKILL.md`, relative to this skill's base directory, and follow it from
   **Arguments** onward with these arguments: `$ARGUMENTS`. Its reference links are relative
   to `../work/`. The context above replaces its Context section.
