# Changelog

All notable changes to this project will be documented in this file.

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
