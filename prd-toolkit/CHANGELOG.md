# Changelog

All notable changes to this project will be documented in this file.

## [2.1.1] - 2026-05-12

### Fixed
- Removed unsupported `permissionMode` and `hooks` frontmatter fields from `prd-specialist` and `prd-validator` agents. Sub-agents in Claude Code plugins silently ignore these fields; removing them keeps definitions accurate and avoids confusion.
- Fixed tool name casing in `prd-validator`: `bash, read, glob, grep` → `Bash, Read, Glob, Grep` to match Claude Code convention.

## [2.1.0] - 2026-05-07

### Added
- `.mcp.json.example` documenting the optional ClickUp MCP server integration. Users can copy and customize for their installed ClickUp MCP server; `/prd:refine` falls back to direct ClickUp REST API calls when no MCP is present.
- README section documenting the ClickUp MCP option.

### Changed
- Added `Do NOT use for…` boundaries to `/prd:analyze` and `/prd:validate` descriptions (clarifies the analyze ↔ validate split).

### Why
Aligns descriptions with Anthropic's Claude Code best practices and makes external dependencies (ClickUp MCP) discoverable per "plugins should bundle their setup" guidance.

## [2.0.0] - 2026-05-06

### Removed (BREAKING)
- `/prd:create` command. PRD-from-scratch creation is consolidated into `/feature-dev:spec`, which produces a richer, gated `SPEC-*.md` artifact that the rest of this toolkit (`/prd:refine`, `/prd:analyze`, `/prd:validate`) can still operate on.

### Changed
- `prd-specialist` agent description narrowed to "refine and analyze" (no longer claims to create from scratch).
- `/prd:refine` "Do NOT use" guidance now points to `/feature-dev:spec` for new specs.
- Plugin description and README updated to reflect the narrower scope. Workflow diagram now starts at `/feature-dev:spec`.

### Migration
- Replace any `/prd:create <feature>` invocations with `/feature-dev:spec <feature>`.

## [1.8.1] - 2026-05-06

### Changed
- Trimmed `prd-best-practices` skill description to fit Claude Code's skill-listing budget.

## [1.8.0] - 2026-04-16

### Changed
- Rewrote skill/command descriptions to contain only triggering conditions and boundaries, removing workflow step summaries that caused the model to shortcut skill bodies

## [1.7.0] - 2026-03-11

### Changed
- Renamed `Task` to `Agent` in `allowed-tools` across all 4 commands (`create`, `refine`, `analyze`, `validate`)
- Replaced `Task tool` with `Agent tool` in all command body text
- Updated cross-plugin hooks: `create` now suggests `/discuss:feature` and `/feature-dev:explore-plan`; `validate` now suggests `/code-review:branch` and `/commit`; `refine` and `analyze` now include cross-plugin suggestions

## [1.6.0] - 2026-01-23

### Added
- Added `hooks` to all commands (`create`, `refine`, `validate`, `analyze`) for next step guidance
- Added `hooks` and `skills` fields to `prd-validator` agent

### Improved
- Updated `prd-best-practices` skill description with "when NOT to use" guidance for better trigger accuracy
- Skill now explicitly states it should NOT be used for technical specs or architecture docs

## [1.5.0] - 2026-01-15

### Added
- Added `keywords` and `triggers` fields to all commands and skill for improved discoverability
- Commands now include semantic keywords for search and natural language triggers for intent matching
- Plugin-level triggers added to plugin.json

### Changed
- Skill description simplified (triggers moved to dedicated field)

## [1.4.1] - 2026-01-08

### Fixed
- Corrected `prd-specialist` agent hooks to use only officially documented variables
- Simplified hook command to static message (removed undocumented `$output` variable usage)
- Hook now complies with official Claude Code hook specification

## [1.4.0] - 2026-01-08

### Changed
- Refactored all commands to use YAML-style lists for `allowed-tools` for better readability
- Updated all command frontmatter to use modern YAML list syntax
- Updated `prd-specialist` agent to use YAML list format for tools

### Added
- Added `context: fork` to `prd-best-practices` skill for isolated execution context
- Added `agent: prd-toolkit:prd-specialist` to `prd-best-practices` skill for proper routing
- Added `user-invocable: true` to `prd-best-practices` skill to enable direct slash command invocation
- Added hooks to `prd-specialist` agent for completion feedback
- Added `Bash(gh *)` wildcard permission to `prd-specialist` agent

### Improved
- Skills now support hot-reload (changes take effect immediately)
- Better agent routing with explicit agent field in skills
- PRD best practices skill can now run in forked context for better isolation

## [1.3.1] - 2025-12-12

### Fixed
- Fixed `author` field in plugin.json to use object format (was string, expected object)

## [1.3.0] - 2025-12-12

### Added
- `/prd:analyze` command - Identify gaps, edge cases, and ambiguities in requirements before implementation
- Supports file paths, GitHub issue URLs, or pasted text directly

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
