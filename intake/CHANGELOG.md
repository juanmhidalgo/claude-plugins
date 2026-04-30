# Changelog

All notable changes to this project will be documented in this file.

## [0.7.0] - 2026-04-30

### Added
- `/intake:feasibility` Phase 3 now spawns **N + 1 parallel Explore subagents**: N capability agents (vertical lens — "does X work?") plus **1 alternatives agent** (horizontal lens — "what existing patterns could be cloned, extended, or repurposed?"). The two lenses are kept separate so each agent's output schema stays clean.
- New synthesis section: **Workarounds available today** — combinations of EXISTS capabilities + manual or admin operation that meet some subset of the customer's ask without writing new production code. Includes operational burden and what each workaround does NOT solve.
- New phased-recommendation subsection: **Pragmatic alternative path** — when an existing pattern in the codebase could be cloned/extended/broadened to ship a larger acceptable version of the ask faster than building bespoke. Always framed as a trade-off (what it sacrifices vs. what it gains), not a strict replacement.
- `/intake:respond-draft` Format A and Format B both surface workarounds and pragmatic alternatives when the feasibility report contains them. Empty-section rule applies — omit headings that have no entries.
- `/intake:objection-prep` checklist gains a new **pragmatic-alternative pushback** category and the **workaround feasibility** category is updated to recognize the report's first-class `Workarounds available today` data.
- Three new rationalization defenses targeting the failure modes the alternatives lens introduces: skipping the alternatives agent because "the capability agents covered it", listing operationally-unrealistic workarounds, and citing pragmatic alternatives without `file:line` evidence.

## [0.6.0] - 2026-04-30

### Added
- Constraints now have an explicit sub-type: **POLICY** (excludes solutions for this customer regardless of timing) vs **TEMPORAL** (deadlines that filter capabilities by feasibility-within-window). The constraints table in `/intake:feasibility` reports gains a `Type` column.
- `/intake:feasibility` synthesis adds a **Feasibility against [customer]'s stated deadline** section with per-capability ✅/⚠️/❌ verdicts when a TEMPORAL constraint exists. The verdict guidance maps effort buckets against window length (< 1 week / 1–4 weeks / 1–3 months / 3+ months), with explicit framing that every verdict is "achievable *in principle*" not "we will deliver by X".
- `/intake:respond-draft` Format A and Format B both gain an `Against [customer]'s stated deadline` section that surfaces the per-capability verdicts to CSM. Empty bucket rule applies — ⚠️ and ❌ rows are omitted when they have no entries, and the entire section is omitted when no TEMPORAL constraint exists.
- New rationalization defenses across both commands targeting the failure modes that motivated this change: treating the customer's stated date as a delivery commitment, dropping awkward `❌` items to hide the verdict, and proposing alternative dates (CSM's job, not engineering's).

## [0.5.0] - 2026-04-30

### Changed (BREAKING — output structure)
- `/intake:respond-draft` is reframed as a **CSM summary of engineering findings**, not a customer-facing reply draft. The customer-facing block is removed from Format B — drafting customer-facing communication is CSM's job, not engineering's, and pre-writing it created expectation drift around voice and authorship.
- Format B now contains: TL;DR engineering read for CSM → open questions to relay → `[CSM TO CONFIRM TIMELINE]`. No quotable customer-facing block.
- Added two rationalization defenses guarding the new boundary: "I should still draft a customer-facing version, CSM will appreciate the head start" and "CSM will paraphrase my Slack message verbatim, I should write it customer-ready."
- Description, header, and Phase 2 wording shifted from "customer language" to "plain language" with CSM as the explicit reader. Translation rules unchanged in substance — engineering jargon (file paths, library names) still drops; product-domain terms (audience, candidate, KPI dashboard) still stay.

## [0.4.0] - 2026-04-30

### Changed
- `/intake:respond-draft` Format A now omits empty commitment-category buckets (no more "Currently supported: (none with no caveats)" placeholder lines).
- `/intake:respond-draft` Format B is reframed as a **Slack message to CSM by default** — the channel most engineers actually use to coordinate with CSM. The structure leads with a TL;DR for CSM, then a quotable customer-facing block CSM can copy-paste-and-adapt for the customer. Other channels (email, ticket comment) work with the same content; the user can ask for an adapted version when needed (no explicit `--channel` argument by design).
- `/intake:objection-prep` output is now tiered into **Must-prep / Should-prep / Nice-to-prep** sections so engineers can triage at a glance instead of scanning a flat list of 8–10 Q&A entries. Tier rules are explicit — silent bugs, constraint-blocked customer-named capabilities, and large-effort customer-named capabilities go to Must-prep automatically.

## [0.3.0] - 2026-04-30

### Added
- `/intake:respond-draft <feasibility-report>` — translate an engineering feasibility report into a customer/CSM-facing reply.
  - Produces two formats: structured status (for CSM internal review) and customer-facing prose (forwardable as-is).
  - **No-calendar-dates discipline**: blocking rule prevents the draft from emitting calendar dates, week counts, sprint references, or any specific timing. Uses `[CSM TO CONFIRM TIMELINE]` placeholders where timelines naturally fit so the CSM/owner — not engineering — sets delivery commitments.
  - Effort buckets (trivial/small/medium/large) translate to commitment categories (currently supported / supported with adjustment / possible with deliberate planning / significant initiative required) — describes shape of effort, not timing.
  - Honors `Excluded for this customer` constraints from the feasibility report and surfaces alternatives.
  - Six rationalization defenses targeting the "I'll add 'approximately X weeks' to be helpful" failure mode and its variants.
- `/intake:objection-prep <feasibility-report>` — anticipate the questions and pushback that will come back from CSM, Sales, or the customer when the report is shared.
  - 10-category objection checklist (effort, hack-it-for-one-customer, constraint, buy-vs-build, existing-customer impact, why-not-already-built, workaround feasibility, silent-bug embarrassment, competitor-does-this, constraint re-litigation).
  - Q&A schema captures the likely question in the asker's actual voice (Sales-pressure, CSM-relationship-anxiety, customer-expectation), with a prepped response and an optional "if pushed" escalation.
  - Reports both triggered and non-triggered categories so the engineer knows what was *not* anticipated.
  - Five rationalization defenses against generic-answer noise, softening hard findings, and lawyering away customer constraints.

## [0.2.0] - 2026-04-30

### Added
- Phase 1 now extracts **constraints** in addition to capabilities. A constraint is a phrase that excludes a class of solutions for this customer (e.g., "no email per IT policy"), and is tracked separately from capabilities.
- Phase 2 confirmation prompts the user to flag misclassifications (capability ↔ constraint) before research starts.
- Phase 4 report template now includes a `Constraints` section above the Capability Map and an `Excluded for this customer` list in the phased recommendation.
- Two new rationalization defenses targeting the failure mode that motivated this change: treating a constraint as motivation to build the excluded capability, and "lawyering" the constraint with technical workarounds (e.g., "a signed URL isn't really sending data via email").

### Changed
- Phasing rule: constraints are applied **before** phasing. Capabilities that violate a constraint are listed under "Excluded for this customer," never in a phase with a hedge like "might work if X passes review."

## [0.1.0] - 2026-04-30

### Added
- Initial release of the `intake` plugin
- `/intake:feasibility` command — translate unstructured customer/CSM/Sales/Support requests into engineering feasibility reports against the current codebase
  - 5-phase workflow: decompose → confirm → parallel research → synthesize → save
  - Capability decomposition pattern: extract atomic asks (`<verb> <object> [via <channel>] [with <constraint>]`)
  - Parallel Explore subagents (one per capability), with `model: "sonnet"` enforced per repository convention
  - Output schema: capability map table + per-capability evidence + Top 3 risks + phased recommendation + open questions
  - Prints the report inline by default; offers to save as `INTAKE-feasibility-<slug>.md` only when the engineer opts in
  - Discussion-only contract: hard-stops after the report and hands off to `/discuss:feature` or `/feature-dev:spec`
  - Rationalization defense table covering the seven failure modes observed during scoping (skipping research, skipping decomposition, missing silent bugs, etc.)
