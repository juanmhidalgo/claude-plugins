# Changelog

## [1.1.2] - 2026-05-07

### Changed
- Added `Do NOT use for…` boundary to `/performance:profile` description (directs broad scans to `/performance:audit`).

### Why
Aligns description with Anthropic's Claude Code best practices.

## [1.1.1] - 2026-05-06

### Changed
- Trimmed `performance-optimization` skill description to fit Claude Code's skill-listing budget.

## [1.1.0] - 2026-04-16

### Changed
- Rewrote skill/command descriptions to contain only triggering conditions and boundaries, removing workflow step summaries that caused the model to shortcut skill bodies

## [1.0.0] - 2026-04-04

### Added

- `audit` command: Performance audit with measure-first approach, anti-pattern scanning, and bottleneck identification
- `profile` command: Focused profiling of specific functions, endpoints, or components with timing data
- `performance-optimization` skill: Optimization workflow, Core Web Vitals targets, symptom decision tree, performance budgets
- Reference: Performance checklist for frontend (images, JS, CSS, network, rendering) and backend (database, API, infrastructure)
