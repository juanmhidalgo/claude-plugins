# Changelog

All notable changes to this project will be documented in this file.

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
