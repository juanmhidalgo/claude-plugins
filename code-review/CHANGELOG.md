# Changelog

All notable changes to this plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
