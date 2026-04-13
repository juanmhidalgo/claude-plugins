# Changelog

## 1.1.0

### Changed

- Migrated from `commands/` to `skills/` with progressive disclosure pattern
- Rewrote skill description to follow "Use when / Do NOT use for" convention
- Added `disable-model-invocation: true` to prevent auto-triggering
- Narrowed `Bash(python *)` to `Bash(python -m pytest *)` for tighter security
- Extracted plan template and critical rules into `references/` for leaner core skill
- Clarified 10-minute exploration limit rationale vs global 15-minute limit

## 1.0.0

### Added

- `fix` command: fetch a GitHub Issue, explore the codebase, plan and implement the fix
- Multi-repo handoff support via `/handoff:prompt` when the fix spans repositories
- Automatic branch creation from issue metadata
