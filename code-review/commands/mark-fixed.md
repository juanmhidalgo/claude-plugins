---
allowed-tools:
  - Read
  - Write
  - Bash(git *)
  - Bash(grep *)
  - Grep
argument-hint: [issue-number | "all"]
description: Verify and mark issues as fixed in REVIEW_FIXES.md
keywords:
  - verify-fix
  - mark-fixed
  - fix-verification
  - issue-completion
triggers:
  - "mark as fixed"
  - "verify fixes"
  - "check if fixed"
  - "mark issue completed"
---

## Context
- **Branch:** !`git branch --show-current`
- **Date:** !`date +%Y-%m-%d`
- **Fixes file:** !`grep -l "type: review-fixes" *.md docs/*.md 2>/dev/null | head -1 || (test -f REVIEW_FIXES.md && echo "REVIEW_FIXES.md") || echo "not found"`

## Instructions

### Step 1: Load Fixes File

Read the review fixes file found above. If not found, inform user.

### Step 2: Determine Mode

Based on `$ARGUMENTS`:
- **Number (e.g., "3")** → Verify and mark specific issue #3
- **"all"** → Verify all pending issues
- **Empty** → Show pending issues and ask which to verify

### Step 3: For Each Issue to Verify

1. **Read the issue details:**
   - File path and line numbers
   - Problem description
   - Expected solution

2. **Verify the fix:**
   - Read the current file at specified path
   - Check if the suggested solution (or equivalent) was implemented
   - Look for the problem pattern - should NOT exist anymore
   - Look for the fix pattern - should exist now

3. **Determine status:**
   - **FIXED** - Solution implemented, problem resolved
   - **PARTIALLY FIXED** - Some changes made, but incomplete
   - **NOT FIXED** - Problem still exists
   - **CANNOT VERIFY** - File changed significantly, manual review needed

### Step 4: Update the File

For each verified fix:

1. **Update checkbox:**
   ```markdown
   - [x] **Completed**
   ```

2. **Add verification note:**
   ```markdown
   **Notes:**
   - ✅ Verified fixed on YYYY-MM-DD
   ```

3. **Update Progress Summary table:**
   - Increment "Completed" count
   - Decrement "Remaining" count

4. **Update frontmatter:**
   ```yaml
   updated: YYYY-MM-DD
   ```

5. **Add to Implementation Log:**
   ```markdown
   | YYYY-MM-DD | 3 | Fixed | @claude | Verified: bulk_create implemented |
   ```

### Step 5: Report

Show summary:
```
## Verification Results

✅ Issue #3: N+1 Query - FIXED
✅ Issue #5: Missing validation - FIXED
⚠️ Issue #7: Race condition - PARTIALLY FIXED (missing transaction)
❌ Issue #2: Data migration - NOT FIXED

Progress: 5/11 completed (was 3/11)
```

## Verification Patterns

### For code fixes:
```bash
# Check if old pattern exists (should NOT)
grep -n "old_pattern" path/to/file.py

# Check if new pattern exists (should)
grep -n "new_pattern" path/to/file.py
```

### For N+1 fixes:
- Look for `select_related()`, `prefetch_related()`, or `bulk_create()`

### For validation fixes:
- Look for validation logic, `raise ValidationError`, etc.

### For migration fixes:
- Check if migration file was modified
- Look for `RunPython` with validation

## Important

- Do NOT modify source code, only REVIEW_FIXES.md
- Be conservative - if unsure, mark as "CANNOT VERIFY"
- Always show what you checked before marking as fixed
