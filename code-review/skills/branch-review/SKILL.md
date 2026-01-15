---
name: branch-review
description: Best practices for reviewing branch changes and pull requests.
keywords:
  - code-review
  - branch-comparison
  - diff-analysis
  - pr-preparation
  - security-checklist
triggers:
  - "review branch changes"
  - "compare branches"
  - "analyze diff"
  - "prepare PR for merge"
  - "check code before merge"
allowed-tools:
  - Bash(git *)
  - Read
  - Grep
agent: code-review:branch-reviewer
user-invocable: true
---

# Branch Review Best Practices

## Git Commands for Review

### Compare branches
```bash
# Full diff
git diff main...HEAD

# Stats only
git diff main...HEAD --stat

# Specific file
git diff main...HEAD -- path/to/file

# Only file names
git diff main...HEAD --name-only

# Commits in branch
git log main..HEAD --oneline
```

### Check what will be merged
```bash
# Preview merge
git merge-tree $(git merge-base main HEAD) main HEAD

# Check for conflicts
git merge --no-commit --no-ff main && git merge --abort
```

## Review Checklist

### Security (CRITICAL)
- [ ] No hardcoded secrets, API keys, or credentials
- [ ] Input validation on all user data
- [ ] SQL queries use parameterized statements
- [ ] Authentication/authorization properly enforced
- [ ] No sensitive data in logs
- [ ] Dependencies don't have known CVEs

### Bug Prevention (HIGH)
- [ ] Null/undefined checks where needed
- [ ] Error handling covers failure cases
- [ ] Edge cases considered (empty arrays, zero values, etc.)
- [ ] Race conditions addressed in concurrent code
- [ ] Resource cleanup (connections, file handles, etc.)

### Performance (HIGH)
- [ ] No N+1 query patterns
- [ ] Appropriate indexing for new queries
- [ ] No blocking calls in async contexts
- [ ] Pagination for large data sets
- [ ] Caching considered for expensive operations

### Code Quality (MEDIUM)
- [ ] Functions have single responsibility
- [ ] Clear, descriptive naming
- [ ] No code duplication
- [ ] Appropriate abstraction level
- [ ] Comments explain "why", not "what"

### Testing (MEDIUM)
- [ ] New code has test coverage
- [ ] Edge cases tested
- [ ] Tests are meaningful, not just coverage padding
- [ ] Mocks used appropriately

### Maintainability (LOW)
- [ ] Consistent with existing codebase style
- [ ] No dead code introduced
- [ ] Dependencies justified and minimal
- [ ] Documentation updated if needed

## Severity Classification

### CRITICAL - Block merge
- Security vulnerabilities
- Data loss/corruption risks
- Breaking changes without migration
- Production stability threats

### HIGH - Should fix before merge
- Bugs likely to affect users
- Performance regressions
- Missing error handling
- Test coverage gaps for critical paths

### MEDIUM - Recommend fixing
- Code smells and anti-patterns
- Minor performance issues
- Inconsistent patterns
- Missing tests for non-critical paths

### LOW - Optional improvements
- Style inconsistencies
- Minor refactoring opportunities
- Documentation improvements
- Naming suggestions

## Feedback Format

```markdown
**[SEVERITY]** Brief title

📍 `path/to/file.py:42`

**Issue:** Clear description of the problem

**Risk:** What could go wrong

**Suggestion:**
\`\`\`python
# Recommended fix
\`\`\`
```

## Review Anti-Patterns to Avoid

1. **Nitpicking** - Don't block on minor style issues
2. **Rubber stamping** - Actually read the code
3. **Bike-shedding** - Focus on important issues
4. **No context** - Understand the "why" before criticizing
5. **Only negative** - Acknowledge good patterns too

## When to Request Changes vs Comment

**Request Changes:**
- Security issues
- Bugs that will affect users
- Breaking changes
- Missing critical tests

**Comment Only:**
- Suggestions for improvement
- Questions about approach
- Style preferences
- Future considerations
