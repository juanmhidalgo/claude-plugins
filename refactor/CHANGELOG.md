# Changelog

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
