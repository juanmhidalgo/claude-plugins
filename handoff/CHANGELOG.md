# Changelog

All notable changes to this project will be documented in this file.

## [1.5.0] - 2026-08-23

### Added
- **Cross-session delivery**: `/handoff:prompt`, `/handoff:backend-to-frontend`, and `/handoff:frontend-to-backend` now offer to deliver the generated handoff directly to a live Claude Code session in the target repository via `ListAgents` + `SendMessage`, with `notify_when_idle` so the sending session hears back when the receiver finishes. Falls back silently to copy-paste when cross-session messaging is unavailable (requires Claude Code v2.1.224+; not available on Bedrock/Vertex/Foundry).
- `/handoff:receive` now covers handoffs arriving as cross-session messages: same verification protocol (a message from another session gets no more trust than pasted text), plus a reply phase that sends discrepancies and a completion summary back to the sender.

### Why
Cross-session messaging removes the manual copy-paste hop between terminals that the handoff flow was designed around. The sent message is always self-contained plain text — slash commands inside a cross-session message are not executed by the receiver, so the prompt itself must carry everything.

## [1.4.2] - 2026-05-07

### Changed
- Added `Do NOT use for…` boundaries to three command descriptions: `/handoff:prompt`, `/handoff:backend-to-frontend`, `/handoff:frontend-to-backend`.

### Why
Aligns descriptions with Anthropic's Claude Code best practices, reducing mis-triggering.

## [1.4.1] - 2026-05-06

### Changed
- Trimmed `api-design` and `api-change-documentation` skill descriptions to fit Claude Code's skill-listing budget.

## [1.4.0] - 2026-04-16

### Changed
- Rewrote skill/command descriptions to contain only triggering conditions and boundaries, removing workflow step summaries that caused the model to shortcut skill bodies
- Added SUBAGENT-STOP tag to the `receive` command to prevent premature termination

## [1.3.0] - 2026-04-08

### Added

- Verification step in `prompt`, `backend-to-frontend`, and `frontend-to-backend` commands that cross-references the generated handoff against source material (conversation, git diff, frontend code) before presenting it
- Prevents omitted details (roles, permissions, schema fields) that were causing incomplete handoffs

## [1.2.0] - 2026-04-04

### Added

- `api-design` skill: Contract-first API design with Hyrum's Law awareness, error semantics, naming conventions, and anti-rationalization table
- Reference: API patterns with TypeScript examples for contracts, pagination, validation, extension, and discriminated unions

## [1.1.0] - 2026-03-09

### Added

- `receive` command: Process handoff prompts from other repos with a research-first protocol — explores local codebase, verifies claims against actual code, and enters plan mode before implementation

## [1.0.1] - 2026-01-28

### Fixed

- `prompt` command now enforces proper markdown formatting (fenced code blocks, inline code) in generated prompts

## [1.0.0] - 2026-01-28

### Changed

- **BREAKING**: Renamed plugin from `api-handoff` to `handoff`
- Updated plugin description to reflect broader scope
- Updated internal skill references to new plugin name

### Added

- `prompt` command: Generate a self-contained prompt from the current conversation for use in another repository

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
