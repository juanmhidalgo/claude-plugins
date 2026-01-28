# handoff

Generate self-contained prompts for use in other repositories. Includes specialized API handoff commands for frontend/backend coordination.

## Installation

```bash
/plugin install handoff@juanmhidalgo-plugins
```

## Commands

| Command | Description |
|---------|-------------|
| `/handoff:prompt [context]` | Generate a prompt from the current conversation for use in another repo |
| `/handoff:backend-to-frontend [file]` | Generate instructions for frontend after backend API changes |
| `/handoff:frontend-to-backend [feature]` | Generate instructions for backend when frontend needs new APIs |

## Use Cases

### Cross-Repository Prompt

When working in one repo and you need to continue or request work in a related repo (frontend to DevOps, backend to backend, etc.), generate a self-contained prompt:

```bash
/handoff:prompt
```

The command synthesizes the current conversation into an actionable prompt with all necessary context (IDs, configurations, decisions made) so the receiving agent needs no additional background.

### Backend to Frontend

After making changes to your API (new endpoints, modified responses, schema changes), generate a structured prompt with TypeScript interfaces and migration guides:

```bash
/handoff:backend-to-frontend src/api/users.py
```

### Frontend to Backend

When the frontend needs new data or API modifications, generate a request with proposed schemas and performance context:

```bash
/handoff:frontend-to-backend "need user activity timeline for dashboard"
```

## Skills

### api-change-documentation

Best practices for documenting API changes including:

- Breaking vs non-breaking change classification
- Schema documentation patterns (TypeScript and language-agnostic)
- Common edge cases (null handling, pagination, timestamps)
- Handoff checklists

## Requirements

- Git repository (for diff analysis in API handoff commands)
