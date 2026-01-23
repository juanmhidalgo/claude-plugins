# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-01-23

### Changed

- Rewrote skill description to be trigger-focused per Anthropic guidelines
- Reduced skill content from ~180 to ~80 lines (progressive disclosure)
- Skill now focuses on specific output formats and classification rules
- Removed generic API documentation advice Claude already knows

### Fixed

- Commands now properly import skill via `@` reference
- Added `hooks` for better UX guidance after command completion
- Added shell context embedding (`!` backticks) for branch/commit info

## [0.1.0] - 2026-01-23

### Added

- Initial release of api-handoff plugin
- `backend-to-frontend` command: Generate structured prompts for frontend teams after backend API changes
- `frontend-to-backend` command: Generate structured prompts for backend teams when frontend needs new APIs
- `api-change-documentation` skill: Best practices for documenting cross-team API changes
