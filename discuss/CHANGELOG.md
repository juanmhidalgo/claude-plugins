# Changelog

All notable changes to this project will be documented in this file.

## [2.9.0] - 2026-08-25

### Fixed
- **The reviewer's report could vanish on the way back.** `doc-adversary` had exactly one egress path — its final message — and no fallback, so any hiccup in delivery produced an agent that completed successfully and a dispatcher holding nothing. The failure is silent and, worse, actively misleading: this skill instructs the caller to treat "no findings" as suspicious, so a lost report reads as a clean bill of health. The agent now gets `Write` (scoped to `OUTPUT_PATH` only — it still never touches the repo or the document under review) and delivers the report **twice**: written to a scratchpad file the dispatcher chose, and returned as its final message. The skill reads the file and falls back to the returned text. Both empty means the review did not happen and must be re-run.
- **Dispatch shape was underspecified.** The skill said "use the Agent tool" without saying *how*. Spawned as a named or background agent, `doc-adversary` delivers through the messaging channel instead of the tool result, and the caller waits on an idle notification with nothing attached. The Dispatch section now says explicitly: plain blocking Agent call, no `name:`, no backgrounding — and one agent per document, never one agent for several, since the Phase 1 independent model is per-problem and merging documents merges their framing.

### Added
- **Re-run the review after fixes are applied.** The skill previously ended at "present the report, don't act on findings automatically", which left the highest-leverage step unstated. The fix round is written by someone who has just been told what was wrong and now believes they understand the problem — a worse starting position than the original authoring, not a better one. Edits are narrow, made under the framing of the findings, and nobody re-reads the whole document afterward. New section covers the mechanics: fresh dispatch with a new `OUTPUT_PATH`, same `MODE`, and — critically — **do not tell the reviewer it is a second pass or what the first round found**, which would be the strongest framing possible to transmit and would steer it past whatever the fix round broke. Bounded: stop when a round produces no HIGH or MEDIUM findings.

### Why
Field-tested on 6 technical documents across 3 repos before this release. The review quality held up — findings included a cross-tenant authorization hole that two prior research passes had missed, and no false positives or fabricated `path:line` citations were observed. What broke was delivery, not analysis, which is why the core design is untouched here.

The re-review addition comes from the same exercise: on a second pass over the edited documents, **three of seven findings were defects introduced by the fix round** rather than defects in the originals — two with real consequences, including a control silently dropped from a section that was only meant to be reworded. Nothing in the skill pointed at that, so it is now a named step with its own anti-framing rule.

## [2.8.0] - 2026-08-25

### Added
- **`adversarial-doc-review` skill + `doc-adversary` agent** — adversarial review of a technical document that exists as a *file* (PRD, ADR, spec, RFC, architecture doc), run in a fresh context. The reviewer has one question: will someone make a worse architecture/design/implementation decision because of what this document says or fails to say? Everything else — style, missing examples, uneven detail — is explicitly out of scope.
  - **Materiality gate**: a finding must name the affected decision, show the outcome would have differed, cost real work to reverse, and not self-correct in the first hour of implementation. Dropping a finding on that last point requires naming the specific test or check that would catch it, so it can't be used as a blanket escape hatch.
  - **Anti-anchoring procedure**: blind read → independent model built from code/domain *before* re-reading the doc → **vocabulary quarantine** (never grep the document's own nouns; every search must be capable of returning something that contradicts the doc) → falsification → self-falsification with a mandatory Steelman → verdict written last.
  - **Falsification log is the credibility floor**: zero findings is a valid outcome, but only when the report shows the attempts that failed with concrete grep patterns and `path:line`. No log means the honest answer is "I was unable to review this", not "no findings".
  - **Two modes**: `design` (decisions not yet built — materiality by cost of reversal) and `descriptive` (claims to describe an existing system — materiality also counts divergence from code). Both apply → run `descriptive` first.
  - Severity by cost of reversal, not indignation: HIGH touches persisted data, public contracts, or several modules; MEDIUM is contained to one module; cheaper than that goes unreported.

### Why
Fills a gap no existing plugin covered. `/feature-dev:spec-review` validates *structure and completeness* of SPEC/PLAN artifacts and states outright that it does not judge technical merit. `/prd:analyze` finds gaps in PRD-shaped requirements without an adversarial method. `/discuss:challenge` is the closest sibling but attacks a proposal *in conversation* and runs in the main context — which is exactly the framing contamination this skill exists to avoid. Nothing reviewed a written document, in a fresh context, filtered by decision-materiality and anchored in the code.

The skill is dispatch-only on purpose: the review depends on the reviewer building its own model of the problem before absorbing the document's framing, which is impossible in a context that already holds the document or the discussion that produced it. The skill passes the subagent **paths, never content**, and refuses to silently downgrade when subagents are unavailable.

Known limit, documented in the skill rather than hidden: on greenfield docs with no code to read, the independent model is domain-derived and the review degrades toward opinion — the agent must say so in its verdict and treat its own findings as one severity level less certain.

## [2.7.0] - 2026-07-20

### Added
- **Bias check on the recommendation** in `/discuss:tradeoffs`. Phase 4 now closes with a `<bias_check>` block requiring the strongest case for the runner-up option, plus what makes that case not hold here. Targets **anchoring**, not false positives — the option named first or described in most detail tends to win on framing rather than merit. If no real case for the runner-up exists, the command says so instead of manufacturing balance; if the runner-up's case is stronger, the recommendation changes.
- **Bias check on every risk** in `/discuss:feature`. Findings gain a `*Doesn't apply if:*` line stating the concrete condition under which the risk never materializes, and a new `<bias_check>` block binds that condition to the existing Confidence label: no such condition (or it contradicts Phase 1 exploration) → HIGH; a realistic but unconfirmed condition → MEDIUM at most; a condition likelier than the risk → LOW or cut it. Also routes dissolvable risks to the Phase 4 open-questions table — a risk that disappears on one user answer is a question, not a risk.

### Why
Extends the code-review counter-case pattern (`code-review` 2.20.0), with the framing adapted to the phase. Nothing in `/discuss:feature` is verifiable against an implementation yet, so asking "is this a false positive?" has no answer and invites filler; "what would have to be true for this never to happen?" is answerable from the proposal and the codebase. Complements the existing `Confirmation-biased risk ranking` anti-pattern, which addressed the *ordering* of the risk list but left each individual risk unchallenged.

Deliberately not added to `/discuss:challenge` — that command is adversarial by construction and has a blocking rule against being balanced, so a self-refutation section would cancel its purpose.

## [2.6.0] - 2026-05-13

### Added
- **`/discuss:feature` now runs on Opus** (`model: opus` in frontmatter). The command's deliverable — critical analysis with confidence-labeled gaps, risks, and counter-positions — is a reasoning-heavy task, distinct from the implementation-heavy work that sonnet handles well. Pre-setting the model on the command guarantees the analysis quality regardless of the caller's default.

### Fixed
- **`agent_type` → `subagent_type`** across all four commands in the plugin (`feature.md`, `brainstorm.md`, `tradeoffs.md`, `challenge.md`). The Agent tool's parameter is `subagent_type`; the prior wording could have led the model to pass an unrecognized parameter and fail the exploration step. In `feature.md` the fix covered three locations (Phase 1 instructions, the example call, and the blocking rule in `<critical_rules>`); the other three commands each had one occurrence in their Phase 1 exploration block.

## [2.5.0] - 2026-05-06

### Added
- **Confidence labeling** on findings in `/discuss:feature`. Phase 4 now requires every gap, risk, and red flag to be labeled HIGH (tied to specific code path / file:line from Phase 1 exploration), MEDIUM (plausible based on patterns or proposal structure), or LOW (speculative — depends on assumptions that may not hold). Format: `**[CONFIDENCE]** **Risk:** ... — *Evidence: file:line or "speculation only"*`. Calibrates the user's reaction so HIGH risks drive action and LOW risks don't get over-weighted.

### Why
Borrowed from Anthropic's `synthesize-research` skill. Without confidence labels, the model's analysis can mix evidenced concerns with speculative ones at equal weight, misleading the user about which risks are actually load-bearing.

## [2.4.0] - 2026-05-06

### Added
- **Common Discussion Mistakes** anti-pattern catalog in `/discuss:feature`. Names traps the model can fall into during analysis: solutioning before framing, anchoring on the first idea, feature-parity thinking, generic (untied-to-code) risks, confirmation-biased risk ranking, no counter-position, padded clarifying questions, internal-focus complaints. Each entry includes a one-line fix. Complements the existing **Rationalization Defenses** table (which catches boundary violations) — these catch *doing the analysis badly* rather than *bypassing the boundary*.

## [2.3.2] - 2026-05-06

### Changed
- `/discuss:tradeoffs` Stop hook and README workflow no longer reference the removed `/prd:create` command — both now suggest `/feature-dev:spec` for formalizing decisions.

## [2.3.1] - 2026-05-06

### Changed
- Trimmed `feature`, `brainstorm`, `tradeoffs`, and `challenge` command descriptions to fit Claude Code's skill-listing budget.

## [2.3.0] - 2026-04-17

### Changed
- `/discuss:feature` now hard-stops after analysis — added a blocking rule forbidding code, task creation, plan mode, or calling implementation skills after Phase 4
- Added Rationalization Defenses table covering the "user answered my questions, so now I can implement" failure mode
- Stop hook now recommends `/feature-dev:spec` as the single next step (replacing `/feature-dev:explore-plan` and `/prd:create`)

## [2.2.0] - 2026-04-16

### Changed
- Rewrote skill/command descriptions to contain only triggering conditions and boundaries, removing workflow step summaries that caused the model to shortcut skill bodies

## [2.1.0] - 2026-03-11

### Changed
- Renamed `Task` to `Agent` in `allowed-tools` across all 4 commands
- Replaced `Task tool` with `Agent tool` and `subagent_type` with `agent_type` in all command body text
- Updated cross-plugin hooks in all commands to suggest `/feature-dev:explore-plan` and `/prd:create` as next steps

## [2.0.0] - 2026-01-24

### Changed
- **BREAKING**: Renamed plugin from `discussion-toolkit` to `discuss`
- **BREAKING**: Renamed `/discuss` to `/discuss:feature`
- **BREAKING**: Renamed `/discuss:devils-advocate` to `/discuss:challenge`
- Commands now follow pattern: `/discuss:feature`, `/discuss:brainstorm`, `/discuss:tradeoffs`, `/discuss:challenge`

## [1.4.0] - 2026-01-24

### Changed
- Open questions now use actionable table format with impact and suggested defaults
- Simplified Stop hook - removed prescriptive next step suggestions

## [1.3.0] - 2026-01-24

### Changed
- Structured exploration framework with 4 dimensions: Entry Points, Related Code, Dependencies, Conventions
- Added file:line reference requirement in exploration output
- Improved Task tool prompt example for more actionable exploration

## [1.2.0] - 2026-01-24

### Changed
- `/discuss` description now emphasizes use for pre-implementation spec review
- Added plan mode check - warns user if running inside plan mode

## [1.1.0] - 2026-01-23

### Added
- `/discuss:brainstorm` command - Generate 4-6 alternative approaches to a problem
- `/discuss:devils-advocate` command - Argue against a proposal to stress-test it
- `/discuss:tradeoffs` command - Compare options with structured pros/cons matrix

## [1.0.0] - 2026-01-23

### Added
- Initial release of discussion-toolkit plugin
- `/discuss` command for critical feature discussion
- Skeptical Staff Engineer persona for idea refinement
- Four-phase workflow: Context Gathering, Clarification, Critical Analysis, Constructive Feedback
- Discoverability fields (keywords, triggers) for improved activation
- Stop hooks with next step guidance
- Clear Task tool usage instructions for Explore agent
