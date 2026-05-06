---
name: second-opinion
description: |
  Use when the user wants a second opinion from another AI (Codex, Gemini, Copilot, Claude) on code or architecture.
  Read-only consultation — does not write code.
argument-hint: "[--backend codex|gemini|copilot|claude] review staged | review <file> | <question>"
disable-model-invocation: true
allowed-tools:
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/ask-codex.sh *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/ask-gemini.sh *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/ask-copilot.sh *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/ask-claude.sh *)
  - Bash(git diff *)
  - Bash(git log *)
  - Bash(git branch --show-current)
  - Bash(git rev-parse *)
  - Read
  - Glob
  - Grep
keywords:
  - code-review
  - second-opinion
  - external-review
  - codex
  - gemini
  - copilot
  - claude
triggers:
  - "get a second opinion"
  - "ask codex"
  - "ask gemini"
  - "ask copilot"
  - "ask claude"
  - "external code review"
---

# Second Opinion via External AI

You are gathering context and asking an external AI for a second opinion.

## Step 0: Select backend

Parse `$ARGUMENTS` for `--backend <name>` or infer from context:

| Flag / keyword | Script |
|----------------|--------|
| `--backend codex` or mentions "codex" or "openai" | `${CLAUDE_PLUGIN_ROOT}/scripts/ask-codex.sh` |
| `--backend gemini` or mentions "gemini" or "google" | `${CLAUDE_PLUGIN_ROOT}/scripts/ask-gemini.sh` |
| `--backend copilot` or mentions "copilot" or "github" | `${CLAUDE_PLUGIN_ROOT}/scripts/ask-copilot.sh` |
| `--backend claude` or mentions "claude" or "anthropic" | `${CLAUDE_PLUGIN_ROOT}/scripts/ask-claude.sh` |
| No preference specified | Default to `${CLAUDE_PLUGIN_ROOT}/scripts/ask-codex.sh` |

Remove the `--backend` flag from arguments before continuing to Step 1.

## Step 1: Determine the review type

Parse remaining arguments to determine what the user wants reviewed:

| Pattern | Action |
|---------|--------|
| `review staged` or `staged` | Review staged git changes |
| `review <filepath>` | Review a specific file |
| `review branch` or `branch` | Review all changes on current branch vs base |
| Any other text | Treat as a free-form question — still gather relevant code context if possible |

## Step 2: Gather context

Based on the review type, gather the minimum necessary context:

- **Staged changes**: Run `git diff --cached` to get the staged diff
- **Specific file**: Read the file with the Read tool
- **Branch review**: Detect the base branch dynamically:
  1. Try `git rev-parse --verify origin/main` — if it exists, use `main`
  2. Else try `origin/master`
  3. Else use the first remote default branch
  Then run `git diff <base>...HEAD`
- **Free-form question**: If the user references specific files or functions, read those. Otherwise proceed with just the question.

**Context budget**: Keep total context under 8000 characters. If a diff or file is larger:
- For diffs: use `git diff --cached --stat` to summarize, then include only the most relevant hunks
- For files: include only the relevant sections

**Security**: Before constructing the prompt, scan gathered context for secrets. NEVER include:
- API keys, tokens, passwords (patterns like `sk-`, `ghp_`, `AKIA`, `Bearer `)
- .env file contents
- Private keys or certificates

If secrets are detected, redact them with `[REDACTED]` and warn the user.

## Step 3: Construct and send the prompt

Pass the prompt directly to the script using a heredoc via stdin:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/ask-{backend}.sh - --timeout 300 <<'PROMPT'
... constructed prompt here ...
PROMPT
```

Do NOT use temp files. Always use heredoc to pipe the prompt directly.

### Prompt template

```
You are reviewing code in a [language] project.

## Context
[branch name, recent commits, project description if relevant]

## Code to review
[diff or file contents]

## Request
[What the user wants: code review, architecture feedback, specific question, etc.]

Focus on:
- Bugs or logic errors
- Security concerns
- Performance issues
- Better approaches or patterns
- Things that look correct and well-done

Be concise. Prioritize actionable feedback.
```

## Step 4: Present the result

Present the response clearly, noting which AI provided it (e.g. "Codex opinion:", "Gemini opinion:").

### Label each substantive claim with confidence

External AIs vary widely in how grounded their feedback is. Apply this rubric to every concern, recommendation, or claim in the response:

| Level | Meaning |
|-------|---------|
| HIGH | The external AI cited specific code, named a function or line, or pointed to evidence visible in the diff/file you sent it |
| MEDIUM | The AI made a defensible argument from general principles or framework behavior, but didn't cite specifics from your code |
| LOW | The AI was hedging, speculating, or applying generic best practices without grounding in the actual code under review |

Format each point as:

> **[CONFIDENCE]** *external AI's claim* — Your assessment: *agree / partial / disagree*, with one-line reason

A LOW-confidence external opinion is a starting point for investigation, not a conclusion. A HIGH-confidence external opinion that contradicts your own analysis warrants a closer look at the actual code rather than dismissing it.

## Important notes

- All scripts default to 180s timeout. Use `--timeout 300` for larger reviews.
- If a script fails, suggest checking authentication for that backend.
