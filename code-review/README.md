# Code Review Plugin

Comprehensive code review workflow for Claude Code: branch reviews, PR feedback triage, false positive dismissal, and fix tracking.

## Commands

| Command | Description |
|---------|-------------|
| `/code-review/branch [base]` | Review current branch vs base (default: main) |
| `/code-review/staged` | Review staged changes before commit |
| `/code-review/triage PR#` | Triage AI feedback (Copilot, Gemini) with skeptical verification |
| `/code-review/dismiss PR#` | Dismiss false positives on GitHub with justification |
| `/code-review/fixes-plan [name]` | Generate/update REVIEW_FIXES.md tracking document |
| `/code-review/mark-fixed [#\|all]` | Verify fixes against code and update tracking |

## Workflows

### Branch Review (before PR)
```
/code-review/branch         → Identify issues in branch
        ↓
/code-review/fixes-plan X   → Generate REVIEW_FIXES.md
        ↓
    Implement fixes         → Write code to fix issues
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
    Implement fixes         → Write code to fix issues
        ↓
/code-review/mark-fixed all → Verify & update tracking doc
```

### Pre-commit Review
```
/code-review/staged         → Review before committing
```

## Core Principle

**AI feedback is NOT valid by default.** Every comment from AI reviewers (Copilot, Gemini, etc.) must be verified against actual code behavior before acting on it.

## Scripts

The plugin includes bash scripts for GitHub API operations (no MCP required):

- `pr-triage-comments.sh` - Fetch PR comments optimized for triage
- `pr-resolve-comment.sh` - Dismiss/resolve comments on GitHub
- `pr-comments.sh` - Full PR comments fetch
- `pr-review-summary.sh` - Quick review status summary

## Agents

- **branch-reviewer** - Code review specialist for branch comparisons
- **pr-feedback-analyst** - Skeptical AI feedback analyst

## Skills

- **branch-review** - Best practices for branch code review
- **review-fixes-plan** - Template for REVIEW_FIXES.md tracking documents
- **receiving-code-review** - Guidelines for evaluating received feedback

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
