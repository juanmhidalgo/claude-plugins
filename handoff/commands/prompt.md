---
argument-hint: "[additional context]"
description: Generate a self-contained prompt based on the current conversation for use in another repository
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

## Output

Output a single prompt block ready to copy-paste. Do not include preamble or explanation outside the prompt itself.
