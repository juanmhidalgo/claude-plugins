---
argument-hint: "<paste review report>"
description: |
  Use when pasting review output from /code-review:staged or :branch.
  Do NOT use for PR triage (/code-review:triage) or to run a new review.
keywords:
  - code-review
  - receive-feedback
  - review-report
  - cross-session
triggers:
  - "received code review feedback"
  - "here's the review from the other session"
  - "process this code review"
  - "got review results"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Agent
  - Bash(git diff *)
  - Bash(git log *)
  - Bash(git show *)
  - Bash(git status)
  - EnterPlanMode
skills:
  - receiving-code-review
hooks:
  - event: Stop
    once: true
    command: |
      echo "Review findings verified. Next steps:"
      echo "  - To track fixes: /code-review:fixes-plan"
      echo "  - To implement directly: /code-review:implement-fix"
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this command and proceed with your assigned task.
</SUBAGENT-STOP>

# Receive Code Review

Process code review feedback from another session. The review is **external analysis, not a source of truth** — findings may reference stale code, misunderstand context, or flag non-issues.

## Review Content

$ARGUMENTS

---

## Protocol

Follow these phases in order. Do NOT skip to implementation.

### Phase 1: Parse Findings

Extract each finding from the review report:
- **File path** and line numbers
- **Severity** (CRITICAL / HIGH / MEDIUM / LOW)
- **Category** (security, performance, bug, code quality, etc.)
- **Description** of the issue
- **Suggested fix** (if provided)

If the review format is unclear or unstructured, do your best to identify individual findings.

### Phase 2: Verify Against Actual Code

For each finding, read the referenced file and check:

| Check | How |
|-------|-----|
| File and line still match | Read the file, compare to what the review references |
| Issue still exists | Code may have changed since the review ran |
| Finding is technically correct | The reviewer (even AI) can be wrong |
| Context was understood | Check surrounding code the reviewer may not have seen |
| Aligns with project conventions | Check CLAUDE.md and existing patterns |

**Classify each finding:**
- **CONFIRMED** — issue exists and finding is correct
- **STALE** — code has changed, finding no longer applies
- **INCORRECT** — finding misunderstands the code or is technically wrong
- **DISPUTED** — finding is debatable, needs user input

### Phase 3: Present Verified Results

Enter plan mode using the EnterPlanMode tool.

Present findings grouped by status:

```
## Verified Review Findings

### Confirmed (X findings)
For each: severity, file:line, issue summary, suggested action

### Disputed (X findings)
For each: what the review says vs what the code actually does, your assessment

### Rejected (X findings)
For each: brief reason (stale / incorrect / non-issue)
```

Include a summary table:

```
| Status    | Count | Action |
|-----------|-------|--------|
| Confirmed | X     | Fix    |
| Disputed  | X     | Discuss|
| Rejected  | X     | None   |
```

**Do NOT start implementing until the user approves which findings to act on.**

### What to Trust vs. Question

| Trust | Question |
|-------|----------|
| Severity classifications (as starting point) | Specific line references (code may have moved) |
| Security and correctness concerns | Style/preference suggestions |
| Bug risk identification | "Should be refactored" without clear benefit |
| Performance analysis with evidence | Performance claims without profiling data |
