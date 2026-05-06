---
name: api-design
description: |
  Use when designing new API endpoints, defining module boundaries, or establishing contracts between teams.
  Do NOT use for general code quality — use api-change-documentation for handoffs.
keywords:
  - api-design
  - rest-api
  - contract-first
  - interface-design
  - schema
triggers:
  - "design an API"
  - "define API contract"
  - "create endpoints"
  - "API schema"
code-triggers:
  - "app.get("
  - "app.post("
  - "app.patch("
  - "router."
  - "APIRouter"
  - "FastAPI"
  - "@app.route"
  - "createTask"
allowed-tools:
  - Read
  - Grep
  - Glob
---

# API and Interface Design

## Contract-First Design

Define the interface before implementing it. The contract is the spec — implementation follows.

1. **Define types** (input and output schemas) before writing route handlers
2. **Document error semantics** — pick one error format and use it everywhere
3. **Add validation at boundaries** — trust internal code after that
4. **Design for extension** — prefer adding optional fields over modifying existing ones

## Hyrum's Law

> With sufficient users, all observable behaviors become depended on — regardless of your contract.

Every public behavior (including error message text, timing, ordering) becomes a de facto commitment. Design implications:
- Be intentional about what you expose
- Don't leak implementation details
- Plan for deprecation at design time

## Error Semantics

Pick one strategy. Use it everywhere. Never mix patterns.

| Status | Meaning |
|--------|---------|
| 400 | Client sent invalid data |
| 401 | Not authenticated |
| 403 | Authenticated but not authorized |
| 404 | Resource not found |
| 409 | Conflict (duplicate, version mismatch) |
| 422 | Validation failed (semantically invalid) |
| 500 | Server error (never expose internals) |

Every error response follows the same shape:
```json
{ "error": { "code": "MACHINE_READABLE", "message": "Human-readable", "details": {} } }
```

## Naming Conventions

| Pattern | Convention | Example |
|---------|-----------|---------|
| REST endpoints | Plural nouns, no verbs | `GET /api/tasks` |
| Query params | camelCase | `?sortBy=createdAt` |
| Response fields | camelCase | `{ createdAt, taskId }` |
| Boolean fields | is/has/can prefix | `isComplete` |
| Enum values | UPPER_SNAKE | `"IN_PROGRESS"` |

## Design Checklist

- [ ] Every endpoint has typed input and output schemas
- [ ] Error responses follow a single consistent format
- [ ] Validation happens at system boundaries only
- [ ] List endpoints support pagination
- [ ] New fields are additive and optional (backward compatible)
- [ ] Naming follows consistent conventions

## Anti-Rationalizations

| Excuse | Reality |
|--------|---------|
| "We'll document the API later" | The types ARE the documentation. Define them first. |
| "We don't need pagination yet" | You will at 100+ items. Add it from the start. |
| "Nobody uses that undocumented behavior" | Hyrum's Law: if it's observable, somebody depends on it. |
| "Internal APIs don't need contracts" | Internal consumers are still consumers. Contracts prevent coupling. |

For detailed patterns and code examples, see [api-patterns.md](references/api-patterns.md).
