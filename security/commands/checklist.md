---
description: |
  Use when you need a fast pass over auth, input handling, data, infra, or dependency security in the current code.
  Do NOT use for deep vulnerability analysis — use /security:audit for that.
argument-hint: "[area: auth|input|data|infra|deps]"
keywords:
  - security
  - checklist
  - verification
triggers:
  - "security checklist"
  - "check security basics"
  - "verify security"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(npm audit *)
  - Bash(pip audit *)
  - Bash(git diff --cached *)
hooks:
  - event: Stop
    once: true
    command: |
      echo "Checklist verification complete."
      echo "  - /security:audit for a deeper analysis"
---

## Context

- **Branch**: !`git branch --show-current`
- **Staged files**: !`git diff --cached --name-only`

<reference>
@security/skills/security-hardening/references/security-checklist.md
</reference>

## Security Checklist Verification

Area focus: **$ARGUMENTS** (if empty, run all areas).

For each checklist item, verify against the actual codebase using Grep and Read. Report each item as:
- **PASS** — verified in code
- **FAIL** — violation found (include file:line)
- **N/A** — not applicable to this codebase
- **UNKNOWN** — could not determine (needs manual review)

### If area is specified

Run only the matching section from the checklist (auth, input, data, infra, or deps).

### If no area specified

Run all sections, starting with the highest-risk areas:
1. Authentication & Authorization
2. Input Validation
3. Data Protection
4. Infrastructure & Headers
5. Dependencies

### Output

```markdown
## Security Checklist Report

### [Area Name]
- [PASS] Item description
- [FAIL] Item description — `file:line` — details
- [N/A] Item description — reason
```

Summarize with pass/fail/na counts per area and overall assessment.
