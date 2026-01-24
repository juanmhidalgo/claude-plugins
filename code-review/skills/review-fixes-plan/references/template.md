# Review Fixes Plan Template

Copy this template when creating a new fixes plan document.

```markdown
---
type: review-fixes
branch: branch-name
feature: Feature Name
pr: 123
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: in_progress
---

# Code Review Fixes Plan - [Feature Name]

## Progress Summary

| Priority | Total | Completed | Remaining |
|----------|-------|-----------|-----------|
| CRITICAL | 0     | 0         | 0         |
| HIGH     | 0     | 0         | 0         |
| MEDIUM   | 0     | 0         | 0         |
| LOW      | 0     | 0         | 0         |

---

## CRITICAL Issues (Must Fix Before Merge)

### 1. [Issue Title]

- [ ] **Completed**

**File:** `path/to/file.py:line-range`
**GitHub:** `ref_id: review_comment:123456789` _(if from PR feedback)_

**Problem:** Clear description of the issue and its impact.

**Solution:**
\`\`\`python
# Code showing the fix
\`\`\`

**Notes:**
- Implementation notes, edge cases, or decisions

---

## HIGH Priority Issues

### 2. [Issue Title]

- [ ] **Completed**

**File:** `path/to/file.py:line-range`
**GitHub:** `ref_id: review_comment:123456789` _(if from PR feedback)_

**Problem:** Description

**Solution:**
\`\`\`python
# Fix code
\`\`\`

**Notes:**
-

---

## MEDIUM Priority Issues

[Same format...]

---

## LOW Priority Issues (Nice to Have)

[Same format...]

---

## Implementation Log

| Date | Issue # | Status | Developer | Notes |
|------|---------|--------|-----------|-------|
| YYYY-MM-DD | 1 | Done | @dev | Fixed with bulk_create |

---

## Additional Notes

_Decisions, context, or observations during implementation._

---

## Post-Merge Monitoring

After merge, monitor:
- [ ] [Metric or behavior to watch]
- [ ] [Performance indicator]
- [ ] [Error rates]

---

**Last Updated:** YYYY-MM-DD
```

## Frontmatter Fields

| Field | Description |
|-------|-------------|
| `type` | Always `review-fixes` (for detection) |
| `branch` | Git branch name |
| `feature` | Human-readable feature name |
| `pr` | PR number (optional, if PR exists) |
| `created` | Date file was created |
| `updated` | Date of last update |
| `status` | `in_progress`, `completed`, `blocked` |
