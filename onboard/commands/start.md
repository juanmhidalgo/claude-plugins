---
description: |
  Generate an onboarding guide for a new developer joining this project.
  Explores the codebase and produces a structured overview of architecture, patterns, and key files.
  Use when joining a new project or helping someone else get started.
argument-hint: "[focus-area]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Task
hooks:
  - event: Stop
    once: true
    command: |
      echo ""
      echo "Onboarding guide complete."
      echo "  - /onboard:explore <topic> to dive deeper"
      echo "  - /onboard:architecture for visual overview"
---

# Project Onboarding

Generate a comprehensive onboarding guide for this project.

**Focus area** (optional): $ARGUMENTS

## Phase 1: Project Discovery

<exploration>
Use the Task tool with `subagent_type: "Explore"` to investigate:

1. **Project Type** - What kind of project is this? (web app, API, CLI, library)
2. **Tech Stack** - Languages, frameworks, major dependencies
3. **Entry Points** - Main files, how the app starts
4. **Project Structure** - Directory layout and organization pattern
5. **Configuration** - Key config files, environment setup
6. **Documentation** - README, CLAUDE.md, docs folder

If a focus area was provided, prioritize that domain.
</exploration>

## Phase 2: Generate Onboarding Guide

<output_format>
Produce a structured guide:

```markdown
# [Project Name] Onboarding Guide

## Quick Start
- How to install dependencies
- How to run the project
- How to run tests

## Architecture Overview
- High-level description (2-3 sentences)
- Key directories and their purpose
- Data flow (how requests/data move through the system)

## Tech Stack
| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | ... | ... |
| Backend | ... | ... |
| Database | ... | ... |

## Key Files to Read First
1. `path/to/file` - Why it's important
2. `path/to/file` - Why it's important
3. `path/to/file` - Why it's important

## Common Patterns
- [Pattern 1]: How it's used, example file
- [Pattern 2]: How it's used, example file

## Development Workflow
- How to create a feature branch
- How to run linters/formatters
- How to submit a PR

## Gotchas & Tribal Knowledge
- Things that aren't obvious from the code
- Common mistakes new developers make
- Quirks specific to this project

## Next Steps
- Suggested first task for a new developer
- Areas to explore based on your role
```
</output_format>

<critical_rules>
<rule priority="blocking">
Use the Explore agent to gather real information. Don't make assumptions.
</rule>

<rule priority="blocking">
Include specific file paths with `file:line` references where helpful.
</rule>

<rule priority="recommended">
If CLAUDE.md exists, incorporate its guidance into the onboarding doc.
</rule>

<rule priority="recommended">
Keep the guide actionable - a new dev should be productive within hours.
</rule>
</critical_rules>
