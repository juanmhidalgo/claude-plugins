# Changelog

All notable changes to this plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.2] - 2026-01-16

### Fixed
- Removed complex shell commands with pipes from `/code-review:branch` that were causing Bash permission check failures
- Shell commands like `git symbolic-ref ... | sed ...` are now handled dynamically by the agent instead of embedded in the command frontmatter

## [2.2.0] - 2026-01-15

### Added
- Added `keywords` and `triggers` fields to all commands and skills for improved discoverability
- Commands now include semantic keywords for search and natural language triggers for intent matching
- Skills updated with structured triggers (moved from prose descriptions)
- Plugin-level triggers added to plugin.json

### Changed
- Skill descriptions simplified (triggers moved to dedicated field)

## [2.1.1] - 2026-01-08

### Fixed
- Corrected agent hooks to use only officially documented variables
- Simplified hook commands to static messages (removed undocumented `$output` variable usage)
- All hooks now comply with official Claude Code hook specification

## [2.1.0] - 2026-01-08

### Changed
- Refactored all commands to use YAML-style lists for `allowed-tools` for better readability
- Implemented wildcard patterns in bash permissions (e.g., `Bash(git *)`, `Bash(gh *)`) to reduce permission prompts
- Updated all command frontmatter to use modern YAML list syntax
- Added `${CLAUDE_PLUGIN_ROOT}/scripts/*` wildcard for script permissions

### Added
- Added hooks to commands for better user guidance:
  - `/pr` now shows next steps after completion
  - `/staged` and `/branch` suggest follow-up commands
- Added hooks to agents for automatic feedback:
  - `bug-scanner` reports issue count on completion
  - `pr-eligibility-checker` shows eligibility status
  - `confidence-scorer` displays confidence levels with visual indicators
  - `pr-summarizer` shows PR type and file count
- Added `agent` field to `branch-review` skill to ensure proper routing to `code-review:branch-reviewer`
- Added `user-invocable: true` to skills that are useful as direct slash commands:
  - `branch-review`
  - `technical-decisions`
  - `receiving-code-review`
  - `review-fixes-plan`

### Improved
- Skills now support hot-reload (changes take effect immediately)
- Better permission handling with wildcard patterns reduces unnecessary prompts

## [2.0.0] - 2025-12-16

### Added
- `/code-review:pr <PR>` - Comprehensive multi-agent PR review workflow inspired by Anthropic's approach
- New specialized agents for parallel review:
  - `pr-eligibility-checker` (Haiku) - Validates PR is reviewable (not draft/closed/bot/trivial)
  - `claudemd-discoverer` (Haiku) - Finds relevant CLAUDE.md files in affected directories
  - `pr-summarizer` (Haiku) - Generates PR change summary
  - `claudemd-compliance-reviewer` (Sonnet) - Audits changes against CLAUDE.md guidelines
  - `bug-scanner` (Sonnet) - Shallow scan for obvious bugs in diff
  - `git-history-reviewer` (Sonnet) - Analyzes git blame/history for context
  - `pr-comments-reviewer` (Sonnet) - Checks previous PR comments that may apply
  - `code-comments-reviewer` (Sonnet) - Verifies compliance with code comment guidance
  - `confidence-scorer` (Haiku) - Scores issues 0-100 to filter false positives
- Confidence scoring system with explicit rubric (0-100 scale, threshold 80)
- Automatic false positive filtering based on:
  - Pre-existing issues
  - Linter/compiler-catchable issues
  - Pedantic nitpicks
  - Issues on unmodified lines
  - Intentionally silenced issues (lint ignore)

### Fixed
- Fixed `branch-reviewer` agent type reference to use namespaced format `code-review:branch-reviewer` in `/code-review:branch` and `/code-review:staged` commands (was causing "Agent type 'branch-reviewer' not found" error)

## [1.3.0] - 2025-12-07

### Changed
- `/code-review:triage` now includes human comments by default (previously only showed bot comments)
- Script option changed from `include_humans` (default: false) to `bots_only` (default: false)

### Fixed
- Added `per_page=100` to GitHub API calls to fetch all comments (was missing comments when PR had more than 30)

## [1.2.2] - 2025-12-07

### Fixed
- Fixed `pr-triage-comments.sh` script to pipe `gh api` output to `jq` instead of using `gh api --jq --arg` which is not supported by `gh` CLI (was causing "accepts 1 arg(s), received 4" error)

## [1.2.1] - 2025-12-07

### Fixed
- Fixed script paths in commands to use `${CLAUDE_PLUGIN_ROOT}` instead of hardcoded `~/.claude/plugins/code-review/scripts/` path, which was causing "no such file or directory" errors

## [1.2.0] - 2025-12-06

### Added
- `/code-review:resolve-fixed PR#` - Resolve GitHub threads for issues marked as fixed in REVIEW_FIXES.md

### Changed
- `review-fixes-plan` skill now includes `**GitHub:** ref_id` field to link issues to PR comments
- Updated workflow documentation to include resolve-fixed step

## [1.1.0] - 2025-12-06

### Added
- `/code-review:implement-fix [issue-number | "all"]` - Implement fixes from REVIEW_FIXES.md with technical decision prompts
- `technical-decisions` skill - Guidelines for asking about technical decisions before implementing fixes

## [1.0.0] - 2025-12-06

### Added
- `/code-review:branch [base]` - Review current branch vs base branch
- `/code-review:staged` - Review staged changes before committing
- `/code-review:triage PR#` - Triage AI reviewer feedback on PRs
- `/code-review:dismiss PR#` - Dismiss false positive comments on GitHub
- `/code-review:fixes-plan` - Generate REVIEW_FIXES.md tracking document
- `/code-review:mark-fixed` - Verify and mark issues as fixed
