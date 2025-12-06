# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Claude Code plugins marketplace containing plugins for development workflows. The marketplace provides installable plugins that extend Claude Code with slash commands, agents, and skills.

## Architecture

```
.claude-plugin/
  marketplace.json     # Marketplace registry with plugin listings

<plugin-name>/
  .claude-plugin/
    plugin.json        # Plugin metadata (name, version, description)
  commands/            # Slash commands (*.md files)
  agents/              # Specialized agent definitions (*.md files)
  skills/              # Reusable skill documents (SKILL.md in subdirs)
  scripts/             # Shell scripts for automation
```

### Plugin Structure

- **Commands**: Markdown files defining slash commands with YAML frontmatter (`allowed-tools`, `argument-hint`, `description`)
- **Agents**: Markdown files with YAML frontmatter defining specialized agents with specific tools and skills
- **Skills**: Best practices documents activated by agents, providing domain knowledge

### Key Patterns

Commands can embed shell output using `!` backticks:
```markdown
- **Current branch**: !`git branch --show-current`
```

Commands accept arguments via `$1`, `$ARGUMENTS`.

## Available Plugin: code-review

Comprehensive code review workflow:

| Command | Purpose |
|---------|---------|
| `/code-review:branch [base]` | Review current branch vs base |
| `/code-review:staged` | Review staged changes |
| `/code-review:triage PR#` | Triage AI reviewer feedback |
| `/code-review:dismiss PR#` | Dismiss false positives on GitHub |
| `/code-review:fixes-plan` | Generate REVIEW_FIXES.md tracking |
| `/code-review:mark-fixed` | Verify and mark issues fixed |

### Core Principle

AI feedback is NOT valid by default. Every comment from AI reviewers must be verified against actual code before acting on it.

## Requirements

- `gh` CLI installed and authenticated
- GitHub token with repo scope

## Installation Commands

```bash
# Add marketplace
/plugin marketplace add juanmhidalgo/claude-plugins

# Install plugin
/plugin install code-review@juanmhidalgo-plugins
```
