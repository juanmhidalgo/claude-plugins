# CLAUDE.md

<project_context>
This is a Claude Code plugins marketplace containing plugins for development workflows. The marketplace provides installable plugins that extend Claude Code with slash commands, agents, and skills.
</project_context>

<architecture>

## Plugin Architecture

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

### Key Patterns

- **Commands**: Markdown files with YAML frontmatter (`allowed-tools`, `argument-hint`, `description`)
- **Agents**: Markdown files with YAML frontmatter defining specialized agents with specific tools and skills
- **Skills**: Best practices documents activated by agents, providing domain knowledge
- **Shell output embedding**: Commands can embed shell output using `!` backticks (e.g., `!`git branch --show-current``)
- **Arguments**: Commands accept arguments via `$1`, `$ARGUMENTS`

</architecture>

<critical_rules>

<rule id="version-bump" priority="blocking" authority="repository-standard">

## Version Management

When modifying any plugin, YOU MUST complete these steps IN ORDER:

1. **Bump the version** in the plugin's `.claude-plugin/plugin.json` file
2. **Use semantic versioning**: patch (0.0.x) for fixes, minor (0.x.0) for features, major (x.0.0) for breaking changes
3. **Update the CHANGELOG.md** in the plugin's root directory with the changes made

NEVER skip version bumping. This is a MANDATORY step that prevents version conflicts and maintains marketplace integrity. No exceptions.

</rule>

<rule id="ai-review-verification" priority="critical">

## AI Code Review Principle

AI feedback is NOT valid by default. YOU MUST verify every comment from AI reviewers against actual code before acting on it. This applies to all code review workflows.

</rule>

<rule id="prd-observable-behavior" priority="recommended">

## PRD Documentation Standard

PRDs focus on **observable behavior**, not implementation details. Describe what users can do, not how it's implemented.

</rule>

</critical_rules>

<available_plugins>

## code-review Plugin

Comprehensive code review workflow:

| Command | Purpose |
|---------|---------|
| `/code-review:branch [base]` | Review current branch vs base |
| `/code-review:staged` | Review staged changes |
| `/code-review:triage PR#` | Triage AI reviewer feedback |
| `/code-review:dismiss PR#` | Dismiss false positives on GitHub |
| `/code-review:fixes-plan` | Generate REVIEW_FIXES.md tracking |
| `/code-review:implement-fix` | Implement fixes, asking for technical decisions |
| `/code-review:mark-fixed` | Verify and mark issues fixed |
| `/code-review:resolve-fixed PR#` | Resolve GitHub threads for fixed issues |

## prd-toolkit Plugin

Create and manage Product Requirements Documents (PRDs):

| Command | Purpose |
|---------|---------|
| `/prd:create [feature]` | Generate a concise mini-PRD for a new feature |
| `/prd:refine [file \| issue-url]` | Improve existing PRD or convert vague issue to PRD |
| `/prd:validate [file \| issue-url]` | Verify implementation matches PRD criteria |
| `/prd:analyze [file \| issue-url \| text]` | Identify gaps, edge cases, and ambiguities before implementation |

</available_plugins>

<environment_requirements>

## Requirements

- `gh` CLI installed and authenticated
- GitHub token with repo scope

</environment_requirements>

<common_commands>

## Installation Commands

```bash
# Add marketplace
/plugin marketplace add juanmhidalgo/claude-plugins

# Install plugin
/plugin install code-review@juanmhidalgo-plugins
```

</common_commands>
