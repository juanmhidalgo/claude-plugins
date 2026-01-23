# api-handoff

Coordinate API changes between frontend and backend teams by generating structured "handoff prompts" that another Claude Code agent can use to implement the corresponding changes.

## Installation

```bash
/plugin install api-handoff@juanmhidalgo-plugins
```

## Commands

| Command | Description |
|---------|-------------|
| `/api-handoff:backend-to-frontend [file]` | Generate instructions for frontend after backend API changes |
| `/api-handoff:frontend-to-backend [feature]` | Generate instructions for backend when frontend needs new APIs |

## Use Cases

### Backend to Frontend

After making changes to your API (new endpoints, modified responses, schema changes), use this command to generate a structured prompt that:

- Documents all changed endpoints
- Provides TypeScript interfaces for the updated schemas
- Marks breaking vs non-breaking changes
- Includes migration steps and edge cases

**Example:**
```bash
/api-handoff:backend-to-frontend src/api/users.py
```

### Frontend to Backend

When the frontend needs new data or API modifications, use this command to generate a request that:

- Explains the UI/UX context
- Defines proposed endpoints with request/response schemas
- Specifies validation and error handling needs
- Includes performance considerations

**Example:**
```bash
/api-handoff:frontend-to-backend "need user activity timeline for dashboard"
```

## Workflow

1. **Backend makes API changes** -> Run `/api-handoff:backend-to-frontend`
2. **Copy the generated prompt** to the frontend team or agent
3. **Frontend agent implements** using the structured instructions

Or in reverse:

1. **Frontend needs new data** -> Run `/api-handoff:frontend-to-backend`
2. **Copy the generated prompt** to the backend team or agent
3. **Backend agent implements** using the structured requirements

## Skills

### api-change-documentation

Best practices for documenting API changes including:

- Breaking vs non-breaking change identification
- Schema documentation patterns (TypeScript and language-agnostic)
- Common edge cases (null handling, pagination, timestamps)
- Versioning guidelines
- Handoff checklists

## Requirements

- Git repository (for diff analysis)
- Source files accessible for reading
