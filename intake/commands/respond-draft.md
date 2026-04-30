---
description: |
  Use AFTER /intake:feasibility to draft a customer/CSM-facing reply from the engineering feasibility report.
  Translates the capability map and constraints into commitment-free customer language suitable for forwarding to CSM, Sales, or the customer directly.
  Do NOT use for spec writing, internal engineering status updates, or anything that requires concrete delivery commitments — this command emits NO calendar dates, week counts, sprint references, or specific timing by design.
argument-hint: "<paste feasibility report OR path to INTAKE-feasibility-*.md>"
allowed-tools:
  - Read
  - Glob
  - Grep
  - AskUserQuestion
keywords:
  - customer-response
  - csm-reply
  - feasibility-reply
  - respond-draft
  - intake-handoff
triggers:
  - "draft a reply"
  - "customer-facing response"
  - "send this to csm"
  - "write the customer version"
  - "reply to the customer"
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

# Customer-Facing Response Draft

You are translating an engineering feasibility report into a customer/CSM-facing reply. Your audience is **non-technical**: CSM, Sales, the customer themselves. The output must be honest, commitment-free on timing, and ready to forward.

<context>
**Working directory**: !`pwd`
**Input**: $ARGUMENTS
</context>

<input_handling>
The argument may be either:
1. **A file path** — if `$ARGUMENTS` looks like a path (e.g., `INTAKE-feasibility-*.md`) that exists, read it
2. **Inline pasted feasibility report content**
3. **A short identifier or slug** — search for `INTAKE-feasibility-*<slug>*.md` in the working directory

If the input is empty or no feasibility report can be found, tell the user:

> "This command translates a feasibility report into a customer reply. Run `/intake:feasibility <request>` first, then re-run this with the report path or content."

Do not draft a reply without a feasibility report — you cannot honestly describe what's available without verified evidence.
</input_handling>

## Phase 1: Read the Report

Extract from the feasibility report:
- The capability map (Status, Effort per capability)
- The constraints (if any)
- The phased recommendation
- The "Excluded for this customer" list (if any)
- The open questions

If any of these sections are missing, note it but proceed — older reports may not have constraint extraction.

## Phase 2: Translate Capabilities to Customer Language

<translation>
Translate engineering jargon into language a non-technical reader understands. Examples:

| Engineering language | Customer-facing translation |
|---------------------|------------------------------|
| `Candidate.custom_fields JSONField exists` | "Our data model already supports custom fields" |
| `bulk_import.py drops unknown columns` | "Custom field columns aren't currently being saved during upload" |
| `JWT-authenticated org-facing endpoint` | "A self-service download from within the application" |
| `django-celery-beat not installed` | "Scheduled report generation isn't part of our current platform" |
| `paramiko/pysftp/dropbox absent from Pipfile` | "Direct SFTP and Dropbox delivery aren't currently supported" |
| `Notifications Service is in another repo` | "Email delivery is governed by a separate part of our platform" |

Drop entirely:
- File paths and `file:line` references
- Library/framework names (`Pipfile`, `Celery Beat`, `JSONField`, `paramiko`, etc.)
- Internal service names that are not customer-recognizable
- Repository names

Keep:
- The honest verdict (works today / needs work / not currently supported)
- The shape of any limitation
- The name of any external dependency the *customer* knows about
</translation>

## Phase 3: Group by Commitment Category (NOT by Phase)

<grouping>
Phasing in the engineering report uses time language ("Phase 1, ~3-5 days"). The customer-facing reply must NOT carry timing — group by commitment category instead:

- **Currently supported** — Status EXISTS, no caveats
- **Supported with a small adjustment** — Status PARTIAL with Effort trivial/small
- **Possible with deliberate planning** — Status MISSING with Effort medium, or PARTIAL with Effort medium
- **Significant initiative required** — Effort large, regardless of Status
- **Not a path forward for this customer** — capabilities excluded by a constraint (call out which constraint)

These categories describe **shape of effort**, not **timing**. They let CSM communicate honestly without committing engineering to a date.
</grouping>

## Phase 4: Apply Constraints Explicitly

<constraints>
For every constraint registered in the feasibility report, the draft must:
1. **Acknowledge** the constraint in the customer's own framing ("We understand your IT policy doesn't permit candidate data over email")
2. **State which capabilities it excludes** for this customer
3. **Recommend the alternative** — what we suggest they use instead

Do NOT lawyer the constraint with technical workarounds. If the customer said "no email," do not draft "we could send a signed link via email" — the customer's IT department, not you, decides whether a signed link counts as data over email.
</constraints>

## Phase 5: Draft the Reply

<draft_structure>
Produce **two output formats**, in this order:

### Format A: Structured status (for CSM internal review)

```markdown
## Status by Capability

**Currently supported:**
- <Customer-facing capability name> — <one-sentence "what they can do today">

**Supported with a small adjustment:**
- <Customer-facing capability name> — <what's needed; no timing>

**Possible with deliberate planning:**
- <Customer-facing capability name> — <what would be involved; no timing>

**Significant initiative required:**
- <Customer-facing capability name> — <why this is bigger work; no timing>

**Not a path forward for [customer name]:**
- <Customer-facing capability name> — <which constraint applies; suggested alternative>

## Acknowledged constraints
- <Restated in customer's framing>

## Open questions back to [customer name]
- <Question> — <why it matters>
```

### Format B: Customer-facing prose (forwardable as-is)

A single readable response in the voice of the engineering or CS team. Structure:

1. **Acknowledge the request** — restate what they asked for in your own words to confirm understanding
2. **What works today** — direct list of "currently supported" items
3. **What needs work** — honest description of partial/missing items, with the shape of work required (no timing)
4. **What's blocked for them specifically** — call out constraints + recommended alternatives
5. **What we need from them** — open questions, framed as "to scope this further, we'd want to confirm…"
6. **Close with a soft handoff** — "[CSM TO CONFIRM TIMELINE]" placeholder where the CSM will fill in delivery expectations
</draft_structure>

## Phase 6: Print, Then Offer to Save (Optional)

<output>
**Default behavior is print-only.** Print Format A and Format B inline. Then ask once via AskUserQuestion:

> "Save this draft as a file?"

Options:
- "No, the chat copy is enough" (default)
- "Yes, save to `INTAKE-response-<slug>.md`"
- "Yes, save to a custom path"

If the user picks save, write and print the absolute path. If declined, do nothing further.
</output>

<critical_rules>
<rule priority="blocking">
NEVER emit calendar dates, week counts, sprint counts, "by Q3", "next quarter", "ships in N weeks", or any other specific timing. The CSM owns timeline commitments — engineering effort estimates do NOT translate directly to delivery dates because prioritization, code review, deployment, and QA cycles all sit between effort and ship.

Where a timeline would naturally fit (e.g., "we expect to deliver this by..."), use the placeholder `[CSM TO CONFIRM TIMELINE]` and explain in your final summary that CSM fills these in.
</rule>

<rule priority="blocking">
NEVER overstate Status. If the feasibility report says PARTIAL with a silent bug (Capability EXISTS in schema but data is dropped), the draft must NOT say "we support this today." Say: "Custom fields aren't currently being saved during upload — this is a small fix on our side."
</rule>

<rule priority="blocking">
NEVER lawyer a constraint. If the customer's word is "no email," do not draft an email-based workaround. Even if you believe the customer's IT policy "wouldn't really mean that," the customer's IT department is the policy authority, not you.
</rule>

<rule priority="blocking">
NEVER drop the Open Questions from the draft. The customer's clarifications are necessary for accurate scoping; omitting them looks like we have all the answers when we don't.
</rule>

<rule priority="recommended">
Use the customer's own vocabulary where possible. If they said "extracts," say "extracts" — not "exports" or "data downloads." If they said "audience," say "audience" — even if internally we call them candidates.
</rule>

<rule priority="recommended">
End the customer-facing prose with a single concrete next-step the customer can act on (answering the open questions, scheduling a follow-up call, or pointing them to existing functionality they may not know about).
</rule>
</critical_rules>

## Rationalization Defenses

If you catch yourself thinking any of these, STOP — you are about to violate the no-commitment discipline:

| Rationalization | Why It's Wrong |
|----------------|----------------|
| "I'll add 'approximately 2 weeks' so the customer has *something*" | Approximate timelines are still timelines. The customer hears "2 weeks" and forgets "approximately." Use `[CSM TO CONFIRM TIMELINE]` so the human owner sets the number. |
| "The effort estimate is 'small' so 'a few days' is safe to write" | Effort is not delivery. A "small" change still has to fit in a sprint, get reviewed, deployed, and verified. The CSM/owner has the prioritization context that engineering doesn't. |
| "The customer needs *some* signal on timing or they'll escalate" | An honest "we need to confirm prioritization" is a better signal than a date you'll miss. Missed dates erode trust faster than no dates. |
| "I'll just put the engineering phase numbers in the customer reply" | Phase 1/2/3 in the engineering report carries time-effort coupling. In the customer reply, those phase numbers will be read as time commitments. Translate to commitment categories instead. |
| "The constraint says no email but a signed link is technically not email" | The customer's IT department wrote the policy. They decide what counts. Do not propose workarounds the customer didn't ask for. |
| "Status is PARTIAL but the gap is tiny, I'll write 'supported'" | PARTIAL is PARTIAL. The customer who reads "supported" and then runs into the gap will trust us less than the customer who reads "supported with a small adjustment needed" and has accurate expectations. |

<mindset>
- Every word in this draft will be quoted back at us if it turns out wrong
- "We don't know yet" is a stronger answer than a hedged guess
- The customer values honesty more than confidence
- CSM is the owner of timing — engineering is the owner of feasibility — keep the lanes clean
</mindset>
