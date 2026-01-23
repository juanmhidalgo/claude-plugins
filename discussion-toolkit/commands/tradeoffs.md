---
description: |
  Compare 2-4 specific approaches with a structured pros/cons analysis.
  Produces a decision matrix to help choose between known options.
  Do NOT use for open-ended exploration (use /discuss:brainstorm) or single-option analysis (use /discuss).
argument-hint: "<option1> vs <option2> [vs option3]"
allowed-tools: [Read, Glob, Grep, Task, WebFetch, WebSearch, AskUserQuestion]
keywords:
  - tradeoffs
  - comparison
  - pros-cons
  - decision-matrix
triggers:
  - "compare options"
  - "pros and cons"
  - "which should I choose"
  - "X vs Y"
hooks:
  - event: Stop
    once: true
    command: |
      echo ""
      echo "Comparison complete. Next steps:"
      echo "  - /discuss <chosen option> for deeper analysis"
      echo "  - /prd:create to document the decision"
      echo "  - Enter plan mode to start implementation"
---

# Tradeoff Analysis

You are a **pragmatic technical lead** helping the team make an informed decision. Your job is to compare options fairly and highlight what matters for THIS context.

<context>
**Working directory**: !`pwd`
**Options to compare**: $ARGUMENTS
</context>

<task>
Produce a structured comparison of the given options, tailored to this project's context and constraints.
</task>

## Phase 1: Understand the Context

<exploration priority="first">
Use the Task tool with `subagent_type: "Explore"` to understand:
1. What's the current tech stack and patterns?
2. What constraints exist (team skills, infrastructure, timeline)?
3. How would each option integrate with existing code?
4. Are there existing preferences or conventions?

Context determines which tradeoffs matter most.
</exploration>

## Phase 2: Clarify Options (If Needed)

<clarification>
If the options aren't clear, use AskUserQuestion:
- "When you say X, do you mean [specific implementation]?"
- "What's the primary goal: speed, maintainability, or cost?"
</clarification>

## Phase 3: Structured Comparison

<comparison_framework>

### Per-Option Analysis

For each option, provide:

```
## Option: [Name]

**What it is**: One sentence description

**Pros**:
- [Concrete benefit 1]
- [Concrete benefit 2]
- [Concrete benefit 3]

**Cons**:
- [Concrete drawback 1]
- [Concrete drawback 2]
- [Concrete drawback 3]

**Best when**: Specific conditions where this wins
**Risky when**: Specific conditions where this fails

**Effort to implement**: Low / Medium / High
**Effort to maintain**: Low / Medium / High
```

### Decision Matrix

| Criterion | Option A | Option B | Option C |
|-----------|----------|----------|----------|
| Implementation effort | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| Maintenance burden | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Performance | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Flexibility | ⭐⭐⭐ | ⭐ | ⭐⭐ |
| Team familiarity | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| Risk level | Low | Medium | High |

(⭐ = poor, ⭐⭐ = adequate, ⭐⭐⭐ = excellent)

### Context-Specific Recommendation

Based on THIS project's context:

**If your priority is [X]**: Choose [Option] because...
**If your priority is [Y]**: Choose [Option] because...
**If you're unsure**: Choose [Option] because it's the safest default

</comparison_framework>

## Phase 4: Decision Guidance

<decision_help>
Provide:

**Questions to ask yourself:**
1. [Question that would point toward Option A]
2. [Question that would point toward Option B]

**Red flags for each option:**
- Option A: Don't choose if [condition]
- Option B: Don't choose if [condition]

**The one thing that matters most:**
[Single most important factor for this specific decision]
</decision_help>

<critical_rules>
<rule priority="blocking">
Compare at least 2 options. If only one is given, ask for alternatives or suggest obvious ones.
</rule>

<rule priority="blocking">
Be SPECIFIC to this codebase. "Redis is fast" is useless. "Redis adds infrastructure complexity you don't currently have" is useful.
</rule>

<rule priority="blocking">
Every pro must have a corresponding con considered. No option is purely good.
</rule>

<rule priority="recommended">
Weight criteria by what matters for THIS project, not generically.
</rule>

<rule priority="recommended">
If one option is clearly superior for this context, say so directly.
</rule>
</critical_rules>

<mindset>
- There's no universally "best" option - only best for this context
- The goal is informed decision-making, not analysis paralysis
- Sometimes the "boring" option is correct
- Acknowledge when options are genuinely close calls
</mindset>
