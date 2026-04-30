# Changelog

All notable changes to this project will be documented in this file.

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
