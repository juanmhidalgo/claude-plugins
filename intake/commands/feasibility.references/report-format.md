# Feasibility — Report Format

Loaded by `/intake:feasibility` Phase 4 (Synthesize).

Produce a single markdown report with these sections in order.

## Header

```markdown
# Intake Feasibility — <short slug derived from the request>

**Source**: <one-sentence summary of who asked and what>
**Codebase**: <repo name from pwd>
**Date**: <today's date>

## Constraints (apply to this customer only)

| Tag | Type | Constraint | Effect |
|-----|------|------------|--------|
| C1 | POLICY | <one-line statement> | Excludes <capability IDs> for this customer |
| C2 | TEMPORAL | <one-line statement, with the date> | Window for feasibility-against-deadline (see section below) |
```

Omit the Constraints section entirely if Phase 1 found none. If constraints exist, the section is **required** and must appear above the Capability Map — readers need to know what's off the table before they read what's on the table.

## Feasibility against [customer]'s stated deadline (Required when a TEMPORAL constraint exists)

Add this section between Constraints and the Capability Map:

```markdown
## Feasibility against [customer]'s stated deadline ([date or window from the request])

| ID | Capability | Verdict | Reason |
|----|------------|---------|--------|
| A | ... | ✅ | <one-line reason — typically effort fits in window if prioritized> |
| C | ... | ⚠️ | <one-line reason — possible but tight, may slip> |
| E | ... | ❌ | <one-line reason — not realistic in window regardless of priority> |
```

**Verdict guidance** (engineer's judgment, not formula):

| Window length (days from today) | Effort `trivial`/`small` | Effort `medium` | Effort `large` |
|---|---|---|---|
| < 1 week | ⚠️ tight, code review + deploy chip into a tight window | ❌ not realistic | ❌ not realistic |
| 1–4 weeks | ✅ achievable in principle | ⚠️ tight, may slip | ❌ not realistic |
| 1–3 months | ✅ achievable in principle | ✅ achievable in principle | ⚠️ likely needs scope reduction |
| 3+ months | ✅ achievable in principle | ✅ achievable in principle | ✅ achievable in principle |

The engineer can override based on team capacity, dependencies, or known constraints. The grid is guidance, not formula.

**Critical framing**: every verdict is "achievable *in principle*" or "not realistic *in this window*", never "we will deliver by X". The verdict comments on the customer's stated date as a constraint to evaluate, not a commitment to make.

Omit this section entirely if no TEMPORAL constraint was extracted in Phase 1.

## Capability Map (Required)

| ID | Capability | Status | Effort | Key Finding |
|----|------------|--------|--------|-------------|
| A | ... | EXISTS | trivial | ... |

The "Key Finding" column is one short sentence with the most important file:line evidence or the dominant gap. Detailed evidence belongs in per-capability sections.

## Workarounds available today (Required when alternatives agent returned workarounds)

Surface the alternatives agent's `Workarounds available today` table verbatim. Do NOT summarize. Place between the Capability Map and Per-Capability Detail. If the alternatives agent returned no workarounds, omit this section entirely.

## Per-Capability Detail (Required)

One subsection per capability with the schema returned by the capability subagents. Do not summarize — copy the full evidence.

## Top 3 Risks (Required)

The three biggest unknowns or risks for the **overall request**, not per-capability. Each risk has:
- A one-line title
- One paragraph explaining the risk and its impact
- A concrete way to verify or de-risk it

Risks to watch for:
- Silent bugs that mean the capability "exists" but is broken (the most dangerous finding — call these out loudly)
- Missing infrastructure where the capability is implementable in principle but requires net-new patterns the codebase has never used
- Cross-team or external service dependencies the engineer alone cannot resolve
- Security/compliance gates (data retention, PII, IT policies mentioned in the request)

## Phased Recommendation (Required)

Group capabilities into phases by effort and dependency:

```markdown
### Phase 1 — <theme> (<aggregate effort>)
**Solves for this customer:** <which part of the ask, after applying constraints>
- <Capability ID and one-line action>
- ...

### Phase 2 — <theme> (<aggregate effort>)
...

### Phase 3 — <theme> (<aggregate effort>)
...

### Pragmatic alternative path (Optional — only when the alternatives agent returned pragmatic alternatives)

Instead of the bespoke Phase 1 → 2 → 3 trajectory, an alternative using existing patterns:
- <Pattern ID from alternatives table> — <one-line action; what existing pattern is broadened, file:line>
- ...

**Trades:** <what this alternative sacrifices for what it gains>

### Excluded for this customer
- <Capability ID> — blocked by <Constraint tag>: <one-line reason>
```

**Rules:**
- Order phases by smallest-impact-to-customer-blockers first.
- **Apply constraints before phasing.** A capability that violates a constraint goes in "Excluded for this customer", NOT in any phase.
- A capability excluded for this customer may still be a product priority — note that separately if relevant.

## Open Questions (Optional, only if unresolved)

Bullet list of questions back to CSM/Sales. Each must be answerable by the customer (not engineering). Format: "Question? — *Why it matters: <impact>*"

## Worked example (decomposition reference)

> "Customer wants extracts multiple times a day, sent via SFTP or dropbox — they can't receive data via email per IT policy. Custom fields joined to KPI data. Need at least the custom-field upload working by Friday for an audit."

Decomposes to:
- **Capabilities**: A custom fields, B join, C scheduling, D email, E SFTP, F Dropbox
- **Constraints**:
  - **C1 [POLICY]** — *"they can't receive data via email per IT policy"* → excludes capability D for this customer
  - **C2 [TEMPORAL]** — *"need at least the custom-field upload working by Friday for an audit"* → window of days; capability A must be ✅ in that window, others assessed accordingly

**Critical distinctions**:
- Capability D (email delivery) is still a valid product capability — other customers may use it. But constraint C1 means D is **out for this customer** permanently.
- A "by Friday" deadline (C2) does NOT exclude any capability — it just maps each capability to ✅/⚠️/❌ feasibility against that window.
