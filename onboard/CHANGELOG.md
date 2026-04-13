# Changelog

## [1.1.1] - 2026-04-13

### Changed
- Upgrade `onboard-discoverer` and `architecture-mapper` agents from haiku to sonnet for better exploration quality

## [1.1.0] - 2026-03-11

### Added
- `onboard-discoverer` agent for thorough project analysis (tech stack, entry points, configuration)
- `architecture-mapper` agent for mapping project architecture (layers, components, boundaries, dependencies)

### Changed
- Commands now use Agent tool instead of Task tool
- `start` command uses dedicated `onboard:onboard-discoverer` subagent
- `architecture` command uses dedicated `onboard:architecture-mapper` subagent
- `explore` command uses generic Explore agent via Agent tool

## [1.0.0] - 2026-01-24

### Added
- `/onboard:start` - Generate onboarding guide for new developers
- `/onboard:explore` - Deep exploration of specific codebase topics
- `/onboard:architecture` - High-level architecture overview with diagrams
- All commands use Explore agent for thorough codebase investigation
