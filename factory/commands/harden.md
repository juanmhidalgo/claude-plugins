---
disable-model-invocation: true
argument-hint: "#N"
description: |
  Use when the factory daemon, or a person testing a stage headless with `claude -p`,
  runs the harden stage for issue #N (`status:in-progress`, last done marker
  `implement`): it runs the review loop on the factory branch with every confirmed
  finding fixed, commits and pushes the fixes, and ends with a done or parked outcome.
  Do NOT use interactively (use /feature-dev:harden), and never invoke it from a
  conversation: it asks nothing, commits and pushes.
keywords:
  - factory
  - headless
  - harden
  - review-loop
allowed-tools:
  - Read
  - Glob
  - Grep
  - Workflow
  - Agent
  - Bash(git *)
  - Bash(gh auth status)
  - Bash(gh repo view *)
  - Bash(gh issue view *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/factory-issue.sh *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/factory-outcome.sh *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tree-hash.sh)
  - Bash(${CLAUDE_PLUGIN_ROOT}/../feature-dev/scripts/features.py *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/../feature-dev/scripts/issue_spec.py *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/../feature-dev/scripts/review_server.py snapshot *)
  - Bash(npm *)
  - Bash(npx *)
  - Bash(yarn *)
  - Bash(pnpm *)
  - Bash(pytest *)
  - Bash(python *)
  - Bash(uv *)
  - Bash(make *)
  - Bash(cargo *)
  - Bash(go *)
---

@factory/references/factory-contract.md

# `/factory:harden` — last done = `implement` → review fixes committed

Stage `harden`. Caps are the daemon's (defaults 100 turns · 8 USD · 40 min; the real numbers for this run, per-repo overrides included, are the `Caps for this run` line under Context: size long steps against those, never against the defaults). It runs
`${CLAUDE_PLUGIN_ROOT}/references/review-loop.md` with `gate: all-confirmed`
on the branch, commits each fix round, and never asks: an out-of-bounds
finding is left open for the PR review, which is the human's gate.

## Context

- **Arguments**: $ARGUMENTS
- **Stage variable set**: !`echo "${#FACTORY_STAGE}"`
- **Caps for this run**: !`echo "turns=${FACTORY_MAX_TURNS:-default} budget_usd=${FACTORY_BUDGET_USD:-default} timeout_min=${FACTORY_TIMEOUT_MINUTES:-default}"`
- **Current branch**: !`git branch --show-current`
- **Working tree**: !`git status --short | head -20`

## Inputs

Run the contract's stage preamble (§4). The status must be
`status:in-progress` and `factory-issue.sh last-marker` must be `done
stage=implement …` or this stage's own `done`. Then:

1. `git fetch origin`; check out `FACTORY_BRANCH` tracking `origin` (it must
   exist there: otherwise `parked reason=no-branch`). A dirty tree is stashed
   as `/factory:implement` does (`git stash push -u -m "factory-#<N>-<run id>"`)
   and named in the report: the review needs a clean tree, because fixes are
   told apart from the reviewed code by `git diff`.
2. Import (contract §2) for the SPEC path and the plan; the issue's Out of
   scope section; the plan's Key Decisions; the Decisions Log. These three
   are **out of bounds** for a fix.
3. The rounds already done: `git log origin/<default>..HEAD` trailers
   `Factory-Step: harden-<r>`. Two rounds present → nothing to do: go to
   **Outputs** with `no new round` (AC-19).

## Composition

Follow `${CLAUDE_PLUGIN_ROOT}/references/review-loop.md` with:

- **scope**: `branch FACTORY_BRANCH vs base <default>`; **spec_sources**:
  `spec-file <SPEC path>` and `issue <N> closes`; **axes**: all three;
  **effort**: `high`; **title**: `Harden #<N>`; **gate**: `all-confirmed`;
  **out of bounds**: the plan's Key Decisions, the Decisions Log entries and
  the issue's Out of scope, each named.
- Step 3 (gate): the answer is **All confirmed**, as the gate says. A
  confirmed finding whose fix crosses the out-of-bounds list is left open and
  listed with the decision or scope line it crosses (AC-18); plausible
  findings are left open.
- Step 4 (fix round): the fixers' files are checked as written. A file outside
  the approved findings' files and their tests is reverted and the finding
  reported as `REFUSED: touched <file>` (the gate's rule). The scoped tests
  run; a failure → the loop's `fix-tests-red` condition → `parked
  reason=fix-tests-red` with the output, the fixes left uncommitted in the
  sandbox and `How to recover:` naming `git diff` and the test command.
- **After each fix round that changed something**: the loop runs as written
  (the fixes land in the working tree, the delta review reads `git diff`, its
  item 5 stages them). Once item 5 has staged them, commit
  `fix: review fixes, round <r> (refs #<N>)` with the trailers
  `Factory-Step: harden-<r>` and `Factory-Run: <run id>` (the staged files
  only: rule 4's exclusions still apply), and push (rejected → `parked
  reason=push-rejected`). `<r>` counts from the trailers across runs, so a
  crash after round 2's commit ends `done` on the next run with no new round.
  Two rounds at most, as the loop says; what is left after the second is
  listed, not fixed (`rounds-exhausted` is not a park).
- The loop's other conditions: `tree-changed` → `parked
  reason=tree-changed-by-reviewer` with `git status --short` and `git diff
  --stat`; `review-failed` → the loop already re-ran the axis once; the
  **defect** axis failing parks (`reason=review-failed`), the spec or debt
  axis failing is reported as `skipped` and the loop continues without it.

Nothing in this stage asks. Rule 6 (authoritative docs) applies to fixes: a
fix that needs them is left open with that reason.

## Outputs

- The fix commits on the branch (zero, one or two).
- The `done` comment: the loop's presentation block (Confirmed / Plausible /
  Unverified / Rejected / Listed, each confirmed finding with its refutation
  line) for every round, then the close block: fixed (ids), declined (out of
  bounds, with the bound each crosses), left open (ids and titles), the test
  selection that ran, the round commits, and the contract's §7 lines. With
  no finding at all: `Harden #<N>: clean`, the axes line, and the selection.
- No flip: the status stays `in-progress` (the script makes no edit call).
- The done call takes no `--sha`: the script reads the clone's HEAD, which is
  the last round's commit after its push (or implement's head when no round
  ran). A typed hash that differs is refused, so never type one.

## Cannot decide

Nothing: an out-of-bounds or plausible finding is left open for the PR
review, not asked about. This stage ends `done` or `parked`, never `question`.

## Resume

Review runs are read-only until the fix commit, so a re-run re-reviews the
branch as it is; the round count comes from the trailers. A re-run whose
latest marker is this stage's `done` runs only the flip (a no-op) and ends.
