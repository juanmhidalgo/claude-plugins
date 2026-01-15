---
allowed-tools:
  - Read
  - Write
  - Bash(git *)
  - Bash(test *)
  - Bash(ls *)
  - Bash(head *)
  - Bash(grep *)
argument-hint: [feature-name]
description: Generate a code review fixes tracking document from recent review findings
keywords:
  - fixes-tracking
  - review-fixes
  - issue-tracking
  - bug-tracking
triggers:
  - "create fixes plan"
  - "track review fixes"
  - "generate fixes document"
  - "create fix tracking"
---

## Context
- **Branch:** !`git branch --show-current`
- **Date:** !`date +%Y-%m-%d`
- **Feature name:** $ARGUMENTS

## Existing Files Check
- **REVIEW_FIXES.md:** !`test -f REVIEW_FIXES.md && head -1 REVIEW_FIXES.md 2>/dev/null || echo "not found"`
- **docs/review-fixes-*.md:** !`ls docs/review-fixes-*.md 2>/dev/null | head -3 || echo "not found"`
- **Files with frontmatter:** !`grep -l "type: review-fixes" *.md docs/*.md 2>/dev/null | head -3 || echo "none"`

## Instructions

### Step 1: Check for Existing File

Look for files with `type: review-fixes` in frontmatter, or REVIEW_FIXES.md.

If an existing fixes file is found:
1. Read the existing file
2. Ask user: "Found existing `[filename]`. Do you want to:"
   - **Update** - Add new issues, preserve existing ones and their status
   - **Replace** - Generate fresh document
   - **New file** - Create separate file

If updating:
- Keep all existing issues and their completion status
- Add new issues from recent reviews
- Update the Progress Summary table
- Update `updated` field in frontmatter

### Step 2: Gather Issues

Sources for new issues:
1. Recent `/code-review/branch` output in this conversation
2. Recent `/code-review/triage` output (verified issues only)
3. Any issues mentioned by the user

### For Each Issue

1. **Classify priority:**
   - CRITICAL: Security, data loss, blocking bugs, migrations
   - HIGH: N+1 queries, race conditions, missing validation
   - MEDIUM: Inconsistencies, deprecated APIs, missing indexes
   - LOW: Style, docs, refactoring

2. **Document clearly:**
   - Descriptive title
   - File path with line numbers
   - Clear problem statement
   - Solution with code example
   - Empty notes section for implementation

3. **Provide actionable solutions:**
   - Include actual code, not just description
   - Consider edge cases
   - Note if solution requires migration

### Output

1. Generate the markdown document following the template
2. Ask user where to save:
   - `docs/review-fixes-{branch}.md`
   - `REVIEW_FIXES.md` in project root
   - Custom path
3. Write the file to the chosen location

### Progress Table

Calculate totals for the progress summary table based on classified issues.

### Post-Merge Monitoring

Suggest monitoring items based on the issues found:
- Query performance if N+1 fixes
- Memory usage if bulk operation fixes
- Error rates if validation fixes
- Data integrity if migration fixes
