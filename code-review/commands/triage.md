---
allowed-tools:
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/*)
  - Bash(git *)
  - Agent
  - Read
argument-hint: PR#
description: Triage PR feedback from AI reviewers - verify validity before implementing
keywords:
  - ai-feedback
  - copilot-review
  - gemini-review
  - false-positives
  - pr-comments
triggers:
  - "triage AI feedback"
  - "review bot comments"
  - "check AI suggestions"
  - "verify AI review"
  - "handle copilot feedback"
hooks:
  - event: Stop
    once: true
    command: |
      echo "Triage complete."
      echo "  - /code-review:fixes-plan to track verified issues"
      echo "  - /code-review:dismiss to dismiss false positives on GitHub"
---

## Context
- **Repository**: !`git remote get-url origin`
- **Current branch**: !`git branch --show-current`
- **PR Number**: $ARGUMENTS

## Core Principle

**AI feedback is NOT valid by default. Every comment must be verified.**

External AI reviewers (Copilot, Gemini, etc.) lack full context. Their suggestions are starting points for investigation, not instructions to follow blindly.

## Process

1. **Fetch PR feedback** (optimized for low token usage):
   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/pr-triage-comments.sh OWNER REPO PR_NUMBER
   ```
   - Returns all comments (bots and humans) by default with `ref_id` for each comment
   - **Automatically excludes resolved and outdated threads** (via GraphQL)
   - Add `1500 true` to show only bot comments
   - Add `1500 false true` to include resolved threads

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
- Bot comments: X | Human comments: Y | Skipped: R resolved, O outdated
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

## Rationalization Defenses

If you catch yourself thinking any of these, STOP — you are about to accept unverified AI feedback:

| Rationalization | Why It's Wrong |
|----------------|----------------|
| "Copilot flagged a real-looking issue, I'll fix it without checking" | AI reviewers lack full context. "Real-looking" is not "verified." Check the actual code first. |
| "This is clearly a false positive, I don't need to document why" | Every dismissal needs evidence. "Clearly" without documentation is just an assumption. |
| "The AI reviewer has access to the same code I do" | AI reviewers see limited context — often just the diff, not the full codebase, test suite, or intent. |
| "I'll mark things VERIFIED VALID unless I can prove them wrong" | Default stance is skeptical, not accepting. Unverified = FALSE POSITIVE until you confirm with evidence. |
| "This best-practice suggestion can't hurt" | Unnecessary changes increase risk, review burden, and merge conflicts. YAGNI applies to AI suggestions too. |
| "I'll batch-fix all the valid ones at once" | Each fix needs individual verification. Batching hides which fix broke what. |

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
