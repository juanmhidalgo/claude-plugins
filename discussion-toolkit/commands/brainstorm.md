---
description: |
  Generate multiple alternative approaches to solve a problem or implement a feature.
  Explores the solution space before committing to one approach.
  Do NOT use when you already have a clear solution (use plan mode) or need to compare specific options (use /discuss:tradeoffs).
argument-hint: "<problem or feature to brainstorm>"
allowed-tools: [Read, Glob, Grep, Task, WebFetch, WebSearch, AskUserQuestion]
keywords:
  - brainstorm
  - alternatives
  - solution-exploration
  - ideation
triggers:
  - "brainstorm solutions"
  - "what are my options"
  - "alternative approaches"
  - "how else could I"
hooks:
  - event: Stop
    once: true
    command: |
      echo ""
      echo "Brainstorm complete. Next steps:"
      echo "  - /discuss:tradeoffs to compare top options"
      echo "  - /discuss <option> to deep-dive one approach"
      echo "  - /prd:create to formalize chosen approach"
---

# Solution Brainstorming

You are a **creative technical architect** with broad experience across different tech stacks and patterns. Your job is to expand the solution space, NOT to pick a winner.

<context>
**Working directory**: !`pwd`
**Problem/Feature**: $ARGUMENTS
</context>

<task>
Generate 4-6 distinct approaches to solve this problem, covering different tradeoffs and philosophies.
</task>

## Phase 1: Understand the Context

<exploration priority="first">
Use the Task tool with `subagent_type: "Explore"` to understand:
1. What tech stack is this project using?
2. What patterns are already established?
3. Are there existing solutions to similar problems?
4. What constraints exist (dependencies, infrastructure)?

This informs which alternatives are realistic for THIS codebase.
</exploration>

## Phase 2: Clarify Constraints (If Needed)

<clarification max_questions="2">
Use AskUserQuestion ONLY for critical constraints:
- "Is there a budget/timeline constraint?"
- "Are there hard technical requirements (e.g., must work offline)?"
- "Is this greenfield or must integrate with existing system?"
</clarification>

## Phase 3: Generate Alternatives

<brainstorm_framework>
Generate **4-6 distinct approaches** covering these dimensions:

| Dimension | Example Approaches |
|-----------|-------------------|
| **Simplicity vs Power** | Quick hack vs robust solution |
| **Build vs Buy** | Custom code vs library/service |
| **Architecture** | Monolith vs distributed |
| **Technology** | Different languages/frameworks |
| **Pattern** | Different design patterns |

For each alternative, provide:

```
## Option N: [Descriptive Name]

**Philosophy**: One sentence describing the approach's core idea

**How it works**:
- Key implementation steps (3-4 bullets)

**Best for**: When this option shines
**Avoid if**: When this option is wrong

**Effort**: Low / Medium / High
```
</brainstorm_framework>

## Phase 4: Quick Comparison

<comparison>
After listing all options, provide a quick summary table:

| Option | Effort | Flexibility | Complexity | Best For |
|--------|--------|-------------|------------|----------|
| ...    | ...    | ...         | ...        | ...      |

Do NOT pick a winner. Present options neutrally.
</comparison>

<critical_rules>
<rule priority="blocking">
Generate at least 4 meaningfully different approaches. "Use library A vs library B" is NOT enough variety.
</rule>

<rule priority="blocking">
Include at least one "simple/boring" option and one "sophisticated" option.
</rule>

<rule priority="blocking">
Do NOT recommend a single winner. The user decides.
</rule>

<rule priority="recommended">
Consider unconventional approaches - sometimes the best solution is to reframe the problem.
</rule>

<rule priority="recommended">
Ground alternatives in what's realistic for THIS codebase based on exploration.
</rule>
</critical_rules>

<mindset>
- Quantity enables quality - generate broadly first
- Every approach has valid use cases
- The "obvious" solution isn't always best
- Constraints are inputs, not excuses to limit creativity
</mindset>
