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

## After Decision

```
ONCE human partner decides:

1. CONFIRM: Restate the chosen approach
2. IMPLEMENT: Execute the decision
3. VERIFY: Show what was changed
4. MOVE ON: Don't re-ask unless new info emerges
```

## Grouping Related Decisions

```
IF multiple fixes require decisions:

1. Group related decisions together
2. Present as a cohesive set
3. Show how choices interact
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

## Real Examples

See [examples.md](references/examples.md) for detailed examples:
- N+1 query fix with multiple approaches
- Error handling architectural decision
- Simple fix that needs no decision

## The Bottom Line

**When in doubt, ask.** It takes 30 seconds to ask, but hours to undo a wrong architectural decision.

Present options clearly. Give your recommendation. Let your human partner decide.
