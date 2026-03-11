---
allowed-tools:
  - Agent
argument-hint: [feature-name | short-description]
description: Generate a concise product mini-PRD for a new feature
keywords:
  - prd
  - product-requirements
  - feature-spec
  - mini-prd
triggers:
  - "create a PRD"
  - "write product requirements"
  - "generate feature spec"
  - "new feature PRD"
hooks:
  - event: Stop
    once: true
    command: |
      echo "PRD created. Next steps:"
      echo "  - /prd:analyze to identify gaps before implementation"
      echo "  - /discuss:feature to critically analyze the PRD"
      echo "  - /feature-dev:explore-plan to explore codebase and plan"
---

## Feature Request

$ARGUMENTS

## Instructions

Use the Agent tool to invoke the `prd-specialist` agent with the feature request above.

The agent will:
1. Detect the project's technical stack automatically
2. Follow adaptive flow (brief input → questions, detailed → draft)
3. Generate mini-PRD and iterate
4. Ask how to deliver (GitHub, ClickUp, file, or display)
