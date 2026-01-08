---
name: review-fixes-plan
description: Template and guidelines for creating code review fix tracking documents. Use when generating fix plans from code reviews, tracking implementation progress, or documenting issues to resolve before merge.
allowed-tools:
  - Read
  - Write
  - Bash(git *)
user-invocable: true
---

# Review Fixes Plan

Standard format for tracking code review issues and their resolution.

## When to Use

- After `/code-review/branch` to create actionable fix list
- After `/code-review/triage` to document verified issues
- When planning fixes for a feature branch
- To track implementation progress across sessions

## Template Structure

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

## Priority Guidelines

### CRITICAL
- Security vulnerabilities
- Data loss/corruption risks
- Blocking bugs that break functionality
- Migration issues that could fail in production

### HIGH
- N+1 queries affecting performance
- Race conditions
- Missing validation on important fields
- Memory issues in bulk operations

### MEDIUM
- Code inconsistencies
- Missing indexes (non-critical paths)
- Deprecated API usage
- Code duplication

### LOW
- Style improvements
- Documentation gaps
- Refactoring opportunities
- Nice-to-have optimizations

## Best Practices

1. **One issue per section** - Keep issues atomic and focused
2. **Include solution code** - Makes implementation faster
3. **Add file paths with lines** - Easy navigation
4. **Preserve ref_id from triage** - Enables auto-resolving on GitHub after fix
5. **Update progress table** - Track completion at a glance
6. **Use implementation log** - Document decisions and blockers
7. **Add post-merge monitoring** - Don't forget to verify in prod

## File Naming Convention

```
docs/review-fixes-{branch-name}.md
```

Or in project root:
```
REVIEW_FIXES.md
```

## Integration with Other Commands

1. `/code-review/branch` → identifies issues
2. `/code-review/triage` → adds verified AI feedback issues (includes ref_id)
3. `/code-review/fixes-plan` → creates/updates this document (preserve ref_id!)
4. `/code-review/implement-fix` → implement fixes
5. `/code-review/mark-fixed` → verify and mark as fixed
6. `/code-review/resolve-fixed` → resolve GitHub threads for fixed issues
7. Post-merge → verify monitoring items

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
