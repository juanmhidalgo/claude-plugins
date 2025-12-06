---
allowed-tools: Task, Read, Bash
argument-hint: PR#
description: Triage PR feedback from AI reviewers - verify validity before implementing
---

## Context
- **Repository**: !`git remote get-url origin 2>/dev/null | sed 's/.*github.com[:/]\(.*\)\.git/\1/' | sed 's/.*github.com[:/]\(.*\)/\1/'`
- **Current branch**: !`git branch --show-current`
- **PR Number**: $ARGUMENTS

## Core Principle

**AI feedback is NOT valid by default. Every comment must be verified.**

External AI reviewers (Copilot, Gemini, etc.) lack full context. Their suggestions are starting points for investigation, not instructions to follow blindly.

## Process

1. **Fetch PR feedback** (optimized for low token usage):
   ```bash
   ~/.claude/plugins/code-review/scripts/pr-triage-comments.sh OWNER REPO PR_NUMBER
   ```
   - Returns only bot comments by default with `ref_id` for each comment
   - Add `1500 true` at the end to include human comments

2. **For EACH comment, ask:**
   - Is this technically correct for THIS codebase?
   - Does the AI have the full context?
   - Would this change break existing functionality?
   - Is there a reason the code is written this way?
   - Is this actually needed or just "best practice theater"?

3. **Classify after verification:**

   **VERIFIED VALID** - Confirmed issues to fix
   - You checked the code and the issue is real
   - Security risk, bug, or genuine problem

   **NEEDS INVESTIGATION** - Can't determine without more context
   - Might be valid, might not
   - Requires checking tests, related code, or asking the author

   **FALSE POSITIVE** - Verified as incorrect or unnecessary
   - AI misunderstood the context
   - Suggestion would break existing behavior
   - YAGNI - feature isn't needed
   - Already handled elsewhere

## Output Format

```markdown
# PR #[number] Feedback Triage

## Stats
- Bot comments: X | Human comments: Y
- Verified valid: Z | Needs investigation: W | False positives: V

## VERIFIED VALID
### [Issue title]
📍 `file.py:42` by @copilot | `ref_id: review_comment:123456789`
**Issue:** [description]
**Verified by:** [how you confirmed it's real]
**Priority:** CRITICAL | HIGH | MEDIUM

## NEEDS INVESTIGATION
### [Issue title]
📍 `file.py:15` by @gemini | `ref_id: review_comment:987654321`
**Suggestion:** [what they want]
**Unknown:** [what needs to be checked]
**To verify:** [specific action needed]

## FALSE POSITIVES
### [Issue title]
📍 `utils.py:88` by @copilot | `ref_id: review_comment:456789123`
**Suggestion:** [what they want]
**Why wrong:** [technical reason]
**Evidence:** [code/test that proves it's wrong]
**Dismiss reason:** YAGNI | Already handled | Context | Style | Breaking
```

## Remember

- Start skeptical, not accepting
- Verify against actual code behavior
- Push back with technical reasoning
- Don't implement "improvements" that aren't needed

## Next Steps

After completing the triage:

1. **For verified issues:**
   > "To add verified issues to a tracking document, run `/code-review/fixes-plan [feature-name]`"

2. **For false positives:** Run `/code-review/dismiss [PR#]` to dismiss with justification and resolve threads on GitHub.
