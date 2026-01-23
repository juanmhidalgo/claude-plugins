---
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(git diff *)
  - Bash(git log *)
argument-hint: "[feature description or file path]"
description: Generate handoff prompt for backend when frontend needs API changes
keywords:
  - api-handoff
  - frontend-to-backend
  - api-request
  - cross-team
  - new-endpoint
triggers:
  - "request backend API"
  - "need new endpoint"
  - "ask backend for changes"
  - "frontend needs API support"
hooks:
  - event: Stop
    once: true
    command: |
      echo "Handoff prompt generated. Next steps:"
      echo "  - Copy the prompt to the backend team/agent"
      echo "  - Or save to a file for async handoff"
---

# Frontend to Backend Handoff

Generate a structured prompt that a backend agent can use to implement API changes requested by frontend requirements.

## Context

- **Current branch**: !`git branch --show-current`

**Target**: $ARGUMENTS

---

<best_practices>
@api-handoff/skills/api-change-documentation/SKILL.md
</best_practices>

## Instructions

### Step 1: Understand the Frontend Requirement

1. If a file path is provided, read the relevant frontend code
2. Identify what data the frontend needs:
   - What UI component or feature requires this?
   - What data is currently missing or insufficient?
   - What user action triggers this need?

### Step 2: Analyze Existing APIs

1. Search for related existing endpoints
2. Determine if this can be solved by:
   - Extending an existing endpoint
   - Adding query parameters
   - Creating a new endpoint

### Step 3: Define the Request

Document what the frontend needs:
- Data fields required
- Filtering/sorting/pagination needs
- Expected response structure
- Error scenarios to handle

### Step 4: Generate Handoff Prompt

Output the following structured prompt that can be given to a backend agent:

---

## Handoff Prompt Output Format

```markdown
# Backend Implementation: [Feature/API Name]

## Context

[1-2 sentences explaining the UI/UX requirement and why this API change is needed]

**Requesting team**: Frontend
**Priority**: [High | Medium | Low]
**Blocking**: [Yes/No - is frontend blocked waiting for this?]

## Requirement Summary

[Plain language description of what data the frontend needs and how it will be used]

## Proposed Endpoint(s)

### [METHOD] /api/suggested/path

**Purpose**: [What this endpoint does]

**Request**:
```json
{
  "field": "type - description",
  "optional_field?": "type - description"
}
```

**Query Parameters** (if applicable):
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `param` | `string` | No | Description |

**Response**:
```json
{
  "data": {
    "field": "type - description"
  },
  "meta": {
    "total": "number - for paginated responses"
  }
}
```

## Validation Requirements

- [ ] [Field validation rules]
- [ ] [Business logic constraints]
- [ ] [Authorization requirements]

## Error Scenarios

| Scenario | Expected Status | Error Code |
|----------|-----------------|------------|
| [Scenario] | 400/404/etc | `ERROR_CODE` |

## Performance Considerations

- Expected call frequency: [e.g., "once per page load", "on every keystroke"]
- Data volume: [e.g., "typically 10-50 items", "could be 1000+ records"]
- Caching: [suggestions for caching strategy if applicable]

## Alternatives Considered

[If applicable, mention alternatives that were ruled out and why]

## Questions for Backend

- [ ] [Any clarifications needed from backend team]

## Frontend Implementation Timeline

[When frontend plans to integrate this - helps backend prioritize]
```

---

## Guidelines

- Keep the request **language-agnostic** - don't assume Python, Go, Node, etc.
- Use JSON Schema-style pseudocode for request/response bodies
- Focus on **what** is needed, not **how** to implement it
- Include performance context so backend can optimize appropriately
- Be explicit about error handling needs - frontend needs to know what to catch
- Include authorization requirements if the endpoint needs specific permissions
- Follow the best practices from the `<best_practices>` section above
