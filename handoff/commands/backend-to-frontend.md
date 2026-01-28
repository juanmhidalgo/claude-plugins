---
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(git diff *)
  - Bash(git log *)
  - Bash(git show *)
argument-hint: "[file or endpoint path]"
description: Generate handoff prompt for frontend after backend API changes
keywords:
  - api-handoff
  - backend-to-frontend
  - api-changes
  - cross-team
  - schema-changes
triggers:
  - "generate frontend handoff"
  - "communicate API changes to frontend"
  - "create handoff for frontend team"
  - "API changed, tell frontend"
hooks:
  - event: Stop
    once: true
    command: |
      echo "Handoff prompt generated. Next steps:"
      echo "  - Copy the prompt to the frontend team/agent"
      echo "  - Or save to a file for async handoff"
---

# Backend to Frontend Handoff

Generate a structured prompt that a frontend agent can use to implement changes after backend API modifications.

## Context

- **Current branch**: !`git branch --show-current`
- **Recent commits**: !`git log --oneline -5`

**Target**: $ARGUMENTS

---

<best_practices>
@handoff/skills/api-change-documentation/SKILL.md
</best_practices>

## Instructions

### Step 1: Identify API Changes

1. If a file or endpoint path is provided, read the relevant files
2. Use `git diff` to identify recent changes to API endpoints, schemas, or response structures
3. Look for changes in:
   - Route/endpoint definitions
   - Request/response schemas
   - Validation rules
   - Error responses
   - Authentication/authorization changes

### Step 2: Analyze the Changes

For each changed endpoint, document:
- HTTP method and path
- What changed (new field, removed field, type change, etc.)
- Whether it's a breaking change
- Any new error conditions

### Step 3: Generate TypeScript Schema

Convert the updated response/request structures to TypeScript interfaces:
- Use strict typing (no `any`)
- Include JSDoc comments for non-obvious fields
- Mark optional fields with `?`
- Include union types for enums

### Step 4: Generate Handoff Prompt

Output the following structured prompt that can be given to a frontend agent:

---

## Handoff Prompt Output Format

```markdown
# Frontend Implementation: [Feature/Change Name]

## Context

[1-2 sentences explaining why this change was made and what business problem it solves]

## Changed Endpoints

### [METHOD] /api/path

**Change type**: [New endpoint | Modified response | Modified request | Deprecated]

**Summary**: [What changed in plain language]

## Updated TypeScript Schema

\`\`\`typescript
// [Filename suggestion, e.g., types/api/users.ts]

interface ResponseType {
  // ... generated types
}
\`\`\`

## Migration Guide

### Breaking Changes

- [ ] [List any breaking changes that require immediate attention]

### Non-Breaking Changes

- [ ] [List additive changes that are backwards compatible]

## Implementation Checklist

- [ ] Update API client types
- [ ] Update components consuming this data
- [ ] Handle new error cases
- [ ] Update tests
- [ ] [Any endpoint-specific tasks]

## Edge Cases to Handle

- [Null handling considerations]
- [Empty array vs null distinction]
- [Pagination changes if applicable]
- [Error state changes]

## Notes

[Any additional context the frontend developer should know]
```

---

## Guidelines

- Focus on **what changed**, not implementation details of the backend
- Always include TypeScript types - frontend devs need exact schemas
- Explicitly mark breaking vs non-breaking changes
- Include concrete examples of before/after payloads when helpful
- Don't assume frontend knows the backend stack
- Follow the best practices from the `<best_practices>` section above
