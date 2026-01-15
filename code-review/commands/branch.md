---
allowed-tools:
  - Bash(git *)
  - Task
  - Read
argument-hint: [base-branch]
description: Code review of current branch changes compared to a base branch (default: main/master)
keywords:
  - branch-review
  - branch-comparison
  - git-diff
  - pre-merge
triggers:
  - "review my branch"
  - "review branch changes"
  - "compare branches"
  - "review before merge"
  - "code review current branch"
hooks:
  - event: Stop
    once: true
    command: |
      echo "📝 Branch review complete."
      echo "  • Track fixes with /code-review:fixes-plan"
      echo "  • Or create PR with gh pr create"
---

## Context
- **Current branch**: !`git branch --show-current`
- **Default base**: !`git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main"`
- **Specified base**: $1

## Branch Configuration
If `$1` is provided, use it as the base branch. Otherwise, use the detected default base.

## Changes Summary
!`BASE="${1:-$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo 'main')}"; git log --oneline $BASE..HEAD 2>/dev/null | head -20 || echo "No commits found"`

## Files Changed
!`BASE="${1:-$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo 'main')}"; git diff $BASE...HEAD --stat 2>/dev/null | tail -20 || echo "No changes found"`

## Instructions

Use Task tool with subagent_type="code-review:branch-reviewer" to perform a comprehensive code review.

**Review process:**
1. Get the full diff: `git diff <base>...HEAD`
2. For large diffs, review file by file using `git diff <base>...HEAD -- <file>`
3. Read modified files for full context when needed

**Analysis focus:**
- Security vulnerabilities (injection, auth issues, secrets)
- Performance problems (N+1 queries, memory leaks, blocking calls)
- Bug risks (edge cases, null checks, race conditions)
- Code quality (readability, maintainability, SOLID principles)
- Missing tests for new/changed functionality

**Output format:**
Organize findings by severity:
- **CRITICAL**: Must fix before merge (security, data loss risks)
- **HIGH**: Should fix (bugs, performance issues)
- **MEDIUM**: Recommended (code quality, maintainability)
- **LOW**: Suggestions (style, minor improvements)

Include file path, line numbers, and concrete fix suggestions.

## Next Step

After completing the review, suggest:
> "To create a trackable fixes document, run `/code-review/fixes-plan [feature-name]`"
