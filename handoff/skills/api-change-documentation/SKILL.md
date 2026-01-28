---
name: api-change-documentation
description: |
  Use when generating cross-team API handoff prompts. Provides structured output
  formats for communicating API changes between frontend and backend teams.
  Includes breaking change classification, schema documentation patterns, and
  handoff checklists specific to this workflow. Do NOT use for general API
  documentation or OpenAPI spec generation.
keywords:
  - api-documentation
  - cross-team
  - handoff
  - schema-changes
  - breaking-changes
triggers:
  - "document API changes"
  - "communicate changes to frontend"
  - "request backend changes"
user-invocable: false
---

# API Cross-Team Handoff Guidelines

This skill provides the specific output formats and classification rules for generating handoff prompts between frontend and backend teams.

## Breaking Change Classification

Use this classification when generating handoff prompts:

| Change Type | Breaking? | Action Required |
|-------------|-----------|-----------------|
| Remove response field | YES | Migration guide required |
| Change field type | YES | Migration guide required |
| Rename field | YES | Migration guide required |
| Change endpoint path/method | YES | Migration guide required |
| Add required request param | YES | Migration guide required |
| Add optional response field | NO | Document only |
| Add optional query param | NO | Document only |
| Add new endpoint | NO | Document only |
| Deprecate (not remove) field | NO | Document with timeline |

## Schema Output Formats

### For Frontend Handoffs (TypeScript)

```typescript
interface Example {
  id: string;
  name: string | null;           // null = field present, value absent
  role: 'admin' | 'user';        // union for enums
  metadata?: Record<string, unknown>;  // ? = field may be omitted
}
```

### For Backend Handoffs (Language-Agnostic)

```json
{
  "id": "string (UUID v4)",
  "count": "integer (min: 0, max: 1000)",
  "status": "enum: pending | active | completed",
  "config": {
    "enabled": "boolean (default: true)"
  }
}
```

## Handoff Checklists

### Backend → Frontend

- [ ] All changed endpoints listed with HTTP method
- [ ] TypeScript interfaces for all affected types
- [ ] Breaking changes marked with migration steps
- [ ] New error scenarios with status codes
- [ ] Before/after payload examples

### Frontend → Backend

- [ ] UI/UX context explaining the need
- [ ] Request/response schemas (language-agnostic)
- [ ] Validation requirements
- [ ] Error scenarios to handle
- [ ] Performance expectations (call frequency, data volume)

## Edge Cases to Always Document

1. **Null vs omission**: `field: null` vs field not present
2. **Empty arrays**: `[]` vs `null` vs omitted
3. **Pagination**: zero/one-based, default size, cursor vs offset
4. **Timestamps**: ISO 8601, timezone, precision
