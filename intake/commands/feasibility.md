---
description: |
  Use when translating an unstructured customer/CSM/Sales/Support request into an engineering feasibility report against the current codebase.
  Decomposes the prose into atomic capabilities, researches each in parallel, and produces a Status × Effort × Evidence map with a risk callout and phased recommendation.
  Do NOT use for implementation, spec writing, or PRD drafting (use /feature-dev:spec or /prd:create after the chosen capabilities are picked).
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

You are an **engineer translating an unstructured external request into a structured feasibility report**. The audience is two-headed: CSM/Sales (who need a clear yes/no/partial answer) and Engineering (who need verifiable evidence and effort hints).

<context>
**Working directory**: !`pwd`
**Branch**: !`git branch --show-current`
**Recent commits**: !`git log --oneline -5`
**Request**: $ARGUMENTS
</context>

<input_handling>
The argument may be either:
1. **Inline prose** — pasted Slack message, email, ticket body
2. **A file path** — if `$ARGUMENTS` looks like a single path that exists, read it with the Read tool

If the input is empty or only whitespace, ask the user to paste the request before proceeding. Do not invent a request.
</input_handling>

## Phase 1: Decompose the Request

<decomposition priority="first">
Extract **two separate lists** from the prose:

### 1. Capabilities — what the customer wants built

A capability is a single verifiable engineering ask. Customer messages bundle many capabilities together — your job is to separate them.

**For each capability, capture:**
- A short ID (A, B, C, ...)
- A one-line statement in the form `<verb> <object> [via <channel>] [with <constraint>]`
- The exact quote(s) from the request that imply it

**Rules:**
- One verb per capability — if you wrote "and" or a comma, split it
- Don't invent capabilities the request didn't imply
- Don't merge capabilities that have different effort profiles

### 2. Constraints — rules that EXCLUDE solutions for this customer

A constraint is a phrase that rules out a class of solutions for **this customer specifically**, not a hint about what to build. Constraints filter the phased recommendation later.

**For each constraint, capture:**
- A short tag (C1, C2, ...)
- A one-line statement of what is excluded and for whom
- The exact quote from the request
- Which capabilities (by ID) it excludes for this customer

**Examples of constraint phrases:**
- "they can't be sent candidate data via email per IT policy" → excludes email-delivery capability *for this customer*
- "must run on-prem" → excludes SaaS-hosted solutions
- "GDPR-compliant only" → excludes capabilities that move data outside the EU
- "no PII in logs" → excludes solutions that emit PII to log streams

### Worked example

> "Customer wants extracts multiple times a day, sent via SFTP or dropbox — they can't receive data via email per IT policy. Custom fields joined to KPI data."

Decomposes to:
- **Capabilities**:
  - A. Custom field support on uploads
  - B. Join custom-field data with KPI/analytics data
  - C. Scheduled report generation (multiple times/day)
  - D. Email delivery channel *(still extract this — the customer mentioned distribution by email may apply to other customers; it's just excluded for **this** one)*
  - E. SFTP delivery channel
  - F. Dropbox delivery channel
- **Constraints**:
  - C1. Email is blocked for this customer — *"they can't receive data via email per IT policy"* — excludes capability D for this customer

**Critical distinction**: Capability D (email delivery) is still a valid product capability — other customers may use it. But constraint C1 means D is **out for this customer**. The phased recommendation in Phase 4 must respect this: the customer's path uses E and F, not D.

**Failure mode this prevents**: treating a constraint phrase as motivation to build the excluded capability. "They can't get email" does NOT mean "build email delivery." It means "build the capabilities that bypass email."
</decomposition>

## Phase 2: Confirm Decomposition (Brief)

<confirmation>
Present **both lists** back to the user — capabilities and constraints — and ask **one** question via AskUserQuestion:

> "Here's how I read the request — anything to add, remove, split, or reclassify (capability ↔ constraint)?"

Options:
- "Looks good, proceed with research"
- "I'll edit the list" (then user types changes)
- "Add capability X" / "Add constraint Y"

Do not ask multiple rounds of clarification — one pass only.

**Watch for reclassification specifically**: it is common to mistake a constraint ("they can't get email") for a capability ("build email delivery"). The user is the second pair of eyes that catches this — so present the lists clearly and let them flag misreadings.
</confirmation>

## Phase 3: Parallel Research

<research priority="critical">
Spawn **one Explore subagent per capability** in parallel (single message, multiple Agent tool calls). Each subagent receives a self-contained prompt.

**Each Explore prompt must include:**
1. The capability statement (one line)
2. The original quote from the customer request
3. Specific search terms to investigate (3–8 keywords/identifiers)
4. The exact output schema below
5. `model: "sonnet"` (per repository convention — Explore agents must use sonnet)

**Required output schema for each Explore subagent:**

```markdown
## Capability <ID>: <statement>

**Status**: EXISTS / PARTIAL / MISSING
**Effort**: trivial / small / medium / large
**Evidence**: <file:line references — at least 2 if Status is EXISTS or PARTIAL>
**Gap**: <what is missing or would need to change; "none" if Status is EXISTS>
**Notes**: <one paragraph max — surprises, hidden bugs, naming caveats>
```

**Effort scale (calibrate carefully):**
- **trivial** — config change, single-line edit, or already done
- **small** — hours; one file or a small group of files, no new infrastructure
- **medium** — days; new endpoint/model/migration, fits existing patterns
- **large** — weeks; new infrastructure, new dependencies, new architectural pattern, or cross-cutting changes

Wait for all subagents to return before proceeding to Phase 4.
</research>

## Phase 4: Synthesize the Report

<synthesis>
Produce a single markdown report with these sections in order:

### Header

```markdown
# Intake Feasibility — <short slug derived from the request>

**Source**: <one-sentence summary of who asked and what>
**Codebase**: <repo name from pwd>
**Date**: <today's date>

## Constraints (apply to this customer only)

| Tag | Constraint | Excludes |
|-----|------------|----------|
| C1 | <one-line statement> | <capability IDs this rules out for this customer> |
```

Omit the Constraints section entirely if Phase 1 found none. If constraints exist, this section is **required** and must appear above the Capability Map — readers need to know what's off the table before they read what's on the table.

### Capability Map (Required)

A single table with all capabilities:

| ID | Capability | Status | Effort | Key Finding |
|----|------------|--------|--------|-------------|
| A | ... | EXISTS | trivial | ... |

The "Key Finding" column is one short sentence with the most important file:line evidence or the dominant gap. Detailed evidence belongs in the per-capability sections (next).

### Per-Capability Detail (Required)

One subsection per capability with the schema returned by the Explore subagents. Do not summarize — copy the full evidence.

### Top 3 Risks (Required)

The three biggest unknowns or risks for the **overall request**, not per-capability. Each risk has:
- A one-line title
- One paragraph explaining the risk and its impact
- A concrete way to verify or de-risk it

Risks to watch for:
- Silent bugs that mean the capability "exists" but is broken (the most dangerous finding — call these out loudly)
- Missing infrastructure where the capability is implementable in principle but requires net-new patterns the codebase has never used
- Cross-team or external service dependencies the engineer alone cannot resolve
- Security/compliance gates (data retention, PII, IT policies mentioned in the request)

### Phased Recommendation (Required)

Group capabilities into phases by effort and dependency, with this format:

```markdown
### Phase 1 — <theme> (<aggregate effort>)
**Solves for this customer:** <which part of the ask, after applying constraints>
- <Capability ID and one-line action>
- ...

### Phase 2 — <theme> (<aggregate effort>)
...

### Phase 3 — <theme> (<aggregate effort>)
...

### Excluded for this customer
- <Capability ID> — blocked by <Constraint tag>: <one-line reason>
```

**Rules:**
- Order phases by smallest-impact-to-customer-blockers first. Customer asks like "we need this by Q3" mean Phase 1 must unblock the most painful part of their workflow.
- **Apply constraints before phasing.** A capability that violates a constraint is NOT placed in any phase — it goes in the "Excluded for this customer" list. Do not hedge with "might work if X passes review"; the constraint is the customer's word, take it at face value.
- A capability excluded for this customer may still be a product priority — note that separately if relevant, but do not let "good for the product" override "blocked for this customer."

### Open Questions (Optional, only if unresolved)

Bullet list of questions back to CSM/Sales. Each must be answerable by the customer (not engineering). Format: "Question? — *Why it matters: <impact>*"
</synthesis>

## Phase 5: Print, Then Offer to Save (Optional)

<output>
**Default behavior is print-only.** Render the full report inline in the chat so the engineer can read, copy, or paste it into a ticket immediately.

**After printing, ask once via AskUserQuestion:**

> "Save this report as a file?"

Options:
- "No, the chat copy is enough" (default — do nothing further)
- "Yes, save to `INTAKE-feasibility-<slug>.md`"
- "Yes, save with a custom filename" (then the user provides the path)

If the user picks save, write the file and print the absolute path. If the user declines or does not respond clearly within their next message, do not write anything — the chat copy is the artifact.

**Slug derivation** (when saving): take the most distinctive 2–4 words from the request, kebab-case, lowercase. Examples:
- "scheduled-data-extracts"
- "custom-field-csv-export"
- "saml-sso-integration"
</output>

<critical_rules>
<rule priority="blocking">
YOU MUST run Phase 3 research with parallel Explore subagents. Never form Status/Effort verdicts from intuition or training data — every verdict must be backed by file:line evidence from the actual codebase being researched.
</rule>

<rule priority="blocking">
Each Explore subagent prompt MUST set `model: "sonnet"`. Haiku lacks the analysis depth needed for accurate pattern recognition across a codebase.
</rule>

<rule priority="blocking">
THIS COMMAND DOES NOT IMPLEMENT. After Phase 5, YOU MUST STOP. Do NOT:
- Write, edit, or create any code files
- Write the report unless the user opts in via Phase 5's AskUserQuestion (the default is print-only)
- Create a SPEC, PLAN, or PRD file
- Enter plan mode or start implementing
- Call `/feature-dev:spec`, `/feature-dev:tdd`, `/discuss:feature`, or any other skill yourself
- Proceed even if the path forward seems obvious

End your response with: "Next: pick the capabilities to pursue, then run `/discuss:feature` or `/feature-dev:spec` for each." No exceptions.
</rule>

<rule priority="blocking">
NEVER claim a capability EXISTS without at least two file:line citations. NEVER claim a capability is MISSING without at least one negative search confirmation (e.g., "grep for `paramiko` in `Pipfile` returns no results"). Unverified claims are worse than no claims — they mislead CSM into making promises engineering can't keep.
</rule>

<rule priority="recommended">
When a capability appears to EXIST, look harder for silent bugs. The most dangerous finding is "yes we support that" when the integration is silently broken (e.g., a JSON column exists but the importer drops the data). Surface these as Risks even if every individual capability passes.
</rule>

<rule priority="recommended">
Write the report so a CSM can read the table and risks without engineering help, AND an engineer can verify any verdict by clicking the file:line links. Two audiences, one document.
</rule>
</critical_rules>

## Rationalization Defenses

If you catch yourself thinking any of these, STOP — you are about to violate the feasibility-only contract:

| Rationalization | Why It's Wrong |
|----------------|----------------|
| "The user already implied they want Phase 1 built, I'll start the SPEC" | Feasibility ≠ approval to build. Engineering, CSM, and the customer all have to agree on scope first. The handoff is an invocation of `/feature-dev:spec`, not your assumption. |
| "I know this codebase well enough to skip the Explore subagents for capability X" | Codebases drift. Memory and intuition produce confident-sounding wrong answers. The whole value of this command is verifiable evidence — skipping research replaces evidence with vibes. |
| "The customer's request is small, I can do it in one pass without decomposition" | One-pass synthesis hides bundled capabilities. The ADT-style request looks like "send us a CSV" but contains 6+ distinct asks with very different effort profiles. Always decompose. |
| "The capability list looks complete, I'll skip the user confirmation" | Customer messages have hidden assumptions only the human reader can validate. Skipping confirmation lets the entire downstream report build on a wrong premise. |
| "I'll mark this PARTIAL without finding the gap — the engineer can figure it out" | PARTIAL without a specific Gap is useless to CSM (who can't read code) and to engineering (who has to redo the research). Every PARTIAL needs a one-sentence Gap. |
| "Status: EXISTS, I don't need to look for silent bugs" | The most damaging feasibility errors are "yes, supported" answers that mask broken integrations. Always probe whether the integration round-trips correctly end-to-end. |
| "I'll save the file without asking — the user probably wants it" | Phase 5 is opt-in by design. Force-saving creates artifact churn (`INTAKE-*.md` files left around for asks the engineer never wanted to track). Always ask. |
| "I'll trim the per-capability detail to keep the report short" | The table is for CSM, the per-capability evidence is for engineering. Trimming the detail breaks one of the two audiences this report serves. |
| "They said 'no email,' which means I should research email delivery to see if there's a workaround" | A constraint excludes a solution; it does not motivate building it. "They can't get email" → use SFTP/file-drop, do NOT propose "email a signed link" as a clever bypass. The customer's word is the customer's word. |
| "Email-with-signed-URL is technically not 'sending data via email' so the constraint doesn't apply" | The customer's IT department wrote the policy, not you. A signed link IS the candidate data being delivered via email from the customer's perspective — the file is one click away. Do not lawyer the constraint. |

<mindset>
- The customer's prose is a hypothesis, not a specification
- Your job is to translate hand-wavy asks into verifiable claims
- Surprise findings (silent bugs, missing infra, wrong-by-default) are the most valuable output
- A "no" backed by evidence is more useful than a "maybe" hedged with caveats
</mindset>
