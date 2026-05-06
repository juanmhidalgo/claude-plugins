# Changelog

## [1.2.0] - 2026-05-06

### Added
- **Confidence labeling** on each substantive claim from external AIs. Step 4 now classifies every concern, recommendation, or claim as HIGH (cited specific code, named function/line, or pointed to evidence in the diff), MEDIUM (defensible argument from general principles without specifics), or LOW (hedging, speculating, or applying generic best practices without grounding). Format: `**[CONFIDENCE]** *external AI's claim* — Your assessment: *agree / partial / disagree*`. A LOW-confidence external opinion is a starting point for investigation; a HIGH-confidence one that contradicts your own analysis warrants a closer look.

### Why
Borrowed from Anthropic's `synthesize-research` skill. External AIs vary widely in how grounded their feedback is — some cite specific code, others apply generic best practices to a vacuum. Labeling each claim's evidence strength prevents users from giving equal weight to a confident-sounding but ungrounded recommendation.

## [1.1.1] - 2026-05-06

### Changed
- Trimmed `second-opinion` skill description to fit Claude Code's skill-listing budget.

## [1.1.0] - 2026-04-16

### Changed
- Rewrote skill/command descriptions to contain only triggering conditions and boundaries, removing workflow step summaries that caused the model to shortcut skill bodies

## [1.0.1] - 2026-02-17

### Fixed

- Eliminate temp file usage (`/tmp/second-opinion-*`) — prompts are now passed via heredoc directly to scripts, removing 2 unnecessary permission prompts per invocation

## [1.0.0] - 2026-02-17

### Added

- Initial release as marketplace plugin
- `ask-codex.sh` wrapper for OpenAI Codex CLI
- `ask-gemini.sh` wrapper for Google Gemini CLI
- `ask-copilot.sh` wrapper for GitHub Copilot CLI
- `ask-claude.sh` wrapper for Claude Code CLI
- `/second-opinion` skill with backend selection, context gathering, and secret redaction
- Support for reviewing staged changes, specific files, branches, and free-form questions
