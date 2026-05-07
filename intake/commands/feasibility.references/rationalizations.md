# Feasibility — Rationalization Defenses & Common Mistakes

Loaded by `/intake:feasibility` when self-checking against shortcuts and quality failures.

## Rationalization Defenses

Catches *violating the feasibility-only contract*. If you catch yourself thinking any of these, STOP:

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
| "The customer set a date, so I can use that as our delivery commitment" | The customer asked; engineering assesses; CSM negotiates. A TEMPORAL constraint is a window to evaluate against, not a date for engineering to commit to. Use ✅/⚠️/❌ "achievable in principle" language, never "we will deliver by X". |
| "The deadline is unrealistic for the larger items, I'll just leave them off the report" | Don't drop capabilities to hide an awkward verdict. ❌ "not realistic in this window" is the honest, useful answer — it tells CSM what to negotiate around. Hiding it just delays the same conversation. |
| "I can skip the alternatives agent — the capability agents already cover what exists" | The capability agents look vertically (does X work?). The alternatives agent looks horizontally (what existing pattern could be cloned, what combination of EXISTS could meet the ask without new code?). Different lens, different output — skipping it costs you the workarounds that often *are* the right answer. |
| "I'll list a workaround as 'an admin can run this hourly' even though that's operationally unrealistic" | A workaround that no human would actually operate is not a workaround. The bar is "could realistically be operated by a real CS team without burning out". State the operational burden honestly so the reader can judge. |
| "I found something similar in the codebase, I'll list it as a pragmatic alternative even without specific file:line" | Pragmatic alternatives must be backed by file:line evidence. "We probably have something like this" is speculation — same problem as guessing Status: EXISTS without citations. |

## Common Intake Mistakes

Catches *producing a low-quality report*. Different failure mode from the boundary violations above:

| Mistake | What it looks like | Fix |
|---------|-------------------|-----|
| **Under-decomposed capabilities** | One capability called "API integration" or "data sync" | Apply the one-verb-per-capability rule. If the statement contains "and" or a comma, split it. Bundled capabilities hide effort variance. |
| **Generic risks** | "Performance, security, scalability might be issues" | Tie each risk to a specific file:line, data flow, or capability ID. Untied risks get ignored; tied risks drive de-risking work. |
| **Customer framing taken as the correct framing** | The customer described a solution; you researched that solution literally | When the requested capability looks like one of several solutions to a deeper need, surface the underlying problem in Open Questions for CSM. Don't second-guess silently — flag it. |
| **Equal-priority phasing** | Phase 1 contains capabilities A, B, C, D, E in arbitrary order | Order Phase 1 by customer-blocker impact. The capability that unblocks the most painful part of *their* workflow goes first. |
| **No counter-recommendation when scope is large** | A 6-capability ask presented as "all feasible, here's the phased plan" | Take a position. "I would push back on capability E — significant scope without clear value, recommend deferring." Useful to CSM; neutral compliance is not. |
| **Surface-level EXISTS** | Status: EXISTS based on a single matching keyword (e.g., a model named `WebhookConfig`) | Confirm the integration *round-trips*. Find producer, consumer, and a test or log line showing the data flow works end-to-end. A name match is not a working feature. |
