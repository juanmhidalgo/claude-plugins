---
description: |
  Use AFTER /intake:feasibility (and optionally /intake:respond-draft) to anticipate the questions, pushback, and objections engineering will receive from CSM, Sales, or the customer when sharing the feasibility report.
  Generates a Q&A list of the most likely objections with prepped, factual responses.
  Do NOT use for technical FAQ generation, customer documentation, or product marketing — this is specifically for adversarial-style anticipation of intake feedback.
argument-hint: "<paste feasibility report OR path to INTAKE-feasibility-*.md>"
allowed-tools:
  - Read
  - Glob
  - Grep
  - AskUserQuestion
keywords:
  - objection-prep
  - q-and-a
  - csm-pushback
  - anticipation
  - intake-followup
triggers:
  - "anticipate questions"
  - "what will csm ask"
  - "objection prep"
  - "what objections might come back"
  - "pushback prep"
hooks:
  - event: Stop
    once: true
    command: |
      echo "Objection prep complete."
      echo "Recommended next steps:"
      echo "  - Review with CSM/owner before customer call or reply"
      echo "  - For new technical findings raised by objections, re-run /intake:feasibility on the relevant capability"
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this command and proceed with your assigned task.
</SUBAGENT-STOP>

# Objection Prep

You are anticipating the questions and pushback that will come back from CSM, Sales, or the customer when the feasibility report is shared. Your goal is to give the engineer a prepped Q&A so they are not caught flat-footed.

<context>
**Working directory**: !`pwd`
**Input**: $ARGUMENTS
</context>

<input_handling>
The argument may be either:
1. **A file path** — if `$ARGUMENTS` looks like a path to `INTAKE-feasibility-*.md` that exists, read it
2. **Inline pasted feasibility report content**
3. **A short identifier or slug** — search for `INTAKE-feasibility-*<slug>*.md` in the working directory

If no feasibility report can be located, tell the user:

> "This command anticipates objections to a feasibility report. Run `/intake:feasibility <request>` first, then re-run this with the report path or content."
</input_handling>

## Phase 1: Read the Report

Extract from the feasibility report:
- The capability map (Status, Effort, Notes)
- The constraints (if any)
- The phased recommendation
- The "Excluded for this customer" list
- The Top 3 risks

## Phase 2: Identify Likely Objection Categories

<objection_checklist>
For each capability and risk in the report, check whether it triggers any of these objection categories. Not every category will apply — only include the ones with concrete grounding in this report.

| Category | Triggers when... | Typical asker |
|----------|------------------|---------------|
| **Effort objection** | A capability is rated `medium` or `large` | CSM, Sales, Customer |
| **Hack-it-for-one-customer** | A capability is `large` AND the customer is asking for a one-off | Sales, occasionally CSM |
| **Constraint objection** | A constraint excludes a capability the customer wanted | Sales, Customer (rare from CSM) |
| **Buy-vs-build** | A `large` capability has a known SaaS substitute | CSM, Sales |
| **Existing-customer impact** | A capability touches code shared with other customers | CSM (always), Engineering Manager |
| **Why-not-already-built** | A `MISSING` capability sounds obvious or table-stakes | CSM, Customer, Sales |
| **Workaround feasibility** | A `MISSING` capability has a manual path | CSM, Sales |
| **Silent-bug embarrassment** | A risk callout names a silent bug | CSM specifically |
| **Competitor-does-this** | A `MISSING` capability is offered by a known competitor | Sales |
| **Constraint re-litigation** | The customer pushes back on their own stated constraint | Customer, Sales |

For each category that triggers, draft a prepped response in the next phase.
</objection_checklist>

## Phase 3: Draft Prepped Responses

<response_schema>
For each likely objection, output the following:

```markdown
### Q: <The likely question, in the asker's voice — make it sound real, not sanitized>

**From**: <CSM | Sales | Customer | Engineering Manager>
**Triggered by**: <Capability ID(s) and/or Risk number(s) in the report>

**Prepped response**: <1–3 sentences, factual, no marketing language. State what's true, not what we wish were true.>

**If pushed**: <Optional — what to say or do if the asker doesn't accept the first response. Often a redirect to "let me bring this back to product/engineering for a real prioritization conversation" or "let's schedule a working session with [the customer's IT/engineering team]". Skip if the prepped response is sufficient.>
```

**Voice rules for the Q phrasing:**
- Sales objections sound like: "Why does this take so long when [Competitor] just does it?" — direct, customer-pressure-flavored
- CSM objections sound like: "How do I explain this to ADT without sounding like we don't have our act together?" — relationship-pressure-flavored
- Customer objections sound like: "We thought this was a basic feature. Why isn't it supported?" — expectation-pressure-flavored

**Voice rules for the response:**
- No marketing speak ("delight," "robust," "enterprise-grade")
- No hedging ("we *think*," "*probably*," "*hopefully*")
- Factual — restate what the report says, in plain language
- It's OK to say "I don't know — let me find out" as the response when the report doesn't cover it
- Never commit to a date or a workaround that isn't in the report
</response_schema>

## Phase 4: Print, Then Offer to Save (Optional)

<output>
**Default behavior is print-only.** Print the Q&A list inline, organized by category. Then ask once via AskUserQuestion:

> "Save this objection prep as a file?"

Options:
- "No, the chat copy is enough" (default)
- "Yes, save to `INTAKE-objections-<slug>.md`"
- "Yes, save to a custom path"

If declined, do nothing further.

End your final response with a one-line summary noting which categories were triggered and which were not (so the user knows what was *not* anticipated, not just what was). Example:

> "Triggered: effort objection, constraint re-litigation, why-not-already-built. Not triggered: buy-vs-build, competitor-does-this, hack-it-for-one-customer."
</output>

<critical_rules>
<rule priority="blocking">
NEVER invent objection responses that aren't grounded in the feasibility report. If the report doesn't address a category, the prepped response is "I'd need to bring this back to engineering" — not a fabricated answer.
</rule>

<rule priority="blocking">
NEVER soften the report's findings to make objections easier to handle. If the report says PARTIAL with a silent bug, the prepped Q for "is this working today?" must answer truthfully ("No — there's a known issue we'd need to fix"), not optimistically ("Yes, with caveats").
</rule>

<rule priority="blocking">
NEVER suggest constraint workarounds the customer didn't ask for. If a constraint excludes email, do not prep a "we could send a signed link" response — that violates the same lawyering-the-constraint discipline as `/intake:respond-draft`.
</rule>

<rule priority="blocking">
NEVER add objection categories the report does not support. If the report has no `large` capabilities, do not prep an effort objection — there's nothing to defend.
</rule>

<rule priority="recommended">
When the prepped response is "we don't know," explicitly call out what the next step is: "Let me bring this back to engineering with a specific scoping question." That gives the engineer a concrete handoff instead of leaving them stuck mid-conversation.
</rule>

<rule priority="recommended">
Order the Q&A list by **likelihood of being asked**, not by category. The most likely questions go first so the engineer reads them even if they skim.
</rule>
</critical_rules>

## Rationalization Defenses

If you catch yourself thinking any of these, STOP:

| Rationalization | Why It's Wrong |
|----------------|----------------|
| "I'll prep a generic answer for every category — better safe than sorry" | Generic answers are noise. The engineer will tune out and miss the objections that actually apply. Only include categories triggered by the report. |
| "I should soften the report's negative findings so they're easier to defend" | The point of objection prep is to be *honest* about hard answers, not to rewrite the report into something defensible. If the report says something hard, the prepped response must say it too. |
| "I'll add a 'how to convince the customer to drop the constraint' Q&A" | The customer's constraints are not engineering's to relitigate. Prep the response that respects the constraint, not the response that argues against it. |
| "I'll write the customer's likely Q in polite, professional language" | Polite-and-professional Q phrasings disarm the engineer. Real objections come in with edge — Sales pressure, CSM relationship anxiety, customer frustration. Capture that voice so the engineer is prepared for the real thing. |
| "Effort large = automatic objection, prep it even if no one will ask" | If the report's `large` capability is something everyone agrees is large (e.g., new infrastructure), the effort objection won't come up. Trigger on capabilities that look "should-be-cheap" but are actually expensive — those are the real objection sources. |

<mindset>
- The point is to surface the questions the engineer would otherwise miss
- An unsurprised engineer is a credible engineer
- "I don't know" is a valid answer when accompanied by a clear next step
- Honesty about hard findings is more durable than soft-pedaling them
</mindset>
