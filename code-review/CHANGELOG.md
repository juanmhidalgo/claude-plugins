# Changelog

All notable changes to this plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.2.0] - 2026-09-08

### Added
- **Verification in `/code-review:branch` and `:staged`, gated on effort level.** At `high` and `max` each finding is now verified by a `finding-verifier` before it reaches the user; `low` and `medium` are unchanged and still present the reviewer's output directly. Those two levels are the fast pre-commit gate, and a verifier costs roughly what the review that produced the finding cost — four findings means four more agents, which is exactly the price `low`/`medium` decline to pay.
- **`references/verification.md` in the `branch-review` skill** — one definition of what happens between a reviewer producing findings and a user reading them: dispatch shape, verdict handling, the empty-refutation and silent-verifier rules, the two pre-presentation checks, carrying the refutation, and no silent drops. `:branch`, `:staged`, `:pr`, `:staged-pipeline` and `:receive` now reference it instead of restating it, and each declares `branch-review` in `skills:` so the chain actually loads. `:tech-debt` keeps its inline copy on purpose: its findings have a different shape, and loading a skill with a competing format would bleed the wrong rubric into it.

### Changed
- `:pr`, `:staged-pipeline` and `:receive` verify at **every** level, and now say why they differ from `:branch`/`:staged`: `:pr` merges up to five dimensions that never read each other, `:staged-pipeline` turns findings into file edits in the next phase, and verifying is the whole job of `:receive`.

### Why
Two field runs settled this. Both times a `:branch` or `:staged` report was passed by hand to `:receive`, and both times verification changed the result materially — it corrected an exception type the finding had named wrongly (the suggested fix would not have caught it), checked and eliminated an obvious refutation the reviewer had not considered, caught that a naive fix would break behavior a code comment documented as deliberate, and found a sibling instance of the same defect elsewhere in the tree. Two for two, on reports that were otherwise good.

That manual step was the design telling us something. Three of five review paths already verified; `:branch` and `:staged` fell back to the reviewer critiquing its own finding, which this plugin's own 2.20.0 entry calls the weaker option.

The gate is the effort level rather than the command because the level already means this. At `high`/`max` the reviewer surfaces findings it *could not confirm* — and shipping those straight to the user handed the verification burden to the human at precisely the level that was supposed to buy more certainty. That was backwards.

## [3.1.0] - 2026-09-08

### Added
- **Evidence provenance rule.** Every review agent is read-only, and now says so about its own claims: evidence is labeled `[read]` (a file opened, `path:line` cited) or `[derived]` (reasoned from reads), and claiming execution is forbidden in any phrasing — no "Reproduced", no test counts, no linter output, no quoted `AssertionError`, no exit codes. A probe worth running is written in the subjunctive and marked *(not run)*. Stated as an Iron Law with a rationalization table in the `branch-review` skill and inlined in all ten finding-producing agents, because safety text must not depend on a skill load.
- **`Effort:` line in the accounting block**, required. Without it `Dropped: 6` is uninterpretable — at `low` a drop can mean "outside reporting range", at `max` it can only mean "refuted". Drops caused by the level must say so.
- **Refutation and counter-case carried into the distilled output.** Each confirmed finding presented by `:receive`, `:pr` and `:staged-pipeline` now carries one line of the verifier's refutation attempt; `:branch`, `:staged` and `:tech-debt` carry one line of the reviewer's counter-case. Both fields already existed and were already mandatory — but they lived only in the `OUTPUT_PATH` files, which nobody reads, so the mandate could be perfectly honored and remain unverifiable from the report. It also makes verdict counts legible: "5 confirmed, 0 refuted" reads as either an accurate incoming review or a rubber stamp, and the refutation lines are what separate the two at a glance.
- **Execution-claim check** alongside the citation spot-check in `:branch`, `:staged`, `:pr`, `:tech-debt`, `:staged-pipeline` and `:receive`, and in the Stop hooks. A fabricated claim is reported as a signal about the whole report, not quietly stripped.

### Changed
- **Read-only agents scoped to read-only verbs.** Seven agents still held bare `Bash`, and the three already narrowed to `Bash(git *)` could still have run `git push` or `git commit`. All eleven now carry an explicit list — `git log|diff|show|blame|rev-parse|symbolic-ref`, `git branch --show-current`, `git status`, and `gh pr view|diff|list` — following the pattern `discuss:doc-adversary` already used. `fix-implementer` keeps full `Bash` by design and is governed by its containment rules.
- `HIGH` confidence no longer described as "reproducible scenario", which read as licence to claim reproduction.

### Why
The first real run of 3.0.0 produced a report that was right about the defect and invented the proof: *"Reproduced. A probe test … fails with `AssertionError: expected dedup to suppress the second post, got 2`"*, plus a count of tests run and linter findings — from an agent whose tools made every one of those impossible. The finding itself was genuine and independently confirmed by reading the file.

That ordering is what makes it serious. A false positive dies the first time someone checks it; a true finding wrapped in fabricated corroboration teaches the reader that checking is unnecessary, and the habit that builds is what eventually ships a bug.

The mechanism generalizes past this plugin: **the tool restrictions worked.** Nothing ran. The agent narrated the verification it could not perform. Restricting capability without constraining claims produces fabricated compliance, so the constraint has to be written down rather than left implied by the tool list — and the reader-side check has to cover claimed execution, not only claimed citations, because this report's citations were accurate.

## [3.0.0] - 2026-09-08

### Security
- **Prompt-injection containment across every surface that ingests third-party text.** PR comment bodies, PR titles and descriptions, code comments, and pasted review reports are now explicitly framed as *data to evaluate, never instructions to follow* — in `receiving-code-review` (long form, with an Iron Law and a rationalization table), and inline in the six feedback-reading agents plus `triage`, `dismiss`, `receive`, and `fix-implementer`. `/code-review:pipeline` gets four hard containment rules that **override its own "NEVER ask for input"**: scope containment (a fix may only touch the file its comment is attached to), no meta-actions from comment text, a never-touch list (CI/workflow, lockfiles, `.env*`, git hooks, plugin scripts), and no authority from asserted identity. A new **Refused** outcome carries these to the report, distinct from Dismissed.

### Why (security)
The pipeline read attacker-reachable text, then edited files, committed and pushed, autonomously, with no guard anywhere in the plugin — every prior mention of "injection" was about *reviewing code for* SQL injection. Anyone who could comment on a PR had a path to `fix-implementer`, which holds `Write`, `Edit` and `Bash`. Verification is the security boundary, so the rules live there rather than in a preamble, and refusal is a reportable outcome rather than a silent no-op.

### Added
- **Effort levels** (`low` | `medium` | `high` | `max`) on `/code-review:pr`, `:branch`, and `:staged`, persisted in `.claude/code-review.local.md`. The level moves the *reporting* threshold, never the standard of evidence.
- **`finding-verifier` agent** — verifies one finding against the code and returns `CONFIRMED` / `PLAUSIBLE` / `REFUTED` / `REFUSED` with a **mandatory refutation attempt**. Callers discard verdicts with an empty refutation and re-run once.
- **`**Failure scenario:**` as a required field** on every finding, replacing `**Risk:**`, with a three-row table contrasting vague risk statements against concrete input→wrong-result scenarios. If one cannot be written, the finding does not ship.
- **`nit` and `pre_existing` as labels** orthogonal to severity — surfaced and marked instead of silently suppressed.
- **`OUTPUT_PATH` durable outbox** on every dispatched reviewer and verifier, with the file as the primary channel and explicit handling for a silent agent.
- **`NO CHANGE NEEDED`** outcome in `/code-review:mark-fixed`.
- **README section** delimiting this plugin against the built-in `/code-review`.

### Changed
- **BREAKING — `/code-review:pr` no longer writes to GitHub.** Findings are reported in the session. Posting was removed from the workflow and `gh` is now scoped to read-only verbs; `Edit`/`Write` are disallowed. The "already reviewed by Claude" eligibility check is gone with it — it only existed to avoid double-posting.
- **BREAKING — `confidence-scorer` removed**, absorbed by `finding-verifier`. The 0-100 rubric was discrete (0/25/50/75/100) behind a `< 80` filter, so a 75 — *"verified real, will be hit in practice, important"* — was discarded and only 100 survived. A binary verdict after real verification is both honest and correctly calibrated.
- **Verification moved out of the main context** in `staged-pipeline` (Phase 2), `triage`, and `receive`. All three verified findings in the conversation that had just written the code.
- `:branch` and `:staged` repositioned around their actual differentiator — a reviewer that has not seen this conversation — with an Iron Law against inline review and a "pass scope, not content" dispatch rule.
- Analysis-focus and output-format blocks deduplicated: the `branch-review` skill is now the single source of truth. The four copies had already drifted (the commands never picked up Confidence or Counter-case).
- `disable-model-invocation: true` on `:dismiss` and `:resolve-fixed` (both write to GitHub).
- Read-only agents scoped from bare `Bash` to `Bash(git *)` / `Bash(gh pr diff|view *)`; `disallowed-tools` on the read-only review commands.
- Removed `background: true` from `comment-verifier` and `fix-implementer` — a deliberate design choice, not a compatibility fix. The field *is* supported for plugin agents; it is dropped because both agents are consumed synchronously (the pipeline needs every verdict before Phase 2, and every fix before Phase 5), and a backgrounded agent hands back a task id instead of a result. `OUTPUT_PATH` makes the report durable; it does not make a detached agent finish sooner.
- **`bug-scanner` no longer instructed to stay shallow.** Depth now scales with the effort level, from "the diff plus what it calls directly" at `low` to "follow the data path until each candidate is confirmed or refuted" at `high`/`max`. Paired with a verification gate, a scanner told to avoid context produced candidates too thin to survive it — the two filters compounded into a path tuned to report almost nothing.
- Silent drops eliminated throughout: every path now reports an explicit count, and `No findings.` must carry an accounting of what was examined.

### Why
Two findings drove this release. First, dispatch: the plugin already ran finding *generation* in fresh subagents, but ran *verification* — the step its own critical rule calls load-bearing — in the context that wrote the code, which is the context least able to read a finding as a stranger would. Second, calibration: the confidence gate was arithmetically unable to pass anything but certainty, while `bug-scanner` was instructed to stay shallow, so the PR path was tuned to find almost nothing and said so nowhere.

The `OUTPUT_PATH` pattern is borrowed from `discuss:adversarial-doc-review`, which learned it the hard way: an Agent call may return async regardless of how it is invoked, and a report that never arrives is indistinguishable from a review that found nothing. That was verified against the built-in `/code-review`, which runs forked and in the background and returns prose rather than structured findings — which is also why delegating to it was rejected: forked execution inherits the caller's context, and measured ~50k tokens per call before doing any work.

## [2.20.0] - 2026-07-20

### Added
- **Counter-case (bias check) in the `tech-debt-reviewer` agent.** Every debt finding now requires the strongest opposing reading — the case that the pattern is a deliberate design choice — written before scoring. It feeds the existing **Impact (I)** term of the priority computation rather than adding a parallel field: an unconfirmed-but-nameable design intent caps I at 3; a counter-case that reads the code better drops the finding. Adds a `**Counter-case:**` line to the finding format, and calls out two specific traps (flagging look-alike code that changes for different reasons, and flagging a "missing" abstraction where repetition was chosen on purpose).
- **Counter-case (bias check) on every finding** in the `branch-review` skill. Each finding now requires an explicit argument against itself — the strongest case that it is a false positive, a deliberate design choice, or an inapplicable edge case — written *before* the Confidence label is assigned. A new `**Counter-case:**` field in the Feedback Format carries it, and a calibration table binds it to the existing Confidence levels: no plausible counter-case → HIGH; a counter-case resting on unverified context → MEDIUM at most; a counter-case as strong as the finding → LOW or drop it. Propagates to `/code-review:staged`, `/code-review:branch`, and `/code-review:pr` via the shared `branch-reviewer` agent.

### Why
The plugin already verifies findings adversarially, but only in the PR pipeline (`confidence-scorer`, `comment-verifier`). The staged and branch paths emitted findings with no refutation pass at all. Self-critique within a single generation is weaker than a separate verifier agent, so it is deliberately *not* added where those agents already run — that would be redundant token cost. The calibration table exists because an unbound bias check degrades into a token counter-argument that leaves Confidence untouched; requiring the label to move makes the output change, not just grow.

## [2.19.3] - 2026-05-27

### Added
- `disallowed-tools: [Edit, Write, NotebookEdit]` on `coverage-gate` and `technical-decisions` skills. Both are read-only by intent; the new Claude Code 2.1.152 frontmatter field enforces this at the runtime level, preventing accidental writes when the skill is active.

## [2.19.2] - 2026-05-13

### Changed
- **`comment-verifier` agent**: promoted from `haiku` to `sonnet`. The agent verifies AI-generated review comments against actual code and returns `VALID BUG` or `FALSE POSITIVE` — a misclassification at this stage propagates false positives to the human reviewer or dismisses real bugs. The CLAUDE.md principle "AI feedback is NOT valid by default" requires verification depth that haiku does not reliably provide.

## [2.19.1] - 2026-05-12

### Fixed
- Removed unsupported `permissionMode: default` from `branch-reviewer` and `pr-feedback-analyst` agents — plugin sub-agents do not support this field; it is silently ignored.
- Removed unsupported `hooks:` blocks from `bug-scanner`, `pr-eligibility-checker`, `pr-summarizer`, and `confidence-scorer` agents — plugin sub-agents do not support hooks; the echo statements were cosmetic and never executed.

### Why
Aligns agent definitions with the Claude Code sub-agent specification. Unsupported frontmatter fields add noise and can mislead future editors into thinking the hooks or permission mode are active.

## [2.19.0] - 2026-05-07

### Changed
- Split `/code-review:pipeline` (248 → 119 lines) into a workflow-narrative core plus `pipeline.references/phase-details.md` for autonomous-mode rules, per-phase details, and report templates. Progressive disclosure per Claude Code best practices.
- Added `Do NOT use for…` boundary clauses to four commands' descriptions: `/code-review:branch`, `/code-review:staged`, `/code-review:triage`, `/code-review:mark-fixed`.

### Added
- Future-direction note in `pipeline.references/phase-details.md` documenting the agent-teams migration path for parallel verifiers and parallel fix-implementers (deferred — Anthropic agent-teams are still experimental).

### Why
Aligns with Anthropic's official Claude Code best practices: "Description = triggering conditions only" (boundaries) and progressive disclosure (split overlong commands into core + references). No behavior changes.

## [2.18.0] - 2026-05-06

### Added
- **Prioritization Formula** in `tech-debt-reviewer` agent: `Priority = (Impact + Risk) × (6 − Effort)`. Each finding now scores Impact/Risk/Effort on a 1-5 scale, computes a numeric priority, and the output is sorted by priority descending. New action thresholds (≥30 BLOCKING, 15-29 SIGNIFICANT, 5-14 MINOR, <5 NOTE) replace vibes-based ordering.

### Why
Borrowed from Anthropic's `engineering:tech-debt` skill. The formula rewards high-impact / high-risk debt that is *cheap* to fix (5/5/1 scores 50) vs. expensive (5/5/5 scores only 10). Defensible numeric ranking surfaces the easy big wins that vibes-based ordering tends to bury under loud-but-expensive items.

## [2.17.0] - 2026-05-06

### Changed
- `branch-review` Focus Areas now delegate Security and Performance depth to sibling plugins: deeper threat-modeling and OWASP analysis go to **`security:security-hardening`**; load profiling and Core Web Vitals go to **`performance:performance-optimization`**. Branch review surfaces the concern; the specialized skills handle the diagnosis. Avoids duplicating their content here.
- `tech-debt-reviewer` agent now points at the **`refactor`** plugin (`/refactor:analyze`, `/refactor:plan`, `/refactor:extract`) for acting on findings, instead of describing refactoring inline. Cleaner separation: this agent identifies debt, refactor acts on it.

### Why
Borrowed from Anthropic's `engineering` plugin: `architecture` delegates depth to `system-design` rather than duplicating. Cross-skill delegation keeps individual skills thin and composable, and prevents drift between plugins that cover overlapping ground.

## [2.16.0] - 2026-05-06

### Added
- **Confidence Classification** in `branch-review` skill — orthogonal dimension to the existing Severity (which answers "should this block merge?"). Confidence answers "how strong is the evidence?": HIGH (verified by reading the code path; cited file:line, observable behavior), MEDIUM (strong inference from patterns; needs runtime confirmation), LOW (speculation or pattern-based concern). Feedback Format updated to require both labels (`**[SEVERITY] · [CONFIDENCE]**`) and adds an `Evidence:` field. Distinguishes "this *might* be a security bug" from "this *is* a security bug" — they need different responses.

### Why
Borrowed from Anthropic's `synthesize-research` skill. Severity alone collapses two distinct judgments (is this bad? is this real?) into one label, which lets weak evidence get treated as confirmed bugs. Pairing severity with confidence prevents over-claiming on speculation and under-reacting on verified critical issues.

## [2.15.1] - 2026-05-06

### Changed
- Trimmed `tech-debt` and `receive` command descriptions and `branch-review` and `receiving-code-review` skill descriptions to fit Claude Code's skill-listing budget.

## [2.15.0] - 2026-04-17

### Added
- `/code-review:tech-debt` pre-flight check for base branch staleness in branch-comparison scope
  - Detects when the local base branch is behind its remote tracking ref and warns the user before analyzing
  - Prevents false tech-debt findings from already-merged upstream commits appearing in the diff
  - Never auto-fetches or auto-pulls — user is prompted to decide

## [2.14.0] - 2026-04-16

### Changed
- Rewrote skill/command descriptions to contain only triggering conditions and boundaries, removing workflow step summaries that caused the model to shortcut skill bodies
- Added rationalization defense tables to `receiving-code-review`, `technical-decisions`, and `coverage-gate` skills, and to the `triage` command
- Added SUBAGENT-STOP tags to `pipeline`, `staged-pipeline`, `implement-fix`, and `receive` commands to prevent premature termination

## [2.13.0] - 2026-04-08

### Added
- **Enhanced tech debt analysis** with new verdict system and expanded coverage
  - New verdict levels: CLEAN / MINOR DEBT / SIGNIFICANT DEBT / BLOCKING DEBT (replaces simple HIGH/MEDIUM/LOW)
  - New analysis category: **Dependencies & Infrastructure** — flags new deps, unpinned versions, ad-hoc reimplementation of shared patterns, undocumented config changes
  - **Positive Patterns** section in output — highlights what's done well, not just problems
  - **Staged scope support** — `/code-review:tech-debt staged` analyzes staged changes; auto-detects scope when no argument is provided
  - Verdict decision rules for consistent classification across reviews
- Discoverability hooks: `/code-review:staged` and `/code-review:branch` now suggest `/code-review:tech-debt` in their Stop hooks

## [2.12.2] - 2026-04-08

### Added
- Lint scoping guard in `/code-review:pipeline` Phase 4 — after fixes are applied, detects and resets unrelated files modified by pre-commit hooks or auto-formatters
- Added autonomous rule: "Linter changed unrelated files → reset them, log in report"
- Prevents cascading lint changes from polluting fix commits (addresses recurring friction from 4+ sessions)

## [2.12.1] - 2026-03-30

### Fixed
- `/code-review:pipeline` now skips Phases 5-7 (tests, commit, push, resolve) when all comments are false positives and no code changes were made
- `/code-review:staged-pipeline` now skips Phases 3-5 (approve, fix, test) when all findings are dropped as incorrect
- Added explicit early-exit guards at each phase boundary to prevent unnecessary test runs on unchanged code

## [2.12.0] - 2026-03-20

### Added
- **Coverage gate** — detect CI coverage thresholds locally and prevent push failures
  - `/code-review:coverage-gate [base]` — standalone command to check coverage against GHA-configured thresholds before pushing
  - Supports `orgoro/coverage`, `irongut/CodeCoverageReport`, `5monkeys/cobertura-action`, and `codecov/codecov-action`
  - Detects per-category thresholds (new files, modified files, overall) from `.github/workflows/*.yml`
  - Runs coverage locally, categorizes changed files, checks against thresholds
  - Writes additional tests to fix coverage gaps (up to 2 cycles)
- `coverage-gate` skill — institutional knowledge for GHA coverage detection and threshold verification
  - Progressive disclosure: core patterns in SKILL.md, detailed action patterns in `references/gha-patterns.md`

### Changed
- `/code-review:pipeline` now includes **Phase 5b: Coverage Gate** between test and commit phases
  - Detects GHA coverage config and checks per-file coverage before pushing
  - Writes tests to fix coverage gaps (up to 2 cycles), stops if still below threshold
  - Added coverage status to final report (PASS/FAIL/SKIPPED)
  - Added autonomous rules: "Coverage below threshold → write tests, then STOP"
- `/code-review:staged-pipeline` now includes **Phase 5b: Coverage Gate** between test and stage phases
  - Same detection and verification logic adapted for staged changes context
  - Added coverage status to final report

## [2.11.1] - 2026-03-13

### Fixed
- Remove all compound shell operators (`||`, `|`, `&&`) from shell embeddings across commands (`dismiss`, `resolve-fixed`, `pipeline`, `pr`, `triage`, `staged`, `staged-pipeline`, `mark-fixed`, `fixes-plan`) to fix "Bash command permission check failed" errors
- Replace compound grep/test file-finding embeddings with static text (agent can find files dynamically)

## [2.11.0] - 2026-03-13

### Added
- `/code-review:staged-pipeline` — single-session review-verify-fix pipeline for staged changes
  - Runs review in forked context (preserves main context for verification and fixes)
  - Self-verifies findings against actual code (drops false positives)
  - Enters plan mode for user approval before implementing
  - Parallel `fix-implementer` agents for independent fixes
  - Runs test suite with retry, stages fixed files
  - No intermediate files — everything stays in conversation context
  - Replaces 3-session workflow (`staged` → `receive` → implement) with a single command

## [2.10.1] - 2026-03-13

### Fixed
- Simplified `git remote` shell embedding in `triage`, `pr`, `pipeline`, `resolve-fixed`, and `dismiss` commands to avoid `bwrap` sandbox errors (removed piped `sed` commands)

## [2.10.0] - 2026-03-11

### Changed
- Renamed `Task` to `Agent` tool in all commands (following Claude Code v2.1.63 rename)
- Updated `/code-review:branch` hook to suggest `/code-review:pipeline` as next step

### Improved
- Cross-plugin workflow suggestions in Stop hooks

## [2.9.0] - 2026-03-11

### Added
- `/code-review:pipeline PR#` - Autonomous PR review-fix-ship pipeline
  - Triages all bot/reviewer comments against actual code
  - Dismisses false positives with one-line justifications
  - Implements valid fixes with parallel subagents (independent fixes run concurrently)
  - Runs full test suite with up to 2 retry attempts on failure
  - Commits with structured message referencing each resolved comment
  - Pushes and resolves all GitHub threads in one pass
  - Fully autonomous: only stops if tests fail after retries
- `comment-verifier` agent - Haiku agent for parallel comment verification during triage
  - Read-only tools (Read, Grep, Glob) — cannot modify code
  - Background execution with 15-turn cap
  - Preloads `receiving-code-review` skill for skeptical verification
  - Returns structured verdict: VALID BUG or FALSE POSITIVE with evidence
- `fix-implementer` agent - Dedicated Sonnet agent for parallel fix implementation
  - Background execution with 25-turn cap to prevent runaway agents
  - Focused tool access (Read, Write, Edit, Grep, Glob, Bash)
  - Minimal-diff approach: fixes only the described issue

## [2.8.0] - 2026-03-10

### Added
- `/code-review:receive` - Process code review feedback from another session with verification
  - Parses findings from pasted review reports
  - Verifies each finding against actual code (confirmed / stale / incorrect / disputed)
  - Enters plan mode before any implementation
  - Connects to existing `/code-review:fixes-plan` → `/code-review:implement-fix` pipeline
  - Uses `receiving-code-review` skill for verification principles

## [2.7.0] - 2026-01-26

### Optimized
- Reduced `branch-review` skill from 162 to 75 lines (-54%)
  - Removed generic git commands section (Claude already knows these)
  - Condensed checklists into compact "Focus Areas" section
  - Improved description with "when to use" and "when NOT to use"
  - Kept institutional content: severity classification, feedback format, anti-patterns

## [2.6.1] - 2026-01-26

### Fixed
- Removed complex shell command with pipes/operators from `/code-review:implement-fix` that was causing Bash permission check failures
- Fixes file discovery is now handled dynamically by the agent instead of embedded in the command frontmatter

## [2.6.0] - 2026-01-24

### Removed
- Removed `claudemd-discoverer` agent - redundant since Claude Code auto-loads CLAUDE.md files

### Changed
- `/code-review:pr` Step 2 now uses simple Glob instead of dedicated agent
- Reduces latency and API calls in PR review workflow

## [2.5.0] - 2026-01-24

### Changed
- Refactored 3 skills with progressive disclosure pattern:
  - `receiving-code-review`: 220 → ~140 lines, examples moved to `references/examples.md`
  - `technical-decisions`: 209 → ~135 lines, examples moved to `references/examples.md`
  - `review-fixes-plan`: 205 → ~100 lines, template moved to `references/template.md`

### Improved
- Token efficiency: Core instructions load fast, detailed content on-demand
- Follows Anthropic's recommended skill structure from Skills documentation update

## [2.4.0] - 2026-01-23

### Added
- Added `hooks` to `/code-review:triage` command for next step guidance
- Added shell embedding to `/code-review:pr` command for repository and branch context

### Changed
- Generalized `receiving-code-review` skill by replacing personalized "your human partner" with neutral "team lead"
- Improved skill reusability across different team contexts

## [2.3.0] - 2026-01-16

### Added
- `/code-review:tech-debt [base]` - Analyze branch changes for technical debt before merging
- `tech-debt-reviewer` agent - Specialized agent for identifying maintainability issues
- Analyzes: complexity, duplication, debt markers (TODO/FIXME), test gaps, code smells

## [2.2.2] - 2026-01-16

### Fixed
- Removed complex shell commands with pipes from `/code-review:branch` that were causing Bash permission check failures
- Shell commands like `git symbolic-ref ... | sed ...` are now handled dynamically by the agent instead of embedded in the command frontmatter

## [2.2.0] - 2026-01-15

### Added
- Added `keywords` and `triggers` fields to all commands and skills for improved discoverability
- Commands now include semantic keywords for search and natural language triggers for intent matching
- Skills updated with structured triggers (moved from prose descriptions)
- Plugin-level triggers added to plugin.json

### Changed
- Skill descriptions simplified (triggers moved to dedicated field)

## [2.1.1] - 2026-01-08

### Fixed
- Corrected agent hooks to use only officially documented variables
- Simplified hook commands to static messages (removed undocumented `$output` variable usage)
- All hooks now comply with official Claude Code hook specification

## [2.1.0] - 2026-01-08

### Changed
- Refactored all commands to use YAML-style lists for `allowed-tools` for better readability
- Implemented wildcard patterns in bash permissions (e.g., `Bash(git *)`, `Bash(gh *)`) to reduce permission prompts
- Updated all command frontmatter to use modern YAML list syntax
- Added `${CLAUDE_PLUGIN_ROOT}/scripts/*` wildcard for script permissions

### Added
- Added hooks to commands for better user guidance:
  - `/pr` now shows next steps after completion
  - `/staged` and `/branch` suggest follow-up commands
- Added hooks to agents for automatic feedback:
  - `bug-scanner` reports issue count on completion
  - `pr-eligibility-checker` shows eligibility status
  - `confidence-scorer` displays confidence levels with visual indicators
  - `pr-summarizer` shows PR type and file count
- Added `agent` field to `branch-review` skill to ensure proper routing to `code-review:branch-reviewer`
- Added `user-invocable: true` to skills that are useful as direct slash commands:
  - `branch-review`
  - `technical-decisions`
  - `receiving-code-review`
  - `review-fixes-plan`

### Improved
- Skills now support hot-reload (changes take effect immediately)
- Better permission handling with wildcard patterns reduces unnecessary prompts

## [2.0.0] - 2025-12-16

### Added
- `/code-review:pr <PR>` - Comprehensive multi-agent PR review workflow inspired by Anthropic's approach
- New specialized agents for parallel review:
  - `pr-eligibility-checker` (Haiku) - Validates PR is reviewable (not draft/closed/bot/trivial)
  - `claudemd-discoverer` (Haiku) - Finds relevant CLAUDE.md files in affected directories
  - `pr-summarizer` (Haiku) - Generates PR change summary
  - `claudemd-compliance-reviewer` (Sonnet) - Audits changes against CLAUDE.md guidelines
  - `bug-scanner` (Sonnet) - Shallow scan for obvious bugs in diff
  - `git-history-reviewer` (Sonnet) - Analyzes git blame/history for context
  - `pr-comments-reviewer` (Sonnet) - Checks previous PR comments that may apply
  - `code-comments-reviewer` (Sonnet) - Verifies compliance with code comment guidance
  - `confidence-scorer` (Haiku) - Scores issues 0-100 to filter false positives
- Confidence scoring system with explicit rubric (0-100 scale, threshold 80)
- Automatic false positive filtering based on:
  - Pre-existing issues
  - Linter/compiler-catchable issues
  - Pedantic nitpicks
  - Issues on unmodified lines
  - Intentionally silenced issues (lint ignore)

### Fixed
- Fixed `branch-reviewer` agent type reference to use namespaced format `code-review:branch-reviewer` in `/code-review:branch` and `/code-review:staged` commands (was causing "Agent type 'branch-reviewer' not found" error)

## [1.3.0] - 2025-12-07

### Changed
- `/code-review:triage` now includes human comments by default (previously only showed bot comments)
- Script option changed from `include_humans` (default: false) to `bots_only` (default: false)

### Fixed
- Added `per_page=100` to GitHub API calls to fetch all comments (was missing comments when PR had more than 30)

## [1.2.2] - 2025-12-07

### Fixed
- Fixed `pr-triage-comments.sh` script to pipe `gh api` output to `jq` instead of using `gh api --jq --arg` which is not supported by `gh` CLI (was causing "accepts 1 arg(s), received 4" error)

## [1.2.1] - 2025-12-07

### Fixed
- Fixed script paths in commands to use `${CLAUDE_PLUGIN_ROOT}` instead of hardcoded `~/.claude/plugins/code-review/scripts/` path, which was causing "no such file or directory" errors

## [1.2.0] - 2025-12-06

### Added
- `/code-review:resolve-fixed PR#` - Resolve GitHub threads for issues marked as fixed in REVIEW_FIXES.md

### Changed
- `review-fixes-plan` skill now includes `**GitHub:** ref_id` field to link issues to PR comments
- Updated workflow documentation to include resolve-fixed step

## [1.1.0] - 2025-12-06

### Added
- `/code-review:implement-fix [issue-number | "all"]` - Implement fixes from REVIEW_FIXES.md with technical decision prompts
- `technical-decisions` skill - Guidelines for asking about technical decisions before implementing fixes

## [1.0.0] - 2025-12-06

### Added
- `/code-review:branch [base]` - Review current branch vs base branch
- `/code-review:staged` - Review staged changes before committing
- `/code-review:triage PR#` - Triage AI reviewer feedback on PRs
- `/code-review:dismiss PR#` - Dismiss false positive comments on GitHub
- `/code-review:fixes-plan` - Generate REVIEW_FIXES.md tracking document
- `/code-review:mark-fixed` - Verify and mark issues as fixed
