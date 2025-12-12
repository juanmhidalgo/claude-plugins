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
| `/prd:refine [file \| issue-url]` | Improve existing PRD or convert vague issue to PRD |
| `/prd:validate [file \| issue-url]` | Verify implementation matches PRD criteria |

## Usage

### Create a new PRD

```
/prd:create user authentication with OAuth
```

The agent will:
1. Ask clarifying questions if needed
2. Generate a structured mini-PRD
3. Let you iterate and refine
4. Publish to GitHub, ClickUp, or save locally

### Refine or convert to PRD

```
/prd:refine ./docs/prd-auth.md
/prd:refine https://github.com/owner/repo/issues/123
/prd:refine paste
```

The agent will:
1. Detect if input is already a PRD or a vague issue
2. If PRD: analyze and suggest improvements
3. If vague issue: convert to structured PRD format
4. Apply changes to file or GitHub issue

### Validate implementation

```
/prd:validate ./docs/prd-auth.md
/prd:validate https://github.com/owner/repo/issues/123
```

The agent will:
1. Extract acceptance criteria from PRD
2. Search codebase for implementations
3. Generate validation report with ✅/⚠️/❌ status
4. Offer to create issues for missing items

## PRD Format

```markdown
# Feature Name

## Overview
[Problem + solution in 2-3 sentences]

## Goals
- [Business/user objective]

## User Stories
- As a [role], I want [action] so that [benefit]

## Acceptance Criteria
- [ ] [Observable behavior from user perspective]

## Out of Scope
- [What this version does NOT include]

## QA Checklist
- [ ] [User scenario to validate]
```

## Philosophy

PRDs focus on **observable behavior**, not implementation details:

| Good ✅ | Bad ❌ |
|---------|--------|
| User can sign in with Google | Implement OAuth 2.0 with PKCE |
| Session stays active for 24 hours | Store JWT in Redis with 24h TTL |
| Error shows retry option | Use exponential backoff retry |

## Requirements

- `gh` CLI installed and authenticated (for GitHub features)
- ClickUp API token (for ClickUp publishing, optional)
