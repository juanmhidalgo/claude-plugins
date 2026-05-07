---
argument-hint: "[additional context]"
description: |
  Use to generate a self-contained prompt based on the current conversation for another repository.
  Do NOT use for in-repo task tracking — handoffs are for cross-repo work only.
keywords:
  - cross-repo
  - handoff
  - prompt
  - context-transfer
triggers:
  - "generate a prompt for the other repo"
  - "write a prompt for another repository"
  - "create handoff prompt"
hooks:
  - event: Stop
    once: true
    command: |
      echo "Prompt generated. Copy it to use in the other repository."
---

# Cross-Repository Prompt

Generate a self-contained prompt based on the current conversation that can be used with Claude Code in another repository.

## Additional context from user

$ARGUMENTS

## Instructions

Review the conversation history and generate a prompt that:

1. **Is fully self-contained** - the receiving agent has zero context about this conversation
2. **Includes all specific details** - IDs, resource names, configurations, domain names, error messages, or any other concrete identifiers discussed
3. **States the objective clearly** - what action needs to be taken in the other repository
4. **Provides decision context** - any decisions made or options considered that the other agent should know about

## Formatting

- Use fenced code blocks with language identifier for any code, JSON, config, or shell commands (e.g., ```json, ```bash)
- Use inline code backticks for endpoints, paths, variable names, and short identifiers (e.g., `POST /api/v2/users`)

## Verification (before presenting)

Before outputting the prompt, cross-reference it against the conversation:

1. **Re-read the user's original request** and any follow-up messages
2. **Check every requirement** — roles, permissions, constants, schema fields, endpoints, config values mentioned in the conversation
3. **Check every decision** — if the conversation discussed tradeoffs or made choices, verify the prompt includes the chosen approach and why
4. **Check specifics** — IDs, error codes, field names, migration steps. Vague summaries lose critical details.

If anything is missing, add it before presenting. Do NOT ask the user — just include it.

## Output

Output a single prompt block ready to copy-paste. Do not include preamble or explanation outside the prompt itself.
