---
allowed-tools: Bash, Read
argument-hint: PR#
description: Dismiss false positive comments on a PR with justification
---

## Context
- **Repository:** !`git remote get-url origin 2>/dev/null | sed 's/.*github.com[:/]\(.*\)\.git/\1/' | sed 's/.*github.com[:/]\(.*\)/\1/'`
- **Current branch:** !`git branch --show-current`
- **PR Number:** $ARGUMENTS

## Instructions

### Step 1: Get Comments to Dismiss

Check if there's a recent `/code-review/triage` output in this conversation with FALSE POSITIVES identified.

If not, fetch PR comments:
```bash
~/.claude/plugins/code-review/scripts/pr-triage-comments.sh OWNER REPO PR_NUMBER
```

### Step 2: For Each False Positive

Show the comment and ask for confirmation:
```
Comment by @copilot on `file.py:42`:
"Consider using dependency injection here..."

Dismiss with reason:
1. Already handled elsewhere
2. YAGNI - not needed
3. Misunderstands context
4. Style preference, not bug
5. Custom reason...
```

### Step 3: Dismiss on GitHub

For each confirmed dismissal, run:
```bash
~/.claude/plugins/code-review/scripts/pr-resolve-comment.sh OWNER REPO PR_NUMBER REF_ID dismiss "REASON"
```

This will:
1. Add a reply with "**Dismissed**" + reason
2. Resolve the thread on GitHub

### Step 4: Report

Show summary:
```
## Dismissed Comments

✅ @copilot on file.py:42 - "YAGNI - not needed"
✅ @gemini on auth.py:15 - "Already handled in middleware"
✅ @copilot on utils.py:88 - "Style preference, not bug"

3 comments dismissed and resolved on PR #42
```

## Dismissal Reasons Templates

| Reason | Template |
|--------|----------|
| YAGNI | "Not implementing - this feature isn't needed (YAGNI). The current implementation meets requirements." |
| Already handled | "Already handled in {location}. See {file}:{line} for the existing implementation." |
| Context | "This suggestion misunderstands the context. {explanation}" |
| Style | "This is a style preference, not a bug or security issue. Keeping current approach for consistency." |
| Breaking | "This change would break {what}. Current implementation is intentional." |
| Performance | "Verified no performance issue here. {evidence}" |

## Important

- Be professional in dismissal messages
- Include enough context for future reference
- Don't dismiss valid concerns - only confirmed false positives
