---
allowed-tools:
  - Agent
  - Read
  - Glob
argument-hint: "[plan-file-path — optional; auto-discovers PLAN-*.md if omitted]"
description: |
  Use to validate a PLAN-*.md for gaps before starting TDD implementation. Outputs Blocking / Should Address / Nice to Have findings.
  Do NOT use for code review or SPEC review (use /feature-dev:spec-review).
keywords:
  - plan-review
  - plan-validation
  - gap-analysis
  - feature-dev
triggers:
  - "review the plan"
  - "validate the plan"
  - "find gaps in the plan"
  - "is the plan ready"
hooks:
  - event: Stop
    once: true
    command: |
      echo "Plan review complete. Next steps:"
      echo "  - /feature-dev:tdd to start test-driven implementation"
      echo "  - /feature-dev:explore-plan to regenerate the plan if exploration was incomplete"
      echo "  - Edit the PLAN and re-run /feature-dev:plan-review to confirm fixes"
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this command and proceed with your assigned task.
</SUBAGENT-STOP>

## Context
- **Repository**: !`git remote get-url origin`
- **Current branch**: !`git branch --show-current`
- **Plan argument**: $ARGUMENTS

## Phase 0: Resolve the Plan File

1. **If `$ARGUMENTS` is provided** → use it as the path to the plan file. If the file does not exist, STOP and report.
2. **If `$ARGUMENTS` is empty** → auto-discover plan files. Use Glob with pattern `PLAN-*.md` in the repo root. From the candidates:
   - **0 plans** → STOP and ask the user to provide a path or run `/feature-dev:explore-plan` first.
   - **1 plan** → use it. Inform the user: "Auto-selected plan: `PLAN-<slug>.md` (feature: <name>)".
   - **2+ plans** → use AskUserQuestion to let the user pick (label = `feature:` value, description = `<filename>`).

## Phase 1: Validate

Use the Agent tool to invoke the `spec-plan-validator` subagent with:
- `artifact_type`: `plan`
- `artifact_path`: the resolved path from Phase 0

The agent will:
1. Read the plan file
2. If frontmatter `source_spec:` is set, verify the linked SPEC file exists
3. Run the PLAN-specific structural checklist
4. Emit a categorical report (Blocking / Should Address / Nice to Have) with section references
5. State explicitly when no blocking gaps exist

## Phase 2: Present and Stop

After the agent returns:

1. Show the report verbatim to the user.
2. Do **NOT** modify the PLAN file — findings are advisory; the user decides what to address.
3. Stop. The Stop hook surfaces the next-step options.

## Rules

- **Never auto-fix the plan.** Findings are advisory. The user must explicitly edit and re-run, or re-invoke `/feature-dev:explore-plan` to regenerate.
- **Never opine on technical choices.** This command checks structure and completeness only — not whether the implementation order or chosen approach is right.
- **Never gate other commands on this.** This command is opt-in by design.
- **The PLAN file is a local working artifact.** Never suggest committing it and never run git commands against it. It should be listed in the project's `.gitignore` (added automatically by `/feature-dev:explore-plan`).
