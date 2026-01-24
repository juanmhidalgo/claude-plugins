---
name: review-fixes-plan
description: Template and guidelines for creating code review fix tracking documents.
keywords:
  - fix-tracking
  - issue-management
  - review-fixes
  - progress-tracking
triggers:
  - "create fix tracking document"
  - "track code review fixes"
  - "document issues to fix"
  - "plan review fixes"
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

## File Naming Convention

```
docs/review-fixes-{branch-name}.md
```

Or in project root:
```
REVIEW_FIXES.md
```

## Template

See [template.md](references/template.md) for the full template with all sections.

Key sections:
- YAML frontmatter (type, branch, feature, pr, status)
- Progress summary table
- Issues by priority (CRITICAL, HIGH, MEDIUM, LOW)
- Implementation log
- Post-merge monitoring checklist

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
4. **Preserve ref_id from triage** - Enables auto-resolving on GitHub
5. **Update progress table** - Track completion at a glance
6. **Use implementation log** - Document decisions and blockers
7. **Add post-merge monitoring** - Don't forget to verify in prod

## Integration with Other Commands

1. `/code-review/branch` → identifies issues
2. `/code-review/triage` → adds verified AI feedback issues (includes ref_id)
3. `/code-review/fixes-plan` → creates/updates this document
4. `/code-review/implement-fix` → implement fixes
5. `/code-review/mark-fixed` → verify and mark as fixed
6. `/code-review/resolve-fixed` → resolve GitHub threads for fixed issues
7. Post-merge → verify monitoring items
