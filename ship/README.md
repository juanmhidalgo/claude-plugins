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
/ship --no-notify        # Don't notify sibling sessions after push
/ship --skip-tests --draft  # Combine flags
```

## Sibling Session Notification

After a successful push to the default branch, `/ship` looks for other live Claude Code sessions working on the same repository (e.g., parallel worktrees) via [cross-session messaging](https://code.claude.com/docs/en/cross-session-messaging) and sends each one a short heads-up: what landed and whether rebasing is advisable. Best-effort by design — it's skipped for feature-branch pushes, with `--no-notify`, or when messaging isn't available (Claude Code < v2.1.224, Bedrock/Vertex/Foundry), and it can never fail the ship workflow.

## Requirements

- `gh` CLI installed and authenticated
- Git remote configured

## Installation

```
/plugin install ship@juanmhidalgo-plugins
```
