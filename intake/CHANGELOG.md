# Changelog

All notable changes to this project will be documented in this file.

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
