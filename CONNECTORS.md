# Connectors

How this marketplace's plugins integrate with external systems.

A "connector" is any external integration a plugin can use — typically the GitHub CLI (`gh`) or an MCP server. Most plugins work fully offline; some optionally enrich their output when a connector is present.

## Connectors used today

| Category | Plugins | Implementation | Status |
|----------|---------|----------------|--------|
| **Code host** | `code-review`, `github-issues`, `handoff` (light), `prd-toolkit` (refine/validate from issues) | GitHub via `gh` CLI | GitHub-native by design (see below) |
| **Project tracker** | `intake` (task fetching), `prd-toolkit` (publishing) | ClickUp via `clickup-local` MCP | Optional — plugins work without it |
| **External AI backends** | `second-opinion` | Codex, Gemini, Copilot, Claude | Configured per-backend (not an MCP connector) |

## Plugin → connector matrix

| Plugin | Code host | Project tracker |
|--------|-----------|----------------|
| `code-review` | ✅ required (`gh`) | — |
| `github-issues` | ✅ required (`gh`) | — |
| `prd-toolkit` | ☑️ optional (`gh`) | ☑️ optional (ClickUp) |
| `handoff` | ☑️ optional (`gh`) | — |
| `intake` | — | ☑️ optional (ClickUp) |
| `feature-dev`, `discuss`, `ship`, `debug`, `performance`, `security`, `second-opinion`, `agents-md-toolkit`, `onboard`, `refactor` | — | — |

Legend: ✅ required, ☑️ optional, — not used

## Why some plugins are GitHub-native

`code-review` and `github-issues` invoke specific `gh` CLI verbs and GitHub GraphQL APIs (PR thread resolution, comment dismissal, review state mutation). Abstracting to a generic "code host" category would either lose capability or force the model to invent commands. These plugins are intentionally GitHub-native; using GitLab, Bitbucket, or other code hosts is not currently supported.

## ClickUp specifically

`intake` and `prd-toolkit` use ClickUp via the `clickup-local` MCP server when configured. Both plugins work without it — they fall back to inline-paste workflows. The MCP server provides automatic ticket fetching, link-to-task, and status updates.

## Setup

### `gh` CLI (for code-host plugins)

```bash
gh auth login
gh auth status   # verify
```

GitHub token must have `repo` scope for the full code-review pipeline (read PRs, post comments, resolve threads, dismiss reviews).

### ClickUp MCP (for project-tracker plugins)

The `clickup-local` MCP server must be configured in your Claude Code environment. Configuration lives outside the marketplace — set it up per the MCP server's own documentation. When present, `intake` and `prd-toolkit` detect it automatically and use it; when absent, both plugins fall back to inline-paste workflows.
