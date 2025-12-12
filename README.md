# Claude Plugins Marketplace

Personal Claude Code plugins for development workflows.

## Installation

```bash
# Add this marketplace
/plugin marketplace add juanmhidalgo/claude-plugins

# Or from local path
/plugin marketplace add /path/to/claude-plugins
```

## Available Plugins

### code-review

Comprehensive code review workflow with skeptical AI feedback triage.

**Commands:**
- `/code-review/branch` - Review branch vs base
- `/code-review/staged` - Review staged changes
- `/code-review/triage` - Triage AI feedback (Copilot, Gemini)
- `/code-review/dismiss` - Dismiss false positives on GitHub
- `/code-review/fixes-plan` - Generate fix tracking document
- `/code-review/implement-fix` - Implement fixes, asking for technical decisions
- `/code-review/mark-fixed` - Verify and mark fixes
- `/code-review/resolve-fixed` - Resolve GitHub threads for fixed issues

**Install:**
```bash
/plugin install code-review@juanmhidalgo-plugins
```

### prd-toolkit

Create and manage Product Requirements Documents (PRDs) with AI assistance.

**Commands:**
- `/prd:create [feature]` - Generate a concise mini-PRD for a new feature
- `/prd:refine [file | issue-url]` - Improve existing PRD or convert vague issue to PRD
- `/prd:validate [file | issue-url]` - Verify implementation matches PRD criteria

**Install:**
```bash
/plugin install prd-toolkit@juanmhidalgo-plugins
```

## Updating Plugins

```bash
# Refresh marketplace metadata
/plugin marketplace update juanmhidalgo-plugins

# Reinstall to get latest version
/plugin uninstall code-review@juanmhidalgo-plugins
/plugin install code-review@juanmhidalgo-plugins
```

## Requirements

- `gh` CLI installed and authenticated
- GitHub token with repo scope
