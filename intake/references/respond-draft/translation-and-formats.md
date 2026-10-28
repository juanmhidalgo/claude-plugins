# Respond-Draft — Translation Tables & Output Formats

Loaded by `/intake:respond-draft`.

## Engineering → plain-language translation

| Engineering language | Plain-language version |
|---------------------|------------------------|
| `Candidate.custom_fields JSONField exists` | "Our data model already supports custom fields" |
| `bulk_import.py drops unknown columns` | "Custom field columns aren't currently being saved during upload" |
| `JWT-authenticated org-facing endpoint` | "A self-service download from within the application" |
| `django-celery-beat not installed` | "Scheduled report generation isn't part of our current platform" |
| `paramiko/pysftp/dropbox absent from Pipfile` | "Direct SFTP and Dropbox delivery aren't currently supported" |
| `Notifications Service is in another repo` | "Email delivery is governed by a separate part of our platform" |

**Drop entirely**: file paths, `file:line`, library/framework names, internal service names, repo names.
**Keep**: honest verdict (works today / needs work / not supported), shape of any limitation, product-domain terms CSM uses.

## Commitment categories (NOT phases)

The customer-facing reply must NOT carry timing — group by commitment category instead:

- **Currently supported** — Status EXISTS, no caveats
- **Supported with a small adjustment** — Status PARTIAL with Effort trivial/small
- **Possible with deliberate planning** — Status MISSING with Effort medium, or PARTIAL with Effort medium
- **Significant initiative required** — Effort large, regardless of Status
- **Not a path forward for this customer** — capabilities excluded by a constraint (call out which constraint)

These describe **shape of effort**, not **timing**.

## Format A: Structured status (CSM internal review)

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

## Workarounds available today (no new build required)

For each workaround in the feasibility report's `Workarounds available today` section:
- **<workaround title>** — combines <existing capabilities, in plain language>. Operational burden: <who runs it, how often>. Does NOT solve: <what's still missing>.

Omit this section entirely if the feasibility report has no workarounds.

## Pragmatic alternative path (instead of bespoke Phase 1)

For each entry in the feasibility report's `Pragmatic alternative path` subsection:
- **<pattern title>** — extends/clones an existing pattern in our system. Could partially or fully address: <which capabilities>. Trades: <what it sacrifices for what it gains>.

Omit this section entirely if no pragmatic alternative was found.

## Against [customer]'s stated deadline ([date])

**Achievable in principle within their window:**
- <Customer-facing capability name>

**Possible but tight, may slip:**
- <Customer-facing capability name>

**Not realistic in that window regardless of priority:**
- <Customer-facing capability name>

(NB: "achievable in principle" describes engineering effort fitting in the window. Actual delivery still depends on prioritization, code review, deployment, and QA cycles — CSM owns timeline commitments.)

## Acknowledged constraints
- <Restated in customer's framing>

## Open questions back to [customer name]
- <Question> — <why it matters>
```

**Empty-bucket rule**: omit any commitment-category bucket with zero entries. Drop the heading entirely. Same rule for the deadline section. **Omit the entire "Against [customer]'s stated deadline"** section if the feasibility report has no TEMPORAL constraint.

## Format B: Slack message to CSM (default channel)

```markdown
**Feasibility on the [short topic] ask** — engineering's read for you below.

**The honest read:**
- <bullet, plain language, what works today>
- <bullet, what needs a small adjustment>
- <bullet, what's a deliberate-planning item>
- <bullet, what's a larger initiative>
- <bullet, what's blocked by a constraint and our recommended alternative>

**Could meet some of the ask today without new code:**
- <one-line workaround> — <operational burden>; doesn't solve <what's still missing>
*(Omit this whole section if no workarounds.)*

**Pragmatic alt to bespoke Phase 1:**
- <pattern title>: extend <existing pattern> to <what it'd cover>. Trades <what it sacrifices> for <what it gains>.
*(Omit this section if no pragmatic alternative was found.)*

**Against [customer]'s stated deadline ([date]):**
- ✅ Achievable in principle: <list of capabilities>
- ⚠️ Tight, may slip: <list of capabilities>
- ❌ Not realistic in that window: <list of capabilities>
*(Omit this whole section if no TEMPORAL constraint. Omit any ✅/⚠️/❌ row that has no entries.)*

**Open questions** to relay back to [customer name]:
- <Question> — <why it matters>
- ...

**Timing**: [CSM TO CONFIRM TIMELINE] — once you have answers above + prioritization context.
```

**Why no customer-facing draft**: CSM owns the customer relationship and voice. Engineering's role is to give CSM a clear engineering read.

**Format adaptation**: this works as-is in Slack. For email/ticket, CSM should ask for a tailored version — don't generate both speculatively.

## Rationalization Defenses

| Rationalization | Why It's Wrong |
|----------------|----------------|
| "I'll add 'approximately 2 weeks' so CSM has something to relay" | Approximate timelines are still timelines. The customer forgets "approximately." Use `[CSM TO CONFIRM TIMELINE]`. |
| "The effort estimate is 'small' so 'a few days' is safe to write" | Effort is not delivery. CSM has prioritization context engineering doesn't. |
| "CSM needs *some* signal on timing or they'll escalate" | An honest "we need prioritization input" beats a date that gets missed. |
| "I'll just put the engineering phase numbers in the Slack message" | Phase 1/2/3 carries time-effort coupling. Translate to commitment categories. |
| "The constraint says no email but a signed link is technically not email" | The customer's IT department wrote the policy. They decide what counts. |
| "Status is PARTIAL but the gap is tiny, I'll write 'supported'" | PARTIAL is PARTIAL. Up-front honesty preserves trust. |
| "I should still draft a customer-facing version, CSM will appreciate the head start" | CSM owns the customer voice. Stay in the engineering→CSM lane. |
| "CSM will paraphrase my Slack message verbatim, I should write it customer-ready" | If it's customer-ready, you've taken over CSM's job. |
| "The customer set their own deadline, so committing to it isn't a date emission" | The customer asked, not committed for us. Use ✅/⚠️/❌ feasibility-in-principle. |
| "The customer's deadline is unrealistic for the larger items, I should suggest an alternative date" | Engineering says what's feasible in their window. Proposing alternative dates is CSM's job. |
| "I'll add 'we expect X by [their date]' just to give CSM something to relay" | "Expect" is a soft commitment that hardens. Use ✅ "achievable in principle". |
