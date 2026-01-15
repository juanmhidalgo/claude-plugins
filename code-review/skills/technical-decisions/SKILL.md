---
name: technical-decisions
description: Guidelines for handling technical decisions during code review implementation.
keywords:
  - technical-decisions
  - implementation-choices
  - architecture-decisions
  - trade-offs
triggers:
  - "decide between approaches"
  - "multiple implementation options"
  - "technical trade-off"
  - "architectural decision"
user-invocable: true
---

# Technical Decisions

## Overview

When implementing fixes from code review, some require technical decisions that should be made by your human partner, not assumed.

**Core principle:** Ask before implementing when there are multiple valid approaches or the change has architectural implications.

## When to Ask

```
BEFORE implementing a fix, check if it involves:

1. ARCHITECTURE: Changes to patterns, structure, or dependencies
2. TRADE-OFFS: Performance vs readability, DRY vs simplicity
3. SCOPE: Fix could be minimal or comprehensive
4. ALTERNATIVES: Multiple valid solutions exist
5. RISK: Change could affect other parts of the codebase
6. NEW DEPENDENCIES: Adding libraries or packages
7. BREAKING CHANGES: API changes, data migrations
```

## Decision Categories

### Always Ask

| Situation | Why |
|-----------|-----|
| Adding new dependency | Cost, maintenance, security implications |
| Changing public API | Breaking changes affect consumers |
| Data model changes | Migration complexity, data integrity |
| Architectural patterns | Consistency across codebase |
| Performance optimizations | Trade-offs with readability/complexity |
| Security-related fixes | Risk of incomplete fix or new vulnerabilities |

### Implement Directly

| Situation | Why |
|-----------|-----|
| Typos and formatting | No decision needed |
| Missing imports | Single correct answer |
| Obvious bug fixes | Clear problem, clear solution |
| Adding tests for existing code | Coverage, not architecture |
| Documentation updates | Clarification, not design |

## The Ask Pattern

```
WHEN decision required:

1. IDENTIFY: What needs deciding
2. OPTIONS: List 2-3 valid approaches
3. TRADE-OFFS: Pros/cons of each
4. RECOMMENDATION: Your suggestion with reasoning
5. ASK: Let human partner decide

FORMAT:
"This fix requires a decision:

**Issue:** [What the review feedback asks for]

**Options:**
1. [Approach A] - [brief description]
   - Pros: [benefits]
   - Cons: [drawbacks]

2. [Approach B] - [brief description]
   - Pros: [benefits]
   - Cons: [drawbacks]

**Recommendation:** [Your suggestion] because [reasoning]

Which approach do you prefer?"
```

## Real Examples

### Example 1: N+1 Query Fix

```
Review feedback: "Fix N+1 query in get_user_posts()"

❌ WRONG: Just add select_related() and move on

✅ RIGHT:
"This fix requires a decision:

**Issue:** N+1 query in get_user_posts()

**Options:**
1. select_related('author') - Eager load in single query
   - Pros: Simple, handles this case
   - Cons: Always loads author even when not needed

2. Prefetch at view level - Load in batch where needed
   - Pros: More control, only when needed
   - Cons: More code, need to update multiple views

3. Cached property - Cache author on first access
   - Pros: Lazy loading, no query changes
   - Cons: Cache invalidation complexity

**Recommendation:** Option 1 (select_related) - this view always displays author info, so eager loading makes sense here.

Which approach?"
```

### Example 2: Error Handling

```
Review feedback: "Add proper error handling to API endpoint"

❌ WRONG: Add try/catch with generic error response

✅ RIGHT:
"This fix requires a decision:

**Issue:** Missing error handling in /api/users endpoint

**Options:**
1. Generic exception handler - Catch all, return 500
   - Pros: Quick, covers everything
   - Cons: Hides specific errors, poor debugging

2. Specific exception types - Custom exceptions for each case
   - Pros: Clear error messages, better client handling
   - Cons: More code, need to define exception hierarchy

3. Result pattern - Return Result<T, Error> types
   - Pros: Type-safe, explicit error handling
   - Cons: Different from rest of codebase, learning curve

**Recommendation:** Option 2 - matches existing patterns in other endpoints.

Which approach?"
```

### Example 3: Simple Fix (No Decision Needed)

```
Review feedback: "Missing null check before accessing user.email"

✅ Just implement:
"Added null check at line 45. Returns early if user is None."

No decision needed - single correct solution.
```

## Grouping Related Decisions

```
IF multiple fixes require decisions:

1. Group related decisions together
2. Present as a cohesive set
3. Show how choices interact

"These 3 fixes are related and should be decided together:

1. Error handling approach (affects #2 and #3)
2. Logging format (depends on #1)
3. Response structure (depends on #1)

[Present options for each, showing dependencies]"
```

## After Decision

```
ONCE human partner decides:

1. CONFIRM: Restate the chosen approach
2. IMPLEMENT: Execute the decision
3. VERIFY: Show what was changed
4. MOVE ON: Don't re-ask unless new info emerges
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Assuming the "obvious" choice | Ask - your human partner may have context you don't |
| Asking about everything | Only architectural/trade-off decisions |
| Long explanations | Keep options concise |
| No recommendation | Always suggest, with reasoning |
| Implementing then asking | Ask BEFORE implementing |
| Re-asking after decision | Trust the decision, move forward |

## The Bottom Line

**When in doubt, ask.** It takes 30 seconds to ask, but hours to undo a wrong architectural decision.

Present options clearly. Give your recommendation. Let your human partner decide.
