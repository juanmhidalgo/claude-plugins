# Changelog

## [1.4.1] - 2026-09-22

### Fixed
- `analyze`'s priority formula defined Risk as breakage risk, so riskier refactorings ranked higher — the opposite of the ordering guidance below it. Risk now means the cost of leaving the code as is, matching the formula's origin in `tech-debt-reviewer`.
- `plan` checks out `<base-branch>` instead of `main`; `extract`'s five-step checklist is condensed to the outcome and defers to the project's docstring convention; dropped "be thorough" from `refactor-analyzer`.

## [1.4.0] - 2026-09-15

### Added
- **`conflict-scout` agent** — maps open PRs, other branches, stashes, worktrees, and uncommitted edits against the files a refactor will touch. Reports two kinds of overlap: *textual* (a PR edits a target file — git will conflict) and *semantic* (a PR calls a symbol you are renaming, so it merges clean and breaks afterwards). Emits a CLEAR / CONTESTED / BLOCKED verdict plus a do-now / do-first / defer / coordinate sequencing recommendation.
- `/refactor:analyze` spawns the scout in parallel with `refactor-analyzer`, adds a **Concurrent Work** section, and gains a third ordering override — **contention** — alongside dependency and coverage gap.
- `/refactor:plan` spawns the scout in parallel with `refactor-planner`, adds **Concurrent Work** and **Conflict Handling** sections, marks contested steps with `**Blocked on**: PR #N`, and adds a rebase check to the pre-flight checklist.
- `/refactor:extract` runs a single inline `gh pr list` check on the source and destination files before editing, and stops to ask when an open PR is already touching them.

### Why
A refactor moves, renames, and deletes existing lines, so the conflict math is not the feature-branch math: *any* overlap on a target file is a near-certain conflict, and a rename can break a PR that never touches your files at all. Borrowed from `feature-dev`'s `history-explorer`, where the open-PR check proved its worth in practice — but specialized, because there the finding is a heads-up and here it decides the order of the work.

## [1.3.1] - 2026-05-07

### Changed
- `/refactor:plan` now recommends running in plan mode (`Shift+Tab`) so the proposed plan is reviewed before any code changes.

### Why
Aligns with Anthropic's Claude Code "explore → plan → implement" workflow.

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
