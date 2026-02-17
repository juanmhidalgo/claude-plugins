# second-opinion

Get second opinions from external AIs on code reviews, architecture decisions, and implementation approaches — directly from Claude Code.

## What it does

The `/second-opinion` command gathers relevant context from your codebase (diffs, files, git history) and sends it to an external AI for review. It supports four backends:

| Backend | CLI Required | Best For |
|---------|-------------|----------|
| **Codex** (default) | `codex` | Code review, bug detection |
| **Gemini** | `gemini` | Architecture feedback, broad analysis |
| **Copilot** | `copilot` | GitHub-aware reviews |
| **Claude** | `claude` | Alternative Claude perspective (different session) |

## Prerequisites

Install at least one backend CLI:

```bash
# OpenAI Codex
npm i -g @openai/codex

# Google Gemini CLI
npm i -g @anthropic-ai/gemini

# GitHub Copilot CLI
npm i -g @anthropic-ai/copilot

# Claude Code (you likely already have this)
npm i -g @anthropic-ai/claude-code
```

Each backend requires its own authentication (API keys or CLI login).

## Installation

```bash
# Add the marketplace (if not already added)
/plugin marketplace add juanmhidalgo/claude-plugins

# Install the plugin
/plugin install second-opinion@juanmhidalgo-plugins
```

## Usage

```bash
# Review staged changes (default backend: Codex)
/second-opinion review staged

# Review a specific file with Gemini
/second-opinion --backend gemini review src/auth.ts

# Review current branch changes with Copilot
/second-opinion --backend copilot review branch

# Ask a free-form question with Claude
/second-opinion --backend claude "Is this the right approach for handling auth tokens?"
```

### Backend selection

Specify a backend explicitly with `--backend <name>`, or mention it naturally:

- "ask **codex** to review" / "get **openai** opinion" → Codex
- "ask **gemini**" / "**google** review" → Gemini
- "ask **copilot**" / "**github** review" → Copilot
- "ask **claude**" / "**anthropic** opinion" → Claude

### Review types

| Command | What it does |
|---------|-------------|
| `review staged` | Reviews your staged git changes (`git diff --cached`) |
| `review <file>` | Reviews a specific file |
| `review branch` | Reviews all changes on current branch vs base |
| Free-form text | Asks the AI your question with relevant code context |

## Security

The skill automatically scans gathered context for secrets (API keys, tokens, passwords) and redacts them before sending to any external AI. It will warn you if secrets are detected.

## Backend comparison

| Feature | Codex | Gemini | Copilot | Claude |
|---------|-------|--------|---------|--------|
| Default timeout | 180s | 180s | 180s | 180s |
| JSON output | Yes | Yes | No | Yes |
| Writable mode | Yes | Yes | Yes | No |
| Sandbox mode | Yes | Yes | No | No |
| Custom model | Yes | Yes | Yes | Yes |
