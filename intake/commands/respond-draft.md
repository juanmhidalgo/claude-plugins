---
description: |
  Use AFTER /intake:feasibility to summarize the engineering findings for CSM in plain language — drops file paths, library names, and engineering jargon so CSM has the context they need to drive the customer conversation in their own voice.
  Do NOT use to draft customer-facing messages — that is CSM's job and out of scope for this command. This command stops at the engineering→CSM handoff.
  Do NOT use for spec writing or internal engineering status updates. Emits NO calendar dates, week counts, sprint references, or specific timing by design.
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

You are summarizing an engineering feasibility report **for CSM**. Your audience is the CSM owner of this customer relationship — they are not engineers, but they speak the product's domain language fluently. Your job is to translate the engineering findings into plain language so CSM has what they need to drive the customer conversation **in their own voice**.

**Out of scope**: drafting the customer-facing message itself. That is CSM's job — they own the customer relationship and the voice that fits it. This command stops at the engineering→CSM handoff.

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

> "This command summarizes a feasibility report for CSM. Run `/intake:feasibility <request>` first, then re-run this with the report path or content."

Do not summarize without a feasibility report — you cannot honestly describe what's available without verified evidence.
</input_handling>

## Phase 1: Read the Report

Extract from the feasibility report:
- The capability map (Status, Effort per capability)
- The constraints (if any)
- The phased recommendation
- The "Excluded for this customer" list (if any)
- The open questions

If any of these sections are missing, note it but proceed — older reports may not have constraint extraction.

## Phase 2: Translate Capabilities to Plain Language

<translation>
Translate engineering jargon into language CSM understands. CSM speaks the product's domain language ("audience," "candidate," "interview," "report") fluently — but does not read code. Examples:

| Engineering language | Plain-language version |
|---------------------|------------------------|
| `Candidate.custom_fields JSONField exists` | "Our data model already supports custom fields" |
| `bulk_import.py drops unknown columns` | "Custom field columns aren't currently being saved during upload" |
| `JWT-authenticated org-facing endpoint` | "A self-service download from within the application" |
| `django-celery-beat not installed` | "Scheduled report generation isn't part of our current platform" |
| `paramiko/pysftp/dropbox absent from Pipfile` | "Direct SFTP and Dropbox delivery aren't currently supported" |
| `Notifications Service is in another repo` | "Email delivery is governed by a separate part of our platform" |

Drop entirely:
- File paths and `file:line` references
- Library/framework names (`Pipfile`, `Celery Beat`, `JSONField`, `paramiko`, etc.)
- Internal service implementation names not recognizable to CSM
- Repository names

Keep:
- The honest verdict (works today / needs work / not currently supported)
- The shape of any limitation
- Product-domain terms CSM uses with customers (audience, interview, candidate, report, KPI dashboard, etc.)
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

**Empty-bucket rule**: Omit any commitment-category bucket that has zero entries. Do not write "Currently supported: (none with no caveats)" — drop the heading entirely. Empty buckets are noise that obscures the buckets that matter.

### Format B: Slack message to CSM (default channel)

This is the channel most engineers actually use to coordinate with CSM. The message is written for posting directly into a Slack thread or DM. Structure:

```markdown
**Feasibility on the [short topic] ask** — engineering's read for you below.

**The honest read:**
- <bullet, plain language, what works today>
- <bullet, what needs a small adjustment>
- <bullet, what's a deliberate-planning item>
- <bullet, what's a larger initiative>
- <bullet, what's blocked by a constraint and our recommended alternative>

**Open questions** to relay back to [customer name]:
- <Question> — <why it matters>
- ...

**Timing**: [CSM TO CONFIRM TIMELINE] — once you have answers above + prioritization context.
```

**Why no customer-facing draft**: writing the customer message is CSM's job — they own the customer relationship, the voice, and the prioritization context. Engineering's role here is to give CSM a clear engineering read so CSM has what they need to drive the conversation in their own voice.

**Format adaptation**: This structure works as-is in Slack. If the team uses email or a ticket comment thread instead, adjust the opener and add a salutation/sign-off if the channel calls for it. Tell the user to ask for an email/ticket version if they need one; don't generate both speculatively.
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
| "I'll add 'approximately 2 weeks' so CSM has something to relay" | Approximate timelines are still timelines. CSM relays "2 weeks" and the customer forgets "approximately." Use `[CSM TO CONFIRM TIMELINE]` so the human owner sets the number after their prioritization conversations. |
| "The effort estimate is 'small' so 'a few days' is safe to write" | Effort is not delivery. A "small" change still has to fit in a sprint, get reviewed, deployed, and verified. CSM has prioritization context that engineering doesn't. |
| "CSM needs *some* signal on timing or they'll escalate" | An honest "we need prioritization input from your side" is a better signal than a date that gets missed. Missed dates erode trust faster than no dates. |
| "I'll just put the engineering phase numbers in the Slack message" | Phase 1/2/3 in the engineering report carries time-effort coupling. In a CSM-facing message, those phase numbers will be read as time commitments. Translate to commitment categories instead. |
| "The constraint says no email but a signed link is technically not email" | The customer's IT department wrote the policy. They decide what counts. Do not propose workarounds the customer didn't ask for. |
| "Status is PARTIAL but the gap is tiny, I'll write 'supported'" | PARTIAL is PARTIAL. The CSM who relays "supported" and then has a customer hit the gap will lose more trust than the CSM who relayed "supported with a small adjustment needed" up front. |
| "I should still draft a customer-facing version, CSM will appreciate the head start" | CSM owns the customer relationship and voice. A pre-written customer-facing block creates expectation drift (CSM may feel pressure to forward verbatim) and strips CSM's authorship of their own communication. Stay in the engineering→CSM lane. |
| "CSM will paraphrase my Slack message verbatim to the customer, I should write it customer-ready" | If the Slack message is customer-ready, you've quietly taken over CSM's job. Write it for CSM as the *reader*, not the customer. CSM translates to customer voice with their own context and tone. |

<mindset>
- Every word in this draft will be quoted back at us if it turns out wrong
- "We don't know yet" is a stronger answer than a hedged guess
- The customer values honesty more than confidence
- CSM is the owner of timing — engineering is the owner of feasibility — keep the lanes clean
</mindset>
