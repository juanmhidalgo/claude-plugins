---
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(git *)
  - Bash(grep *)
  - Grep
  - Glob
  - AskUserQuestion
argument-hint: [issue-number | "all"]
description: Implement fixes from REVIEW_FIXES.md, asking for technical decisions when needed
keywords:
  - implement-fix
  - code-fix
  - bug-fix
  - review-fixes
triggers:
  - "implement review fixes"
  - "fix review issues"
  - "apply code fixes"
  - "implement bug fixes"
skills:
  - technical-decisions
  - receiving-code-review
---

## Context
- **Branch:** !`git branch --show-current`
- **Date:** !`date +%Y-%m-%d`
- **Fixes file:** !`grep -l "type: review-fixes" *.md docs/*.md 2>/dev/null | head -1 || (test -f REVIEW_FIXES.md && echo "REVIEW_FIXES.md") || echo "not found"`

## Instructions

### Step 1: Load Fixes File

Read the review fixes file found above. If not found, inform user to run `/code-review:fixes-plan` first.

### Step 2: Determine Scope

Based on `$ARGUMENTS`:
- **Number (e.g., "3")** → Implement specific issue #3
- **"all"** → Implement all pending issues
- **Empty** → Show pending issues and ask which to implement

### Step 3: Analyze Each Issue

For each issue to implement:

1. **Read the issue details:**
   - File path and line numbers
   - Problem description
   - Suggested solution

2. **Read the current code:**
   - Understand the context
   - Check if issue still exists (may have been fixed already)

3. **Classify the fix:**

   **Simple fixes (implement directly):**
   - Typos, formatting
   - Missing imports
   - Obvious null checks
   - Documentation updates

   **Decision-required fixes (ASK FIRST):**
   - Multiple valid approaches exist
   - Architectural implications
   - Adding dependencies
   - Performance trade-offs
   - Breaking changes
   - Security-related changes

### Step 4: For Decision-Required Fixes

**STOP and ask before implementing:**

```
This fix requires a decision:

**Issue #X:** [Brief description]

**Options:**
1. [Approach A]
   - Pros: ...
   - Cons: ...

2. [Approach B]
   - Pros: ...
   - Cons: ...

**Recommendation:** [Your suggestion] because [reasoning]

Which approach do you prefer?
```

Wait for user response before implementing.

### Step 5: Implement the Fix

1. **Make the code change:**
   - Use Edit tool for modifications
   - Follow existing code patterns
   - Keep changes minimal and focused

2. **Verify the fix:**
   - Read the changed file
   - Ensure no syntax errors
   - Check surrounding code wasn't broken

3. **Report what was done:**
   ```
   ✅ Issue #3: Added null check at line 45
   ```

### Step 6: Update REVIEW_FIXES.md

After implementing each fix:

1. **Update status to in-progress:**
   ```markdown
   - [~] **In Progress**
   ```

2. **Add implementation note:**
   ```markdown
   **Notes:**
   - 🔧 Implemented on YYYY-MM-DD: [brief description of change]
   ```

3. **Update Implementation Log:**
   ```markdown
   | YYYY-MM-DD | 3 | Implemented | @claude | Added null check at users/views.py:45 |
   ```

### Step 7: Final Summary

```
## Implementation Results

✅ Issue #3: N+1 Query - Implemented (used select_related)
✅ Issue #5: Missing validation - Implemented
⏸️ Issue #7: Race condition - Awaiting decision (presented options)
⏭️ Issue #2: Data migration - Skipped (needs manual review)

Next: Run /code-review:mark-fixed to verify implementations
```

## Decision Patterns

### When to ask:

| Pattern | Ask? | Why |
|---------|------|-----|
| "Add caching" | ✅ Yes | Where? What strategy? TTL? |
| "Fix N+1 query" | ✅ Yes | select_related vs prefetch vs cache |
| "Add error handling" | ✅ Yes | Generic vs specific exceptions |
| "Add validation" | Maybe | If simple = no, if complex = yes |
| "Fix typo" | ❌ No | Single correct answer |
| "Add null check" | ❌ No | Obvious implementation |

### Example decisions:

**N+1 Query:**
- Option 1: `select_related()` - always load
- Option 2: `prefetch_related()` - batch load
- Option 3: Cache at application level

**Error Handling:**
- Option 1: Generic try/catch
- Option 2: Specific exception types
- Option 3: Result/Either pattern

**Adding Dependency:**
- Option 1: Use library X (popular, large)
- Option 2: Use library Y (lightweight, focused)
- Option 3: Implement manually (no dependency)

## Important

- **ASK before implementing** when multiple valid approaches exist
- **Group related decisions** - if fixes are connected, present together
- **Follow existing patterns** - match codebase style
- **Keep changes minimal** - only fix what's needed
- **One fix at a time** - easier to track and verify
