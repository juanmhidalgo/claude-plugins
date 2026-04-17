---
allowed-tools:
  - Bash(git *)
  - Agent
  - Read
argument-hint: "[staged | base-branch]"
description: |
  Analyze changes for technical debt before committing or merging.
  Supports two scopes: "staged" for staged changes, or a base branch for branch comparison.
  Use when you want to check if changes introduce maintainability issues.
  Do NOT use for bug detection or security review.
keywords:
  - tech-debt
  - technical-debt
  - code-quality
  - maintainability
  - refactoring
triggers:
  - "check for tech debt"
  - "analyze technical debt"
  - "review code quality"
  - "check maintainability"
  - "tech debt on staged"
hooks:
  - event: Stop
    once: true
    command: |
      echo "Technical debt analysis complete."
      echo "  - Address BLOCKING/SIGNIFICANT items before merge"
      echo "  - Create tickets for MINOR items"
      echo "  - /code-review:branch for full code review"
---

## Context
- **Current branch**: !`git branch --show-current`
- **Argument**: $ARGUMENTS
- **Staged files**: !`git diff --cached --name-only`

## Scope Detection

Determine the scope based on the argument:

- If `$ARGUMENTS` is `staged` → analyze staged changes only
- If `$ARGUMENTS` is a branch name → use it as the base branch
- If `$ARGUMENTS` is empty → check if there are staged files:
  - If staged files exist → analyze staged changes
  - Otherwise → default to branch comparison against `main` (or `master`)

## Pre-flight: Base Branch Staleness Check

**Only for branch scope.** Skip entirely for staged scope.

Before running the analysis, check if the local base branch is behind its remote. A stale base produces false findings by including already-merged commits in the diff.

1. Resolve the remote tracking ref: `git rev-parse --abbrev-ref <base>@{upstream}` (falls back to `origin/<base>` if no upstream is configured)
2. If a remote ref exists, run `git rev-list --count <base>..<remote-ref>` to count commits the local base is behind
3. If the count is `0` → proceed silently
4. If the count is `>0` → **stop and warn the user**:

   > Your local `<base>` is N commits behind `<remote-ref>`. The tech-debt analysis may include commits already merged upstream, producing false findings.
   >
   > Suggested: `git fetch origin <base>:<base>` (or pull if checked out), then re-run.
   >
   > Proceed anyway? (yes / no)

5. If the remote ref cannot be resolved (no upstream, no `origin/<base>`) → proceed silently; do not fail the command

Never auto-fetch or auto-pull — the user decides.

## Instructions

Use Agent tool with subagent_type="code-review:tech-debt-reviewer" to analyze technical debt.

**Pass the scope clearly in the agent prompt:**

- For staged scope: Tell the agent to use `git diff --cached` and mention "staged" explicitly
- For branch scope: Tell the agent the base branch to compare against

**Analysis categories:**

1. **Complexity** — Functions >30 lines, deep nesting, god classes
2. **Duplication** — Copy-pasted blocks, similar logic that could be abstracted
3. **Debt Markers** — New TODO/FIXME/HACK/XXX/TEMP comments
4. **Test Gaps** — New code without tests, weakened assertions
5. **Code Smells** — Magic numbers, poor naming, long parameter lists, dead code
6. **Dependencies & Infrastructure** — New deps, version pinning, ad-hoc reimplementation of shared patterns, undocumented config
7. **Maintainability** — Missing docs on public APIs, implicit dependencies, tight coupling

**Output requirements:**

- Verdict: CLEAN / MINOR DEBT / SIGNIFICANT DEBT / BLOCKING DEBT
- Findings organized by severity with file:line references
- Each item includes: what the debt is, why it matters, suggested fix
- Positive Patterns section highlighting what's done well
- Only flag issues in the changed code, not pre-existing debt
