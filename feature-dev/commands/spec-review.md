---
allowed-tools:
  - Agent
  - Read
  - Glob
argument-hint: "[spec-file-path — optional; auto-discovers SPEC-*.md if omitted]"
description: |
  Use to validate a SPEC-*.md for gaps before planning or implementation. Outputs Blocking / Should Address / Nice to Have findings.
  Do NOT use to verify implementation (use /prd:validate).
keywords:
  - spec-review
  - spec-validation
  - gap-analysis
  - feature-dev
triggers:
  - "review the spec"
  - "validate the spec"
  - "find gaps in the spec"
  - "is the spec ready"
hooks:
  - event: Stop
    once: true
    command: |
      echo "Spec review complete. Next steps:"
      echo "  - /feature-dev:explore-plan to explore the codebase and produce a plan"
      echo "  - /feature-dev:tdd to start test-driven implementation"
      echo "  - Edit the SPEC and re-run /feature-dev:spec-review to confirm fixes"
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this command and proceed with your assigned task.
</SUBAGENT-STOP>

## Context
- **Repository**: !`git remote get-url origin`
- **Current branch**: !`git branch --show-current`
- **Spec argument**: $ARGUMENTS

## Phase 0: Resolve the Spec File

1. **If `$ARGUMENTS` is provided** → use it as the path to the spec file. If the file does not exist, STOP and report.
2. **If `$ARGUMENTS` is empty** → auto-discover spec files. Use Glob with pattern `SPEC-*.md` in the repo root, then read each file's frontmatter. Do **not** filter by `status:` — a spec with `status: implemented` is still legitimate to re-review (e.g., for retro learning). From the candidates:
   - **0 specs** → STOP and ask the user to provide a path or run `/feature-dev:spec` first.
   - **1 spec** → use it. Inform the user: "Auto-selected spec: `SPEC-<slug>.md` (feature: <name>, status: <status>)".
   - **2+ specs** → use AskUserQuestion to let the user pick (label = `feature:` value, description = `<filename> — status: <status>`).

## Phase 1: Validate

Use the Agent tool to invoke the `spec-plan-validator` subagent with:
- `artifact_type`: `spec`
- `artifact_path`: the resolved path from Phase 0

The agent will:
1. Read the spec file
2. Run the SPEC-specific structural checklist
3. Emit a categorical report (Blocking / Should Address / Nice to Have) with section references
4. State explicitly when no blocking gaps exist

## Phase 2: Present and Stop

After the agent returns:

1. Show the report verbatim to the user.
2. Do **NOT** modify the SPEC file — findings are advisory; the user decides what to address.
3. Stop. The Stop hook surfaces the next-step options.

## Rules

- **Never auto-fix the spec.** Findings are advisory. The user must explicitly edit and re-run if they want.
- **Never opine on technical choices.** This command checks structure and completeness only — not whether the chosen approach is right. That's a code-review or `/discuss:feature` concern.
- **Never gate other commands on this.** This command is opt-in by design. Surfacing findings to the user is the entire job; they choose whether to act.
- **The SPEC file is a local working artifact.** Never suggest committing it and never run git commands against it. It should be listed in the project's `.gitignore` (added automatically by `/feature-dev:spec`).
