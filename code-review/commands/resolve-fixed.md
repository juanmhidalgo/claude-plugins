---
allowed-tools:
  - Read
  - Edit
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/*)
  - Bash(git *)
  - Bash(grep *)
  - Grep
argument-hint: PR#
description: |
  Use after marking issues as fixed in REVIEW_FIXES.md to close corresponding GitHub threads.
  Do NOT use before verifying fixes — use /code-review:mark-fixed first.
keywords:
  - resolve-threads
  - github-comments
  - pr-threads
  - close-threads
triggers:
  - "resolve GitHub threads"
  - "close PR threads"
  - "resolve fixed issues"
  - "mark threads resolved"
---

## Context
- **Repository**: !`git remote get-url origin`
- **Branch:** !`git branch --show-current`
- **Date:** !`date +%Y-%m-%d`
- **PR Number**: $ARGUMENTS
- **Fixes file:** REVIEW_FIXES.md (or run `/code-review:fixes-plan` to create one)

## Instructions

### Step 1: Validate Inputs

1. **Check PR number** - Must be provided as argument
2. **Check fixes file exists** - If not found, inform user to run `/code-review:fixes-plan` first

### Step 2: Load and Parse Fixes File

Read the REVIEW_FIXES.md file and identify:
- Issues marked as **completed** (`- [x] **Completed**`)
- That have a **GitHub ref_id** (`**GitHub:** \`ref_id: review_comment:123456789\``)

Extract for each completed issue with ref_id:
- Issue number/title
- The ref_id value

### Step 3: Resolve Threads on GitHub

For each completed issue with a ref_id:

1. **Parse the ref_id** to get the comment type and ID
2. **Run the resolve script:**
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/pr-resolve-comment.sh OWNER REPO PR_NUMBER REF_ID resolve
   ```
3. **Track result** - success or failure

### Step 4: Update REVIEW_FIXES.md

For each successfully resolved issue:

1. **Add resolution note:**
   ```markdown
   **Notes:**
   - ✅ Verified fixed on YYYY-MM-DD
   - 🔗 GitHub thread resolved on YYYY-MM-DD
   ```

2. **Update Implementation Log:**
   ```markdown
   | YYYY-MM-DD | 3 | Resolved | @claude | GitHub thread resolved |
   ```

### Step 5: Report Results

```markdown
## GitHub Resolution Results

**PR:** #[number]
**Repository:** owner/repo

### Resolved
✅ Issue #3: N+1 Query - Thread resolved
✅ Issue #5: Missing validation - Thread resolved

### Skipped (no ref_id)
⏭️ Issue #1: Code style - No GitHub thread linked

### Failed
❌ Issue #7: Race condition - Could not resolve (thread not found)

### Not Fixed Yet
⏸️ Issue #2: Data migration - Still pending

---
**Summary:** 2 resolved, 1 skipped, 1 failed, 1 pending
```

## Important

- **Only resolves completed issues** - Issues must be marked `[x]` first
- **Requires ref_id** - Issues without `**GitHub:**` line are skipped
- **Safe to run multiple times** - Already resolved threads are skipped by GitHub
- **Run after push** - Resolve threads after your fixes are pushed to the PR

## Parsing Patterns

### Finding completed issues with ref_id:

```
- [x] **Completed**
```
followed by:
```
**GitHub:** `ref_id: review_comment:123456789`
```

### Extracting ref_id:

Pattern: `ref_id: (review_comment:\d+|issue_comment:\d+)`

## Error Handling

| Error | Action |
|-------|--------|
| PR number not provided | Ask user to provide PR# |
| Fixes file not found | Suggest running `/code-review:fixes-plan` |
| ref_id format invalid | Skip issue, report in results |
| Thread not found | Report failure, may be already resolved |
| API error | Report error, continue with other issues |
