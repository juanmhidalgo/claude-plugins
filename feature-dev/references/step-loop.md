# The step loop

Shared by `/feature-dev:tdd` and `/factory:implement` (canonical copy in
`shared/step-loop/`; edit it there and run `shared/sync.sh --write`). It takes
the Implementation Order of a reviewed plan and drives it one step at a time
through feature-dev's runners (`tdd-runner`, `plan-step-executor`), recording
progress in the feature store with `features.py step`. The caller owns what the
loop cannot decide: what a halt means, whether a gate-blocked step can be put
to a person, and what happens after each recorded step.

**You are the orchestrator. You do not write tests or production code — the
runners do.**

The caller sets, before section 1:

- **plan**: the `PLAN-*.md` path, the feature slug (`.feature-dev/features/<slug>/`),
  the repo root, and **scripts**: the directory holding feature-dev's
  `features.py` (every call below is `<scripts>/features.py … --root <repo root>`).
  A run with no feature in the store (a description-only run) records no state
  and is not resumable; the caller says so instead of calling `step`.
- **spec**: the `SPEC-*.md` path, or none. Its `## Decisions Log` entries (or
  the PLAN's, for a plan-only feature) are **prior decisions**: as binding as
  the plan, never re-opened on your own judgment, threaded into the initial
  carry-over, listed back in the caller's summary.
- **baseline**: the plan's `### Baseline` table, and whether HEAD is still the
  sha it was run on (after unexplained HEAD movement the rows are not
  attributable, and the caller said so in its summary).
- **gate policy**: `ask` (section 2 puts gate-blocked steps to the user before
  the first dispatch) or `settled` (nobody can answer: a gate-blocked step the
  plan does not settle is `halt: gate-blocked`).
- **resume**: `yes` when a prior run recorded steps in `plan.completed` that
  must be re-verified first (section 1), else `no`.
- **after each step**: what runs once `step done n` is recorded (a progress
  line, a commit and push, nothing). The loop itself commits nothing.
- **decisions**: where a binding decision is written (section 3, item 5) and
  whether it is also posted to a linked issue.
- **cross-repo**: what happens to a halt that is a question rather than a
  defect, beyond the advisor brief (route it to a coordinator session, turn it
  into a question for a human, or hand it back as any other halt).

## Halts

Every point where this loop cannot continue is a **halt**: `halt: <reason>`,
with the diagnosis verbatim beside it. A halt ends the loop at that step: no
further dispatch, no `step done` for the step, no commit, no description of
the run as complete with a caveat attached. Return it to the caller, which
records it (`features.py step <slug> halt <n> --reason "<one line>"`) and
decides what it means. The reasons:

| Reason | Where | Meaning |
|---|---|---|
| `step-gap` | section 1 | `plan.completed` skips a step number that exists in the plan |
| `branch-diverged` | section 1 | every completed step re-verifies red |
| `plan-contract` | section 2 | a step lacks `Accept:` or a runnable `Verify:`, or carries `Pins:` on a step not routed to `tdd-runner` |
| `vague-target` | section 2 | the source is too coarse to yield testable criteria |
| `gate-blocked` | sections 2, 3 | a step is gate-blocked and the plan does not settle it (policy `settled`, or an answer that was not recorded) |
| `plan-order` | section 3 | a step's `Depends on` is not satisfied |
| `precondition-failed` | section 3 | a precondition step failed its `Verify` |
| `step-mis-sized` | section 3 | a runner stopped at its turn limit twice on one step |
| `cycle-cap` | section 3 | a runner capped its cycles twice on one step |
| `green-unreachable` | section 3 | the runner reported `GREEN unreachable` |
| `verification-failed` | section 3 | `Verify` failed and the failures are attributable to the change |
| `scope-mismatch` | section 3 | the runner reported `scope mismatch` |
| `blocker` | section 3 | the runner reported a blocker |
| `tree-broken` | section 3 | the runner led with `Tree state: BROKEN` |
| `unattributable` | section 3 | `Verify` ran and the result cannot be attributed to the change or to the baseline |
| `defective-verify` | section 3 | the plan's `Verify` is defective; a substitute is proposed, not run |
| `cross-repo-question` | section 3 | the halt is a question about a contract or ownership, not a defect |
| `step-refused` | section 3 | `features.py step done` refused the step |

## 1. Resume (only with `resume: yes`)

The feature's `plan.completed` in `list --json` records what a prior run
finished. Do not trust it blindly — the tree may have been edited since.

1. **Re-verify each completed step.** Run its `Verify:` command from the plan.
   This is exactly why the step contract requires a real command.
   - **Green** → genuinely done, skip it.
   - **Red** (failures beyond the Baseline's `pre-existing-fail` rows) → the
     step regressed or was reverted by hand. Note it; the restart is recorded
     in item 5.
2. **Report the resume point** before dispatching anything:

   ```
   Resuming <plan path> — halted at step <N> (<plan.halt_reason>)
     Steps 1-<N-1>: re-verified green, skipping
     Step <M>: re-verify FAILED, will re-run
     Resuming at step <N>
   ```
3. **Reject a gapped record.** If `plan.completed` skips a number that exists
   in the plan, the prior run advanced past an unfinished step and the record
   is unreliable → `halt: step-gap`, naming the gap. Resume from the gap, not
   from the highest recorded number. (`features.py` refuses to write a gap, so
   this only happens if `feature.json` was hand-edited or rebuilt.)
4. If **every** completed step re-verifies red, the tree is not what the plan
   thinks it is → `halt: branch-diverged`. Do not attempt a partial repair.
5. **Reopen the lowest regressed step.** When any step re-verified red, take
   the lowest one, `m`, and run `<scripts>/features.py step <slug> reopen <m>
   --root <repo root>`. It removes `m` and every later step from
   `plan.completed` and clears any halt, so the feature is `running` again.
   Re-dispatch `m` in section 3; for the later steps that re-verified green,
   record each with `step done` in order, without re-dispatching them.
6. **Record the restart.** When the feature's `status` is `halted`, run
   `<scripts>/features.py step <slug> resume --root <repo root>` once the
   re-verification is done and before dispatching anything; it clears the halt
   (skip it if `reopen` already ran: it clears the halt itself). A `running`
   feature (a run that died without halting) needs no `resume`.

Then continue into section 2 with the remaining steps only.

## 2. Resolve the criteria

Every criterion needs six fields before anything is dispatched. Where they
come from depends on whether a plan is in use.

### With a `PLAN-*.md` (the normal path)

The plan's **Implementation Order** already carries them, one block per step:

```
1. **[Step name]**
   - Kind: ...        → routing (optional; default behavior)
   - Accept: ...      → behavior
   - Pins: ...        → existing behaviors to lock in (optional; passed to the runner)
   - Covers: ...      → spec AC ids (passed to the runner; the caller's report tallies AC coverage)
   - Impl: ...        → impl target path
   - Test: ...        → test target path (or `n/a — <reason>`)
   - Verify: ...      → verification command
   - Depends on: ...  → dispatch order
```

**Take these verbatim. Do not re-derive, re-word, or "improve" them** — the
plan was reviewed; re-deriving silently drops that review. The spec reference
is the plan path + step number (or the feature's spec, if it has one). Cycle
cap is 5 unless the step is a tight bug fix.

**If a step is missing `Accept:` or `Verify:`, or `Verify:` is a description
rather than a runnable command** → `halt: plan-contract`. The plan predates the
step contract or was hand-edited; `/feature-dev:plan-review` and a re-generation
with `/feature-dev:explore-plan` are the fix. Do not fill the gap by inference —
that is the improvisation the runner contracts exist to prevent.

### Without a plan (the spec came as text or as a `SPEC-*.md` with no plan)

Derive the criteria yourself, producing the same six fields per criterion. The
spec is the feature's SPEC file when one was given, else the text. If the spec
has a Tasks section (only specs written before feature-dev 3.0.0 do), start
from its tasks — they already carry Accept, Verify, Files and Covers. Otherwise start from its
acceptance criteria by id (`**AC-1**`…), carrying the ids in each criterion's
`Covers:`, with the caller's exploration filling in paths and commands — the
ACs are then the only reviewed anchor. A criterion is correctly sized when it
is:

- **Specific and testable** — not "add the booking flow", but "when contact has no active subjects, `start_booking` returns `NO_SUBJECTS` error code"
- **Independently verifiable** — one command proves it
- **Bounded to one impl target** — if it needs edits in two unrelated modules, split it

`Verify` must be a real command built from the runner and path conventions the
caller's exploration reported — never a placeholder.

### Before dispatching

Present the criteria compactly — one line each: number, Accept (shortened if
long), route (section 3), and a flag on any gate-blocked step (below). If the
plan has milestone headings, show them as separators. If the source is too
coarse to yield testable criteria → `halt: vague-target` — TDD on a vague
target produces tests that lie.

**Resolve gate-blocked steps now, not mid-run.** A step is gate-blocked when
its `Verify` row in the Baseline is `hollow` or `not-run: missing` and its
Detail does not already carry `accepted by user`. (`not-run: slow` and
`not-run: writes` do not gate: the step dispatches normally, and a failure it
produces is attributed by the unattributable-is-a-failure rule in section 3.)

- **Policy `ask`**: before the first dispatch, ask about every remaining
  gate-blocked step at once — AskUserQuestion, one question per step, at most
  4 per call — quoting its row, with three options:
  - **Fix the environment now** — the user fixes it; re-run the command, update the row's Result and Detail with Edit, and treat the step as ungated if the new result is not gate-blocking.
  - **Replace the Verify** — the user types the command. Rewrite that step's `Verify:` line in the plan with Edit, run the new command once, and replace the row with its result.
  - **Accept as unverifiable by its gate** — append `accepted by user: <reason>` to the row's Detail with Edit. The step dispatches; you verify it by the runner's own tests only, and the caller's report says so for that step.

  Writing the answer into the plan is what makes it stick: a resumed run reads
  `accepted by user` or the new `Verify:` and does not ask again.
- **Policy `settled`**: before the first dispatch, `halt: gate-blocked` naming
  every gate-blocked step and quoting its row. The caller turns that into its
  own question, with the same three options; the answer lands in the plan the
  same way (`accepted by user: <answer>` in the row's Detail, or the replaced
  `Verify:` line), so the next run finds the step settled.

## 3. Execute (delegated, sequential)

Work through the criteria **one at a time, in `Depends on` order**.

### The gates — check these before every dispatch

**Baseline gate.** If the step is still gate-blocked (section 2) — the answer
was not recorded, or a refreshed row turned gate-blocking — `halt: gate-blocked`
before dispatching, quoting the row. A runner cannot verify against a gate that
checks nothing or cannot run; dispatching anyway spends its whole budget to
reach the same halt. This applies to inline precondition steps too.

**Dependency gate. Every step number in a step's `Depends on` must already be
in `plan.completed`.** If any is missing → `halt: plan-order`. Do not dispatch.
Report which dependency is outstanding and why you cannot proceed.

This is not advisory. Two rationalizations look reasonable in the moment and
are both wrong:

- *"The dependency is still running, but this step touches a different repo / different files, so there is no overlap."* `Depends on` encodes a **decision gate**, not a file-locking concern. A step that depends on a verification step is waiting for an *answer* — if that answer turns out to be "red", the work you dispatched in the meantime was built on a contract that does not hold, and you now have to unpick it.
- *"The dependency will almost certainly pass."* Then waiting costs you nothing. If it fails, dispatching early cost you the whole downstream branch.

Never dispatch two agents concurrently. Beyond the dependency gate, concurrent
agents collide on overlapping files and on the working tree itself.

### Routing

Route on **who writes the test**, not on whether `Test:` names a path. A step
that only makes an already-written test pass has no RED to drive — its RED was
written by an earlier step.

| Step shape | Agent | Why |
|---|---|---|
| `Test:` names a path this step creates | `feature-dev:tdd-runner` | New behavior with a test to write — drive it red-green-refactor |
| `Kind: characterization`, `Test:` names a path this step creates | `feature-dev:tdd-runner` with `Mode: characterization` | Structure changes, behavior does not: the tests are expected green on first run, so a RED-first runner would report `RED passed early` and prove nothing. Characterization mode proves each test can fail instead |
| A `tdd-runner` row above with `Pins:` | Same agent, plus `Pins:` verbatim | Pins are written in the same run, against the same test file — never as a separate dispatch. Only `tdd-runner` takes pins; `Pins:` on a step routed to `plan-step-executor` or inline is a plan defect → `halt: plan-contract`, naming the step |
| `Test:` names a path marked `(written by step N)` | `feature-dev:plan-step-executor` | RED already exists and is failing. A `tdd-runner` would try to write a test that is already there and stall on its own "did RED fail for the right reason" check |
| `Test: n/a — <reason>`, `Impl:` names a path | `feature-dev:plan-step-executor` | Migration, config wiring, dependency bump — nothing to assert test-first, but `Verify` still gates it |
| `Test: n/a` **and** `Impl: n/a` | **You, inline** | A precondition on the environment or the working tree (rebase, `makemigrations --check`, a dependency install). `plan-step-executor` is forbidden from committing and owns no git state, so dispatching one is wrong. Run the `Verify` command yourself and record the step like any other |

Non-behavioral steps are not exempt from verification. If a step of any shape
has no `Verify` command, it fails section 2 and the loop halts there.

A precondition step that fails its `Verify` is `halt: precondition-failed`, not
a step to work around — the plan assumed a baseline that does not hold.

A precondition step that moves HEAD (a rebase) makes the Baseline stale by
design. Once it passes, re-run the Baseline commands of the remaining steps
once, update their rows and the `Run on` sha in the plan with Edit, and
continue — a refreshed row that is now gate-blocking stops at the Baseline gate
like any other.

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
| `Pins: <n> written, <m> proven falsifiable` with m < n | Advance, but list the unproven pins in the caller's report — a pin never shown to fail locks in nothing |
| `RED passed early` | Behavior already exists. The runner still wrote and proved the step's pins; read its `Pins:` line as above. Note it, advance — do **not** re-dispatch |
| Agent stopped at its turn limit (the harness reports "stopped at its N-turn limit (partial result; SendMessage to … to continue)") | Resume it **once**, before anything else: `SendMessage` "continue step N and report". It still holds the context of what it already did; rebuilding that from the diff costs the budget the step was delegated to protect. A second stop on the same step means the step is mis-sized → `halt: step-mis-sized` |
| `cycle cap` | Re-dispatch **once** with the remaining slice and accumulated carry-over. If it caps again → `halt: cycle-cap` |
| `GREEN unreachable` | `halt: green-unreachable`. Report the diagnosis verbatim |
| Verification failed | Attribute against the Baseline (below). Every failure in a `pre-existing-fail` row → the step passes; note them for the report. Anything else → `halt: verification-failed`, report verbatim |
| `scope mismatch` | `halt: scope-mismatch`. The step's impl target was wrong — the plan needs revision |
| `blocker` (includes a mis-sized step, a pin that failed on first run, a characterization gap, a characterization test no mutation could break, a missing test seam) | `halt: blocker`. Report the blocker verbatim |
| `Tree state: BROKEN` block | `halt: tree-broken`, carrying the block verbatim. The agent stopped mid-change on purpose; never dispatch the next step over a broken tree — that agent would read the breakage as pre-existing |
| Deviation but verification passed | Accept, note it in the final report, continue |
| Verification ran but you **cannot attribute** the result | `halt: unattributable`. See below — this is a blocker, not a pass |

**With a Baseline, attribution is a lookup, not a judgment.** A failure whose test id is listed in the `pre-existing-fail` row for that command is attributable to the baseline. For a count-only row (a lint gate), a finding is attributable when its file's count has not grown versus the row's per-file count; a file absent from the row has a baseline of 0. Anything not in the row is attributed to the change. A step whose row was `accepted by user` has no row to attribute against: its runner's own tests are the verification. The Baseline gives the rule below its data; it does not relax it.

**An unattributable verification is a failure, not a pass.** If a step's `Verify` produced failures you cannot confidently assign to this change rather than to a pre-existing baseline — because the plan has no Baseline and the tree is red, because HEAD moved since the Baseline without a precondition step of this plan moving it, because the row is `not-run` and so recorded nothing, because the output was truncated, because you stopped waiting, because a parallel runner distributes names only in a final summary you never saw — then the step is **not verified**. Halt and say so plainly, naming the unresolved failures or the fact that you could not name them.

Do **not**: advance to the next step, run `step done` for the step, commit, or describe the run as complete with a caveat attached. "N tests pass and 2 failures are probably pre-existing" is an unverified step wearing a verified step's clothes. Hand the ambiguity to the caller — a person can tell you the baseline in one sentence, which is cheaper than you guessing.

**When a halt is a cross-repo question rather than a defect** — "which side owns this field?", "does this break the declared contract?", "should the consumer branch on the code or on the status?" — you may spawn `feature-dev:cross-repo-advisor` **once** to produce a decision brief before handing the halt to the caller as `halt: cross-repo-question`. It is read-only and writes nothing.

Its brief is an input to the decision, not a substitute for it. Do not act on its recommendation yourself, do not resume the run on the strength of it, and do not record it in the Decisions Log until a person has accepted it. If the halt is a plain defect — a red test, a wrong path, a failed migration — skip the advisor; it has nothing to add to a bug. What happens to the question next is the caller's **cross-repo** input.

4. **Record progress.** After each step that passes, run `<scripts>/features.py step <slug> done <n> --root <repo root>`. The script moves the feature to `running` and refuses any `n` that is not the next step after those completed, so the record never has a gap — if it refuses, you are about to advance past an unfinished step: `halt: step-refused`, and fix that instead of editing `feature.json`. Then run the caller's **after each step** action. On a halt, run `<scripts>/features.py step <slug> halt <n> --reason "<one line>" --root <repo root>`, with `n` the step that halted. This is what makes the run resumable — a halted run that recorded nothing is a lost run. A halt is recordable from `planned` (step 1 halting) or `running`. If the script refuses it anyway, report the refusal in the caller's halt message instead of editing `feature.json`.

   Wait for each agent's completion notification rather than polling with `sleep`. **Notifications for finished work get no turn.** Once a subagent's report has been parsed and its step recorded, a later idle or completion notification for that same agent needs nothing from you. Do not write an acknowledgement ("Noted", "Step 3 already recorded") and do not re-summarize; go on with the next action, or end the turn silently if there is none. A notification that carries a report you have not processed yet is not one of these: parse it.

   A run with no feature in the store (a description-only run) records no state. It is not resumable: on a halt, the caller's halt message says so instead.

5. **Record decisions that bind other work.** Most steps produce none — that is the normal case, and an empty log is a correct log. A decision qualifies only when **both** hold:

   - it is **not already written** in the plan or the spec (if it is, it is not new), and
   - it **constrains code outside this step** — another step, another repo, or a future change.

   The second clause is the filter. "Renamed a local variable" fails it. "The empty-subjects case returns `NO_SUBJECTS` with 409, and the backend owns it" passes. Three sources produce nearly all of them:

   - a **deviation a runner reported that you accepted** — step 3 already tells you to note it; this is where the note goes,
   - a **carry-over delta that touches the contract**: a new error code, a schema change, a renamed field another repo reads,
   - an **answer that unblocked a halt** — otherwise it is lost the moment the run resumes, which is exactly the answer you will need again in the consuming repo.

   Append each to the `## Decisions Log` of the feature's SPEC (the spec in the same folder as the plan, or the `SPEC-*.md` passed as the argument), creating the section at the end of the spec if it is absent. Newest last:

   ```
   - **[repo: <repo name> · step <N>]** <the decision, one sentence>
     **Because:** <why it went this way and not the other>
     **Binds:** <who must obey — a repo name, a later step, or `this repo only`>
   ```

   `Binds` is the field that earns the log its keep: it is what a run in the *other* repo reads to know the decision applies to it.

   **If the feature's entry in `list --json` has a non-null `issue`**, also post the decision as an issue comment (issue-store.md's Decision comment format, in feature-dev's `skills/spec-driven-development/references/issue-store.md`): write it to a scratch file (the reference's Scratch files rule) under a `## Decision — <slug>` heading, then `gh issue comment <N> --repo <owner>/<repo> --body-file <file>`. A failed post, or a failed `gh` preflight, does not halt the run — add the decision text to a running "unposted decisions" list for the caller's report and move on. This comment is the only write this loop makes to the issue. It never edits the issue body and never closes the issue — marking the feature `implemented` is a local store change only. The caller's **decisions** input may add to the comment (a trailing marker line) or redirect it.

   **If the feature has no SPEC** (a plan-only feature, or a run from a text description), keep the entries in a `## Decisions Log` section at the end of the PLAN body when there is a plan, and reproduce them verbatim in the caller's report either way. A run from a spec always has a spec, so its decisions never go to the PLAN.

Thread only the **carry-over deltas** forward (new symbols, new fixtures, new test markers, schema changes) — not the full prior reports. The next agent needs the deltas, not a retrospective.

Do not re-dispatch a failed step with a "better" prompt. That masks a defect in the step or the plan; halt and let a person re-scope.

**Do not substitute a step's `Verify` command on your own.** If a plan's `Verify` turns out to be defective — it fails on pre-existing errors the Baseline does not list, it would rewrite unrelated files, it names a gate that is unusable in this repo — that is a real finding and you should surface it. But a narrower command you chose yourself is a **different gate than the one the plan was reviewed against**. `halt: defective-verify`: state the defect, propose the substitute, and let a person accept it. Running your own substitute and recording the step as passed converts a plan defect into a silent scope reduction.

**RED-GREEN-REFACTOR all happen inside each `tdd-runner`** — including the per-cycle refactor pass and the validation that RED failed for the right reason. There is no separate refactor phase in this loop.

When the last step is recorded, hand back to the caller: the per-step outcomes (met / pinned / already satisfied / halted, cycles used), the tests written and unproven pins, the files changed, the decisions recorded and any unposted ones, the deviations accepted, the steps verified by runner tests only, and the carry-over.
