---
description: |
  Create a step-by-step refactoring plan from analysis findings.
  Produces an ordered list of changes with dependencies and checkpoints.
  Use after /refactor:analyze to organize the work.
argument-hint: "[file-or-topic]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Task
  - AskUserQuestion
hooks:
  - event: Stop
    once: true
    command: |
      echo ""
      echo "Plan created."
      echo "  - /refactor:extract to start implementing"
      echo "  - Enter plan mode to execute step by step"
---

# Refactoring Plan

Create a structured refactoring plan.

**Target**: $ARGUMENTS

## Phase 1: Gather Context

<exploration>
If no recent analysis exists, use the Task tool with `subagent_type: "Explore"` to understand:

1. What needs to be refactored and why
2. Current test coverage
3. Dependencies that could break
4. Similar refactorings done in this project
</exploration>

## Phase 2: Clarify Scope

<clarification>
Use AskUserQuestion to confirm:

- "What's the primary goal: reduce complexity, improve testability, or prepare for a new feature?"
- "Are there parts of the code that must NOT change?"
- "What's the acceptable risk level: conservative or aggressive?"
</clarification>

## Phase 3: Generate Plan

<output_format>
```markdown
# Refactoring Plan: [target]

## Goal
[One sentence describing the end state]

## Scope
- **In scope**: [what will change]
- **Out of scope**: [what stays unchanged]
- **Risk level**: Low / Medium / High

## Pre-Refactoring Checklist
- [ ] Tests pass before starting
- [ ] Git branch created: `refactor/[name]`
- [ ] Backup or stash any uncommitted work

## Steps

### Phase 1: Preparation (Low Risk)
No behavior changes - just setup.

#### Step 1.1: [Add missing tests]
- **Files**: `test_file.py`
- **What**: Add tests for [uncovered behavior]
- **Why**: Safety net before changes
- **Checkpoint**: Run tests, should pass

#### Step 1.2: [Extract constants]
- **Files**: `file.py`
- **What**: Move magic numbers to named constants
- **Why**: Makes next steps easier
- **Checkpoint**: Tests pass, no behavior change

### Phase 2: Core Refactoring (Medium Risk)
Main structural changes.

#### Step 2.1: [Extract function/class]
- **Files**: `file.py`
- **What**: Extract [code block] into [new_function]
- **How**:
  1. Create new function with signature
  2. Move code
  3. Replace original with call
  4. Run tests
- **Checkpoint**: Tests pass

#### Step 2.2: [Rename for clarity]
...

### Phase 3: Cleanup (Low Risk)
Polish and documentation.

#### Step 3.1: [Remove dead code]
...

#### Step 3.2: [Update documentation]
...

## Rollback Plan
If something goes wrong:
1. `git stash` current changes
2. `git checkout main`
3. Investigate what broke
4. Either fix forward or abandon

## Success Criteria
- [ ] All tests pass
- [ ] [Specific metric improved: e.g., function <30 lines]
- [ ] No new linter warnings
- [ ] Code review approved

## Estimated Effort
| Phase | Time | Risk |
|-------|------|------|
| Phase 1 | [X hours] | Low |
| Phase 2 | [X hours] | Medium |
| Phase 3 | [X hours] | Low |
| **Total** | [X hours] | |
```
</output_format>

<critical_rules>
<rule priority="blocking">
Every step must have a checkpoint to verify success.
</rule>

<rule priority="blocking">
Order steps by risk - low risk first.
</rule>

<rule priority="blocking">
Include rollback instructions.
</rule>

<rule priority="recommended">
Keep individual steps small enough to complete in <30 minutes.
</rule>
</critical_rules>
