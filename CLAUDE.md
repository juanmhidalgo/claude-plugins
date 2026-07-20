# CLAUDE.md

<project_context>
Claude Code plugins marketplace. Each top-level directory (e.g., `code-review/`, `feature-dev/`) is a plugin that bundles slash commands, agents, and skills. The marketplace registry lives in `.claude-plugin/marketplace.json`.
</project_context>

<architecture>

## Plugin layout

```
.claude-plugin/
  marketplace.json     # Marketplace registry

<plugin-name>/
  .claude-plugin/
    plugin.json        # Plugin metadata (name, version, description)
  commands/            # Slash commands (*.md)
  agents/              # Specialized agents (*.md)
  skills/<name>/SKILL.md  # Skills with optional references/
  scripts/             # Shell scripts
  CHANGELOG.md
  README.md
```

For deeper conventions (frontmatter fields, discoverability, progressive disclosure), see `.claude/rules/plugin-creation.md` (auto-loaded when working in a plugin directory). For skill testing, see `.claude/rules/skill-testing.md`.

</architecture>

<critical_rules>

<rule id="version-bump" priority="blocking" authority="repository-standard">

## Version Management

When modifying any plugin, YOU MUST complete these steps IN ORDER:

1. **Bump the version** in the plugin's `.claude-plugin/plugin.json`
2. **Use semantic versioning**: patch (0.0.x) for fixes, minor (0.x.0) for features, major (x.0.0) for breaking changes
3. **Update the CHANGELOG.md** in the plugin's root with the changes made
4. **Mirror the new version** in `.claude-plugin/marketplace.json` — the registry duplicates every plugin's version, and a stale entry pins installs to the old version

NEVER skip version bumping. Two `PostToolUse` hooks enforce this: `version-bump-check.sh` warns when a plugin file is edited without a bump or CHANGELOG entry, and `marketplace-sync-check.sh` warns when a registry version drifts from its `plugin.json`. Bypass either with `SKIP_VERSION_CHECK=1` for genuinely in-progress work.

When editing `marketplace.json`, change the version lines in place. Re-serializing the file (e.g. `json.dump`) reflows every inline `keywords` array and turns a 3-line change into a 120-line diff.

</rule>

<rule id="ai-review-verification" priority="critical">

## AI Code Review Principle

AI feedback is NOT valid by default. YOU MUST verify every comment from AI reviewers against actual code before acting on it. Applies to all code review workflows.

</rule>

<rule id="prd-observable-behavior" priority="recommended">

## PRD Documentation Standard

PRDs focus on **observable behavior**, not implementation details. Describe what users can do, not how it's implemented.

</rule>

</critical_rules>

<plugin_catalog>

For the full plugin list, commands, and usage examples, see `README.md` or run `/plugin marketplace` in Claude Code.

</plugin_catalog>
