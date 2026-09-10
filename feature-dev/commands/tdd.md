---
disable-model-invocation: true
allowed-tools:
  - Bash(git *)
  - Bash(npm *)
  - Bash(npx *)
  - Bash(yarn *)
  - Bash(pnpm *)
  - Bash(pytest *)
  - Bash(python *)
  - Bash(make *)
  - Bash(cargo *)
  - Bash(go *)
  - Read
  - Write
  - Edit
  - Agent
  - Glob
  - Grep
skills:
  - tdd-patterns
argument-hint: "[feature spec — optional; auto-discovers PLAN-*.md if omitted]"
description: |
  Use when implementing a new feature or fixing a bug where you want tests to lead, not follow.
  Do NOT use for quick one-line fixes or refactors without behavioral change.
keywords:
  - tdd
  - test-driven
  - feature-development
  - coverage
  - red-green-refactor
triggers:
  - "implement with TDD"
  - "test-driven development"
  - "write tests first"
  - "implement feature with coverage"
hooks:
  - event: Stop
    once: true
    command: |
      echo "TDD cycle complete."
      echo "  - /code-review:branch to review before merge"
      echo "  - /commit to commit changes"
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this command and proceed with your assigned task.
</SUBAGENT-STOP>

## Context
- **Repository**: !`git remote get-url origin`
- **Current branch**: !`git branch --show-current`
- **Working tree clean**: !`git status --short`
- **Feature spec**: $ARGUMENTS

## Phase 0: Resolve Spec and Validate

1. **Resolve the feature spec:**
   - **If `$ARGUMENTS` is provided** → use it as the feature spec. Continue to step 2.
   - **If `$ARGUMENTS` is empty** → auto-discover plan files. Use Glob with pattern `PLAN-*.md` in the repo root:
     - **0 plans found** → **STOP** and ask the user for a feature description.
     - **1 plan found** → read it, extract the `feature:` value from its frontmatter, and use that as the spec. Record the plan path as the **pre-selected plan** for Phase 1. Inform the user: "Auto-selected plan: `PLAN-<slug>.md` (feature: <name>)".
     - **2+ plans found** → read each plan's frontmatter to extract the `feature:` value. Use AskUserQuestion to let the user pick one (label = feature name, description = filename). The chosen plan's `feature:` becomes the spec and its path is the **pre-selected plan** for Phase 1.
2. **Working tree is clean.** If dirty, **STOP** and ask the user to commit or stash.

## Phase 1: Load Plan or Explore Codebase

**First, determine the plan:**

- **If a pre-selected plan was set in Phase 0** → use it directly; skip the search below.
- **Otherwise** (spec came from `$ARGUMENTS`), look for `PLAN-*.md` files in the repo root (created by `/feature-dev:explore-plan`). If multiple exist, pick the one whose `feature:` frontmatter best matches the spec; if none clearly matches, ask the user which to use.

**If a plan file is in use:**
- Read it and use it as the source of truth for files to modify/create, implementation order, and key decisions
- **Drift check**: if the plan's frontmatter has `source_spec:` pointing to a `SPEC-*.md` file, compare modification times (`stat -c %Y <spec>` and `stat -c %Y <plan>`, or `git log -1 --format=%ct -- <file>` as a fallback). If the spec is newer than the plan, **warn the user**: "The source spec `<path>` was modified after the plan was generated. The plan may be stale. Proceed with the current plan, or re-run `/feature-dev:explore-plan` first?" and wait for confirmation.
- Only do a **minimal exploration** with the Agent tool (`subagent_type: "Explore"`) focused on:
  - Test framework and runner command
  - Coverage tool and current thresholds
  - Existing test patterns (naming, structure, fixtures)
- Skip general codebase exploration — the plan already has that context

**If no plan file exists:**
- Use the Agent tool with `subagent_type: "Explore"` to understand:
  1. **Existing patterns**: Test conventions, file structure, naming, frameworks (pytest/vitest/jest/etc.)
  2. **Related code**: Models, services, components, APIs relevant to the feature
  3. **Test infrastructure**: Fixtures, factories, mocks, helpers, config files

Summarize findings before proceeding. Include:
- Test framework and runner command
- Coverage tool and current thresholds (if configured)
- Key files to modify/create
- Existing patterns to follow

## Phase 2: Resolve Acceptance Criteria

**You are the orchestrator from here on. You do not write tests or production code — the runners do.**

Every criterion needs six fields before anything is dispatched. Where they come from depends on whether a plan is in use.

### If a `PLAN-*.md` is in use (the normal path)

The plan's **Implementation Order** already carries them, one block per step:

```
1. **[Step name]**
   - Accept: ...      → behavior
   - Impl: ...        → impl target path
   - Test: ...        → test target path (or `n/a — <reason>`)
   - Verify: ...      → verification command
   - Depends on: ...  → dispatch order
```

**Take these verbatim. Do not re-derive, re-word, or "improve" them** — the plan was reviewed; re-deriving silently drops that review. The spec reference is the plan path + step number (or its `source_spec:` if set). Cycle cap is 5 unless the step is a tight bug fix.

**If a step is missing `Accept:` or `Verify:`, or `Verify:` is a description rather than a runnable command** → **STOP**. The plan predates the step contract or was hand-edited. Tell the user to run `/feature-dev:plan-review` and re-generate with `/feature-dev:explore-plan`. Do not fill the gap by inference — that is the improvisation the runner contracts exist to prevent.

### If no plan exists (spec came from `$ARGUMENTS`)

Derive the criteria yourself from the spec and the Phase 1 exploration, producing the same six fields per criterion. A criterion is correctly sized when it is:

- **Specific and testable** — not "add the booking flow", but "when contact has no active subjects, `start_booking` returns `NO_SUBJECTS` error code"
- **Independently verifiable** — one command proves it
- **Bounded to one impl target** — if it needs edits in two unrelated modules, split it

`Verify` must be a real command built from the runner and path conventions Phase 1 reported — never a placeholder.

### Before dispatching

Present the numbered criteria list to the user, each with its route (see Phase 3). If the source is too coarse to yield testable criteria, **STOP** and say so — TDD on a vague target produces tests that lie.

## Phase 3: Execute (delegated, sequential)

Work through the criteria **one at a time, in `Depends on` order**. Never dispatch two runners concurrently — they collide on overlapping files, and later criteria consume symbols earlier ones introduce.

### Routing

| Step shape | Agent | Why |
|---|---|---|
| `Test:` names a test file | `feature-dev:tdd-runner` | Behavioral change — drive it red-green-refactor |
| `Test: n/a — <reason>` | `feature-dev:plan-step-executor` | Migration, config wiring, dependency bump — nothing to assert test-first, but `Verify` still gates it |

Non-behavioral steps are not exempt from verification. If such a step has no `Verify` command, it fails Phase 2 and the run stops there.

### Loop

For each criterion:

1. **Spawn** the Agent tool with the routed `subagent_type`, passing that agent's contract fields plus the **accumulated carry-over** from all prior steps in this run.
2. **Parse its report.** `tdd-runner`: Behavior / Cycles run / Tests added / Production changes / Verification / Halt reason / Carry-over / Blockers. `plan-step-executor`: Files changed / Verification / Deviations / Carry-over / Blockers.
3. **Decide:**

| Outcome | Action |
|---|---|
| `criteria met` / verification passed, no blockers | Accumulate carry-over, advance |
| `RED passed early` | Behavior already exists. Note it, advance — do **not** re-dispatch |
| `cycle cap` | Re-dispatch **once** with the remaining slice and accumulated carry-over. If it caps again, **STOP** and report |
| `GREEN unreachable` / verification failed | **STOP**. Report the diagnosis verbatim |
| `scope mismatch` | **STOP**. The step's impl target was wrong — the plan needs revision |
| `blocker` | **STOP**. Report the blocker verbatim |
| Deviation but verification passed | Accept, note it in the final report, continue |

Thread only the **carry-over deltas** forward (new symbols, new fixtures, new test markers, schema changes) — not the full prior reports. The next agent needs the deltas, not a retrospective.

Do not re-dispatch a failed step with a "better" prompt. That masks a defect in the step or the plan; halt and let the user re-scope.

**RED-GREEN-REFACTOR all happen inside each `tdd-runner`** — including the per-cycle refactor pass and the validation that RED failed for the right reason. There is no separate refactor phase in this command.

## Phase 4: Coverage Check

Each runner gates coverage on the lines it added. This phase checks the aggregate.

1. Run the project's coverage tool across the **changed files** from all runners
2. Compare against project thresholds (from config) or 80% minimum
3. If below threshold: identify the uncovered paths and dispatch one more `tdd-runner` per meaningful gap, treating each as a new criterion. Do not write the tests inline
4. If no coverage tool is configured, skip with a note

## Phase 5: Lint and Format

Run the project's linter and formatter once, across everything the runners touched:

1. Detect tool: `ruff`/`black`/`eslint`/`prettier`/`rustfmt`/`gofmt`
2. Fix any issues — this is mechanical, handle it inline
3. Re-run the full test suite to confirm nothing broke

## Phase 6: Report

Output a final summary:

```
## TDD Results

### Feature: [brief description]

### Criteria: [N] total — [N] met, [N] already satisfied, [N] halted

| # | Criterion | Cycles | Outcome |
|---|-----------|--------|---------|
| 1 | [criterion] | 2/5 | met |

### Tests Written: [count]
- [test file]: [count] tests ([brief categories])

### Implementation Files Modified: [count]
- [file path] — [what was changed]

### Coverage: [percentage] on changed files (threshold: [threshold])

### Test Run: ALL PASSING

### Blockers: [verbatim, or None]

### Ready to commit: Yes/No
```

If every criterion was met and the suite is green:
1. **Close the loop on the source spec (if any):** if the plan's frontmatter had a `source_spec:` pointing to a `SPEC-*.md` file, use Edit to set that spec's `status:` field to `implemented`. This prevents auto-discovery from re-surfacing a completed feature on future runs.
2. **Delete the `PLAN-*.md` file** that was used (it has served its purpose — the implementation is done).
3. Suggest a commit message following the project's convention.

If any criterion halted, do **none** of the above — leave the plan and spec intact so the run can be resumed.
