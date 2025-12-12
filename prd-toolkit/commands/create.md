---
allowed-tools: Task
argument-hint: [feature-name | short-description]
description: Generate a concise product mini-PRD for a new feature
---

## Feature Request

$ARGUMENTS

## Instructions

Use the Task tool to invoke the `prd-specialist` agent with the feature request above.

The agent will:
1. Detect the project's technical stack automatically
2. Follow adaptive flow (brief input → questions, detailed → draft)
3. Generate mini-PRD and iterate
4. Ask how to deliver (GitHub, ClickUp, file, or display)
