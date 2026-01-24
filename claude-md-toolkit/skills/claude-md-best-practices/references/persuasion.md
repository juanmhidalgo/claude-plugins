# Persuasion Principles for CLAUDE.md

Use these principles to enforce critical rules effectively.

## Authority

**When to use**: Blocking requirements, safety-critical practices

```xml
<rule priority="blocking">
Write code before test? Delete it. Start over. No exceptions.
</rule>
```

**Language**: "YOU MUST", "NEVER", "No exceptions", imperative framing

## Commitment

**When to use**: Multi-step processes, accountability

```xml
<instructions>
Before proceeding, you MUST:
1. Announce which skill you're using
2. Create TodoWrite checklist
3. Mark each step completed
</instructions>
```

**Requires**: Announcements, explicit choices, tracking

## Social Proof

**When to use**: Establishing norms, warning about failures

```xml
<anti_pattern>
Checklists without TodoWrite = steps get skipped. Every time.
</anti_pattern>
```

**Language**: "Every time", "Always", "X without Y = failure"

## Scarcity

**When to use**: Time-sensitive workflows, preventing procrastination

```xml
<workflow>
After implementation: IMMEDIATELY run tests before proceeding.
</workflow>
```

**Language**: "IMMEDIATELY", "Before proceeding", "First thing"

## Combining Principles

For maximum effect, combine principles:

```xml
<rule priority="blocking" id="mandatory-testing">
  <!-- Authority -->
  YOU MUST run tests after every change.

  <!-- Social Proof -->
  Skipping this step = bugs in production. Every time.

  <!-- Commitment -->
  Before committing: announce "Tests passing" or stop.

  <!-- Scarcity -->
  IMMEDIATELY after implementation, not "later".
</rule>
```
