---
allowed-tools: Bash, Task, Read
description: Code review of staged changes before committing
---

## Context
- **Current branch**: !`git branch --show-current`
- **Staged files**: !`git diff --cached --name-only | head -20`

## Staged Changes Summary
!`git diff --cached --stat | tail -20`

## Instructions

Use Task tool with subagent_type="branch-reviewer" to perform a comprehensive code review of staged changes.

**Review process:**
1. Get staged diff: `git diff --cached`
2. For large diffs, review file by file: `git diff --cached -- <file>`
3. Read full files when needed for context

**Analysis focus:**
- Security vulnerabilities (injection, auth issues, secrets)
- Performance problems (N+1 queries, memory leaks, blocking calls)
- Bug risks (edge cases, null checks, race conditions)
- Code quality (readability, maintainability, SOLID principles)
- Missing tests for new/changed functionality

**Output format:**
Organize findings by severity:
- **CRITICAL**: Must fix before commit (security, data loss risks)
- **HIGH**: Should fix (bugs, performance issues)
- **MEDIUM**: Recommended (code quality, maintainability)
- **LOW**: Suggestions (style, minor improvements)

Include file path, line numbers, and concrete fix suggestions.

**Important:**
- Do NOT modify any code
- Do NOT stage or commit changes
- Focus on the diff, not entire files

## Next Step

After completing the review, suggest:
> "To create a trackable fixes document, run `/code-review/fixes-plan [feature-name]`"
