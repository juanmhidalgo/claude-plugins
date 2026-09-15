---
description: |
  Use after /refactor:analyze when you need an ordered plan before executing changes.
  Do NOT use to make code changes directly — use /refactor:extract for that.
argument-hint: "[file-or-topic]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Agent
  - AskUserQuestion
hooks:
  - event: Stop
    once: true
    command: |
      echo ""
      echo "Plan created."
      echo "  - /refactor:extract to start implementing"
      echo "  - /feature-dev:tdd to implement with test-driven development"
      echo "  - Enter plan mode to execute step by step"
---

# Refactoring Plan

> **Recommended:** run in plan mode (`Shift+Tab` to toggle) so the proposed plan is reviewed before any code changes.

Create a structured refactoring plan.

**Target**: $ARGUMENTS

## Phase 1: Gather Context

<exploration>
Launch both agents in a SINGLE response so they run concurrently.

Agent — `subagent_type: "refactor:refactor-planner"` (skip only if a recent analysis already covers this) to understand:

1. What needs to be refactored and why
2. Current test coverage
3. Dependencies that could break
4. Similar refactorings done in this project

Agent — `subagent_type: "refactor:conflict-scout"`, always. Pass:
- **Targets**: every file and directory the refactor will touch — including the consumers that a rename would reach, not just the file being restructured.
- **Symbols**: the names you expect to rename, move, or delete. Leave empty only if the refactor genuinely renames nothing; the semantic-overlap scan is the half git cannot do for you.

A plan written without this scan orders the work by internal risk alone and ignores the only cost that grows while you work: someone else's branch drifting away from yours.
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

## Concurrent Work

From the conflict scout. State its verdict verbatim; if it could not reach `gh`, say so instead of claiming a clean scan.

**Verdict**: CLEAR | CONTESTED | BLOCKED — [one sentence]

| Target | Concurrent work | Type | Handling |
|--------|-----------------|------|----------|
| `path` | PR #N "title" (@author, 12d, +340/-120) | textual — same functions | defer to Phase 3, after #N merges |
| `symbol` | PR #N calls it in `path:line` | semantic — merges clean, breaks after | land after #N, or tell @author |
| `path` | uncommitted local edits | local | commit or stash in the pre-flight checklist |

(If nothing is in flight, write exactly: "No open PRs, branches, or local edits touch these files.")

## Pre-Refactoring Checklist
- [ ] Tests pass before starting
- [ ] Branch rebased on the latest base — a refactor started behind conflicts twice
- [ ] Git branch created: `refactor/[name]`
- [ ] Backup or stash any uncommitted work
- [ ] Contested files from Concurrent Work confirmed still contested (PRs move fast; re-check `gh pr list` if the plan is more than a day old)

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

## Conflict Handling

For each contested target, the plan commits to one of these — never leaves it implicit:

| Situation | Move |
|-----------|------|
| PR is small and young (<3 days, <10 files) | Do that target **first and now**; land the refactor before the PR grows |
| PR is large or long-lived | **Defer** the target to a later phase; note "blocked on #N" on the step |
| PR only *calls* a symbol being renamed | Keep a **deprecation shim** (old name delegating to new) until #N merges, then remove it in a cleanup step |
| Work is local and yours | Commit or stash it in the pre-flight checklist — no plan step needed |

A step that touches a contested file carries `**Blocked on**: PR #N` on its own line, so it is visible when the step is dispatched, not only here.

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

<rule priority="blocking">
Every contested target from the conflict scout appears in the plan with an explicit handling decision — do-first, defer, shim, or local cleanup. Silently planning a step over someone else's open PR is a defect in the plan.
</rule>

<rule priority="blocking">
If the conflict scout could not reach `gh`, the plan says so under Concurrent Work. Never write a clean scan you did not get.
</rule>

<rule priority="recommended">
Keep individual steps small enough to complete in <30 minutes.
</rule>
</critical_rules>
