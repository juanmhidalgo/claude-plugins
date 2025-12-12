# PRD Toolkit

Create and manage Product Requirements Documents (PRDs) with AI assistance.

## Installation

```bash
# Add marketplace (if not already added)
/plugin marketplace add juanmhidalgo/claude-plugins

# Install plugin
/plugin install prd-toolkit@juanmhidalgo-plugins
```

## Commands

| Command | Description |
|---------|-------------|
| `/prd:create [feature]` | Generate a concise mini-PRD for a new feature |

## Usage

### Create a new PRD

```
/prd:create user authentication with OAuth
```

The agent will:
1. Detect your project's tech stack automatically
2. Ask clarifying questions if needed
3. Generate a structured mini-PRD
4. Let you iterate and refine
5. Publish to GitHub, ClickUp, or save locally

### Example Output

```markdown
# User Authentication with OAuth

## Overview
Enable users to sign in using their existing Google or GitHub accounts,
reducing friction and improving security.

## Goals
- Reduce signup abandonment by 30%
- Eliminate password management overhead
- Improve account security with OAuth providers

## Acceptance Criteria
- [ ] User can sign in with Google OAuth
- [ ] User can sign in with GitHub OAuth
- [ ] New users are created on first OAuth login
- [ ] Existing users can link OAuth providers

## QA Checklist
- [ ] OAuth flow completes successfully
- [ ] User profile is populated from OAuth data
- [ ] Error states show helpful messages
```

## Features

- **Adaptive flow**: Brief input gets clarifying questions, detailed input gets immediate draft
- **Stack detection**: Automatically detects your project type for tailored criteria
- **Multiple outputs**: GitHub Issues, ClickUp tasks, local files, or just display
- **Iterative**: Refine the PRD through conversation

## Requirements

- `gh` CLI installed and authenticated (for GitHub publishing)
- ClickUp API token (for ClickUp publishing, optional)
