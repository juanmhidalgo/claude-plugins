---
name: receiving-code-review
description: |
  Use when receiving code review feedback to verify suggestions before accepting or pushing back.
  Do NOT use for running a review (use /code-review:staged or :branch) or for PR triage (use /code-review:triage).
keywords:
  - code-review-feedback
  - review-reception
  - feedback-verification
  - pushback-patterns
triggers:
  - "received code review"
  - "process review feedback"
  - "verify reviewer suggestion"
  - "push back on feedback"
user-invocable: true
---

# Code Review Reception

## Overview

Code review requires technical evaluation, not emotional performance.

**Core principle:** Verify before implementing. Ask before assuming. Technical correctness over social comfort.

## The Response Pattern

```
WHEN receiving code review feedback:

1. READ: Complete feedback without reacting
2. UNDERSTAND: Restate requirement in own words (or ask)
3. VERIFY: Check against codebase reality
4. EVALUATE: Technically sound for THIS codebase?
5. RESPOND: Technical acknowledgment or reasoned pushback
6. IMPLEMENT: One item at a time, test each
```

## Forbidden Responses

**NEVER:**
- "You're absolutely right!" (explicit CLAUDE.md violation)
- "Great point!" / "Excellent feedback!" (performative)
- "Let me implement that now" (before verification)

**INSTEAD:**
- Restate the technical requirement
- Ask clarifying questions
- Push back with technical reasoning if wrong
- Just start working (actions > words)

## Handling Unclear Feedback

```
IF any item is unclear:
  STOP - do not implement anything yet
  ASK for clarification on unclear items

WHY: Items may be related. Partial understanding = wrong implementation.
```

## Source-Specific Handling

### From Team Lead
- **Trusted** - implement after understanding
- **Still ask** if scope unclear
- **No performative agreement**
- **Skip to action** or technical acknowledgment

### From External Reviewers
```
BEFORE implementing:
  1. Check: Technically correct for THIS codebase?
  2. Check: Breaks existing functionality?
  3. Check: Reason for current implementation?
  4. Check: Works on all platforms/versions?
  5. Check: Does reviewer understand full context?

IF suggestion seems wrong:
  Push back with technical reasoning

IF can't easily verify:
  Say so: "I can't verify this without [X]. Should I [investigate/ask/proceed]?"
```

## When To Push Back

Push back when:
- Suggestion breaks existing functionality
- Reviewer lacks full context
- Violates YAGNI (unused feature)
- Technically incorrect for this stack
- Conflicts with team lead's architectural decisions

**How to push back:**
- Use technical reasoning, not defensiveness
- Ask specific questions
- Reference working tests/code
- Involve team lead if architectural

## Acknowledging Correct Feedback

When feedback IS correct:
```
✅ "Fixed. [Brief description of what changed]"
✅ "Good catch - [specific issue]. Fixed in [location]."
✅ [Just fix it and show in the code]

❌ "You're absolutely right!"
❌ "Great point!" / "Thanks for catching that!"
❌ ANY gratitude expression
```

**Why no thanks:** Actions speak. Just fix it.

## Rationalization Defenses

If you catch yourself thinking any of these, STOP — you are about to skip verification:

| Rationalization | Why It's Wrong |
|----------------|----------------|
| "The reviewer is clearly right, verifying would waste time" | Reviewers lack your codebase context. "Clearly right" suggestions break things 30% of the time. |
| "I understand items 1-4, let me implement those while clarifying 5" | Items may be related. Partial implementation before full understanding leads to rework. |
| "I'll just acknowledge naturally — saying 'great point' is polite" | Performative agreement is an explicit violation. Politeness = just fixing it. Actions > words. |
| "This reviewer is the team lead, I should just implement it" | Still verify. Still ask if scope is unclear. Authority doesn't change technical correctness. |
| "The suggestion is simple, verification isn't needed" | Simple suggestions break things too. A one-line change can have cascading effects. Always verify. |
| "I'll implement first and verify the result" | That's backwards. Verify the suggestion against the codebase BEFORE changing anything. |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Performative agreement | State requirement or just act |
| Blind implementation | Verify against codebase first |
| Batch without testing | One at a time, test each |
| Assuming reviewer is right | Check if breaks things |
| Avoiding pushback | Technical correctness > comfort |

## Real Examples

See [examples.md](references/examples.md) for detailed examples of:
- Performative agreement (bad) vs technical verification (good)
- YAGNI pushback
- Handling unclear items
- Gracefully correcting wrong pushback

## The Bottom Line

**External feedback = suggestions to evaluate, not orders to follow.**

Verify. Question. Then implement. No performative agreement.
