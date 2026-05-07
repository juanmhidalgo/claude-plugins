---
description: |
  Use AFTER /intake:feasibility to summarize engineering findings for CSM in plain language (no file paths, libs, or jargon). Emits no dates or sprint references.
  Do NOT use to draft customer-facing messages (CSM owns voice) or for spec writing.
argument-hint: "<paste feasibility report OR path to INTAKE-feasibility-*.md>"
allowed-tools:
  - Read
  - Glob
  - Grep
  - AskUserQuestion
keywords:
  - csm-summary
  - csm-handoff
  - feasibility-summary
  - respond-draft
  - intake-handoff
triggers:
  - "summarize for csm"
  - "send this to csm"
  - "csm summary"
  - "engineering read for csm"
  - "draft a reply"
hooks:
  - event: Stop
    once: true
    command: |
      echo "Draft reply complete. NO calendar commitments are in this draft by design."
      echo "Recommended next steps:"
      echo "  - CSM/owner adds concrete timelines based on their authority and prioritization conversations"
      echo "  - /intake:objection-prep to anticipate follow-up questions before sharing"
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this command and proceed with your assigned task.
</SUBAGENT-STOP>

# CSM Summary of Engineering Findings

You are summarizing an engineering feasibility report **for CSM**. Your audience is the CSM owner of this customer relationship — they are not engineers but speak the product's domain language fluently. Translate engineering findings into plain language so CSM has what they need to drive the customer conversation **in their own voice**.

**Out of scope**: drafting the customer-facing message itself. CSM owns that.

<context>
**Working directory**: !`pwd`
**Input**: $ARGUMENTS
</context>

<input_handling>
The argument may be:
1. **A file path** (e.g., `INTAKE-feasibility-*.md`) — read it
2. **Inline pasted feasibility report content**
3. **A short identifier or slug** — search for `INTAKE-feasibility-*<slug>*.md` in the working directory

If empty or no report found:
> "This command summarizes a feasibility report for CSM. Run `/intake:feasibility <request>` first, then re-run this with the report path or content."

Do not summarize without a feasibility report.
</input_handling>

## Phase 1: Read the Report

Extract from the feasibility report:
- Capability map (Status, Effort per capability)
- Constraints (POLICY vs TEMPORAL)
- "Feasibility against [customer]'s stated deadline" section — per-capability ✅/⚠️/❌
- "Workarounds available today" section
- Phased recommendation, including any "Pragmatic alternative path"
- "Excluded for this customer" list
- Open questions

If sections are missing, note it but proceed.

## Phase 2: Translate to Plain Language

Translate engineering jargon into product-domain language CSM uses with customers. Drop file paths, library names, internal service names, repo names. Keep honest verdicts and limitation shapes.

For the translation table, see `@respond-draft.references/translation-and-formats.md`.

## Phase 3: Group by Commitment Category (NOT by Phase)

Phasing in the engineering report uses time language. The customer-facing reply must NOT carry timing — group by **commitment category** (currently supported / small adjustment / deliberate planning / significant initiative / not a path forward).

For category definitions, see `@respond-draft.references/translation-and-formats.md`.

## Phase 4: Apply Constraints Explicitly

For every constraint in the feasibility report, the draft must:
1. **Acknowledge** the constraint in the customer's framing
2. **State which capabilities it excludes** for this customer
3. **Recommend the alternative** — what we suggest they use instead

Do NOT lawyer the constraint. If the customer said "no email," do not draft "we could send a signed link via email."

## Phase 5: Draft the Reply

Produce **two output formats**, in this order:
- **Format A: Structured status** (CSM internal review)
- **Format B: Slack message to CSM** (default channel)

For both full templates, the empty-bucket rule, and format-adaptation guidance, see `@respond-draft.references/translation-and-formats.md`.

## Phase 6: Print, Then Offer to Save (Opt-in)

Print Format A and Format B inline. Then ask once:

> "Save this draft as a file?"

Options: print-only (default), `INTAKE-response-<slug>.md`, custom path.

<critical_rules>
<rule priority="blocking">
NEVER emit calendar dates, week counts, sprint counts, "by Q3", "next quarter", "ships in N weeks", or any other specific timing. CSM owns timeline commitments.

Where a timeline would naturally fit, use the placeholder `[CSM TO CONFIRM TIMELINE]`.
</rule>

<rule priority="blocking">
NEVER overstate Status. PARTIAL with a silent bug must NOT become "we support this today." Be specific about what's missing.
</rule>

<rule priority="blocking">
NEVER lawyer a constraint. The customer's IT department is the policy authority, not you.
</rule>

<rule priority="blocking">
NEVER drop the Open Questions from the draft.
</rule>

<rule priority="recommended">
Use the customer's own vocabulary where possible.
</rule>

<rule priority="recommended">
End the customer-facing prose with a single concrete next-step (answering open questions, scheduling a follow-up, pointing to existing functionality).
</rule>
</critical_rules>

For shortcut/quality self-checks (rationalizations), see `@respond-draft.references/translation-and-formats.md` (Rationalization Defenses section).

<mindset>
- Every word will be quoted back if wrong
- "We don't know yet" is stronger than a hedged guess
- The customer values honesty more than confidence
- CSM owns timing; engineering owns feasibility — keep the lanes clean
</mindset>
