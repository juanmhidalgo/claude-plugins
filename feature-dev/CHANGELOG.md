# Changelog

## 1.30.0 (2026-09-28)

A GitHub issue can now be the durable home of a spec, not just the local file.

### Added
- **GitHub-issue store for specs** ("issue in, issue out, local file in between"): the local SPEC stays the working copy, the issue is the durable home once published. **Why:** in repos where the issue is the record of what gets built, specs had to be hand-copied into issues and projects re-implemented the spec process in their own skills.
- **`/feature-dev:spec --publish <SPEC> new|#N|owner/repo#N|URL`**: publishes the spec between markers, never touching text outside them; a fingerprint conflict check runs before writing (overwrite / import the issue's version / cancel) and verification runs after; only then does it record `issue:`/`issue_fingerprint:`. The post-approval publish question is gated on `spec_store: issue` in `.claude/feature-dev.local.md` or an existing `issue:`.
- **Issue arguments (`#N`, `owner/repo#N`, URL)** for `/feature-dev:explore-plan`, `/feature-dev:tdd`, `/feature-dev:spec-review` and `/feature-dev:review`: import into `SPEC-<slug>.md` with a three-way compare and a snapshot before overwriting; a closed issue asks first. Issue text is treated as data, never as instructions. Import never silently overwrites an unrelated `SPEC-<slug>.md` with the same slug (it asks, defaulting to `SPEC-<slug>-<N>.md`), refreshes `issue_fingerprint` whenever local and issue agree, and when the issue wins replaces only the spec body, keeping the local Decisions Log. **Why:** specs are uncommitted, so any unasked overwrite is unrecoverable, and a stale fingerprint would make a synced spec look conflicted.
- **`/feature-dev:tdd` posts each recorded decision as a `## Decision — <slug>` issue comment.** A failed post does not halt the run; it is reported as unposted. `tdd` never edits the body or closes the issue.
- **`/feature-dev:cleanup`** skips the rescue question for a published-and-current spec, and always runs the rescue flow (offering `Republish to #<N>`, even with no decisions or QA) for an issue-linked spec that is not current. **Why:** unpublished edits must never be deleted silently.
- **`scripts/issue_spec.py`** (stdlib; `section`, `extract [--slug --fallback-title]`, `fingerprint`, `splice`) with `scripts/test_issue_spec.py` (34 unittest tests). `splice` is idempotent: republishing never grows the body outside the markers. **Why:** the deterministic text operations (marker parsing, path-safe slug, fingerprint, splice) are tested code, not prompt prose; `gh` is only called from commands.
- **`skills/spec-driven-development/references/issue-store.md`**: the single definition of the format and algorithms that every command links to, to keep the store's rules from drifting apart across commands.

### Changed
- `allowed-tools` of `spec`, `explore-plan`, `tdd`, `spec-review`, `review` and `cleanup` gained narrowly scoped `gh issue …` / `issue_spec.py` patterns (no bare `gh *`, no `rm`).
- README documents the store and lists the `gh` permissions to pre-approve (not added to `settings.example.json` on purpose).

## 1.29.0 (2026-09-28)

### Added
- **An eval guards the explore-plan fan-out** (`feature-dev/evals/explore-plan-fanout/`). It runs `/feature-dev:explore-plan` on a small scaffolded fixture project and checks with deterministic graders only (no LLM judge):
  - the four core explorers were spawned;
  - no `Agent` call passed a `name`;
  - no spawn was refused with the teammate errors;
  - the plan was written with a Baseline and one Exploration Findings subsection per explorer, and with no `Degraded exploration` line.

  **Why:** the 1.25.0 bug (a named generator whose explorer spawns were all refused, falling back silently to a single reader) produced normal-looking plans in 3 runs before anyone noticed. Both regression graders were checked against the transcripts of those failing runs. Run it when `explore-plan` or the explorer agents change: one run costs about 4 minutes and $1.50. The command is in `feature-dev/evals/README.md`.

### Changed
- **`/feature-dev:cleanup` also removes local review data** (`.feature-dev/history/<slug>/` snapshots and `.feature-dev/reviews/<slug>-*.md` feedback), which accumulated forever after 1.28.0. Review data follows its slug rather than a file, because a SPEC and its PLAN share the slug:
  - it goes in the same confirmation only when no remaining SPEC or PLAN uses that slug;
  - a slug counts as orphaned only when every one of its reviews points at an artifact that no longer exists. History with no reviews, or reviews whose artifact still exists, is listed as ambiguous and never deleted;
  - a slug with an `in-progress` or `halted` plan is never touched;
  - a slug with a review server still answering is never touched either, and its SPEC or PLAN moves to active work ("review in progress").

  The confirmation question counts every kind of deletion, stale server pointers included.
- **Every deletion in cleanup goes through `review_server.py purge`.** It validates each name first (`SPEC-`/`PLAN-` files directly in the root, slugs without `/`, `..` or a leading dot), refuses symlinks and anything resolving outside `.feature-dev/`, skips git-tracked files, and deletes nothing if any argument is invalid. Cleanup runs it with `--dry-run` before asking.
  - Its allowed-tools no longer carry any `rm` pattern. **Why:** a pre-approved `Bash(rm SPEC-*.md)` also matched `rm SPEC-a.md <any other path>`, because the trailing `*` spans spaces. This was already true before 1.29.0, and the new history patterns would have made it worse (`rm -r .feature-dev/history/../..`).
- **`GET /alive`** on the review server answers liveness probes without resetting the idle timer. Cleanup probes it, so checking whether a forgotten server is alive no longer keeps it running for another 4 hours.
- **History snapshots always use the sanitized slug.** `explore-plan` calls `review_server.py snapshot`, and `/spec` follows the same rule, so cleanup can map every history folder back to its artifact.

## 1.28.0 (2026-09-27)

Third batch from the same retro of 19 sessions (6 features). It gives reviewers a real way to read what they approve, traces each acceptance criterion from spec to test, and keeps the `/tdd` orchestrator's context from growing unchecked.

### Added
- **`/feature-dev:review <SPEC|PLAN path>`: review in a local browser page.** `scripts/review_server.py` serves the artifact on `127.0.0.1` at a random free port and opens the browser. The command runs it in the background, so the harness wakes the model when it exits, with no polling. The page has:
  - an outline built from the headings, with a spec's `AC-n` criteria highlighted;
  - for a plan, each Key Decisions row as a card with **Accept** / **Change to**, and a highlighted Baseline table;
  - comments anchored to any selected text and its nearest heading (or plan step);
  - a **Changes** tab with a line diff against the previous version.
  
  There are three verdicts:
  - **Approve**: the only verdict that sets a spec's `status: approved`.
  - **Approve with notes**: the notes are context. They are recorded in the Decisions Log when they bind later work, and nothing changes unless a note asks.
  - **Request changes**: each item is checked against the artifact and the code before it is applied, then another round is offered, which shows the diff.
  
  On submit, the verdict and the anchored items are written to `.feature-dev/reviews/<slug>-<UTC timestamp>.md`, with the `reviewed_sha256` of the version served. The command finds that file with `review_server.py latest <artifact> --since <start>`, not from the task's stdout. The script derives and sanitizes the slug itself, and it does not depend on Glob listing the gitignored `.feature-dev/`. `review_server.py url <artifact>` prints the page's URL when the browser did not open. A sha mismatch means the file changed while it was being reviewed; the command says so and applies nothing. After 4 h with no request the server exits and writes nothing. A visible tab pings it every minute, so a long read is not idle.
  - **Nothing leaves the machine.** Python 3 stdlib only, no CDN, fonts or external scripts. The markdown renderer is a small inline one that escapes everything. A nonce-based CSP allows the page to talk only to its own server. Requests must carry a per-run token and a `127.0.0.1`/`localhost` Host header. Links are allowlisted: `http(s)`, `mailto`, fragments and relative paths only. Ids generated from the document are prefixed (`h-`, `ac-`), so a `## Submit` heading cannot shadow a page control.
  - **Why:** specs and plans of 332–1073 lines were approved 37–72 s after being written. Users answered decisions from chat summaries and never opened the files in an IDE.
  - `scripts/test_review_server.py` (unittest, stdlib) covers the page, submit, validation, a second submit (409), the idle timeout and the ping that defers it, token checks, slug sanitizing, `latest`/`url`, snapshots and the diff endpoint. When `node` is installed it also syntax-checks the page script and the link allowlist: `python3 feature-dev/scripts/test_review_server.py`.
- **Version history for specs and plans.** Before `/spec`, the explore-plan generator (and its fix re-dispatch) or `/feature-dev:review` overwrites an existing SPEC or PLAN, it copies it to `.feature-dev/history/<slug>/<name>.<n>.md`. The review page diffs against the newest copy that differs. **Why:** nobody could see what changed between plan v1 and v2. `.feature-dev/` is added to `.gitignore` next to `SPEC-*.md` and `PLAN-*.md`.
- **AC traceability, end to end.** 1.26.0 added `AC-n` ids and an informational `Covers:`. Now:
  - When the source spec numbers its ACs, every behavior and characterization step in the plan carries `Covers:` (explore-plan rule 8).
  - `spec-plan-validator` raises Should Address for an AC no step covers and for a `Covers:` citing an id the spec does not define, and for a behavior step without `Covers:`. An AC that the plan's Risks names by id as deliberately left out is not flagged. It reports `AC coverage: covered/total`, which leads explore-plan's brief.
  - `/tdd`'s final report adds an **Acceptance criteria** line: ACs covered by met steps out of the total, with the uncovered and halted ones named.
  - `tdd-runner` puts the AC id in the test's docstring or name where the project's style allows.
  - **Why:** two ACs were lost between spec and plan. One was made unreachable by the code; a docs step was dispatched only because the user asked for it.

### Changed
- **`/tdd` prints a checkpoint line** at each `#### Milestone` boundary, or every ~8 steps in a plan without milestones. The line says progress is recorded and that `/clear` then `/feature-dev:tdd PLAN-<slug>.md` resumes, re-verifying the completed steps. It does not prompt or pause. **Why:** one orchestrator grew from 98k to 389k tokens.
- **`/tdd` and `feature-implementer` stay silent on notifications for finished work.** An idle or completion notice for a subagent whose report was already processed gets no acknowledgement turn. **Why:** one run received 18 idle notices and spent 13 turns only acknowledging them.
- The review briefs of `/spec`, `/spec-review` and `/explore-plan` end with one line offering `/feature-dev:review <path>`.

## 1.27.0 (2026-09-27)

Second batch from the same retro: fewer hand-made handoffs between steps, scope settled before anything else, and nothing lost when artifacts are cleaned up.

### Added
- **`/feature-dev:explore-plan` reviews its own plan.** After the generator writes the plan, the command runs `spec-plan-validator` on it in a fresh context. On Blocking findings it re-dispatches the generator once to fix them in place, re-baselining any `Verify` it changes, then validates again. The findings lead the review brief. **Why:** `plan-review` was optional and ran in only 2 of 6 features, and one of those runs was pasted in from another session. `/feature-dev:plan-review` remains for plans edited by hand.
- **`/feature-dev:spec-review` offers to apply its fixes.** "Never auto-fix" becomes "never fix without confirmation". Findings whose edit follows directly from the finding (a missing AC id, a drifted path) can be applied after one question. Findings that need a decision, such as a REFUTED claim an AC depends on, stay in the brief. **Why:** users typed "Fix your findings" by hand, and interrupted `explore-plan` to do it.
- **A scope question before anything else in `/spec`.** It asks which repos and components are in and what is explicitly out, as a single question with a recommended option, before assumptions and before exploring. The spec gains `## Non-Goals`, which feeds the brief's Out of scope group. The validator's "Out of Scope statement" row becomes a Non-Goals row (Nice to Have). **Why:** in 2 of 6 features the scope changed after the spec was approved, forcing re-plans. A scope question mixed in with other questions sat unanswered for almost 7 hours.
- **`/feature-dev:cleanup` rescues before deleting.** When a spec has Decisions Log entries or unticked QA items, cleanup offers three options for it: post them as a comment on the open PR of *the spec's own* `branch:`, save them to `docs/decisions/<slug>.md`, or delete anyway, in which case the report lists what was lost. It comments rather than editing the PR body, because re-typing someone else's description is where a slip overwrites it. Headings carry the slug, so a rerun never posts twice. A spec whose rescue failed is not deleted. **Why:** a real cleanup deleted a manual QA checklist that had not been run and the only copy of a feature's decisions.
- **The QA Checklist has a fixed shape:** `### Happy path` / `### Edge cases` / `### Error states` groups of `- [ ]` items that the user ticks while verifying. This gives cleanup something reliable to detect.
- **`/feature-dev:tdd SPEC-<slug>.md`** runs without a plan. Criteria come from the spec's tasks or AC ids, decisions go to that spec's Decisions Log, and the spec is marked `implemented` on success. It is meant for small features; `explore-plan` is still the default.

### Changed
- **The Stop hooks of `spec`, `spec-review`, `explore-plan`, `plan-review` and `tdd` are gone.** Each command's last step now prints the exact next command with the artifact path it just wrote or read, and suggests `/clear` before `/tdd`. A halted `/tdd` run prints its own resume command. **Why:** a `once: true` Stop hook fires at the end of the *first* turn. In a command that asks questions (scope, then assumptions, or explore-plan's draft-spec confirmation) that is before the artifact exists, and the hook never fires again. The old generic text hid this; a hook printing a concrete path would have pointed at an older, possibly implemented, artifact.
- `explore-plan` now accepts a `SPEC-*.md` path and `tdd` a `PLAN-*.md` path as their argument, so the printed command works as-is.
- `spec-review` applies fixes before writing its brief, lets you pick fixes with a multi-select, and never touches `status:`.

## 1.26.0 (2026-09-27)

Driven by a retro of 19 sessions (6 features, 6 repos, 2026-09-14 → 09-27) that ran the spec → explore-plan → tdd flow. The gates existed but did not catch what later stalled implementation. The fixes move that discovery earlier and shrink what the user has to read.

### Added
- **The plan carries a `### Baseline`.** The explore-plan generator runs every distinct `Verify` and gate command once on HEAD before writing the plan, and records each as `pass`, `expected-red`, `pre-existing-fail`, `hollow` or `not-run`. It never installs, starts or restarts anything to make a command runnable.
  - **Why:** in 5 of 6 features at least one `Verify` was broken on HEAD and nobody knew until `/tdd` reached it. Causes included master already red, 99 pre-existing ruff findings, and a migration gate that loaded zero apps without an env var, so it checked nothing. In one feature this caused 4 of 6 halts and about 2.5 h of waiting on the user.
  - **How `/tdd` uses it:**
    - Failure attribution becomes a lookup: a failure listed as `pre-existing-fail` belongs to the baseline, and anything else belongs to the change. Lint rows carry per-file counts for the files the plan touches, so a finding is attributable when its file's count has not grown. This gives the existing "an unattributable verification is a failure" rule a data source; it does not relax the rule.
    - `not-run` carries a reason: `missing`, `slow` or `writes`. Only `hollow` and `not-run: missing` gate a step. `/tdd` settles every gated step in Phase 2, before the first dispatch, with one question each: fix the environment, replace the `Verify`, or accept the step as verified by its own tests. It writes the answer into the plan (`accepted by user: …`), so a resumed run does not ask again.
    - A precondition step that moves HEAD, such as a rebase, re-runs the remaining Baseline commands instead of invalidating them.
    - The full-suite, lint and coverage commands of Phases 4–5 are baselined too.
  - Plans without a Baseline keep the previous behaviour, and `plan-review` flags them.
- **Code-claims pass in `spec-review`.** The validator pulls up to ~15 load-bearing claims about the existing code out of the spec: paths, symbols, nullability and FK direction, import direction, migration numbers, config keys. It checks each with Read and Grep and reports it as CONFIRMED, DRIFTED, REFUTED or UNVERIFIED, with `file:line` and the quoted line. A REFUTED claim that an acceptance criterion depends on is Blocking. The validator still offers no opinions on design.
  - **Why:** three specs passed with 0 Blocking and then proved wrong against the code, found by explore-plan or `/tdd` between 12 minutes and hours later. The errors were an inverted mapping, an import cycle, and a non-null FK that made an acceptance criterion unreachable.
  - The validator has no Bash, and its contract forbids claiming it ran anything; anything that needs execution is UNVERIFIED. The validator now runs on **opus**, because an A/B on the sibling `issue-verifier` showed sonnet confirming a harmful fix that opus refuted.
  - `plan-review` gains a path check: Files to Modify must exist, and Files to Create must not.
- **Review brief at every approval gate.** `/spec`, `/spec-review` and `/explore-plan` no longer re-print the artifact. They end with a block of about 15 lines: Decided, Assumed (confirm), Unverified claims about the code, and Out of scope. Items are numbered continuously, so the user can answer "2: no, 5: ok".
  - **Why:** specs of 332–378 lines were approved 37–72 s after being written, and decisions were answered from the chat summary ("D2 … D3 …", "1.OK 2.OK"). The brief makes the fast approval an approval of the things that matter.
- **`tdd-runner` characterization mode and `Pins:`.**
  - `Kind: characterization` covers refactor, deprecation and removal steps. The runner writes tests against the current code, sees them pass, proves each one can fail with a temporary mutation that it restores in the same command, then makes the structural change. New outcome: `pinned`.
  - `Pins:` covers tests that only lock in behavior that already exists. They ride on the step that creates their test file and are proven falsifiable the same way. A pin that fails on first run is a behavior gap and is reported as a blocker.
  - **Why:** plans of 49 and 62 steps. Splitting on every "and" turned each regression pin into its own step. In one run 16 of 45 steps passed at RED, and in another 4 of 4. Each such step cost a runner plus about 6k tokens of orchestrator context; one run grew from 98k to 389k.
- **Acceptance criteria carry stable ids (`**AC-1**`).** Ids are never renumbered. Plan steps and spec tasks may cite them in `Covers:`, and `/tdd` without a plan starts from them.

### Changed
- **`/spec` stops at the spec.** The Implementation Plan and Tasks phases now run only with `--with-tasks`, for when `explore-plan` will not run. Before this, the spec carried a plan that explore-plan then re-derived with different numbering (bulk: T1–T19 became 23 steps), and one spec grew to 1073 lines. The architectural Consequences block moves into Phase 1 of `spec-driven-development`.
- **Plan size guidance.** Step 2b rule 2 now splits on "and" for new behavior only. A new rule 7 says to re-examine a plan with more than ~20 steps; above 25, `plan-review` raises Should Address. Optional `#### Milestone N — <name>` headings group steps for reading, and step numbering stays continuous.
- **`tdd-runner` gets `plan-step-executor`'s hard rules:**
  - no mutating the environment to unblock itself;
  - no git state changes of any kind (one runner ran `git stash` and then contradicted itself in its report);
  - enumerate before you mutate, and hand back a `Tree state: BROKEN` manifest when it stops mid-change.
  
  It also gets a budget section: run only the step's `Verify` during cycles, stop early on a step that is too big for the budget, and re-check the tree when resumed. `maxTurns` stays at 25.
- **`/tdd` resumes a turn-limit stop once** with SendMessage before doing anything else. A second stop on the same step is treated as a mis-sized step and halts, matching `feature-implementer` (1.24.1). The retro counted 15 turn-limit stops.
- **`/tdd` progress is one line per step, in the user's language only.** There is no longer a duplicated recap in two languages. `/tdd` waits for notifications instead of polling with `sleep`, and prints one line when a new milestone starts.
- **`feature-implementer` halts on steps with `Pins:` or `Kind: characterization`** and points to `/feature-dev:tdd`, because only `tdd-runner` writes pins and does the falsifiability proof. It reads the Baseline the same way `/tdd` does. Before this, those plans would have silently dropped the pins on the non-TDD path.
- **The global coverage threshold moves from `tdd-runner` to `/tdd` Phase 4.** Checking it per step would need a full-suite run, which the runner's new budget rule forbids.
- **`tdd-patterns` now allows first-run passes in characterization mode and for pins,** provided a mutation shows each test can fail. A runner measures coverage within its step's `Verify` scope; the full suite runs only in the orchestrator's aggregate pass.

## 1.25.1 (2026-09-22)

### Fixed
- `feature-implementer` no longer carries a paragraph copied from `plan-step-executor` claiming it sees only one step. `tdd-patterns`' cycle-cap rule now defers the re-dispatch decision to the orchestrator, matching `tdd`. `spec` no longer calls the multi-repo section "seventh".
- `spec-driven-development` no longer argues that trivial changes need a spec, which contradicted its own description. Removed strategy coaching from the explorers, a caps-lock note outside the plan generator's prompt, and dead `SUBAGENT-STOP` guards on non-model-invocable commands.

## 1.25.0 (2026-09-17)

### Fixed
- **The eight explorers were unspawnable whenever the Phase 1 generator was named.** `/feature-dev:explore-plan` never spawns an explorer itself — it launches one anonymous `general-purpose` generator, and *that* agent fans out. Nothing in the command said to leave the generator anonymous, so callers routinely passed a `name` ("bulk-plan-generator", "plan-generator"). A named agent is a **teammate**, and the harness then refuses every nested spawn twice over: with a `name` on the child, `Teammates cannot spawn other teammates — the team roster is flat`; without one, `In-process teammates cannot spawn background agents. Agent 'feature-dev:backend-explorer' has background: true in its definition`. The generator falls back to reading the tree alone and the run still produces a plan, which is why this survived — the plan looks normal, it just had one reader instead of eight, no cross-check, and a sweep scoped to whatever files the spec happened to name.
  - **Measured, not inferred.** Across the explore-plan runs on this machine since 2026-09-04: every run whose generator was spawned anonymously got `Async agent launched successfully` for all of its explorers; every run whose generator carried a `name` got 100% refusals — 8 of 8, 5 of 5, 8 of 8 in the three most recent — and fell back to solo exploration. The two failure messages above are quoted from those transcripts.
  - **`background: true` is gone from all eight explorers.** It bought nothing: the generator has to block on all of their reports before it can synthesize anything, so backgrounding only converts a tool result into a notification — while making the agents unspawnable from any in-process caller. Parallelism is unaffected; it comes from issuing the spawns in one response, not from the flag. A caller that invokes one of the four opt-in explorers directly now gets the report in the tool result instead of a handle.
  - **The command now says to leave the generator anonymous**, tells the generator to omit `name` on the explorers, and — because neither guarantee is enforceable from inside a prompt — defines what a refused spawn must produce: retry once, then explore the layer directly and write a `Degraded exploration` line under `### Exploration Findings` naming the explorers that could not run and quoting the refusal. Phase 2 leads with that line when it is present. A degraded plan that says so is reviewable; one that does not is the actual defect.

### Changed
- **Explorer turn cap raised from 15 to 30.** 15 was a guess made when these agents were written; it was never checked against a run. Two of the eight — `observability-explorer` and `config-explorer` — were cut off by it in a real explore-plan run, and stalled explorers return nothing: no partial section, just a layer missing from the plan with no marker saying why.
  - **What was measured:** 17 completed explorer runs on this machine. Tool calls per run ranged 13–43, median 27, and the heaviest run that *finished on its own* (a `test-explorer` sweep, 43 calls) produced a 14k-character report. Calibration against the two that stalled puts a harness turn at roughly two tool calls, so that heaviest natural run sat near 20 harness turns. 30 leaves ~50% headroom over it while still bounding a read-only agent that goes wandering. The tool-call counts are direct; the turns-to-calls ratio is inferred from two data points, so treat 30 as "comfortably above every run we have", not as a tuned figure.
  - **Cheap is still the point.** These stay read-only, Sonnet, and parallel — the cap protects against a runaway, and nothing about a bigger cap makes a well-scoped explorer take longer.
  - **Not changed here:** `tdd-runner` (25) and `plan-step-executor` (20) stall far more often — 11 and 7 recorded stalls respectively against 2 for the explorers — but their caps interact with the deliberate "enumerate before you mutate" discipline from 1.23.0, so raising those is a separate decision, not a side effect of this one.

## 1.24.1 (2026-09-16)

### Fixed
- **1.23.0 claimed a stalled executor is unrecoverable. It is not.** The "Halting mid-change" section stated that running out of turns leaves "no final message, no blocker, no manifest" — true of what the *agent* writes, wrong about the *run*. The harness reports a stalled subagent as `stopped at its N-turn limit (partial result; SendMessage to task-id to continue)`, handing the spawner a partial result and a handle to continue the same agent with its context intact. The claim was taken from an orchestrator's summary of a stall ("hit its turn limit without reporting") instead of the raw notification, which said the opposite in that same run — twice, and went unused both times: the orchestrator finished 7 of 19 call sites by hand and verified the other 12 by reading the diff, work one resume message would have avoided.
  - **`feature-implementer` resumes before reconstructing.** A stall gets one continuation first; rebuilding state from the diff is the fallback, not the default, because it spends exactly the context budget the step was delegated to protect. A second stall is read as a mis-sized step, not as an agent short on turns.
  - **A stall and a hand-back are now distinguished.** `Tree state: BROKEN` is a deliberate stop the spawner asked for and must wire; a turn-limit stall is accidental and recoverable. The two arrive looking alike and want opposite responses.
  - **The executor's preventive discipline is unchanged.** It still cannot self-report, recovery still depends on someone reading the notification, and no resume un-applies a half-finished mutation already on disk.

## 1.24.0 (2026-09-15)

### Added
- **`plan-step-executor` may not mutate the environment to unblock itself.** The contract already said "do not debug adjacent systems", filed under *Edge cases* alongside flaky tests. That phrasing did not cover what actually happened in the run that prompted this change: a step's verification failed because a dependency service was crash-looping, and the executor restarted the container and installed a missing package inside it. Neither reads as "debugging" from the inside — each is a plausible unblocking move — so the rule never engaged. The service ended up in a state that needed a full rebuild of a sibling repo to recover, the step halted with its acceptance criteria unproven, and the next turn was spent re-verifying the four steps that had already passed.
  - **Promoted from an edge case to a *Hard rule*.** Restarting or rebuilding a container, installing a package into a running service, editing a service's config, and seeding a database are now named explicitly, and none of them belong to a step that does not name them. The edge-case bullet for an unrelated verification failure now points at the hard rule instead of carrying the constraint alone.
  - **The reason is attribution, not tidiness.** A service that is down is a blocker the executor reports; a half-repaired one is a state nobody chose and nobody can attribute afterwards. The run that prompted this could not establish whether the dependency was already failing or whether the restart finished it off — the executor said so honestly, and that ambiguity was itself the cost.

## 1.23.0 (2026-09-15)

### Added
- **A hand-back protocol for a step that stops with the tree broken.** A step that moves a symbol and updates its consumers passes through a window where nothing compiles. Every halt case the executor contract described — missing input, step contradicts reality, unrelated verification failure — happens *before* any edit, so the contract never said what state the working tree is in when an agent stops. Exhaustion mid-edit is the one case where halt does not mean a clean tree, and it was the one case left unspecified: the observed failure is an executor that gets the mechanical move right, runs out of budget on the consumers, and hands back a broken tree that the next step's executor then debugs as a pre-existing failure.
  - **The discipline is preventive, because it cannot be reactive.** Running out of turns is not an event an agent gets to handle — there is no final message, no blocker, no manifest. So the rule is *enumerate before you mutate*: grep the full set of sites first (cheap, read-only), and if the set is bigger than the step sized for you, return the enumeration as a blocker having edited nothing. Twenty-three consumers listed and none touched is worth more to the run than eleven edited and silence.
  - **An intentional broken state is a hand-back; an accidental one is a defect.** When the step explicitly directs a stop mid-change, the report now leads with a **Tree state: BROKEN** manifest — symbols moved (`old` → `new`), **every** consumer found as `file:line`, which of them were updated, and what the verification command will report until the rest is wired. The full consumer list matters because the spawner cannot otherwise distinguish a site deliberately skipped from one never seen, and the sites that only fail at runtime (dynamic imports, string references, skipped tests) never surface in its checkpoint. Omitted entirely on a clean run.
  - **`feature-implementer` halts on the block and refuses to dispatch over it.** It parses `Tree state`, carries the manifest into its own final report, never commits, and never spawns the next executor onto a broken tree. New terminal recommendation: *tree broken — wire before anything else*.

### Changed
- **"Fix failures only if caused by your change" no longer eats a boundary the spawner drew on purpose.** The rule is right in isolation, but when a step splits a change in half — the agent moves the code, the spawner wires the imports and runs the checkpoints — an executor that moves a symbol and sees the tree break is *following* that rule when it goes off to repair the consumers, which is the reserved half. That is how both stalled agents in the run that prompted this change spent their budget on work the orchestrator had kept for itself. New rule 6 states the carve-out: breakage inside a reserved half is reported, not repaired. Where a step is silent about who owns the consumers, the minimum reasonable interpretation is now that they are not the executor's — list them, edit none, flag it under "Deviations".

## 1.22.0 (2026-09-14)

### Added
- **`--coordinator <session-name>` routes cross-repo questions to a live session.** Covers the other half of the second-session workflow: a session opened deliberately before the run, to answer the questions a multi-repo feature raises. On a halt that is a *question* rather than a defect, the run sends that session one message — step number, the question, and the `cross-repo-advisor` brief if one was produced — with `notify_when_idle: true`, and still hands the halt to the user. Never per-step progress: one message per halt that needs one.
  - **The command does not search for a session, and that is deliberate.** Measured against `ListAgents`: the listing carries name, kind and status but **no working directory**, so matching degrades to the session's name — which `handoff/*` and `ship` already document as the fallback. A coordinator session for a multi-repo feature has no single repo to be named after (that is *why* it gets named by hand), so name-matching reliably finds the implementer sessions, named after their repos, and misses the coordinator. Auto-discovery here does not merely fail, it selects the wrong sessions. The user names it or it is not used.
  - **A gated hint instead of a prompt.** When the spec has a `repos:` block and no `--coordinator` was passed, Phase 1 emits one line suggesting the flag. It never asks, and never fires on a single-repo run.
  - **An unreachable coordinator is a downgrade, never a halt.** `ListAgents` missing (older Claude Code, Bedrock/Vertex/Foundry), no match, or several matches — say so once, continue normally, do not retry on later steps.
  - **Log first, announce second.** A question may go out immediately; a decision is written to the spec's `## Decisions Log` before it is announced, and only once the user has accepted it. A decision that reached the coordinator session but not the log is the split-brain the log was built to prevent — and the session will not outlive the feature.

### Changed
- **Agent messaging silence is now a rule, not a report of what is installed.** Since v1.20.0 the three implementation agents were told "you have none, you need none" — an availability claim, which stops binding the moment a messaging tool becomes reachable, and the observed failure was agents *reaching for* the tool on their own. The contracts in `tdd-runner`, `plan-step-executor`, `feature-implementer` and `cross-repo-advisor` now state the rule and its reason: the spawner is the only party that sees every step's report, holds the accumulated carry-over, and owns the Decisions Log, so it is the only party that can judge what is worth telling anyone and record it where the run's history can find it. A subagent sees one step; a message it sends sideways is un-contextualized by construction and lands outside the record. This is why subagents stay mute even where `SendMessage` exists — the orchestrator is the run's single voice.

## 1.21.0 (2026-09-14)

### Added
- **Decisions taken during a run now survive it.** `/feature-dev:tdd` is single-repo by construction — it resolves `origin`, discovers `PLAN-*.md` in *this* repo root, and never reads the `repos:` block that `spec-driven-development` generates for a multi-repo feature. So a two-repo feature is two runs that do not know each other, and everything Phase 3 learned (an accepted deviation, a new error code, the user's answer that unblocked a halt) lived only in the orchestrator's context and died with it. The gap was being filled by hand: keeping a second session open as the feature's memory and re-explaining the decision in the consuming repo.
  - **New `## Decisions Log` section in the `SPEC-*.md`.** The spec is the home because it outlives the run — a `PLAN-*.md` is deleted on success, so a decision written there dies with it. Entries carry **what**, **Because:**, and **Binds:** — the last naming the repo, step, or `this repo only` that must obey, which is what makes a run in the other repo able to tell whether an entry applies to it.
  - **Phase 3 writes them; Phase 1 reads them back.** Phase 1 loads the log through the existing `source_spec:` link (already used for the drift check) and threads it into the initial carry-over, treating a recorded decision as binding as the plan. A `source_spec:` that points outside the repo (`../<sibling>/SPEC-*.md`) is the expected multi-repo shape, not an error.
  - **A sharp qualifying test, because a vague one records everything or nothing.** An entry qualifies only if it is not already written in the plan or spec **and** it constrains code outside its step. Renaming a local fails; "the empty case returns `NO_SUBJECTS` and the backend owns it" passes.
  - **Single-repo runs keep entries in the plan's `decisions:` frontmatter** and reproduce them in the Phase 6 report — the plan is deleted on success, so the report is the only place they survive.

- **`feature-dev:cross-repo-advisor`** — read-only decision brief for ONE bounded cross-repo question ("which side owns this field?", "does this break the declared contract?"). Reads the Cross-Repo Contracts section, the Decisions Log, and the actual call sites in each repo from the `repos:` block, then returns two or three implementable options and a recommendation with the condition that would flip it.
  - **Spawned from a Phase 3 STOP, once, and only when the halt is a question rather than a defect.** A brief adds nothing to a red test. The advisor never edits, never resumes the run, and its recommendation is not recorded in the Decisions Log until the user accepts it — the log holds decisions, not suggestions.
  - **Constrained claims, not just constrained tools.** It cannot run anything, so its contract forbids any phrasing that implies execution, requires `[read]` (with `path:line`) / `[derived]` provenance labels on every factual claim, makes an unresolvable repo path a reported gap rather than an inference, and requires a non-empty `Not checked` section. A recommendation that is right but supported by invented evidence is worse than one that is wrong: the wrong one dies at the first check, the invented evidence teaches the reader that checking is unnecessary.
  - Git access is scoped to `log`/`diff`/`show` rather than `Bash(git *)`, which still permits `commit` and `push`.

## 1.20.0 (2026-09-11)

### Fixed
- **Step routing now asks who writes the test, not whether `Test:` names a path.** Observed in a real 9-step run: a step whose `Test:` pointed at a guard file an *earlier* step had already written was, by the v1.17.0 table, a `tdd-runner` step — but its RED already existed and was failing, so there was no test to write. The orchestrator noticed and re-routed to `plan-step-executor` on its own judgment; the table gave it no rule, so the next run could just as easily route it the other way and stall a runner on its own "did RED fail for the right reason" check. Plans now mark such a step `Test: <path> (written by step N)` and the routing table keys on that marker.
- **Precondition steps have a route.** A step with `Impl: n/a` *and* `Test: n/a` — a rebase, a `makemigrations --check`, a dependency install — was matched by the "`Test: n/a` → `plan-step-executor`" row, but `plan-step-executor` is forbidden from committing and owns no git state, so dispatching one is wrong. Observed the orchestrator handling such a step inline instead, correctly but unprompted. The table now says so explicitly, and adds that a precondition failing its `Verify` is a hard stop rather than something to work around — the plan assumed a baseline that does not hold.
- **Agents no longer try to *deliver* their report.** Every `tdd-runner` and `plan-step-executor` in the observed run finished by attempting `SendMessage({to: "team-lead"})`, hitting `No such tool available: SendMessage`, and then pasting the report inline with an apology about not reaching the team lead. Harmless — the report still reached the spawner through the normal completion notification — but it cost a failed tool call and two turns per step, nine times over. The agents infer the teammate addressing scheme from the harness and read "report back" as "hand it to someone". All three agent contracts now state that the final message *is* the delivery and that no messaging tool exists or is needed.

- **The dependency gate is now enforced before every dispatch.** Every number in a step's `Depends on` must be in `completed_steps` or the run stops. Observed the orchestrator state the rule itself — *"Waiting on the suite before dispatching Step 10 — if Step 9 is red, the frontend doesn't start"* — and then dispatch Step 10 anyway ~50 turns later, reasoning that the frontend lived in a different repo with "zero overlap". `Depends on` encodes a decision gate, not a file-locking concern: steps 10 and 12 both declared `Depends on: 9`, step 9 was a release gate that never resolved, and three frontend steps were built on a contract nobody had confirmed. The rule now names both rationalizations ("different repo, no overlap" and "it will probably pass") and rejects them.
- **An unattributable verification is now a failure, not a pass.** The same run finished with *"hay 1 error y 1 fallo… no puedo decirte todavía cuáles son — pytest con xdist no imprime los nombres hasta el resumen final, y corté la espera. Eso queda pendiente"* — and then committed. A step whose `Verify` produced failures that cannot be assigned to this change rather than a pre-existing baseline is not verified, whatever the pass count next to it. The command must halt and hand the ambiguity to the user rather than advance, record the step, or commit with a caveat attached.
- **Substituting a step's `Verify` now requires the user.** The plan's step 9 gate was genuinely defective — `ruff check . && ruff format .` would have failed on 100 pre-existing errors and reformatted 100 unrelated files — and the orchestrator was right to catch it. But it then chose its own narrower gate and recorded the step as passed, twice (ruff scoped to changed files, then `make test-related` in place of the plan's full-app run). A substitute command is a different gate than the one the plan was reviewed against; surfacing the defect is required, silently replacing it converts a plan defect into a scope reduction.
- **`completed_steps` may not contain gaps.** The cut run left `[0,1,2,3,4,5,6,7,8,10,11,12]` — step 9 never completed, three later steps recorded anyway. Phase 3 now refuses to write a gap, and Phase 1b rejects a gapped record on resume and resumes from the gap rather than the highest recorded number. Without this the resume path re-verifies the recorded steps, finds them green, and silently inherits the hole.

### Changed
- **`spec-plan-validator`** accepts `Impl: n/a` + `Test: n/a` as a valid precondition step, and flags a step whose test is created by an earlier step but is missing the `(written by step N)` marker as Should Address.

## 1.19.0 (2026-09-10)

### Added
- **`/feature-dev:tdd` runs are now resumable.** A halted run was previously unrecoverable in practice: it left the working tree dirty with the criteria that *had* passed, and Phase 0's `Working tree is clean. If dirty, STOP` gate then refused to start again. The user had to hand-commit partial work the command never tracked, and the re-run re-decomposed the feature from scratch with no idea which criteria were already green — re-implementing over existing code, one wasted `RED passed early` runner per finished step. `feature-implementer` solved this for its own path with `start_at_step`; the command had no equivalent.
  - **`PLAN-*.md` frontmatter gained `run_status:` and `completed_steps:`**, written by the plan generator as `not-started` / `[]` and owned thereafter by `/feature-dev:tdd`. Phase 3 appends each passing step and flips `run_status: in-progress`; a halt writes `run_status: halted` plus `halted_at:` and a one-line `halt_reason:`.
  - **Phase 0's dirty-tree gate is now resume-aware.** Dirty + an `in-progress`/`halted` plan is the command's own unfinished work, not stray edits, and routes to the new Phase 1b. Dirty with no such plan still stops. Plans without `run_status:` predate this version and fall back to the plain stop.
  - **New Phase 1b re-verifies before trusting.** `completed_steps:` is a claim about a tree that has been sitting dirty, so each recorded step's `Verify:` command is re-run: green skips, red re-dispatches. If every recorded step re-verifies red the tree is not what the plan describes, and the command stops rather than attempting a partial repair. This is the first thing the v1.17.0 step contract bought that could not be built before it — the check is only possible because every step now carries a real command.
  - **The halt message tells the user not to stash.** Stashing is the one action that makes recorded progress unrecoverable.

### Changed
- **`/feature-dev:cleanup` will not offer an in-progress or halted plan for deletion.** It now reads `run_status:` / `completed_steps:` and classifies those plans as active work, overriding the "safe to delete" rules — including the `source_spec` is `implemented` rule that would otherwise sweep up a resumable run. Deleting one discards the progress record and strands a dirty tree with no way to tell which steps landed.
- **`spec-plan-validator`** flags a plan missing `run_status:` / `completed_steps:` as Nice to Have, noting it cannot be resumed if a run halts.

### Notes
- Progress recording is deliberately not commit-per-step. `feature-implementer` defaults `commit_per_step: false`, and the command's contract is one reviewable change set handed to `/commit` and `/code-review:branch` via the Stop hook. Resume is built on re-verification instead, which also catches hand-edits between runs.

## 1.18.0 (2026-09-10)

### Changed
- **`/feature-dev:explore-plan` now selects its explorers instead of hardcoding four.** v1.14.0 added `config-explorer`, `schema-explorer`, `api-contract-explorer` and `observability-explorer`, documented as "opt-in primitives — invoke directly from any skill". Nothing invoked them: no command and no skill in the plugin referenced any of the four, and `explore-plan` dispatched exactly `backend` / `frontend` / `test` / `history`, always the same four regardless of the feature. The practical cost was not dead code but blind planning — a feature with a migration got planned without anyone reading the migration state, and a multi-repo feature got planned without anyone reading the API contracts, with the right agent sitting unused next door.
  - **New Phase 0 step 4** picks the additional explorers from signals in the feature description and, when `source_spec` is set, the spec **body** (frontmatter alone is too thin a signal). Selection table: persistence → `schema-explorer`; settings / environment variables / credentials / feature flags → `config-explorer`; 2+ `repos:` entries or a declared-contract change → `api-contract-explorer`; silent-failure surfaces (background jobs, queue consumers, scheduled tasks, webhook handlers, auth and payment paths) → `observability-explorer`. Ties break toward including the explorer — they are read-only, parallel, and capped at `maxTurns: 15`.
  - The selection is stated to the user in one line before the fork, and passed into the Phase 1 agent prompt. All selected explorers launch in the **same** response as the base four, so the added ones cost wall-clock only, not extra rounds.
  - **Plan template** gained matching optional subsections under Exploration Findings (Schema & Migrations, Configuration, API Contracts, Observability), emitted only for explorers that actually ran — no "N/A" placeholder headings.
  - Template placeholders now name the explorers (`[Key findings from backend-explorer]`) instead of positions (`[Key findings from Agent 1]`), which stopped being stable once the batch size varies.

## 1.17.0 (2026-09-10)

### Changed
- **`PLAN-*.md` steps now carry a dispatchable contract.** `/feature-dev:explore-plan` emitted its Implementation Order as free prose (`1. [Step 1 — with rationale]`) — one sentence per step, no acceptance criterion, no file paths, no verification command. Every consumer requires those: `plan-step-executor` demands *"exact commands that prove the step works"*, and `feature-implementer` has it as a hard rule — *"A step's verification command is missing from the plan → halt. Verification is non-negotiable."* The plugin's own generator was producing plans its own implementer agent was contractually required to reject on step 1, which is why the agent path was effectively unreachable. Each step now emits `Accept` / `Impl` / `Test` / `Verify` / `Depends on` / `Rationale`, mirroring the `Task / Accept / Verify / Files` convention the SPEC template has used since v1.0.
  - Five non-negotiable generation rules added to the plan-writing agent's prompt: `Verify` must be a real runnable command derived from test-explorer findings (never "run the tests"), `Accept` must be a single criterion (an "and" means split the step), `Impl`/`Test` must be paths that also appear in the Files tables, non-behavioral steps still need `Verify` with `Test: n/a — <reason>`, and ordering follows dependency rather than layer.
- **`spec-plan-validator` now enforces the step contract.** The plan checklist replaced one prose-quality row ("with rationale or dependency note") with six structural rows — `Accept`, `Verify`, `Impl`/`Test` as Blocking; path cross-reference, `Depends on`/`Rationale`, and compound-criterion detection as Should Address. Previously `/feature-dev:plan-review` returned "ready for `/feature-dev:tdd`" on plans that no agent could execute.
- **`/feature-dev:tdd` Phase 2 reads the contract instead of inferring it.** With a plan in use it takes the six fields verbatim and halts if a step lacks `Accept`/`Verify` or if `Verify` is a description rather than a command, pointing the user at `/feature-dev:plan-review`. Inference is now confined to the no-plan path (`$ARGUMENTS` only). Re-deriving fields from a reviewed plan silently discards that review.

### Added
- **`/feature-dev:tdd` routes non-behavioral steps to `plan-step-executor`.** A step whose `Test:` is `n/a` (migration, config wiring, dependency bump) has nothing to assert test-first, but still has a `Verify` gate. Previously the command had no path for these at all — it dispatched `tdd-runner` for everything or nothing. This also makes `plan-step-executor` reachable from a command for the first time.

## 1.16.0 (2026-09-10)

### Changed
- **`/feature-dev:tdd` now delegates implementation to the `tdd-runner` agent instead of doing it in the main context.** The command shipped three implementation agents (`tdd-runner`, `plan-step-executor`, `feature-implementer`) that no command ever dispatched — they were reachable only by the user naming them directly. Phases 2–6 were written as imperatives to whoever ran the command, so every run implemented the whole feature inline, burning the main context on test bodies and impl diffs. The Agent tool was already in `allowed-tools` and used in Phase 1 for `Explore`; only the implementation half was missing.
  - **New Phase 2 — Decompose into Acceptance Criteria**: the main agent breaks the feature into ordered, independently verifiable criteria and resolves the six fields `tdd-runner`'s spawner contract requires (behavior, spec reference, test target, impl target, verification command, cycle cap) *before* dispatching. A runner halts on a missing contract field, so resolving up front converts a mid-loop halt into an early stop.
  - **New Phase 3 — Execute TDD Cycles**: one `tdd-runner` per criterion, dispatched sequentially with accumulated carry-over deltas threaded forward. Explicit halt-reason routing table (`criteria met` / `RED passed early` / `cycle cap` / `GREEN unreachable` / `scope mismatch` / `blocker`) so the orchestrator's decision is not left to judgment.
  - **Stricter RED**: the old Phase 2 wrote the full test suite up front and expected all of it to fail — big-bang RED. Each `tdd-runner` now does incremental RED per behavior *and* validates the failure mode (test fails because the behavior is missing, not because of an import error or a missing fixture). That check — which `tdd-runner.md` calls "the most common way TDD agents fail" — had no equivalent in the command.
  - **Phase 5 (Refactor) removed as a standalone phase**: `tdd-runner` runs REFACTOR inside every cycle, gated on green. A separate end-of-run refactor pass would have been a second, unsynchronized one.
  - **Coverage (now Phase 4) is aggregate-only**: per-line coverage is gated inside each runner; the command checks the union of changed files and dispatches an extra runner per meaningful gap rather than writing catch-up tests inline.
  - **Report (now Phase 6)** gains a per-criterion table (cycles run, outcome) and a Blockers section. Spec `status:` flipping and `PLAN-*.md` deletion now happen **only** when every criterion was met — a halted run leaves both intact so it can be resumed.
- **README**: the "Alternative implementation path (agent-driven)" section no longer lists `tdd-runner` as an alternative to the command — it is now the command's execution engine. `feature-implementer` / `plan-step-executor` remain the non-TDD agent path.

- **`tdd-patterns` skill**: the iteration limit now reads "5 cycles per bounded behavior (one acceptance criterion), not per feature". The skill is loaded by both the orchestrator and every `tdd-runner`; under the old wording a feature with N criteria would have read as sharing a single 5-cycle budget.

### Notes
- Sequential dispatch is deliberate and unchanged in spirit from `explore-plan.md`'s note that "TDD requires sequential discipline": criteria depend on symbols earlier criteria introduce, and concurrent runners collide on overlapping files. The delegation is for context hygiene and RED discipline, not for parallelism.
- No change to `tdd-runner.md` itself — its contract was already correct and complete; the command was simply never calling it.


## 1.15.0 (2026-07-02)

### Changed
- **`/feature-dev:spec` now writes eight spec areas instead of six** — added a dedicated `## Acceptance Criteria` section and a `## QA Checklist` section. Previously the command folded "what success looks like" into `## Objective` and left QA-facing checks implicit inside `## Testing Strategy`, so **every** `/feature-dev:spec-review` run reported the same two findings: a Blocking "no dedicated Acceptance Criteria section" and a Should-Address "no QA Checklist". The generator now emits exactly the sections the `spec-plan-validator` agent checks for, closing the recurring feedback loop.
  - **Acceptance Criteria**: dedicated, scannable, user-observable criteria — must include at least one failure/error-state criterion, not only happy-path outcomes (matches the validator's Blocking + Should-Address checks).
  - **QA Checklist**: QA-facing list grouped as happy path / edge cases / error states, distinct from the engineering-oriented Testing Strategy.
- **`spec-driven-development` skill** updated in lockstep: the Phase 1 area list (six → eight) and the Verification checklist now name the Acceptance Criteria and QA Checklist requirements, keeping the imported best-practices source of truth aligned with the command.

### Notes
- No change to `spec-plan-validator` / `/feature-dev:spec-review` — the validator's bar was already correct; the generator was under-producing. Alignment was done by raising the generator, not lowering the checker.

## 1.14.0 (2026-05-16)

### Added
- **`config-explorer` agent** — locates environment/config surface for a feature: `.env*` files, settings modules, env-var reads, typed-settings loaders (pydantic-settings, viper, zod env schemas), feature-flag providers (LaunchDarkly, GrowthBook, Unleash), secrets handling (vault, SSM, KMS), and per-environment overrides. Read-only; same frontmatter contract as the existing explorers (`tools: Read, Grep, Glob`, `model: sonnet`, `maxTurns: 15`, `background: true`).
- **`schema-explorer` agent** — maps DB schema and migration state for a feature's domain: migration tool detection (Django / Alembic / Prisma / Knex / Flyway / sqlx / Diesel), domain-touching migrations, current schema definitions, indexes/constraints, naming conventions, pending migrations (detected without executing), and safety patterns (squashing, multi-tenancy, backfills, online-DDL). Read-only; complements `backend-explorer` on the highest-risk layer.
- **`api-contract-explorer` agent** — maps declared API contracts (OpenAPI, GraphQL SDL, tRPC routers, protobuf, JSON Schema) as a layer distinct from endpoint *code*. Reports operations in the domain, shared DTOs / generated clients, versioning strategy, contract testing (Pact, Dredd, Schemathesis), codegen pipelines, and consumer repos. Critical for multi-repo features that `/feature-dev:spec` already supports via `repos:` frontmatter.
- **`observability-explorer` agent** — maps logging stack, metrics, tracing SDK, error reporting, alerting config, dashboards, and the codebase's conventions for adding new signals. Helps new feature code match existing logging/metric/trace naming so post-ship visibility doesn't degrade.

### Notes
- All four agents are **opt-in primitives** — not auto-spawned by `/feature-dev:explore-plan`. They are invokable directly from any skill (in this plugin or elsewhere) via `subagent_type: "feature-dev:<name>"`, matching how the existing explorers are reused outside `explore-plan`.
- README's agent section gains an "Opt-in explorers" subsection documenting the new agents.
- No changes to `/feature-dev:explore-plan` — the default 4-agent fan-out stays universal. Wiring an opt-in flag (e.g., `--with=config,schema`) is deferred.

## 1.13.0 (2026-05-13)

### Added
- **`plan-step-executor` agent** — focused implementation specialist that executes ONE step of an approved plan in isolation. Restricted tools (`Read, Edit, Write, Grep, Glob, Bash, NotebookEdit`), explicit Spawner contract (step description, file paths, verification, carry-over), and a fixed return format (Files changed / Verification / Deviations / Carry-over / Blockers).
- **`feature-implementer` agent** — orchestrator that drives an approved `PLAN-*.md` end-to-end by dispatching each step to `plan-step-executor`, threading carry-over deltas forward, and halting cleanly on blockers. Tools: `Read, Bash, Agent`. Links the `spec-driven-development` skill.
- **`tdd-runner` agent** — strict red-green-refactor enforcer for one bounded behavior. Caps at 5 cycles, validates the RED failure mode is legitimate before allowing GREEN, gates promotion on coverage. Stack-agnostic (pytest / vitest / jest from path). Links the `tdd-patterns` skill.

### Changed
- **`/feature-dev:spec` Phase 2**: clarified that the Plan section gets appended to the SPEC file (high-level outline only) and explicitly defers the file-level, codebase-aware plan to `PLAN-<slug>.md` produced by `/feature-dev:explore-plan`. Previously the phase described an activity but did not name its deliverable, leaving the model unsure whether to write to the spec, verbalize, or generate a separate PLAN.
- **Model selection on new agents**: `feature-implementer`, `plan-step-executor`, and `tdd-runner` set `model: sonnet` (was `inherit`) to align with the 20+ sonnet agents across the marketplace and keep cost/latency predictable when the agents run in loops (TDD cycles, multi-step plans).
- **`history-explorer` agent**: promoted from `haiku` to `sonnet`. As an exploration agent spawned by `/feature-dev:explore-plan` for parallel codebase analysis, it must produce findings the synthesizer can integrate into a PLAN. The user's global CLAUDE.md states: *"Explore agents use sonnet — Haiku lacks the analysis depth needed for accurate pattern recognition and synthesis across a codebase."* Now matches `backend-explorer`, `frontend-explorer`, `test-explorer`.
- **`/feature-dev:spec` and `/feature-dev:explore-plan` now run on Opus** (`model: opus` in frontmatter). Both are reasoning-heavy phases — spec formalization with multi-repo detection and gated user reviews, exploration synthesis across four parallel agents into a coherent plan. Pre-setting the model on the command guarantees quality regardless of the caller's default. Implementation-side workhorses (`/feature-dev:tdd`, `feature-implementer`, `plan-step-executor`, `tdd-runner`) intentionally stay on sonnet — they're bounded by tests and acceptance criteria, not by reasoning depth.
- **`maxTurns` on the three new agents**: `plan-step-executor` (20), `tdd-runner` (25), `feature-implementer` (30). Aligns with the existing pattern (explorers, refactor agents, comment-verifier, fix-implementer all set `maxTurns`) and guards against runaway loops on degenerate plans / TDD cycles.
- **`feature-implementer` commit discipline section**: documented explicit rules for `commit_per_step` — never `--no-verify`, halt on pre-commit hook failure (no amend, no retry), commit subject = step acceptance criteria, new commit per step (no `--amend`). Inherits the repo's CLAUDE.md commit safety protocol.
- **`feature-implementer` parallelization clarification**: the "Do not parallelize steps" hard rule now explicitly states that the "Parallelization Hints" section of a PLAN is informational for human readers, not an instruction to dispatch parallel executors.
- **README workflow**: added an "Alternative implementation path (agent-driven)" subsection documenting `feature-implementer` / `plan-step-executor` / `tdd-runner` as an alternative to the interactive `/feature-dev:tdd` command path.
- **Example languages**: normalized examples in `feature-implementer.md` and `tdd-runner.md` to English to match the rest of the marketplace.

### Why
The three compose naturally with the existing `feature-dev` surface: `/feature-dev:spec` and `/feature-dev:explore-plan` produce the artifacts `feature-implementer` consumes; `/feature-dev:tdd` and the `tdd-patterns` skill define the discipline `tdd-runner` enforces; `plan-step-executor` is the atomic unit both higher-level agents (and the main agent) can dispatch to without polluting the orchestrator's context budget. Co-locating them with `backend-explorer`, `frontend-explorer`, `spec-plan-validator` keeps the feature-dev workflow self-contained instead of scattered across user-scope `~/.claude/agents/`.

## 1.12.2 (2026-05-12)

### Changed
- Removed unsupported `permissionMode: default` frontmatter field from `spec-plan-validator` agent. Plugin agents do not support `permissionMode`, `hooks`, or `mcpServers` — they are silently ignored by the harness.

## 1.12.1 (2026-05-07)

### Changed
- `/feature-dev:spec` now recommends running in plan mode (`Shift+Tab` to toggle) so the spec is reviewed before files land on disk.

### Why
Aligns with Anthropic's Claude Code "explore → plan → implement" workflow: planning surfaces should default to plan mode, not write mode.

## 1.12.0 (2026-05-06)

### Added
- **Consequences** three-way split in `spec-driven-development` Phase 2 (Plan), required when the plan makes an architectural choice (new pattern, framework, data store, integration, or significant refactor): *what becomes easier* / *what becomes harder* / *what we'll need to revisit later*. Includes a worked example (event sourcing for billing reconciliation).

### Why
Borrowed from Anthropic's `engineering:architecture` ADR template. Most spec/ADR templates stop at pros/cons; the third clause (`revisit when`) is the operational gold — it forces the plan to name the conditions that would invalidate the choice, rather than letting the decision drift into "permanent" by default. Surfaces scale thresholds, integration points, and cross-domain coupling that pros/cons hide.

## 1.11.0 (2026-05-06)

### Changed
- `spec-driven-development` Phase 4 now explicitly delegates to the **`feature-dev:tdd-patterns`** skill rather than describing TDD inline. Avoids duplicating the cycle rules (5-cycle limit, stuck-after-3, coverage gate) in two places — `tdd-patterns` becomes the single canonical reference. Pattern borrowed from Anthropic's `engineering` plugin where `architecture` delegates depth to `system-design`.

## 1.10.0 (2026-05-06)

### Added
- **Decision Rules** section in `spec-driven-development` skill — operational tests applied in real time when writing a spec or pushing back on stakeholders. Includes the P0 cut-test ("if removed, does the feature still solve the core problem?"), the "if everything is P0, nothing is P0" rule, the scope-trade-only rule (any addition requires a removal or timeline extension), time-boxed investigations, and the genuinely-open-questions rule (open questions must be unanswerable from context, owner-tagged, and marked blocking vs non-blocking).
- **Common Spec Mistakes** section in `spec-driven-development` skill — anti-pattern catalog covering bad-spec failure modes (vague criteria, solution-prescriptive stories, internal-focus stories, everything-is-P0, padded open questions, perfunctory boundaries, post-hoc specs). Complements the existing Anti-Rationalizations table, which catches *skipping* the spec; this catches *writing it badly*.

### Changed
- Phase 1's "Reframe vague requirements" step now bans nine specific vague words from acceptance criteria (`fast`, `slow`, `easy`, `simple`, `user-friendly`, `intuitive`, `seamless`, `better`, `improved`) unless immediately defined concretely. Added a second worked example showing the reframe for "intuitive."
- Verification checklist expanded with three new gates: no banned vague words without concrete definitions, P0 list passes the cut-test (≤5 items each truly required), and open questions are genuinely open, owner-tagged, and blocking-vs-non-blocking marked. Boundaries verification now requires one-line rationale per Never-do item.

### Why
Borrowed from a comparable Anthropic spec-writing skill we studied. Our previous skill defined what a good spec contains; the new content adds operational decision rules and an anti-pattern catalog so the model can self-correct mid-conversation rather than only catch issues in review.

## 1.9.2 (2026-05-06)

### Changed
- Trimmed `cleanup`, `plan-review`, `spec-review` command descriptions and `spec-driven-development` skill description to fit Claude Code's skill-listing budget. Workflow detail remains in command/skill bodies.

## 1.9.1 (2026-05-01)

### Fixed
- `/feature-dev:spec` no longer fails with `Shell command failed` when `.claude/settings.local.json` is absent. The Context block's `jq` call previously exited non-zero on a missing file (stderr was silenced but the exit code was not), tripping the harness. Appended `|| true` so a missing settings file just produces an empty `Additional directories` value, which is the intended single-repo signal.

## 1.9.0 (2026-04-22)

### Added
- `/feature-dev:spec-review` — opt-in validator that reads a `SPEC-*.md` and emits a Blocking / Should Address / Nice to Have gap checklist. Modeled on `prd-toolkit`'s validate pattern but checks SPEC-specific structure: acceptance criteria observability, multi-repo `Cross-Repo Contracts` presence, `Repo:` task tagging, frontmatter validity. Auto-discovers `SPEC-*.md` in repo root when called without arguments.
- `/feature-dev:plan-review` — opt-in validator for `PLAN-*.md`. Checks `source_spec:` linkage (and that the linked SPEC file still exists), Files-to-Modify table presence, Implementation Order rationale, Risks, Estimated Test Cases. Auto-discovers `PLAN-*.md` in repo root when called without arguments.
- `spec-plan-validator` subagent — shared backend for both new commands. Routes by `artifact_type` (`spec` or `plan`). Categorical findings only — no numerical scoring (scoring invites rubber-stamping). Findings are advisory and never written back into the artifact.
- `### Parallelization Hints` section in the plan template emitted by `/feature-dev:explore-plan`. Informational only — flags independent steps from the Implementation Order so a human or future executor can decide where parallel work is safe. Does NOT contain executable subagent prompts (TDD requires sequential discipline, and concurrent edits to overlapping files would collide).
- `/feature-dev:cleanup` — opt-in bulk deletion of SPEC/PLAN artifacts that are no longer in active use. Categorizes files by safety (implemented specs and orphan plans → safe; in-flight specs/plans → never offered; ambiguous standalone plans → surfaced but not auto-included), then requires a single explicit Y/N confirmation before deletion. `disable-model-invocation: true` so it can never auto-trigger; allowed-tools scoped to `Bash(rm SPEC-*.md)` and `Bash(rm PLAN-*.md)` only. Solves long-term clutter without forcing a delete prompt at every TDD completion.

### Changed
- `/feature-dev:spec` Stop hook now lists `/feature-dev:spec-review` as an optional next step.
- `/feature-dev:spec` Phase 4 handoff text updated to include `spec-review` in the next-step parenthetical.
- `/feature-dev:spec` now adds `SPEC-*.md` to the project's `.gitignore` (new Phase 1 step 6, mirroring the existing `/feature-dev:explore-plan` behavior for `PLAN-*.md`). Closes the `git add .` loophole that previously let SPEC files be committed accidentally despite the documented "local artifact" convention.
- `/feature-dev:explore-plan` Stop hook now lists `/feature-dev:plan-review` as an optional next step.
- `/feature-dev:spec-review` and `/feature-dev:plan-review` rules now explicitly state that SPEC/PLAN files are local working artifacts and must not be committed.

## 1.8.0 (2026-04-17)

### Added
- `/feature-dev:spec` Phase 1 now detects multi-repo scope when the feature description spans concerns owned by different repos AND either `additionalDirectories` (`.claude/settings.local.json`) or a parent-directory `CLAUDE.md` catalog corroborates sibling-repo access. The inferred repo set is folded into the step's assumption list for a single user confirmation round-trip.
- Spec frontmatter gains an optional `repos:` block (name, path, role: `owns-contract` | `consumes-contract`) that declares which repositories are in scope — single-repo features omit it, no behavior change
- Spec body gains a **Cross-Repo Contracts** section (endpoint, request/response shape, error codes, breaking-change flag) for multi-repo features so the API contract is written down before tasks are broken out
- Tasks in multi-repo specs are tagged with `Repo:` and ordered so contract-owning repo tasks land before contract-consuming repo tasks
- `spec-driven-development` skill documents the multi-repo detection signals and per-repo spec structure

## 1.7.1 (2026-04-17)

### Changed
- `/feature-dev:spec` Phase 4 clarifies that `SPEC-*.md` is a local working artifact, not committed to the repo. Explicitly forbids git commands and defers next-step choice to the Stop hook.

## 1.7.0 (2026-04-17)

### Added
- `/feature-dev:spec` now emits required YAML frontmatter (`type`, `feature`, `slug`, `date`, `branch`, `status`) on `SPEC-*.md` files so downstream commands can auto-discover them
- `/feature-dev:explore-plan` auto-discovers `SPEC-*.md` files when called without arguments (same 0/1/2+ pattern as tdd)
  - Filters out specs with `status: implemented` so shipped features don't re-surface
  - Warns when the only candidate is `status: draft` (not yet approved) before proceeding
  - Generated `PLAN-*.md` now records the `source_spec:` path and `slug:` for traceability from SPEC → PLAN → implementation
- `/feature-dev:tdd` closes the loop: on successful completion, updates the linked SPEC's `status:` to `implemented` before deleting the PLAN
- `/feature-dev:tdd` drift detection: warns when the source spec was modified after the plan was generated, so stale plans don't silently drive implementation

## 1.6.0 (2026-04-17)

### Added
- `/feature-dev:tdd` auto-discovers `PLAN-*.md` files when called without arguments
  - 0 plans → stop and ask for a feature description
  - 1 plan → auto-select and use its `feature:` frontmatter as the spec
  - 2+ plans → prompt user to pick one via AskUserQuestion
  - Supports the common workflow `/feature-dev:explore-plan` → clear context → `/feature-dev:tdd` without having to re-type the feature name

## 1.5.0 (2026-04-16)

### Changed
- Rewrote skill/command descriptions to contain only triggering conditions and boundaries, removing workflow step summaries that caused the model to shortcut skill bodies
- Added rationalization defense table to `tdd-patterns` skill
- Added SUBAGENT-STOP tags to `explore-plan`, `tdd`, and `spec` commands to prevent premature termination

## 1.4.1 (2026-04-13)

### Changed
- Upgrade `backend-explorer`, `frontend-explorer`, and `test-explorer` agents from haiku to sonnet for better codebase exploration quality

## 1.4.0 (2026-04-04)

### Added
- `spec` command: Spec-driven development with gated workflow (Specify → Plan → Tasks → Implement), assumption surfacing, and success criteria reframing
- `spec-driven-development` skill: Structured specification methodology with six-area spec template, anti-rationalization table, and living document practices

## 1.3.1 (2026-03-13)

### Fixed
- Remove all compound shell operators (`||`, `|`) from shell embeddings in `explore-plan` and `tdd` commands to fix "Bash command permission check failed" errors

## 1.3.0 (2026-03-13)

### Changed
- `explore-plan` now runs all exploration inside a forked general-purpose agent
  - 4 explorer subagents run inside the fork, keeping main conversation context clean
  - Fork writes `PLAN-<slug>.md` to disk, then its context is discarded
  - Main context only reads the saved plan file for user review
  - Eliminates context exhaustion that prevented running `tdd` after exploration
- Removed Write/Edit/Bash tools from `explore-plan` frontmatter (only the forked agent needs them)

## 1.2.1 (2026-03-13)

### Fixed
- `explore-plan` now explicitly prohibits `run_in_background` for parallel agents — background task outputs were expiring before being read, causing silent data loss

## 1.2.0 (2026-03-13)

### Added
- `explore-plan` now saves the implementation plan to `PLAN-<feature-slug>.md` (Phase 3)
- `tdd` now checks for `PLAN-*.md` and skips redundant exploration when a plan exists
- Plan file includes frontmatter (`type`, `feature`, `date`, `branch`) for identification
- `explore-plan` adds `PLAN-*.md` to `.gitignore` if not already present

### Changed
- `explore-plan` stop hook now suggests starting a new conversation for TDD to maximize context
- `tdd` Phase 1 is now "Load Plan or Explore Codebase" — uses saved plan when available, only does minimal test-infrastructure exploration
- `tdd` deletes the plan file after successful completion (cleanup)

## 1.1.1 (2026-03-13)

### Fixed
- Simplified `git remote` shell embedding in `explore-plan` and `tdd` commands to avoid `bwrap` sandbox errors (removed piped `sed` commands)

## 1.1.0 (2026-03-11)

### Added
- `backend-explorer` agent: Dedicated agent for backend/API layer exploration (models, views, serializers, endpoints)
- `frontend-explorer` agent: Dedicated agent for frontend/UI layer exploration (components, hooks, routing, state)
- `test-explorer` agent: Dedicated agent for test suite exploration (frameworks, fixtures, patterns, coverage)
- `history-explorer` agent: Dedicated agent for git history and open PR exploration (conflicts, patterns)
- `tdd-patterns` skill: Institutional knowledge for TDD workflows (iteration limits, coverage gates, phase constraints)
- Stop hooks on `explore-plan` and `tdd` commands for next-step guidance

### Changed
- `explore-plan` command now spawns named agents instead of inline Explore subagents
- `tdd` command now references `tdd-patterns` skill for consistent TDD constraints

## 1.0.0 (2026-03-11)

### Added
- `tdd` command: Test-driven feature development with RED-GREEN-REFACTOR cycle and coverage gates
- `explore-plan` command: Parallel 4-agent codebase exploration with synthesized implementation plan
