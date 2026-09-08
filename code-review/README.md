# Code Review Plugin

Comprehensive code review workflow for Claude Code: branch reviews, PR feedback triage, false positive dismissal, and fix tracking.

## Commands

| Command | Description |
|---------|-------------|
| `/code-review:pipeline PR#` | **Autonomous pipeline**: triage, fix, dismiss, test, commit, push, resolve |
| `/code-review:pr <PR> [level]` | **Multi-agent PR review**, reported in session — never posts to GitHub |
| `/code-review:branch [base] [level]` | Review current branch vs base, in a reviewer that has not seen this conversation |
| `/code-review:staged [level]` | Review staged changes, in a reviewer that has not seen this conversation |
| `/code-review:coverage-gate [base]` | Check coverage against CI thresholds locally before push |
| `/code-review:receive <report>` | Process review feedback from another session with verification |
| `/code-review:triage PR#` | Triage AI feedback (Copilot, Gemini) with skeptical verification |
| `/code-review:dismiss PR#` | Dismiss false positives on GitHub with justification |
| `/code-review:fixes-plan [name]` | Generate/update REVIEW_FIXES.md tracking document |
| `/code-review:implement-fix [#\|all]` | Implement fixes, asking for technical decisions when needed |
| `/code-review:mark-fixed [#\|all]` | Verify fixes against code and update tracking |
| `/code-review:resolve-fixed PR#` | Resolve GitHub threads for issues marked as fixed |

## Workflows

### Autonomous Pipeline (fastest)

```
/code-review:pipeline 42   → Triage → fix → dismiss → test → commit → push → resolve
```

**What it does in one pass:**
1. Fetches and triages all bot/reviewer comments
2. Dismisses false positives with justifications
3. Implements valid fixes (parallel subagents for independent fixes)
4. Runs full test suite (retries up to 2x on failure)
5. Commits with structured message, pushes
6. Resolves all GitHub threads

Fully autonomous - only stops if tests fail after retries or coverage is below CI thresholds.

### Multi-Agent PR Review (recommended)

```
/code-review:pr 123          → PR review at the default effort level
/code-review:pr 123 high     → broader coverage, includes unverified findings
```

**Workflow steps:**
1. Eligibility check (skip drafts, bots, trivial PRs)
2. CLAUDE.md discovery (via Glob)
3. PR summary generation
4. **Parallel reviews**, 2 to 5 dimensions depending on effort level
5. Deduplicate findings across dimensions
6. **Verification**: one `finding-verifier` per finding → CONFIRMED / PLAUSIBLE / REFUTED
7. Filter by effort level
8. **Report in this session** — nothing is written to GitHub

**Effort levels** (`low` | `medium` | `high` | `max`, default `medium`, remembered
in `.claude/code-review.local.md`):

| Level | Dimensions | Surfaced |
|-------|-----------|----------|
| `low` | 2 | `CONFIRMED` only |
| `medium` | 3 | `CONFIRMED`, plus `pre_existing` grouped separately |
| `high` | 5 | `CONFIRMED` + `PLAUSIBLE`, each marked |
| `max` | 5 | Everything, every label shown |

Low and medium give fewer findings you can trust; high and max give broader
coverage including findings that may not hold. Pick by what the diff costs to
get wrong.

### Branch Review (before PR)
```
/code-review/branch         → Identify issues in branch
        ↓
/code-review/fixes-plan X   → Generate REVIEW_FIXES.md
        ↓
/code-review/implement-fix  → Implement fixes (asks for tech decisions)
        ↓
/code-review/mark-fixed 3   → Verify & mark issue #3 as fixed
        ↓
/code-review/mark-fixed all → Verify all remaining issues
```

### PR Feedback Triage (after PR)
```
/code-review/triage 42      → Filter AI feedback (valid vs false positive)
        ↓
/code-review/dismiss 42     → Dismiss false positives on GitHub
        ↓
/code-review/fixes-plan X   → Add verified issues to tracking doc
        ↓
/code-review/implement-fix  → Implement fixes (asks for tech decisions)
        ↓
/code-review/mark-fixed all → Verify & update tracking doc
        ↓
    git push                → Push fixes to PR
        ↓
/code-review/resolve-fixed 42 → Resolve GitHub threads
```

### Cross-Session Review
```
Session B:
/code-review/staged         → Run review, copy output

Session A:
/code-review/receive <paste> → Verify findings against code
        ↓
/code-review/fixes-plan X   → Track confirmed issues
        ↓
/code-review/implement-fix  → Implement fixes
```

### Pre-commit Review
```
/code-review/staged         → Review before committing
```

### Coverage Gate (pre-push)
```
/code-review:coverage-gate      → Detect GHA thresholds, run coverage, fix gaps
/code-review:coverage-gate main  → Explicit base branch
```

Detects coverage thresholds from `.github/workflows/*.yml` (orgoro/coverage, codecov, etc.), categorizes files as new/modified, runs coverage locally, and writes tests to fix gaps.

## This plugin vs. the built-in `/code-review`

Claude Code ships its own `/code-review`. The two are not interchangeable, and
the boundary is worth knowing before reaching for either.

**Use the built-in `/code-review`** for interactive review of a diff you are
looking at: it scales effort from `low` to `max`, renders findings in the host
UI, applies them with `--fix`, posts inline PR comments with `--comment`, and
runs a deep multi-agent pass in the cloud with `ultra`.

**Use this plugin** for the things it does not do:

| Need | Why the built-in does not cover it |
|------|-----------------------------------|
| A reviewer that has **not** seen this conversation | It runs forked, so it inherits the session that wrote the code |
| Triaging **incoming** bot feedback (Copilot, Gemini) | It emits its own findings; it does not consume anyone else's |
| Dismissing false positives with justification, resolving threads | No feedback-lifecycle commands |
| Tracking findings across sessions (`REVIEW_FIXES.md`) | Findings live in the session |
| Reviewing code that is **not** in a diff | Its targets are always diff-scoped |
| Technical debt as its own axis, with a merge verdict | Its categories are correctness / simplification / efficiency / test-coverage |
| Coverage gated against thresholds parsed from CI config | Coverage is a finding category, not a gate |
| An autonomous triage → fix → test → push → resolve pipeline | No such orchestration |

The short version: **the built-in finds problems in a diff; this plugin manages
the lifecycle of the feedback around one** — and reviews from a context that did
not write the code.

They compose. A reasonable habit is the built-in while iterating, and
`/code-review:branch` before opening the PR, precisely because by then this
session has been reasoning about the code for an hour.

## Core Principle

**AI feedback is NOT valid by default.** Every comment from AI reviewers (Copilot, Gemini, etc.) must be verified against actual code behavior before acting on it.

## Scripts

The plugin includes bash scripts for GitHub API operations (no MCP required):

- `pr-triage-comments.sh` - Fetch PR comments optimized for triage (filters resolved/outdated via GraphQL)
- `pr-resolve-comment.sh` - Dismiss/resolve comments on GitHub
- `pr-comments.sh` - Full PR comments fetch
- `pr-review-summary.sh` - Quick review status summary

### pr-triage-comments.sh

```bash
# Basic usage (bot comments only, excludes resolved)
./scripts/pr-triage-comments.sh owner repo pr_number

# Include human comments
./scripts/pr-triage-comments.sh owner repo pr_number 1500 true

# Include resolved threads
./scripts/pr-triage-comments.sh owner repo pr_number 1500 false true
```

Output includes `resolved` and `outdated` status for inline comments, with stats on filtered items.

## Agents

### PR Review Workflow Agents

| Agent | Model | Purpose |
|-------|-------|---------|
| `pr-eligibility-checker` | Haiku | Validates PR is reviewable |
| `pr-summarizer` | Haiku | Generates change summary |
| `claudemd-compliance-reviewer` | Sonnet | Audits CLAUDE.md compliance |
| `bug-scanner` | Sonnet | Shallow scan for obvious bugs |
| `git-history-reviewer` | Sonnet | Analyzes git blame/history |
| `pr-comments-reviewer` | Sonnet | Checks previous PR feedback |
| `code-comments-reviewer` | Sonnet | Verifies code comment guidance |
| `finding-verifier` | Sonnet | Verifies one finding → CONFIRMED / PLAUSIBLE / REFUTED |

### Other Agents

- **comment-verifier** - Sonnet agent for parallel comment verification (used by pipeline and triage)
- **fix-implementer** - Focused Sonnet agent for implementing individual fixes (used by pipeline)
- **branch-reviewer** - Code review specialist for branch comparisons
- **pr-feedback-analyst** - Skeptical AI feedback analyst

## Skills

- **branch-review** - Best practices for branch code review
- **review-fixes-plan** - Template for REVIEW_FIXES.md tracking documents
- **receiving-code-review** - Guidelines for evaluating received feedback
- **technical-decisions** - When and how to ask for technical decisions before implementing fixes
- **coverage-gate** - GHA coverage threshold detection and local verification patterns

## Requirements

- `gh` CLI installed and authenticated
- GitHub token with repo scope

## Installation

```bash
# Add marketplace (first time only)
/plugin marketplace add juanmhidalgo/claude-plugins

# Install plugin
/plugin install code-review@juanmhidalgo-plugins
```

## Updating

```bash
# Refresh marketplace metadata
/plugin marketplace update juanmhidalgo-plugins

# Reinstall to get latest version
/plugin uninstall code-review@juanmhidalgo-plugins
/plugin install code-review@juanmhidalgo-plugins
```
