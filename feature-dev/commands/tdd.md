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
  - Bash(gh auth status)
  - Bash(gh repo view --json nameWithOwner*)
  - Bash(gh issue view *)
  - Bash(gh issue comment *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/issue_spec.py *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py snapshot *)
  - Read
  - Write
  - Edit
  - Agent
  - Glob
  - Grep
  - ListAgents
  - SendMessage
skills:
  - tdd-patterns
argument-hint: "[PLAN-*.md or SPEC-*.md path, or feature description — optional; auto-discovers PLAN-*.md] [--coordinator <session-name>]"
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
---

## Context
- **Repository**: !`git remote get-url origin`
- **Current branch**: !`git branch --show-current`
- **Working tree clean**: !`git status --short`
- **Feature spec**: $ARGUMENTS

## Phase 0: Resolve Spec and Validate

**First, strip flags from `$ARGUMENTS`.** `--coordinator <session-name>` names a live Claude Code session acting as this feature's coordinator (Phase 3 routes cross-repo questions to it). Remove the flag and its value before anything else reads `$ARGUMENTS` — what remains is the feature spec, and it may now be empty, which is the normal auto-discovery path. Record the name. Do not resolve or validate it yet; a coordinator that turns out to be unreachable must not block a run that is otherwise fine.

1. **Resolve the feature spec:**
   - **If `$ARGUMENTS` is the path of an existing `PLAN-*.md`** → read it and use it exactly as a single auto-discovered plan below (the closing lines of `/feature-dev:explore-plan` and `/feature-dev:plan-review` print this form).
   - **If `$ARGUMENTS` is the path of an existing `SPEC-*.md`** → read its frontmatter, use `feature:` as the spec, and record the path as `source_spec`. There is no plan: skip the plan search in Phase 1 and take the no-plan path. This is the small-feature fallback `/feature-dev:spec` mentions; the spec's ACs (or its Tasks) are the reviewed anchor, the decisions go to its Decisions Log, and Phase 6 closes it. If its `status:` is `implemented`, say so and ask before continuing.
   - **If `$ARGUMENTS` is `#N`, `owner/repo#N`, or an issue URL** → resolve it per [issue-store.md's Argument parsing](../skills/spec-driven-development/references/issue-store.md#argument-parsing), then run [issue-store.md's Import algorithm](../skills/spec-driven-development/references/issue-store.md#import-ac-8-ac-9-ac-10-ac-11-ac-12) against it, start to finish. Do not restate Import's steps here — follow the reference; its own step 3 is where a closed issue asks before continuing, the same shape as this command's `status: implemented` check above. A failed `gh` preflight, or a failed `gh issue view` call, stops here and names the issue that could not be read. On success, continue as if `$ARGUMENTS` had been the resulting `SPEC-<slug>.md` path (the `SPEC-*.md` bullet above applies).
   - **If `$ARGUMENTS` is anything else** → use it as the feature spec. Continue to step 2.
   - **If `$ARGUMENTS` is empty** → auto-discover plan files. Use Glob with pattern `PLAN-*.md` in the repo root:
     - **0 plans found** → **STOP** and ask the user for a feature description.
     - **1 plan found** → read it, extract the `feature:` value from its frontmatter, and use that as the spec. Record the plan path as the **pre-selected plan** for Phase 1. Inform the user: "Auto-selected plan: `PLAN-<slug>.md` (feature: <name>)".
     - **2+ plans found** → read each plan's frontmatter to extract the `feature:` value. Use AskUserQuestion to let the user pick one (label = feature name, description = filename). The chosen plan's `feature:` becomes the spec and its path is the **pre-selected plan** for Phase 1.
2. **Check the working tree.** Use the `Working tree clean` field from the Context section above — it was captured before Phase 0 ran, so an issue import in step 1 (which writes a new, untracked `SPEC-<slug>.md` when no local copy exists) never trips this check on its own output.
   - **Clean** → proceed normally.
   - **Dirty** → this may be a halted run, not stray edits. Read the frontmatter of the plan resolved in step 1 (a spec-only run has no plan, so it cannot be a resumable run: apply the stop below). If it has `run_status: in-progress` or `run_status: halted` with a non-empty `completed_steps:`, the dirty tree is *this command's own* unfinished work → go to **Phase 1b: Resume** after Phase 1.
   - **Dirty with no in-progress plan** → **STOP** and ask the user to commit or stash.

   A plan with no `run_status:` field predates v1.19.0. Treat it as `not-started` and apply the plain dirty-tree stop.

## Phase 1: Load Plan or Explore Codebase

**First, determine the plan:**

- **If a pre-selected plan was set in Phase 0** → use it directly; skip the search below.
- **If `source_spec` was set from a `SPEC-*.md` argument** → no plan; go to "If no plan file exists" below. Also load that spec's `## Decisions Log`, if it has one, as binding prior decisions (see "Load prior decisions").
- **Otherwise** (spec came from `$ARGUMENTS` as text), look for `PLAN-*.md` files in the repo root (created by `/feature-dev:explore-plan`). If multiple exist, pick the one whose `feature:` frontmatter best matches the spec; if none clearly matches, ask the user which to use.

**If a plan file is in use:**
- Read it and use it as the source of truth for files to modify/create, implementation order, and key decisions
- **Drift check**: if the plan's frontmatter has `source_spec:` pointing to a `SPEC-*.md` file, compare modification times (`stat -c %Y <spec>` and `stat -c %Y <plan>`, or `git log -1 --format=%ct -- <file>` as a fallback). If the spec is newer than the plan, **warn the user**: "The source spec `<path>` was modified after the plan was generated. The plan may be stale. Proceed with the current plan, or re-run `/feature-dev:explore-plan` first?" and wait for confirmation.
- **Load prior decisions**: if `source_spec:` resolves, read the spec's `## Decisions Log` section (if it has one). Those are decisions taken during earlier runs — in this repo or in a sibling one — and they bind this run. Thread them into the initial carry-over for Phase 3 and list them back in the Phase 1 summary. A recorded decision is as binding as the plan: do not re-open one on your own judgment, and do not let a runner contradict it. If `source_spec:` points outside this repo (`../<sibling>/SPEC-<slug>.md`), that is the expected multi-repo shape, not an error — read it there.
- **Load the Baseline**: if the plan has a `### Baseline` section, keep its table — Phase 3 attributes failures against it and gates dispatch on it. If HEAD is no longer the sha it was run on and no precondition step of this plan moved it, say so in the Phase 1 summary: after unexplained HEAD movement the rows are not attributable. (A precondition step that moves HEAD refreshes the rows itself — see Routing.) A plan without the section (pre-1.26.0) keeps the behaviour below unchanged.
- **Coordinator hint**: if the resolved spec has a `repos:` block and no `--coordinator` was passed, add exactly one line to the Phase 1 summary — "Multi-repo spec. If you have a coordinator session open, pass `--coordinator <name>` to route cross-repo questions to it." A line, not a question: do not block on it.

  **Do not call `ListAgents` to find a candidate.** The listing gives name, kind and status — not a working directory — so matching reduces to the session's name, and a coordinator session for a multi-repo feature has no single repo to derive a name from. Name-matching reliably finds the *implementer* sessions (named after their repos) and misses the coordinator (named by hand, precisely because it belongs to no one repo). The user names it or it does not get used.
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
   - **Red** (failures beyond the Baseline's `pre-existing-fail` rows) → the step regressed or was reverted by hand. Drop it from the completed set and re-dispatch it in Phase 3.
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
   - Kind: ...        → routing (optional; default behavior)
   - Accept: ...      → behavior
   - Pins: ...        → existing behaviors to lock in (optional; passed to the runner)
   - Covers: ...      → spec AC ids (passed to the runner; Phase 6 reports AC coverage)
   - Impl: ...        → impl target path
   - Test: ...        → test target path (or `n/a — <reason>`)
   - Verify: ...      → verification command
   - Depends on: ...  → dispatch order
```

**Take these verbatim. Do not re-derive, re-word, or "improve" them** — the plan was reviewed; re-deriving silently drops that review. The spec reference is the plan path + step number (or its `source_spec:` if set). Cycle cap is 5 unless the step is a tight bug fix.

**If a step is missing `Accept:` or `Verify:`, or `Verify:` is a description rather than a runnable command** → **STOP**. The plan predates the step contract or was hand-edited. Tell the user to run `/feature-dev:plan-review` and re-generate with `/feature-dev:explore-plan`. Do not fill the gap by inference — that is the improvisation the runner contracts exist to prevent.

### If no plan exists (spec came from `$ARGUMENTS`)

Derive the criteria yourself, producing the same six fields per criterion. The spec is the `source_spec` file when one was given, else the text. If the spec has a Tasks section (written with `--with-tasks`), start from its tasks — they already carry Accept, Verify, Files and Covers. Otherwise start from its acceptance criteria by id (`**AC-1**`…), carrying the ids in each criterion's `Covers:`, with the Phase 1 exploration filling in paths and commands — the ACs are then the only reviewed anchor. A criterion is correctly sized when it is:

- **Specific and testable** — not "add the booking flow", but "when contact has no active subjects, `start_booking` returns `NO_SUBJECTS` error code"
- **Independently verifiable** — one command proves it
- **Bounded to one impl target** — if it needs edits in two unrelated modules, split it

`Verify` must be a real command built from the runner and path conventions Phase 1 reported — never a placeholder.

### Before dispatching

Present the criteria compactly — one line each: number, Accept (shortened if long), route (see Phase 3), and a flag on any gate-blocked step (below). If the plan has milestone headings, show them as separators. If the source is too coarse to yield testable criteria, **STOP** and say so — TDD on a vague target produces tests that lie.

**Resolve gate-blocked steps now, not mid-run.** A step is gate-blocked when its `Verify` row in the Baseline is `hollow` or `not-run: missing` and its Detail does not already carry `accepted by user`. (`not-run: slow` and `not-run: writes` do not gate: the step dispatches normally, and a failure it produces is attributed by the unattributable-is-a-failure rule in Phase 3.) Before the first dispatch, ask about every remaining gate-blocked step at once — AskUserQuestion, one question per step, at most 4 per call — quoting its row, with three options:

- **Fix the environment now** — the user fixes it; re-run the command, update the row's Result and Detail with Edit, and treat the step as ungated if the new result is not gate-blocking.
- **Replace the Verify** — the user types the command. Rewrite that step's `Verify:` line in the plan with Edit, run the new command once, and replace the row with its result.
- **Accept as unverifiable by its gate** — append `accepted by user: <reason>` to the row's Detail with Edit. The step dispatches; you verify it by the runner's own tests only, and the Phase 6 report says so for that step.

Writing the answer into the plan is what makes it stick: a resumed run reads `accepted by user` or the new `Verify:` and does not ask again.

## Phase 3: Execute (delegated, sequential)

Work through the criteria **one at a time, in `Depends on` order**.

### The gates — check these before every dispatch

**Baseline gate.** If the step is still gate-blocked (Phase 2) — the user's answer was not recorded, or a refreshed row turned gate-blocking — **STOP** before dispatching and quote the row. A runner cannot verify against a gate that checks nothing or cannot run; dispatching anyway spends its whole budget to reach the same halt. This applies to inline precondition steps too.

**Dependency gate. Every step number in a step's `Depends on` must already be in `completed_steps`.** If any is missing, **STOP**. Do not dispatch. Report which dependency is outstanding and why you cannot proceed.

This is not advisory. Two rationalizations look reasonable in the moment and are both wrong:

- *"The dependency is still running, but this step touches a different repo / different files, so there is no overlap."* `Depends on` encodes a **decision gate**, not a file-locking concern. A step that depends on a verification step is waiting for an *answer* — if that answer turns out to be "red", the work you dispatched in the meantime was built on a contract that does not hold, and you now have to unpick it.
- *"The dependency will almost certainly pass."* Then waiting costs you nothing. If it fails, dispatching early cost you the whole downstream branch.

Never dispatch two agents concurrently. Beyond the dependency gate, concurrent agents collide on overlapping files and on the working tree itself.

### Routing

Route on **who writes the test**, not on whether `Test:` names a path. A step that only makes an already-written test pass has no RED to drive — its RED was written by an earlier step.

| Step shape | Agent | Why |
|---|---|---|
| `Test:` names a path this step creates | `feature-dev:tdd-runner` | New behavior with a test to write — drive it red-green-refactor |
| `Kind: characterization`, `Test:` names a path this step creates | `feature-dev:tdd-runner` with `Mode: characterization` | Structure changes, behavior does not: the tests are expected green on first run, so a RED-first runner would report `RED passed early` and prove nothing. Characterization mode proves each test can fail instead |
| A `tdd-runner` row above with `Pins:` | Same agent, plus `Pins:` verbatim | Pins are written in the same run, against the same test file — never as a separate dispatch. Only `tdd-runner` takes pins; `Pins:` on a step routed to `plan-step-executor` or inline is a plan defect → **STOP** and name the step |
| `Test:` names a path marked `(written by step N)` | `feature-dev:plan-step-executor` | RED already exists and is failing. A `tdd-runner` would try to write a test that is already there and stall on its own "did RED fail for the right reason" check |
| `Test: n/a — <reason>`, `Impl:` names a path | `feature-dev:plan-step-executor` | Migration, config wiring, dependency bump — nothing to assert test-first, but `Verify` still gates it |
| `Test: n/a` **and** `Impl: n/a` | **You, inline** | A precondition on the environment or the working tree (rebase, `makemigrations --check`, a dependency install). `plan-step-executor` is forbidden from committing and owns no git state, so dispatching one is wrong. Run the `Verify` command yourself and record the step like any other |

Non-behavioral steps are not exempt from verification. If a step of any shape has no `Verify` command, it fails Phase 2 and the run stops there.

A precondition step that fails its `Verify` is a **hard stop**, not a step to work around — the plan assumed a baseline that does not hold.

A precondition step that moves HEAD (a rebase) makes the Baseline stale by design. Once it passes, re-run the Baseline commands of the remaining steps once, update their rows and the `Run on` sha in the plan with Edit, and continue — a refreshed row that is now gate-blocking stops at the Baseline gate like any other.

### Loop

For each criterion:

1. **Spawn** the Agent tool with the routed `subagent_type`, passing that agent's contract fields, the step's `Covers:` ids when it has them, and the **accumulated carry-over** from all prior steps in this run.
   If the step has Baseline rows, include them in the carry-over, so the agent does not spend its budget chasing a failure that was already there.
2. **Parse its report.** `tdd-runner`: Behavior / Cycles run / Tests added / Pins / Production changes / Verification / Halt reason / Carry-over / Blockers. `plan-step-executor`: Files changed / Verification / Deviations / Carry-over / Blockers. Either may lead with a `Tree state: BROKEN` block.
3. **Decide:**

| Outcome | Action |
|---|---|
| `criteria met` / verification passed, no blockers | Accumulate carry-over, advance |
| `pinned` (characterization mode) | Success: tests proven falsifiable, structural change made with them green. Accumulate carry-over, advance |
| `Pins: <n> written, <m> proven falsifiable` with m < n | Advance, but list the unproven pins in the Phase 6 report — a pin never shown to fail locks in nothing |
| `RED passed early` | Behavior already exists. The runner still wrote and proved the step's pins; read its `Pins:` line as above. Note it, advance — do **not** re-dispatch |
| Agent stopped at its turn limit (the harness reports "stopped at its N-turn limit (partial result; SendMessage to … to continue)") | Resume it **once**, before anything else: `SendMessage` "continue step N and report". It still holds the context of what it already did; rebuilding that from the diff costs the budget the step was delegated to protect. A second stop on the same step means the step is mis-sized → **STOP** and report |
| `cycle cap` | Re-dispatch **once** with the remaining slice and accumulated carry-over. If it caps again, **STOP** and report |
| `GREEN unreachable` | **STOP**. Report the diagnosis verbatim |
| Verification failed | Attribute against the Baseline (below). Every failure in a `pre-existing-fail` row → the step passes; note them for Phase 6. Anything else → **STOP**, report verbatim |
| `scope mismatch` | **STOP**. The step's impl target was wrong — the plan needs revision |
| `blocker` (includes a mis-sized step, a pin that failed on first run, a characterization gap, a characterization test no mutation could break) | **STOP**. Report the blocker verbatim |
| `Tree state: BROKEN` block | **STOP** and carry the block verbatim. The agent stopped mid-change on purpose; never dispatch the next step over a broken tree — that agent would read the breakage as pre-existing |
| Deviation but verification passed | Accept, note it in the final report, continue |
| Verification ran but you **cannot attribute** the result | **STOP**. See below — this is a blocker, not a pass |

**With a Baseline, attribution is a lookup, not a judgment.** A failure whose test id is listed in the `pre-existing-fail` row for that command is attributable to the baseline. For a count-only row (a lint gate), a finding is attributable when its file's count has not grown versus the row's per-file count; a file absent from the row has a baseline of 0. Anything not in the row is attributed to the change. A step whose row was `accepted by user` has no row to attribute against: its runner's own tests are the verification. The Baseline gives the rule below its data; it does not relax it.

**An unattributable verification is a failure, not a pass.** If a step's `Verify` produced failures you cannot confidently assign to this change rather than to a pre-existing baseline — because the plan has no Baseline and the tree is red, because HEAD moved since the Baseline without a precondition step of this plan moving it, because the row is `not-run` and so recorded nothing, because the output was truncated, because you stopped waiting, because a parallel runner distributes names only in a final summary you never saw — then the step is **not verified**. Halt and say so plainly, naming the unresolved failures or the fact that you could not name them.

Do **not**: advance to the next step, mark the step in `completed_steps`, commit, or describe the run as complete with a caveat attached. "N tests pass and 2 failures are probably pre-existing" is an unverified step wearing a verified step's clothes. Hand the ambiguity to the user — they can tell you the baseline in one sentence, which is cheaper than you guessing.

**When a STOP is a cross-repo question rather than a defect** — "which side owns this field?", "does this break the declared contract?", "should the consumer branch on the code or on the status?" — you may spawn `feature-dev:cross-repo-advisor` **once** to produce a decision brief before handing the halt to the user. It is read-only and writes nothing.

Its brief is an input to the user's decision, not a substitute for it. Do not act on its recommendation yourself, do not resume the run on the strength of it, and do not record it in the Decisions Log until the user has accepted it. If the halt is a plain defect — a red test, a wrong path, a failed migration — skip the advisor; it has nothing to add to a bug.

### Routing a cross-repo question to the coordinator session

**Only if `--coordinator <name>` was passed in Phase 0.** Without it, skip this section entirely — do not go looking for a session to talk to.

1. **Resolve the name once**, on the first halt that needs it. Call `ListAgents` and find the local session whose name matches. If `ListAgents` is unavailable (older Claude Code, or Bedrock/Vertex/Foundry), or no session matches, or several do — say so once, hand the halt to the user as normal, and do not retry on later steps. A coordinator you cannot reach is a downgrade to the normal flow, never a halt of its own.
2. **Send the question, not the run.** One plain-text `SendMessage`: the step number, the question in a sentence, and the `cross-repo-advisor` brief verbatim if one was produced. Set `notify_when_idle: true` so this session hears back when the coordinator finishes. The message must stand alone — a slash command inside it arrives as text and is not executed.
3. **Never send intermediate state.** Not per-step reports, not accumulated carry-over, not green verifications, not progress. The coordinator exists to answer a question; a step-by-step feed is the noise that makes it stop reading the messages that matter. One message per halt that needs one — nothing else, ever.

**Log first, announce second.** A *question* can go out immediately; there is nothing to store yet. A *decision* is written to the `## Decisions Log` **before** it is announced to anyone, and only after the user has accepted it. A decision that reached the coordinator session but not the log is exactly the split-brain the log exists to prevent: the session knows something the spec does not, and the session will not outlive the feature.

4. **Record progress.** After each step, tell the user one line — `Step N/M — <name>: <outcome>` — in the user's language only; do not repeat it in a second language or recap earlier steps. When the next step opens a new `#### Milestone` heading, add one line naming it; it is not a prompt. Wait for each agent's completion notification rather than polling with `sleep`.

   **Checkpoint line.** At each `#### Milestone` boundary, once the finished milestone's last step is recorded, print one line. In a plan without milestones, print it every ~8 completed steps:

   ```
   Progress recorded in PLAN-<slug>.md (steps 1–<N> done). To free context: /clear, then /feature-dev:tdd PLAN-<slug>.md; resume re-verifies the completed steps.
   ```

   Then continue with the next step in the same turn. Do not ask, and do not pause for an answer. The line exists because this orchestrator's context only grows: one run went from 98k to 389k tokens. Resume already re-verifies every recorded step (Phase 1b), so clearing between milestones costs one re-verification pass, not the run.

   **Notifications for finished work get no turn.** Once a subagent's report has been parsed and its step recorded, a later idle or completion notification for that same agent needs nothing from you. Do not write an acknowledgement ("Noted", "Step 3 already recorded") and do not re-summarize; go on with the next action, or end the turn silently if there is none. One run received 18 such notices and spent 13 turns only acknowledging them. A notification that carries a report you have not processed yet is not one of these: parse it.

   After each step that passes, use Edit on the `PLAN-*.md` frontmatter to append the step number to `completed_steps:` and set `run_status: in-progress`. **`completed_steps` must never contain a gap** — a recorded `[0,1,2,4]` claims step 3 was completed-and-skipped, which is not a state this command can produce. If you are about to write a gap, you have advanced past an unfinished step: stop and fix that instead. On a halt, set `run_status: halted` and add `halted_at: <step number>` plus a one-line `halt_reason:`. This is what makes the run resumable — a halted run that recorded nothing is a lost run.

   Do **not** commit between steps. The command's contract is one reviewable change set at the end; `/code-review:branch` and `/commit` come after, as Phase 6 tells the user.

   A spec-only run has no plan frontmatter to record progress in. It is not resumable: on a halt, the Phase 6 halt message says so instead.

5. **Record decisions that bind other work.** Most steps produce none — that is the normal case, and an empty log is a correct log. A decision qualifies only when **both** hold:

   - it is **not already written** in the plan or the spec (if it is, it is not new), and
   - it **constrains code outside this step** — another step, another repo, or a future change.

   The second clause is the filter. "Renamed a local variable" fails it. "The empty-subjects case returns `NO_SUBJECTS` with 409, and the backend owns it" passes. Three sources produce nearly all of them:

   - a **deviation a runner reported that you accepted** — step 3 already tells you to note it; this is where the note goes,
   - a **carry-over delta that touches the contract**: a new error code, a schema change, a renamed field another repo reads,
   - a **user answer that unblocked a halt** — otherwise it is lost the moment the run resumes, which is exactly the answer you will need again in the consuming repo.

   Append each to the `## Decisions Log` of the `source_spec` file (the plan's `source_spec:`, or the `SPEC-*.md` passed as the argument), creating the section at the end of the spec if it is absent. Newest last:

   ```
   - **[repo: <repo name> · step <N>]** <the decision, one sentence>
     **Because:** <why it went this way and not the other>
     **Binds:** <who must obey — a repo name, a later step, or `this repo only`>
   ```

   `Binds` is the field that earns the log its keep: it is what a run in the *other* repo reads to know the decision applies to it.

   **If the source spec has `issue:`**, also post the decision as an issue comment (issue-store.md's [Decision comment format](../skills/spec-driven-development/references/issue-store.md#decision-comment-format-ac-13)): write it to a scratch file (the reference's Scratch files rule) under a `## Decision — <slug>` heading, then `gh issue comment <N> --repo <owner>/<repo> --body-file <file>`. A failed post, or a failed `gh` preflight, does not halt the run — add the decision text to a running "unposted decisions" list for the Phase 6 report and move on. This comment is the only write this command makes to the issue: it never edits the issue body and never closes the issue — `status: implemented` (Phase 6) stays a local edit to the spec file only.

   **If there is no `source_spec`** (a plan with `source_spec: null`, or a run from a text description), keep the entries under a `decisions:` key in the `PLAN-*.md` frontmatter when there is a plan, and reproduce them verbatim in the Phase 6 report either way — the plan is deleted on success, so the report is the only place they survive. A spec-only run always has a `source_spec`, so its decisions never go to a `decisions:` key.

Thread only the **carry-over deltas** forward (new symbols, new fixtures, new test markers, schema changes) — not the full prior reports. The next agent needs the deltas, not a retrospective.

Do not re-dispatch a failed step with a "better" prompt. That masks a defect in the step or the plan; halt and let the user re-scope.

**Do not substitute a step's `Verify` command on your own.** If a plan's `Verify` turns out to be defective — it fails on pre-existing errors the Baseline does not list, it would rewrite unrelated files, it names a gate that is unusable in this repo — that is a real finding and you should surface it. But a narrower command you chose yourself is a **different gate than the one the plan was reviewed against**. Halt, state the defect, propose the substitute, and let the user accept it. Running your own substitute and recording the step as passed converts a plan defect into a silent scope reduction.

**RED-GREEN-REFACTOR all happen inside each `tdd-runner`** — including the per-cycle refactor pass and the validation that RED failed for the right reason. There is no separate refactor phase in this command.

## Phase 4: Coverage Check

Each runner gates coverage on the lines it added, within its Verify scope. This phase checks the aggregate and owns the project-wide threshold — a runner cannot see it from one test file.

1. Run the project's coverage tool across the **changed files** from all runners
2. Compare against project thresholds (from config) or 80% minimum. If the project enforces a global threshold, run the Baseline's coverage command too: a drop versus its row is this run's; with no usable row (`not-run: slow`), a global threshold below its configured minimum is unattributable and handled as in Phase 3
3. If below threshold: identify the uncovered paths and dispatch one more `tdd-runner` per meaningful gap, treating each as a new criterion. Do not write the tests inline
4. If no coverage tool is configured, skip with a note

## Phase 5: Lint and Format

Run the project's linter and formatter once, across everything the runners touched:

1. Detect tool: `ruff`/`black`/`eslint`/`prettier`/`rustfmt`/`gofmt`
2. Fix any issues — this is mechanical, handle it inline
3. Re-run the full test suite to confirm nothing broke — failures in the Baseline's `pre-existing-fail` rows are not breakage; anything else is. When the suite's row is `not-run: slow`, there is nothing to attribute against: a failure is unattributable, and the Phase 3 rule applies

## Phase 6: Report

Output a final summary:

```
## TDD Results

### Feature: [brief description]

### Criteria: [N] total — [N] met, [N] pinned, [N] already satisfied, [N] halted

### Acceptance criteria: [covered]/[total] covered by met steps — uncovered: [AC ids, or None] · halted: [AC ids on halted or never-run steps, or None]

| # | Criterion | Cycles | Outcome |
|---|-----------|--------|---------|
| 1 | [criterion] | 2/5 | met |

### Tests Written: [count] — pins: [n written, n proven falsifiable]
- [test file]: [count] tests ([brief categories])
- Unproven pins: [list, or None]

### Implementation Files Modified: [count]
- [file path] — [what was changed]

### Coverage: [percentage] on changed files (threshold: [threshold])

### Decisions Recorded: [count, or None]
- [decision] — binds: [who] ([recorded in SPEC-<slug>.md | report only — no source_spec])

### Unposted decisions: [count, or None]
- [decision text, verbatim]

### Coordinator: [session name — N questions routed | not used | named but unreachable]

### Test Run: ALL PASSING | PASSING except Baseline pre-existing failures: [ids]

### Verified by runner tests only (gate accepted by user): [step numbers, or None]

### Blockers: [verbatim, or None]

### Ready to commit: Yes/No
```

**The Acceptance criteria line** traces the run back to the spec. Take the AC ids from the `source_spec` (the plan's, or the spec passed as the argument). An AC is *covered* when at least one step whose `Covers:` cites it ended `met`, `pinned` or `RED passed early`. It is *halted* when every step citing it halted or never ran. It is *uncovered* when no step cites it. Omit the line when there is no source spec with numbered ACs. The line reports; it does not gate. An uncovered AC on an otherwise green run still gets named, because it is the criterion nobody built.

If every criterion was met and the suite is green (apart from failures listed in the Baseline's `pre-existing-fail` rows):
1. **Close the loop on the source spec (if any):** if the plan's frontmatter had a `source_spec:` pointing to a `SPEC-*.md` file, or the run was given a `SPEC-*.md` as its argument, use Edit to set that spec's `status:` field to `implemented`. This prevents auto-discovery from re-surfacing a completed feature on future runs.
2. **Delete the `PLAN-*.md` file** that was used, if any (it has served its purpose — the implementation is done).
3. Suggest a commit message following the project's convention.
4. End with the next commands:

   ```
   Next: /code-review:branch to review before merge, then /commit
   ```

If any criterion halted, do **none** of the above. Leave the plan and spec on disk with `run_status: halted`, and tell the user verbatim:

> Halted at step `<N>`. Fix the blocker, then run `/feature-dev:tdd PLAN-<slug>.md` — it will re-verify steps 1-`<N-1>` and resume from `<N>`. The dirty working tree is expected; do not stash it.

with the path of the plan this run used. A spec-only run has no plan to resume from; tell the user instead that the steps landed so far are uncommitted in the tree, and that the next step is `/feature-dev:explore-plan <spec path>` against that tree or finishing by hand — re-running `/feature-dev:tdd` on the spec would stop on the dirty tree.

The stash instruction matters: stashing is the one action that makes the recorded progress unrecoverable.
