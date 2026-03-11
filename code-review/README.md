# Code Review Plugin

Comprehensive code review workflow for Claude Code: branch reviews, PR feedback triage, false positive dismissal, and fix tracking.

## Commands

| Command | Description |
|---------|-------------|
| `/code-review:pipeline PR#` | **Autonomous pipeline**: triage, fix, dismiss, test, commit, push, resolve |
| `/code-review:pr <PR>` | **Multi-agent PR review** with confidence scoring |
| `/code-review:branch [base]` | Review current branch vs base (default: main) |
| `/code-review:staged` | Review staged changes before commit |
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

Fully autonomous - only stops if tests fail after retries.

### Multi-Agent PR Review (recommended)

```
/code-review:pr 123         → Full PR review with 5 parallel agents
```

**Workflow steps:**
1. Eligibility check (skip drafts, bots, trivial PRs)
2. CLAUDE.md discovery (via Glob)
3. PR summary generation
4. **5 parallel reviews**: CLAUDE.md compliance, bug scan, git history, previous PR comments, code comments
5. Confidence scoring (0-100) for each issue
6. Filter issues below 80 confidence
7. Post review comment on PR

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
| `confidence-scorer` | Haiku | Scores issues 0-100 |

### Other Agents

- **comment-verifier** - Haiku agent for parallel comment verification (used by pipeline triage)
- **fix-implementer** - Focused Sonnet agent for implementing individual fixes (used by pipeline)
- **branch-reviewer** - Code review specialist for branch comparisons
- **pr-feedback-analyst** - Skeptical AI feedback analyst

## Skills

- **branch-review** - Best practices for branch code review
- **review-fixes-plan** - Template for REVIEW_FIXES.md tracking documents
- **receiving-code-review** - Guidelines for evaluating received feedback
- **technical-decisions** - When and how to ask for technical decisions before implementing fixes

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
