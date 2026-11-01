---
disable-model-invocation: true
argument-hint: "#N"
description: |
  Use when the factory daemon, or a person testing a stage headless with `claude -p`,
  runs the implement stage for issue #N (`status:ready` or `in-progress` with no done
  marker): it drives the plan's steps through the step loop on the factory branch,
  one commit and one push per step, and ends with a done, question or parked outcome.
  Do NOT use interactively (use /feature-dev:tdd), and never invoke it from a
  conversation: it asks nothing, commits and pushes.
keywords:
  - factory
  - headless
  - implement
  - tdd
  - step-loop
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
  - SendMessage
  - Bash(git *)
  - Bash(gh auth status)
  - Bash(gh repo view *)
  - Bash(gh issue view *)
  - Bash(gh issue edit * --body-file *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/factory-issue.sh *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/factory-outcome.sh *)
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
  - Bash(ruff *)
  - Bash(black *)
  - Bash(eslint *)
  - Bash(prettier *)
---

@factory/references/factory-contract.md

# `/factory:implement` — `status:ready` / `in-progress` → commits on the branch

Stage `implement`. Caps are the daemon's (200 turns · 15 USD · 90 min). This
stage runs the plan's Implementation Order through
`${CLAUDE_PLUGIN_ROOT}/references/step-loop.md` with one commit and one push
per step, so a killed run loses at most one step and resume is `git log`.

## Context

- **Arguments**: $ARGUMENTS
- **Stage variable set**: !`echo "${#FACTORY_STAGE}"`
- **Branch variable set**: !`echo "${#FACTORY_BRANCH}"`
- **Current branch**: !`git branch --show-current`
- **Working tree**: !`git status --short | head -20`

## Inputs

Run the contract's stage preamble (§4). The status must be `status:ready`
(first run) or `status:in-progress` with no `factory:done` marker from this
stage. Then: the spec and plan sections (Import, contract §2; both are needed
→ a missing plan section is `parked reason=no-plan-section`), the branch,
`git log origin/<default>..FACTORY_BRANCH` and its `Factory-Step` trailers, the
Decisions Log rebuilt from the `## Decision — <slug>` comments (Import does
it), and the comments after the last marker (an answer, contract §5).

## Start

1. `git fetch origin`. `FACTORY_BRANCH` exists on `origin` → `git checkout
   FACTORY_BRANCH` tracking it (`git checkout -B FACTORY_BRANCH
   origin/FACTORY_BRANCH` when no local branch exists). Otherwise `git
   checkout -b FACTORY_BRANCH origin/<default>` and `git push -u origin
   FACTORY_BRANCH`; a rejected push → `parked reason=push-rejected`.
2. **First run** (no `Factory-Step` trailer on the branch, status
   `status:ready`): flip `status:ready → status:in-progress` now, with
   `factory-outcome.sh flip <N> --stage implement`, before any commit. This is
   the stage's first write; a crash after it re-enters as `in-progress` with
   no done marker, which is this stage again.
3. **Dirty tree** (a crash mid-step): `git stash push -u -m
   "factory-#<N>-<run id>"` (never `.feature-dev/`, which is excluded) and
   name the stash in the report. Work that reached a commit was pushed; a stash
   is at most one step and stays in the sandbox.
4. **Rebuild `feature.json` from git.** Import leaves the feature `planned`
   with the plan's step count (issue-store.md step 5b). Then, for each
   `Factory-Step: <n>` trailer in `git log origin/<default>..HEAD`, ascending,
   run `features.py step <slug> done <n>`. A gap in the trailers (a `3`
   without a `2`) → `parked reason=step-gap`. Trailers `coverage` and `lint`
   mean the loop already finished: go to **End** (a re-run after a crash
   between the last commit and the done comment).
5. **Resume as the step loop's section 1** (`resume: yes`) when any step is
   recorded: re-run the `Verify:` of every recorded step; a red one →
   `features.py step <slug> reopen <m>` and re-dispatch from `m` (its commit
   stays in history; the new work lands in a new commit); every recorded step
   red → `parked reason=branch-diverged`. Say in the report which steps were
   re-verified and which reopened (AC-15).

**Plan changed mid-run.** After the first commit, the issue's plan section
must still match the fingerprint the cache recorded (`issue_spec.py
fingerprint --kind plan` on the body vs `issue.plan_fingerprint`). A
mismatch → `parked reason=plan-changed-mid-run`: a human edited the plan
after work started, and only a human can say whether the branch restarts. The
one exception is a Baseline row this stage itself settled (below), which it
republishes before continuing.

## Loop

Follow `${CLAUDE_PLUGIN_ROOT}/references/step-loop.md` with these inputs:

- **plan**: `.feature-dev/features/<slug>/PLAN-<slug>.md`, the slug, the repo
  root; **scripts** = `${CLAUDE_PLUGIN_ROOT}/../feature-dev/scripts`.
- **spec**: the SPEC from Import; its Decisions Log entries are prior decisions.
- **baseline**: the plan's table; HEAD is the branch head, which is past the
  Baseline's sha by this stage's own commits only, so the rows stay attributable
  unless the base moved (say so in the report; it is not a halt).
- **gate policy**: `settled`.
- **resume**: as decided in Start.
- **after each step**: once `step done n` is recorded —
  1. stage per the contract's rule 4 (`git add -A -- . ':!.env' ':!.env.*'
     ':!*.pem' ':!id_rsa*' ':!*credentials*' ':!.feature-dev'`);
  2. commit:

     ```
     <type>(<scope>): <step name>

     Step <n>/<T> of the plan for #<N>.

     Factory-Step: <n>
     Factory-Run: <run id>
     Refs #<N>
     ```

     `<type>` from the issue's `type:` label (`feature → feat`, `bug → fix`,
     `tech-debt → refactor`, `test → test`, `docs → docs`); `<scope>` from the
     step's `Impl:` path the way `/ship` infers it (the module or component,
     omitted when it adds nothing). A pre-commit hook that fails stops here:
     `parked reason=hook-failed` with its output, never `--no-verify`;
  3. `git push` (rejected → `parked reason=push-rejected`);
  4. `factory-outcome.sh progress <N> --stage implement --run <id> --step
     <n>/<T>` (the sha defaults to HEAD).
- **decisions**: the SPEC's Decisions Log as the loop says, and the issue
  comment posted with `factory-outcome.sh decision` (the marker is its last
  line) instead of a bare `gh issue comment`. An accepted deviation that binds
  other work is such a decision.
- **cross-repo**: a `halt: cross-repo-question` becomes a **question**, with
  the `cross-repo-advisor` brief quoted under the options.

**Halt mapping**, replacing every halt the loop returns:

| Step-loop halt | Factory outcome |
|---|---|
| `step-mis-sized` (the loop already sent one `SendMessage` continue) | `parked reason=step-mis-sized` |
| `cycle-cap` (the loop already re-dispatched once) | `parked reason=cycle-cap` |
| `green-unreachable`, `scope-mismatch`, `blocker`, `tree-broken`, `unattributable`, `defective-verify`, `verification-failed`, `precondition-failed` | `parked reason=<the halt's slug>`, the diagnosis verbatim (AC-16) |
| `gate-blocked` (a step the plan did not settle) | **question**, one item per step, the same three options as `/factory:plan` |
| `cross-repo-question`, or a halt whose fix needs a choice between contract shapes | **question**, with the advisor's brief when the question is cross-repo |
| `plan-order` | `parked reason=plan-order` (a plan defect) |
| `step-gap`, `branch-diverged` | `parked` with that reason (Start handles the first; the loop's section 1 the second) |
| `plan-contract`, `vague-target` | `parked reason=plan-contract` (the plan predates the step contract or was hand-edited) |
| `step-refused` | `parked reason=step-refused`, the script's message verbatim |

Every park records the halt first (`features.py step <slug> halt <n> --reason
"<one line>"`), leaves the step's uncommitted work in the tree, and writes
`git status --short` and the resume command into `How to recover:`. Work
that reached a commit is already on `origin`.

A question that settles a gate-blocked step on the re-run is written into the
plan as the loop expects (`accepted by user: <answer>` in the row's Detail,
or the replaced `Verify:` line), the plan section is republished (Publish
`--kind plan`, so the issue stays the source of truth and the mid-run check
above passes), and the loop continues.

## End

When the last step is recorded, run `/feature-dev:tdd`'s Phases 4 and 5 once
(read `${CLAUDE_PLUGIN_ROOT}/../feature-dev/commands/tdd.md` for them):
coverage across the changed files with one more `tdd-runner` per meaningful
gap, then lint and format. Each lands in one more commit, staged per rule 4,
pushed, with a progress comment: `test: cover <gap>` with trailer
`Factory-Step: coverage` (one commit for all gaps; none when there is no gap
or no coverage tool), and `chore: lint and format` with `Factory-Step: lint`
(none when nothing changed). A coverage target the run cannot meet is
reported, not looped on (tdd's `/goal` offer has no reader here).

Then `features.py implemented <slug>`, and the `done` comment, with the last
push already made (the call takes no `--sha`: the script reads the clone's
HEAD, which is what that push sent; a typed hash is refused when it differs,
so never type one): tdd's Phase 6
report (`## TDD Results`: criteria, the Acceptance criteria line, tests
written, files, coverage, decisions, blockers `None`), the commit list
(`git log --oneline origin/<default>..HEAD`), the re-verified and reopened
steps, and the contract's §7 lines. The status stays `in-progress`.

## Cannot decide → question

A cross-repo question; a contract choice two steps disagree on; a gate-blocked
step the plan did not settle.

## Resume

Entirely from the branch (Start steps 4–5): a re-run after a kill re-verifies
the recorded steps and continues with the next one, adding no duplicate
commit (AC-14); a step whose file was reverted by hand is reopened and
re-done before the later steps (AC-15). A re-run whose latest marker is this
stage's `done` and whose branch carries the `lint` or `coverage` trailer (or
every step's) runs only the flip (a no-op for this stage) and ends `done`.
