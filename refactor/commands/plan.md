---
description: |
  Use after /refactor:analyze when you need an ordered plan before executing changes.
  Do NOT use to make code changes directly — use /refactor:extract for that.
argument-hint: "[file-or-topic]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Workflow
  - AskUserQuestion
hooks:
  - event: Stop
    once: true
    command: |
      echo ""
      echo "Plan created."
      echo "  - /refactor:extract to start implementing"
      echo "  - /feature-dev:tdd to implement with test-driven development"
---

# Refactoring Plan

Create a structured refactoring plan.

**Target**: $ARGUMENTS

## Phase 1: Gather Context

<exploration>
**Requires the `Workflow` tool.** If `Workflow` is not available, **STOP** and
say so: under `claude -p` or the SDK it needs a `Workflow(refactor:refactor)`
allow rule. There is no in-session fallback: the planner and the conflict
scout are the fan-out this command exists to keep out of the conversation.

Before launching, list with Grep (not sampled):

- **Targets**: every file and directory the refactor will touch — including the
  consumers that a rename would reach, not just the file being restructured.
- **Symbols**: the names you expect to rename, move, or delete. Leave empty
  only if the refactor genuinely renames nothing; the semantic-overlap scan is
  the half git cannot do for you.

Then launch the `refactor:refactor` workflow and wait for its notification. It
runs `refactor-planner` and `conflict-scout` in parallel and returns both
reports as structured data:

```
Workflow({ name: "refactor:refactor", args: {
  mode: "plan", target: "<the target>",
  targets: ["<path>", "<path>"], symbols: ["<name>", "<name>"] } })
```

- `target` is the file, directory or topic as given.
- Add `skip_explore: true` only if a recent `/refactor:analyze` already covers
  this target; the scout always runs.
- Add `base: "<branch>"` only when the user named a base branch; otherwise the
  scout reads it from `origin/HEAD`.

The planner gathers **what needs to change and why**, **test coverage**,
**dependencies that could break** and **similar refactorings done in this
project**. The scout maps the targets and symbols against open PRs, branches
and local work. A plan written without this scan orders the work by internal
risk alone and ignores the only cost that grows while you work: someone else's
branch drifting away from yours.

**Read what comes back.** `summary` is first and survives a result cut off at
the end; the full reports are `explore` (the planner) and `scout`:

- `summary.explore` is `ran`, `skipped` (you passed `skip_explore`) or
  `failed`. A failed planner did not explore: say so and offer to re-run before
  writing the coverage and dependency parts of the plan from your own reading.
- `summary.verdict` is the scout's `CLEAR | CONTESTED | BLOCKED`, or
  `UNSCANNED` when the scout failed twice. Copy `scout.verdict_reason` into
  Concurrent Work verbatim. `summary.gh_available` false and every line of
  `summary.data_gaps` go there too: a scan on missing data is never clean.
- `scout.textual` (same file) and `scout.semantic` (a PR calls a symbol you
  rename) are the contested targets; each needs a handling decision in the
  plan. `scout.local` feeds the pre-flight checklist; `scout.sequencing` the
  phase order.
- `explore.coverage.gaps` become Phase 1 test steps; `explore.risks` and
  `explore.suggested_order` shape Phase 2. `explore.clarifications` are
  questions to fold into Phase 2 below.
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

From the workflow's `scout` report. State its verdict and `verdict_reason` verbatim; if the verdict is `UNSCANNED` or `gh_available` is false, say so instead of claiming a clean scan, and list `data_gaps`.

**Verdict**: CLEAR | CONTESTED | BLOCKED — [one sentence]

| Target | Concurrent work | Type | Handling |
|--------|-----------------|------|----------|
| `path` | PR #N "title" (@author, 12d, +340/-120) | textual — same functions | defer to Phase 3, after #N merges |
| `symbol` | PR #N calls it in `path:line` | semantic — merges clean, breaks after | land after #N, or tell @author |
| `path` | uncommitted local edits | local | commit or stash in the pre-flight checklist |

(If nothing is in flight, write exactly: "No open PRs, branches, or local edits touch these files.")

## Call Sites

Every reference to a symbol being renamed, moved, or deleted, found with Grep (not sampled). The user checks this list to confirm nothing was missed.

| Symbol | Call site | Step that updates it |
|--------|-----------|----------------------|
| `old_name` | `path/to/file.py:42` | 2.2 |
| `old_name` | `templates/x.html:7` (string reference) | 2.2 |

**Total**: [N] call sites in [M] files. Searched: [the exact patterns used, including string/dynamic forms such as `getattr`, templates, config]

(If the refactor renames, moves, or deletes nothing, write exactly: "No symbols change name or location.")

## Execution Mode

- **Step by step** (default): follow the phases below
- **Hand off to `/batch`**: when the migration is mechanical and touches many files (roughly 10+ files, or call sites that can each be updated independently), offer the built-in `/batch <instruction>`; it splits the work into independent units, each in its own worktree. Pass it this plan's Goal, the Call Sites table, and the checkpoints. Not for steps that must land in order

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
2. `git checkout <base-branch>`
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
If the scout's verdict is `UNSCANNED` or `gh_available` is false, the plan says so under Concurrent Work. Never write a clean scan you did not get.
</rule>

<rule priority="blocking">
List every call site of a symbol the plan renames, moves, or deletes — with the search patterns used — so the user can verify coverage. "Update all callers" without the list is a defect in the plan.
</rule>

<rule priority="recommended">
Keep individual steps small enough to complete in <30 minutes.
</rule>
</critical_rules>
