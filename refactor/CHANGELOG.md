# Changelog

## [1.3.0] - 2026-05-06

### Added
- **Priority scoring formula** in `/refactor:analyze` output: `Priority = (Impact + Risk) × (6 − Effort)` with each dimension on a 1-5 scale. Replaces the previous qualitative Low/Med/High labels with explicit numeric scores and an explicit Priority column. Refactorings now sort by computed priority by default, with two overrides (dependency order and missing-test-coverage prerequisites).

### Why
Borrowed from Anthropic's `engineering:tech-debt` skill. The formula rewards high-impact / high-risk refactorings that are *cheap* to fix. A 5/5/1 scores 35; a 5/5/5 scores only 10 — correctly reflecting that shipping easy big wins beats grinding on a hard fix that sits unstarted. Replaces vibes-based ordering with a defensible ranking.

## [1.2.1] - 2026-05-06

### Changed
- Trimmed `extract` command description to fit Claude Code's skill-listing budget.

## [1.2.0] - 2026-04-16

### Changed
- Rewrote skill/command descriptions to contain only triggering conditions and boundaries, removing workflow step summaries that caused the model to shortcut skill bodies

## [1.1.1] - 2026-04-13

### Changed
- Upgrade `refactor-analyzer` and `refactor-planner` agents from haiku to sonnet for better code analysis quality

## [1.1.0] - 2026-03-11

### Added
- `refactor-analyzer` agent for context-aware refactoring analysis (similar code, abstractions, tests, consumers)
- `refactor-planner` agent for safe refactoring planning (test coverage, dependencies, past patterns)
- Cross-plugin hooks: plan suggests `/feature-dev:tdd`, extract suggests `/code-review:staged`

### Changed
- Commands now use Agent tool instead of Task tool
- `analyze` command uses dedicated `refactor:refactor-analyzer` subagent
- `plan` command uses dedicated `refactor:refactor-planner` subagent
- `extract` command uses generic Explore agent via Agent tool

## [1.0.0] - 2026-01-24

### Added
- `/refactor:analyze` - Analyze code for refactoring opportunities
- `/refactor:plan` - Create step-by-step refactoring plan with checkpoints
- `/refactor:extract` - Safely extract code into functions, classes, or modules
- All commands use Explore agent to understand codebase context before suggesting changes
