# Skill Testing Methodology

Test skills before deployment using TDD-for-documentation: RED-GREEN-REFACTOR applied to skill content.

<sources>
Inspired by the Superpowers plugin's `writing-skills` methodology and persuasion science research (Meincke et al., 2025).
</sources>

## The Problem

Skills enforce discipline, but the model rationalizes its way around them. A skill that looks correct may fail under pressure because:
- The description triggers incorrectly (too broad, too narrow, or leaks workflow steps)
- The model follows the description summary instead of reading the full skill body
- Rationalizations bypass explicit rules ("this is a simple case, I'll skip the gate")
- Edge cases aren't covered, creating loopholes

## TDD-for-Skills Cycle

### Phase 1: RED — Discover Failure Modes

Run pressure scenarios **without the skill loaded** and document exact rationalizations:

1. Give the model a task that the skill is designed to govern
2. Observe what shortcuts it takes, what steps it skips, what excuses it gives
3. Record each rationalization verbatim — these become your test cases

**Pressure scenario types:**
- **Time pressure**: "This is urgent, just fix it quickly"
- **Scope minimization**: "This is a simple change, no need for the full process"
- **Authority override**: "The reviewer/lead said to just do it"
- **Sunk cost**: "I already wrote the implementation, let me just add tests after"
- **Social compliance**: "The suggestion looks reasonable, I'll implement it"

### Phase 2: GREEN — Write Skill Addressing Failures

For each recorded rationalization, write a specific counter in the skill:

1. **Iron Law statement**: A non-negotiable rule in imperative language
2. **Rationalization table entry**: Map the exact excuse to a specific counter-response
3. **Red flag trigger**: A self-check condition ("If you catch yourself thinking X, STOP")

**Description rules:**
- Description = triggering conditions only, never workflow steps
- Include "Use when..." and "Do NOT use for..." boundaries
- Test: If the description is all Claude reads, will it still trigger correctly without executing the workflow from the description alone?

### Phase 3: REFACTOR — Find New Loopholes

1. Re-run the pressure scenarios WITH the skill loaded
2. Document any new rationalizations that bypass the skill's defenses
3. Add counters for newly discovered loopholes
4. Repeat until no rationalizations survive

## Rationalization Table Format

Every discipline-enforcing skill should include a "Rationalization Defenses" section:

```markdown
## Rationalization Defenses

If you catch yourself thinking any of these, STOP — you are about to violate [the discipline]:

| Rationalization | Why It's Wrong |
|----------------|----------------|
| "[exact excuse the model uses]" | [specific counter explaining why this is wrong] |
```

**Writing effective counters:**
- Counter the specific logic, not just the behavior
- Reference concrete consequences ("breaks things 30% of the time", "wastes hours")
- Keep counters to one sentence — long explanations get skimmed

## Persuasion Principles for Compliance

Apply these principles when writing skill content that enforces discipline:

| Principle | Application in Skills |
|-----------|----------------------|
| **Authority** | Imperative language: "YOU MUST", "NEVER", "No exceptions" |
| **Commitment** | Require announcements: "State which skill you are using before proceeding" |
| **Scarcity** | Time-bound gates: "BEFORE proceeding", "IMMEDIATELY after X" |
| **Social proof** | Universal failure modes: "Every time this is skipped, [consequence]" |
| **Consistency** | Reference prior commitments: "You already agreed to the spec" |

## Creation Log Template

For each new skill, maintain a `CREATION-LOG.md` documenting the testing process:

```markdown
# [Skill Name] — Creation Log

## Pressure Scenarios Tested

### Scenario 1: [description]
- **Input**: [what was asked]
- **Without skill**: [what the model did wrong]
- **Rationalization observed**: "[exact quote]"
- **Counter added**: [what was written to address it]

### Scenario 2: ...

## Validation Results

- [ ] All pressure scenarios pass with skill loaded
- [ ] No new rationalizations observed
- [ ] Description triggers correctly (not too broad, not too narrow)
- [ ] Description contains NO workflow steps
- [ ] Rationalization table covers all observed excuses
```

## When to Apply This Methodology

**Always apply for:**
- Skills that enforce process discipline (TDD, code review, security gates)
- Skills with `disable-model-invocation: false` (auto-triggered — higher risk of mis-triggering)
- Skills that block or gate other actions

**Skip for:**
- Pure reference/knowledge skills (no discipline to enforce)
- Skills that are `user-invocable: false` (background knowledge only)
- Simple utility skills with no process gates
