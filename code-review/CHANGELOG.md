# Changelog

All notable changes to this plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.14.0] - 2026-04-16

### Changed
- Rewrote skill/command descriptions to contain only triggering conditions and boundaries, removing workflow step summaries that caused the model to shortcut skill bodies
- Added rationalization defense tables to `receiving-code-review`, `technical-decisions`, and `coverage-gate` skills, and to the `triage` command
- Added SUBAGENT-STOP tags to `pipeline`, `staged-pipeline`, `implement-fix`, and `receive` commands to prevent premature termination

## [2.13.0] - 2026-04-08

### Added
- **Enhanced tech debt analysis** with new verdict system and expanded coverage
  - New verdict levels: CLEAN / MINOR DEBT / SIGNIFICANT DEBT / BLOCKING DEBT (replaces simple HIGH/MEDIUM/LOW)
  - New analysis category: **Dependencies & Infrastructure** — flags new deps, unpinned versions, ad-hoc reimplementation of shared patterns, undocumented config changes
  - **Positive Patterns** section in output — highlights what's done well, not just problems
  - **Staged scope support** — `/code-review:tech-debt staged` analyzes staged changes; auto-detects scope when no argument is provided
  - Verdict decision rules for consistent classification across reviews
- Discoverability hooks: `/code-review:staged` and `/code-review:branch` now suggest `/code-review:tech-debt` in their Stop hooks

## [2.12.2] - 2026-04-08

### Added
- Lint scoping guard in `/code-review:pipeline` Phase 4 — after fixes are applied, detects and resets unrelated files modified by pre-commit hooks or auto-formatters
- Added autonomous rule: "Linter changed unrelated files → reset them, log in report"
- Prevents cascading lint changes from polluting fix commits (addresses recurring friction from 4+ sessions)

## [2.12.1] - 2026-03-30

### Fixed
- `/code-review:pipeline` now skips Phases 5-7 (tests, commit, push, resolve) when all comments are false positives and no code changes were made
- `/code-review:staged-pipeline` now skips Phases 3-5 (approve, fix, test) when all findings are dropped as incorrect
- Added explicit early-exit guards at each phase boundary to prevent unnecessary test runs on unchanged code

## [2.12.0] - 2026-03-20

### Added
- **Coverage gate** — detect CI coverage thresholds locally and prevent push failures
  - `/code-review:coverage-gate [base]` — standalone command to check coverage against GHA-configured thresholds before pushing
  - Supports `orgoro/coverage`, `irongut/CodeCoverageReport`, `5monkeys/cobertura-action`, and `codecov/codecov-action`
  - Detects per-category thresholds (new files, modified files, overall) from `.github/workflows/*.yml`
  - Runs coverage locally, categorizes changed files, checks against thresholds
  - Writes additional tests to fix coverage gaps (up to 2 cycles)
- `coverage-gate` skill — institutional knowledge for GHA coverage detection and threshold verification
  - Progressive disclosure: core patterns in SKILL.md, detailed action patterns in `references/gha-patterns.md`

### Changed
- `/code-review:pipeline` now includes **Phase 5b: Coverage Gate** between test and commit phases
  - Detects GHA coverage config and checks per-file coverage before pushing
  - Writes tests to fix coverage gaps (up to 2 cycles), stops if still below threshold
  - Added coverage status to final report (PASS/FAIL/SKIPPED)
  - Added autonomous rules: "Coverage below threshold → write tests, then STOP"
- `/code-review:staged-pipeline` now includes **Phase 5b: Coverage Gate** between test and stage phases
  - Same detection and verification logic adapted for staged changes context
  - Added coverage status to final report

## [2.11.1] - 2026-03-13

### Fixed
- Remove all compound shell operators (`||`, `|`, `&&`) from shell embeddings across commands (`dismiss`, `resolve-fixed`, `pipeline`, `pr`, `triage`, `staged`, `staged-pipeline`, `mark-fixed`, `fixes-plan`) to fix "Bash command permission check failed" errors
- Replace compound grep/test file-finding embeddings with static text (agent can find files dynamically)

## [2.11.0] - 2026-03-13

### Added
- `/code-review:staged-pipeline` — single-session review-verify-fix pipeline for staged changes
  - Runs review in forked context (preserves main context for verification and fixes)
  - Self-verifies findings against actual code (drops false positives)
  - Enters plan mode for user approval before implementing
  - Parallel `fix-implementer` agents for independent fixes
  - Runs test suite with retry, stages fixed files
  - No intermediate files — everything stays in conversation context
  - Replaces 3-session workflow (`staged` → `receive` → implement) with a single command

## [2.10.1] - 2026-03-13

### Fixed
- Simplified `git remote` shell embedding in `triage`, `pr`, `pipeline`, `resolve-fixed`, and `dismiss` commands to avoid `bwrap` sandbox errors (removed piped `sed` commands)

## [2.10.0] - 2026-03-11

### Changed
- Renamed `Task` to `Agent` tool in all commands (following Claude Code v2.1.63 rename)
- Updated `/code-review:branch` hook to suggest `/code-review:pipeline` as next step

### Improved
- Cross-plugin workflow suggestions in Stop hooks

## [2.9.0] - 2026-03-11

### Added
- `/code-review:pipeline PR#` - Autonomous PR review-fix-ship pipeline
  - Triages all bot/reviewer comments against actual code
  - Dismisses false positives with one-line justifications
  - Implements valid fixes with parallel subagents (independent fixes run concurrently)
  - Runs full test suite with up to 2 retry attempts on failure
  - Commits with structured message referencing each resolved comment
  - Pushes and resolves all GitHub threads in one pass
  - Fully autonomous: only stops if tests fail after retries
- `comment-verifier` agent - Haiku agent for parallel comment verification during triage
  - Read-only tools (Read, Grep, Glob) — cannot modify code
  - Background execution with 15-turn cap
  - Preloads `receiving-code-review` skill for skeptical verification
  - Returns structured verdict: VALID BUG or FALSE POSITIVE with evidence
- `fix-implementer` agent - Dedicated Sonnet agent for parallel fix implementation
  - Background execution with 25-turn cap to prevent runaway agents
  - Focused tool access (Read, Write, Edit, Grep, Glob, Bash)
  - Minimal-diff approach: fixes only the described issue

## [2.8.0] - 2026-03-10

### Added
- `/code-review:receive` - Process code review feedback from another session with verification
  - Parses findings from pasted review reports
  - Verifies each finding against actual code (confirmed / stale / incorrect / disputed)
  - Enters plan mode before any implementation
  - Connects to existing `/code-review:fixes-plan` → `/code-review:implement-fix` pipeline
  - Uses `receiving-code-review` skill for verification principles

## [2.7.0] - 2026-01-26

### Optimized
- Reduced `branch-review` skill from 162 to 75 lines (-54%)
  - Removed generic git commands section (Claude already knows these)
  - Condensed checklists into compact "Focus Areas" section
  - Improved description with "when to use" and "when NOT to use"
  - Kept institutional content: severity classification, feedback format, anti-patterns

## [2.6.1] - 2026-01-26

### Fixed
- Removed complex shell command with pipes/operators from `/code-review:implement-fix` that was causing Bash permission check failures
- Fixes file discovery is now handled dynamically by the agent instead of embedded in the command frontmatter

## [2.6.0] - 2026-01-24

### Removed
- Removed `claudemd-discoverer` agent - redundant since Claude Code auto-loads CLAUDE.md files

### Changed
- `/code-review:pr` Step 2 now uses simple Glob instead of dedicated agent
- Reduces latency and API calls in PR review workflow

## [2.5.0] - 2026-01-24

### Changed
- Refactored 3 skills with progressive disclosure pattern:
  - `receiving-code-review`: 220 → ~140 lines, examples moved to `references/examples.md`
  - `technical-decisions`: 209 → ~135 lines, examples moved to `references/examples.md`
  - `review-fixes-plan`: 205 → ~100 lines, template moved to `references/template.md`

### Improved
- Token efficiency: Core instructions load fast, detailed content on-demand
- Follows Anthropic's recommended skill structure from Skills documentation update

## [2.4.0] - 2026-01-23

### Added
- Added `hooks` to `/code-review:triage` command for next step guidance
- Added shell embedding to `/code-review:pr` command for repository and branch context

### Changed
- Generalized `receiving-code-review` skill by replacing personalized "your human partner" with neutral "team lead"
- Improved skill reusability across different team contexts

## [2.3.0] - 2026-01-16

### Added
- `/code-review:tech-debt [base]` - Analyze branch changes for technical debt before merging
- `tech-debt-reviewer` agent - Specialized agent for identifying maintainability issues
- Analyzes: complexity, duplication, debt markers (TODO/FIXME), test gaps, code smells

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
