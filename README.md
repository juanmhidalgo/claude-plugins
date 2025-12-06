# Claude Plugins Marketplace

Personal Claude Code plugins for development workflows.

## Installation

```bash
# Add this marketplace
/plugin marketplace add juanmhidalgo/claude-plugins

# Or from local path
/plugin marketplace add /home/juan/Develop/juanmhidalgo/claude-plugins
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
- `/code-review/mark-fixed` - Verify and mark fixes

**Install:**
```bash
/plugin install code-review@juanmhidalgo-plugins
```

## Requirements

- `gh` CLI installed and authenticated
- GitHub token with repo scope
