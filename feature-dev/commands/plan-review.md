---
allowed-tools:
  - Agent
  - Read
  - Glob
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/herdr-pane.sh *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/features.py *)
argument-hint: "[plan-file-path — optional; auto-discovers PLAN-*.md if omitted] [--pane|--no-pane]"
description: |
  Use to re-validate a PLAN-*.md edited by hand, or one written before explore-plan reviewed its own plans. Outputs Blocking / Should Address / Nice to Have findings.
  Do NOT use right after /feature-dev:explore-plan (it already ran this review), for code review, or for SPEC review (use /feature-dev:spec-review).
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
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this command and proceed with your assigned task.
</SUBAGENT-STOP>

## Context
- **Repository**: !`git remote get-url origin`
- **Current branch**: !`git branch --show-current`
- **Plan argument**: $ARGUMENTS
- **Feature store**: each feature lives in `.feature-dev/features/<slug>/`, managed by `${CLAUDE_PLUGIN_ROOT}/scripts/features.py` (pass `--root <repo root>`). Layout: [artifact-locations.md](../skills/spec-driven-development/references/artifact-locations.md).

## Phase 0: Resolve the Plan File

`--pane` / `--no-pane` are flags: drop them before reading `$ARGUMENTS` below.

1. **If `$ARGUMENTS` is provided** → use it as the path to the plan file. If the file does not exist, STOP and report. Refuse any path outside `.feature-dev/features/` (a root `PLAN-*.md`, or the layout older than 2.0.0) in one line, naming `.feature-dev/features/<slug>/` as the only place plans live.
2. **If `$ARGUMENTS` is empty** → auto-discover plan files. Run `${CLAUDE_PLUGIN_ROOT}/scripts/features.py list --json --root <repo root>` and take the `artifacts` entries with `kind: "plan"` (each has a `path`). From the candidates:
   - **0 plans** → STOP and ask the user to provide a path or run `/feature-dev:explore-plan` first.
   - **1 plan** → use it. Inform the user: "Auto-selected plan: `<plan path>` (feature: <name>)".
   - **2+ plans** → use AskUserQuestion to let the user pick (label = `feature:` value, description = `<filename>`).

## Herdr pane

With `--pane`, run Phases 1–2 in a Herdr pane in **collect** mode: follow
`${CLAUDE_PLUGIN_ROOT}/references/herdr-pane.md`. It falls back to the normal run outside
Herdr. Questions the run asks happen in the pane, and Herdr notifies the user.
Resolve the plan here first (Phase 0), so the pane receives a path.

- **Command string**: `/feature-dev:plan-review <resolved plan path> --no-pane`
- **Report**: `<scratchpad dir>/plan-review-<slug>.md`
- **Present**: the Blocking / Should Address / Nice to Have list as the report has it.

## Phase 1: Validate

Use the Agent tool to invoke the `spec-plan-validator` subagent with:
- `artifact_type`: `plan`
- `artifact_path`: the resolved path from Phase 0
- `feature`: that feature's entry from `${CLAUDE_PLUGIN_ROOT}/scripts/features.py list --json --root <repo root>` (matched by slug), so the agent sees its state without parsing frontmatter

The agent will:
1. Read the plan file
2. Locate the source spec: the `SPEC-*.md` in the plan's own feature folder, or, for a sibling-repo spec, the path on the `Source spec:` line in the PLAN body; verify it exists
3. Run the PLAN-specific structural checklist, including the `### Baseline` section (steps whose `Verify:` is `hollow` or `not-run: missing` on HEAD and not yet `accepted by user`), `Kind:` / `Pins:` usage, and the step-count cap
4. Check that every Files to Modify path exists and no Files to Create path already does
5. When the source spec numbers its ACs, trace them: an AC no step `Covers:` (unless Risks names it as deliberately left out), a `Covers:` citing an id the spec does not define, and a behavior step without `Covers:` are Should Address, and it reports `AC coverage: covered/total`
6. Emit a categorical report (Blocking / Should Address / Nice to Have) with section references
7. State explicitly when no blocking gaps exist

## Phase 2: Present and Stop

After the agent returns:

1. Show the report verbatim to the user.
2. Do **NOT** modify the PLAN file — findings are advisory; the user decides what to address.
3. End with the next commands, using the resolved plan path, then stop:

   ```
   Next: /clear, then /feature-dev:tdd <plan path>   (a fresh context leaves /tdd's budget to the steps)
   Or edit the plan and re-run /feature-dev:plan-review <plan path>; regenerate it with /feature-dev:explore-plan if exploration was incomplete
   ```

## Rules

- **Never auto-fix the plan.** Findings are advisory. The user must explicitly edit and re-run, or re-invoke `/feature-dev:explore-plan` to regenerate.
- **Never opine on technical choices.** This command checks structure, completeness, and that the paths the plan names exist — not whether the implementation order or chosen approach is right.
- **Never gate other commands on this.** `/feature-dev:explore-plan` already runs this review on every plan it writes; this command is the standalone re-check for a plan changed since.
- **The PLAN file is a local working artifact.** Never suggest committing it and never run git commands against it. It should be listed in the project's `.gitignore` (added automatically by `/feature-dev:explore-plan`).
