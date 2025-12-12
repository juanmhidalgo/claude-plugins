# Changelog

All notable changes to this project will be documented in this file.

## [1.2.1] - 2025-12-12

### Changed
- Unified `/prd:refine` to also convert vague issues to structured PRDs
- Standardized all examples and documentation to English

## [1.2.0] - 2025-12-12

### Added
- `/prd:refine` command - Improve existing PRDs with feedback and suggestions
- `/prd:validate` command - Verify implementation matches PRD acceptance criteria
- `prd-validator` agent - QA-focused agent for validating implementations

## [1.1.0] - 2025-12-12

### Changed
- Refocused PRD format on **observable behavior** instead of implementation details
- Added **User Stories** section to PRD template
- Added **Out of Scope** section to prevent scope creep
- Updated acceptance criteria examples to user perspective
- Removed technical stack detection (unnecessary for high-level PRDs)
- Updated skill with clearer good/bad examples

## [1.0.0] - 2025-12-12

### Added
- Initial release of prd-toolkit plugin
- `/prd:create` command - Generate mini-PRDs for new features
- `prd-specialist` agent - AI assistant for PRD creation
- `prd-best-practices` skill - Best practices for writing PRDs
- Support for publishing to GitHub Issues, ClickUp, or local files
