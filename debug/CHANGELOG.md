# Changelog

## [1.1.1] - 2026-05-06

### Changed
- Trimmed `debugging-strategies` skill description to fit Claude Code's skill-listing budget.

## [1.1.0] - 2026-04-16

### Changed
- Rewrote skill/command descriptions to contain only triggering conditions and boundaries, removing workflow step summaries that caused the model to shortcut skill bodies

## [1.0.0] - 2026-04-04

### Added

- `debug` command: Systematic 6-step debugging workflow with Stop-the-Line Rule and regression guard enforcement
- `triage` command: Quick error classification with decision trees for test, build, and runtime failures
- `debugging-strategies` skill: Structured triage methodology, error output safety rules, anti-rationalization table
- Reference: Error patterns for test failures, build errors, runtime issues, non-reproducible bugs, and git bisect
