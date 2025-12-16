# Changelog

All notable changes to this plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
