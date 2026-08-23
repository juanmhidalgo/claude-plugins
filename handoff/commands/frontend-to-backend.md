---
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(git diff *)
  - Bash(git log *)
  - ListAgents
  - SendMessage
argument-hint: "[feature description or file path]"
description: |
  Use to generate a handoff prompt for the backend team when the frontend needs new APIs or schema changes.
  Do NOT use when frontend requirements are still unclear — use /discuss:feature to clarify scope first.
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
      echo "  - Or let Claude send it to a live backend session directly"
      echo "  - Or save to a file for async handoff"
---

# Frontend to Backend Handoff

Generate a structured prompt that a backend agent can use to implement API changes requested by frontend requirements.

## Context

- **Current branch**: !`git branch --show-current`

**Target**: $ARGUMENTS

---

<best_practices>
@handoff/skills/api-change-documentation/SKILL.md
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

## Formatting

- Use fenced code blocks with language identifier for any code, JSON, config, or shell commands (e.g., ```json, ```bash)
- Use inline code backticks for endpoints, paths, variable names, and short identifiers (e.g., `POST /api/v2/users`)

## Step 5: Verify Completeness

Before outputting the handoff, cross-reference against the frontend code:

1. **Re-read the frontend code** — every data need identified in Step 1 must appear in the proposed endpoints
2. **Check authorization** — if the UI has role-based visibility or permission checks, the handoff must specify which roles/permissions are required
3. **Check all data fields** — compare what the frontend component renders/uses against what the proposed response includes. Missing fields cause blocked frontend work.
4. **Check user actions** — every user interaction that triggers an API call must have a corresponding endpoint or parameter

If anything is missing, add it. Do NOT present an incomplete handoff.

## Step 6: Deliver (optional, after presenting)

If cross-session messaging is available, offer to deliver the handoff directly to a live backend session:

1. Call `ListAgents`. If the tool is unavailable or errors, skip this step silently — copy-paste remains the fallback.
2. Identify the local session working in the **backend repository**. Match by working directory when the listing shows one; if it doesn't, fall back to the session's name. If neither is conclusive, treat it as zero matches.
3. Exactly one match: ask the user whether to send it there. If they agree, deliver the full handoff verbatim as plain text with `SendMessage`, setting `notify_when_idle: true` so this session hears back when the backend session finishes.
4. Zero or multiple matches: list candidates and let the user pick or decline — never guess.
5. Slash commands inside a cross-session message arrive as plain text and are NOT executed; the handoff must stand on its own. A refused or held message is not an error to retry — report it and fall back to copy-paste.

## Guidelines

- Keep the request **language-agnostic** - don't assume Python, Go, Node, etc.
- Use JSON Schema-style pseudocode for request/response bodies
- Focus on **what** is needed, not **how** to implement it
- Include performance context so backend can optimize appropriately
- Be explicit about error handling needs - frontend needs to know what to catch
- Include authorization requirements if the endpoint needs specific permissions
- Follow the best practices from the `<best_practices>` section above
