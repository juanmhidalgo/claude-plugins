---
allowed-tools:
  - Agent
  - Read
  - Glob
  - Edit
  - AskUserQuestion
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
3. Check up to ~15 load-bearing claims the spec makes about the existing code (paths, symbols, field nullability and FK direction, endpoints, migrations, config keys) with Read/Grep/Glob, classifying each `CONFIRMED` / `DRIFTED` / `REFUTED` / `UNVERIFIED` with `file:line` evidence
4. Emit a categorical report (Blocking / Should Address / Nice to Have) with section references, followed by a `## Code claims` table
5. State explicitly when no blocking gaps exist

## Phase 2: Present, Offer Fixes, Stop

After the agent returns:

1. Show the report verbatim to the user, including the `## Code claims` table. Do not drop, re-grade or summarize away a claim: the table is the evidence behind any Blocking or Should Address finding that cites it.
2. **Offer the fixes once.** Sort the Blocking and Should Address findings into two kinds:
   - *Applicable* — the edit follows from the finding itself, with nothing left to choose: a missing AC id, a path or symbol name the code shows `DRIFTED`, a QA item missing for an error-state AC that already exists, a missing frontmatter field whose value is already fixed by the spec or the repo (`type: specification`, `slug:` from the filename).
   - *Needs a decision* — the right content is not known from the spec or the code: a `REFUTED` claim an AC depends on, two sections that contradict each other, a missing section whose content someone has to decide, a missing frontmatter field whose value needs a choice (`feature:`, `branch:` when the spec may predate the current branch). These are never applied; they stay in the brief for the user to rule on.

   `status:` is never applicable, and this command never touches it — a missing or invalid `status:` is a *needs a decision* item. Approval is the user's to record, and a review that flips it would mark a spec approved that nobody approved.

   If there is at least one applicable fix, ask one AskUserQuestion: **Apply the N fixes** (recommended) / **Let me pick** / **Don't apply**. On **Let me pick**, ask a second AskUserQuestion with `multiSelect: true`, one option per applicable fix (label: the section; description: the edit), at most 4 options per question — with more fixes, split them across several questions (up to 4 per call, further calls past that). A free-text reply would end the turn and leave the choice unparsed. Apply the chosen ones with Edit, keeping AC ids stable (a removed criterion retires its id). Then report one line per fix — `- <section>: <what changed> (<finding>)` — so the user sees exactly what moved in an artifact they may already have approved.
3. **End with the review brief.** Read the spec yourself — after step 2, so the brief describes the spec as it now is, not the one the validator read — and write this block instead of re-printing the spec (~15 lines, numbering continuous across groups, empty groups omitted):

   ```markdown
   ### Review brief — SPEC-<slug>.md (<line count> lines)
   **Decided** (review if you disagree)
   1. ...
   **Assumed — confirm**
   2. ...
   **Unverified claims about the code**
   3. `Booking.contact` is non-null — REFUTED: `app/bookings/models.py:88` declares `null=True` (AC-3 depends on it)
   **Out of scope**
   - ...
   Reply with the numbers you want changed, or "approved".
   ```

   - **Decided**: choices the spec makes that a reader could disagree with (scope cuts, contract shape, error behavior). A `DRIFTED` claim that one of those choices rests on goes here, with the drift stated, so the user re-confirms the decision against what the code actually says.
   - **Assumed — confirm**: assumptions the spec states, or that its ACs silently depend on, which the user has not confirmed.
   - **Unverified claims about the code**: every `REFUTED` and `UNVERIFIED` claim from the table, and any `DRIFTED` claim not already fixed in step 2 or listed under Decided — each with its status and the one-line evidence. Every *needs a decision* finding from step 2 appears in the brief too.
   - **Out of scope**: the spec's `## Non-Goals`, one line each (for a spec without that section, its Never-do items).
4. End with the next command, using the resolved spec path, then stop:

   ```
   Next: /feature-dev:explore-plan <spec path>   (or re-run /feature-dev:spec-review <spec path> after editing the spec by hand)
   ```

## Rules

- **Never fix without confirmation.** A silent edit to a reviewed artifact un-reviews it: the user approved a spec they no longer have. The question in step 2 keeps the edit visible, and a fix that needs a judgment call is never offered as applicable.
- **Never opine on technical choices.** This command checks structure, completeness, and whether the spec's factual claims about the existing code hold — not whether the chosen approach is right. That's a code-review or `/discuss:feature` concern.
- **Never gate other commands on this.** This command is opt-in by design. It surfaces findings and offers the fixes that need no judgment; the user chooses whether to act.
- **The SPEC file is a local working artifact.** Never suggest committing it and never run git commands against it. It should be listed in the project's `.gitignore` (added automatically by `/feature-dev:spec`).
