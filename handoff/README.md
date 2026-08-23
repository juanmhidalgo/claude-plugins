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
| `/handoff:receive <prompt>` | Process a received handoff with research-first verification and plan mode |

## Use Cases

### Cross-Repository Prompt

When working in one repo and you need to continue or request work in a related repo (frontend to DevOps, backend to backend, etc.), generate a self-contained prompt:

```bash
/handoff:prompt
```

The command synthesizes the current conversation into an actionable prompt with all necessary context (IDs, configurations, decisions made) so the receiving agent needs no additional background.

### Direct Delivery to a Live Session

All three generator commands can skip the copy-paste step: if [cross-session messaging](https://code.claude.com/docs/en/cross-session-messaging) is available and a Claude Code session is already running in the target repository, the command offers to deliver the handoff there directly (`ListAgents` + `SendMessage`), and asks to be notified when the receiving session finishes. When messaging isn't available (Claude Code < v2.1.224, Bedrock/Vertex/Foundry, or no live target session), the commands fall back to the normal copy-paste output.

The message sent is the full handoff as plain text — cross-session messages never execute slash commands on the receiving side, so the prompt always stands on its own.

### Backend to Frontend

After making changes to your API (new endpoints, modified responses, schema changes), generate a structured prompt with TypeScript interfaces and migration guides:

```bash
/handoff:backend-to-frontend src/api/users.py
```

### Receiving a Handoff

When you receive a handoff prompt from another repo or team, use `receive` to process it safely. It forces research of the local codebase, verifies claims against actual code, and enters plan mode before any implementation:

```bash
/handoff:receive <paste the handoff prompt here>
```

Handoffs that arrive as cross-session messages get the same treatment — verification first, no extra trust for coming from another session — plus a reply back to the sender with any discrepancies found and a completion summary.

### Frontend to Backend

When the frontend needs new data or API modifications, generate a request with proposed schemas and performance context:

```bash
/handoff:frontend-to-backend "need user activity timeline for dashboard"
```

## Skills

### api-design

Contract-first API design guidance including:

- Hyrum's Law awareness (every observable behavior becomes a commitment)
- Error semantics (consistent error format across endpoints)
- Naming conventions (REST, query params, response fields)
- Boundary validation patterns (validate at edges, trust internal code)
- Anti-rationalization table for common API design shortcuts

### api-change-documentation

Best practices for documenting API changes including:

- Breaking vs non-breaking change classification
- Schema documentation patterns (TypeScript and language-agnostic)
- Common edge cases (null handling, pagination, timestamps)
- Handoff checklists

## Requirements

- Git repository (for diff analysis in API handoff commands)
