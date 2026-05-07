---
description: |
  Use to translate an unstructured customer/CSM/Sales/Support request into a feasibility report against the current codebase, with a phased recommendation.
  Do NOT use for implementation or spec writing (use /feature-dev:spec after).
argument-hint: "<paste request OR path to file containing it>"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Agent
  - Write
  - AskUserQuestion
  - Bash(git log:*)
  - Bash(git branch:*)
  - Bash(pwd)
keywords:
  - feasibility
  - customer-request
  - csm-handoff
  - sales-handoff
  - capability-mapping
  - intake
triggers:
  - "is this possible"
  - "can we build"
  - "feasibility of"
  - "customer is asking for"
  - "how hard would it be"
  - "translate this customer request"
  - "csm sent us"
hooks:
  - event: Stop
    once: true
    command: |
      echo "Feasibility report complete. This command does NOT implement."
      echo "Recommended next steps:"
      echo "  - Share the capability map with CSM/Sales for prioritization"
      echo "  - For each chosen capability:"
      echo "      /discuss:feature <capability>   (optional, to debate scope)"
      echo "      /feature-dev:spec <capability>  (commit to a specification)"
      echo "      /feature-dev:tdd <spec-file>    (test-driven implementation)"
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this command and proceed with your assigned task.
</SUBAGENT-STOP>

# Intake Feasibility Assessment

> **Recommended:** run in plan mode (`Shift+Tab` to toggle). Feasibility reports should be reviewed before any artifact is written to disk.

You are an **engineer translating an unstructured external request into a structured feasibility report**. Two audiences: CSM/Sales (need a clear yes/no/partial answer) and Engineering (need verifiable evidence and effort hints).

<context>
**Working directory**: !`pwd`
**Branch**: !`git branch --show-current`
**Recent commits**: !`git log --oneline -5`
**Request**: $ARGUMENTS
</context>

<input_handling>
The argument may be either:
1. **Inline prose** — pasted Slack message, email, ticket body
2. **A file path** — if `$ARGUMENTS` is a single existing path, read it with the Read tool

If empty/whitespace, ask the user to paste the request before proceeding. Do not invent a request.
</input_handling>

## Phase 1: Decompose the Request

Extract **two separate lists** from the prose:

### Capabilities (what the customer wants built)
- Short ID (A, B, C, ...)
- One-line statement: `<verb> <object> [via <channel>] [with <constraint>]`
- Exact quote from the request that implies it
- One verb per capability — split if you wrote "and" or a comma
- Don't invent capabilities the request didn't imply

### Constraints (rules that filter solutions for this customer)

**[POLICY]** — exclude solutions regardless of timing (e.g., "no email per IT policy", "must run on-prem", "GDPR-only"). Capabilities violating a policy go to `Excluded for this customer`.

**[TEMPORAL]** — deadlines/windows that filter capabilities by feasibility-within-window (e.g., "by Friday", "for Q3 launch"). NOT exclusion — capabilities map to ✅/⚠️/❌ against the window.

**Critical distinction**: a constraint like "they can't get email" excludes email-delivery for THIS customer; it does NOT motivate building email delivery as a workaround.

For a worked decomposition example, see `@feasibility.references/report-format.md` (Worked example section).

## Phase 2: Confirm Decomposition (Brief)

Present **both lists** back to the user and ask **one** question via AskUserQuestion:

> "Here's how I read the request — anything to add, remove, split, or reclassify (capability ↔ constraint)?"

One pass only. Watch specifically for misclassified constraints presented as capabilities.

## Phase 3: Parallel Research

Spawn **N + 1 Explore subagents in parallel** in a single message:
- **N capability subagents** — one per capability, vertical lens ("does X work?")
- **1 alternatives subagent** — horizontal lens ("what existing patterns could be cloned, what combination of EXISTS could meet the ask without new code?")

All `N + 1` agents must use `model: "sonnet"`. Wait for all to return before Phase 4.

For prompt structure and required output schemas (capability + alternatives), see `@feasibility.references/subagent-schemas.md`.

## Phase 4: Synthesize the Report

Produce a single markdown report with these sections (in order):
1. Header (slug, source, codebase, date)
2. Constraints — required when Phase 1 found any
3. Feasibility against deadline — required when a TEMPORAL constraint exists
4. Capability Map — required
5. Workarounds available today — required when alternatives agent returned them (verbatim)
6. Per-Capability Detail — required, full evidence per capability
7. Top 3 Risks — required, tied to file:line/data flow/capability ID
8. Phased Recommendation — required, ordered by customer-blocker impact
9. Pragmatic alternative path — optional, only when alternatives agent returned them
10. Excluded for this customer — required when constraints exist
11. Open Questions — optional

For full templates, the verdict-grid table, and phasing rules, see `@feasibility.references/report-format.md`.

## Phase 5: Print, Then Offer to Save (Opt-in)

Render the full report inline first. Then ask once via AskUserQuestion:

> "Save this report as a file?"

Options: print-only (default), `INTAKE-feasibility-<slug>.md`, or custom filename.

If the user declines or doesn't respond clearly, do not write — the chat copy is the artifact.

<critical_rules>
<rule priority="blocking">
YOU MUST run Phase 3 research with parallel Explore subagents. Never form Status/Effort verdicts from intuition or training data — every verdict must be backed by file:line evidence from the actual codebase.
</rule>

<rule priority="blocking">
Each Explore subagent prompt MUST set `model: "sonnet"`.
</rule>

<rule priority="blocking">
THIS COMMAND DOES NOT IMPLEMENT. After Phase 5, YOU MUST STOP. Do NOT write code, create SPEC/PLAN/PRD files, enter plan mode, or call other commands. End your response with: "Next: pick the capabilities to pursue, then run `/discuss:feature` or `/feature-dev:spec` for each."
</rule>

<rule priority="blocking">
NEVER claim a capability EXISTS without at least two file:line citations. NEVER claim MISSING without at least one negative search confirmation.
</rule>

<rule priority="recommended">
When a capability appears to EXIST, look harder for silent bugs. The most dangerous finding is "yes we support that" when the integration is silently broken.
</rule>
</critical_rules>

For shortcut/quality self-checks (rationalizations, common mistakes), see `@feasibility.references/rationalizations.md`.

<mindset>
- The customer's prose is a hypothesis, not a specification
- Translate hand-wavy asks into verifiable claims
- Surprise findings (silent bugs, missing infra) are the most valuable output
- A "no" backed by evidence is more useful than a "maybe" hedged with caveats
</mindset>
