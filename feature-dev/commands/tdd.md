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
2. **Check the working tree.**
   - **Clean** → proceed normally.
   - **Dirty** → this may be a halted run, not stray edits. Read the frontmatter of the plan resolved in step 1. If it has `run_status: in-progress` or `run_status: halted` with a non-empty `completed_steps:`, the dirty tree is *this command's own* unfinished work → go to **Phase 1b: Resume** after Phase 1.
   - **Dirty with no in-progress plan** → **STOP** and ask the user to commit or stash.

   A plan with no `run_status:` field predates v1.19.0. Treat it as `not-started` and apply the plain dirty-tree stop.

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

## Phase 1b: Resume (only if Phase 0 detected a halted run)

The plan's `completed_steps:` records what a prior run finished. Do not trust it blindly — the tree has been sitting dirty and may have been edited since.

1. **Re-verify each completed step.** Run its `Verify:` command from the plan. This is exactly why the step contract requires a real command.
   - **Green** → genuinely done, skip it.
   - **Red** → the step regressed or was reverted by hand. Drop it from the completed set and re-dispatch it in Phase 3.
2. **Report the resume point** to the user before dispatching anything:

   ```
   Resuming PLAN-<slug>.md — halted at step <N> (<halt reason from frontmatter>)
     Steps 1-<N-1>: re-verified green, skipping
     Step <M>: re-verify FAILED, will re-run
     Resuming at step <N>
   ```
3. **Reject a gapped record.** If `completed_steps` skips a number that exists in the plan, the prior run advanced past an unfinished step and the record is unreliable — **STOP** and report the gap. Resume from the gap, not from the highest recorded number.
4. If **every** completed step re-verifies red, the tree is not what the plan thinks it is → **STOP**. Ask the user to reset or re-plan; do not attempt a partial repair.

Then continue into Phase 2 with the remaining steps only.

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

Work through the criteria **one at a time, in `Depends on` order**.

### The dependency gate — check this before every dispatch

**Every step number in a step's `Depends on` must already be in `completed_steps`.** If any is missing, **STOP**. Do not dispatch. Report which dependency is outstanding and why you cannot proceed.

This is not advisory. Two rationalizations look reasonable in the moment and are both wrong:

- *"The dependency is still running, but this step touches a different repo / different files, so there is no overlap."* `Depends on` encodes a **decision gate**, not a file-locking concern. A step that depends on a verification step is waiting for an *answer* — if that answer turns out to be "red", the work you dispatched in the meantime was built on a contract that does not hold, and you now have to unpick it.
- *"The dependency will almost certainly pass."* Then waiting costs you nothing. If it fails, dispatching early cost you the whole downstream branch.

Never dispatch two agents concurrently. Beyond the dependency gate, concurrent agents collide on overlapping files and on the working tree itself — including any `git stash` window one of them opens.

### Routing

Route on **who writes the test**, not on whether `Test:` names a path. A step that only makes an already-written test pass has no RED to drive — its RED was written by an earlier step.

| Step shape | Agent | Why |
|---|---|---|
| `Test:` names a path this step creates | `feature-dev:tdd-runner` | New behavior with a test to write — drive it red-green-refactor |
| `Test:` names a path marked `(written by step N)` | `feature-dev:plan-step-executor` | RED already exists and is failing. A `tdd-runner` would try to write a test that is already there and stall on its own "did RED fail for the right reason" check |
| `Test: n/a — <reason>`, `Impl:` names a path | `feature-dev:plan-step-executor` | Migration, config wiring, dependency bump — nothing to assert test-first, but `Verify` still gates it |
| `Test: n/a` **and** `Impl: n/a` | **You, inline** | A precondition on the environment or the working tree (rebase, `makemigrations --check`, a dependency install). `plan-step-executor` is forbidden from committing and owns no git state, so dispatching one is wrong. Run the `Verify` command yourself and record the step like any other |

Non-behavioral steps are not exempt from verification. If a step of any shape has no `Verify` command, it fails Phase 2 and the run stops there.

A precondition step that fails its `Verify` is a **hard stop**, not a step to work around — the plan assumed a baseline that does not hold.

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
| Verification ran but you **cannot attribute** the result | **STOP**. See below — this is a blocker, not a pass |

**An unattributable verification is a failure, not a pass.** If a step's `Verify` produced failures you cannot confidently assign to this change rather than to a pre-existing baseline — because the baseline is red, because the output was truncated, because you stopped waiting, because a parallel runner distributes names only in a final summary you never saw — then the step is **not verified**. Halt and say so plainly, naming the unresolved failures or the fact that you could not name them.

Do **not**: advance to the next step, mark the step in `completed_steps`, commit, or describe the run as complete with a caveat attached. "N tests pass and 2 failures are probably pre-existing" is an unverified step wearing a verified step's clothes. Hand the ambiguity to the user — they can tell you the baseline in one sentence, which is cheaper than you guessing.

4. **Record progress.** After each step that passes, use Edit on the `PLAN-*.md` frontmatter to append the step number to `completed_steps:` and set `run_status: in-progress`. **`completed_steps` must never contain a gap** — a recorded `[0,1,2,4]` claims step 3 was completed-and-skipped, which is not a state this command can produce. If you are about to write a gap, you have advanced past an unfinished step: stop and fix that instead. On a halt, set `run_status: halted` and add `halted_at: <step number>` plus a one-line `halt_reason:`. This is what makes the run resumable — a halted run that recorded nothing is a lost run.

   Do **not** commit between steps. The command's contract is one reviewable change set at the end; `/commit` and `/code-review:branch` come after, via the Stop hook.

Thread only the **carry-over deltas** forward (new symbols, new fixtures, new test markers, schema changes) — not the full prior reports. The next agent needs the deltas, not a retrospective.

Do not re-dispatch a failed step with a "better" prompt. That masks a defect in the step or the plan; halt and let the user re-scope.

**Do not substitute a step's `Verify` command on your own.** If a plan's `Verify` turns out to be defective — it fails on pre-existing errors, it would rewrite unrelated files, it names a gate that is unusable in this repo — that is a real finding and you should surface it. But a narrower command you chose yourself is a **different gate than the one the plan was reviewed against**. Halt, state the defect, propose the substitute, and let the user accept it. Running your own substitute and recording the step as passed converts a plan defect into a silent scope reduction.

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

If any criterion halted, do **none** of the above. Leave the plan and spec on disk with `run_status: halted`, and tell the user verbatim:

> Halted at step `<N>`. Fix the blocker, then re-run `/feature-dev:tdd` — it will re-verify steps 1-`<N-1>` and resume from `<N>`. The dirty working tree is expected; do not stash it.

The stash instruction matters: stashing is the one action that makes the recorded progress unrecoverable.
