# Ship Plugin

End-to-end shipping workflow for Claude Code. Takes your changes from working directory to remote with minimal interaction.

## What it does

`/ship` orchestrates the full git workflow in 6 phases:

1. **Status & Branch Detection** — detects default branch, offers to create feature branch if on main
2. **Smart Staging** — analyzes change cohesion; auto-stages if cohesive, groups and asks if mixed concerns
3. **Commit Message** — generates conventional commit automatically
4. **Test Gate** — detects and runs your test suite
5. **Commit & Push** — commits and pushes to remote
6. **Pull Request** — offers to create PR on feature branches

## Smart Staging

The key feature. Instead of always asking what to stage, the plugin analyzes your changes:

- **Single concern** (e.g., all files relate to the same feature): auto-stages everything, no question asked
- **Mixed concerns** (e.g., a bug fix + unrelated feature work): groups changes by concern and asks which group to ship

This means zero friction in the common case, but still catches the "I fixed a bug while working on a feature" scenario.

## Usage

```
/ship                    # Full workflow
/ship --skip-tests       # Skip test phase
/ship --no-pr            # Don't offer to create PR
/ship --draft            # Create PR as draft
/ship --skip-tests --draft  # Combine flags
```

## Requirements

- `gh` CLI installed and authenticated
- Git remote configured

## Installation

```
/plugin install ship@juanmhidalgo-plugins
```
