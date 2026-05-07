# Changelog

## [1.2.1] - 2026-05-07

### Changed
- Added `Do NOT use for…` boundary to `/debug:triage` description (directs systematic debugging to `/debug:debug` instead).

### Why
Aligns descriptions with Anthropic's Claude Code best practices ("Description = triggering conditions only, with what NOT to use it for").

## [1.2.0] - 2026-05-06

### Added
- **`/debug:incident`** command and **`incident-response`** skill — manages the full incident lifecycle through three explicit modes: `new` (triage with SEV1-4 classification + roles assignment), `update` (status broadcast with cadence guidance per severity), and `postmortem` (blameless retrospective with 5 Whys, What Went Well/Poorly, action items table with P0/P1/P2 owners).
- Common Postmortem Mistakes anti-pattern catalog (naming the person, 5 Whys stopping early, action items without owners, symptom-only timeline, skipping What Went Well, pre-populated conclusions).
- Rationalization Defenses for postmortem-skipping and severity-downgrading patterns.
- Cross-skill delegation: incident-response is the coordination layer; root-cause investigation delegates to `debug:debugging-strategies`.

### Changed
- Plugin description expanded to cover incident response alongside debugging.

### Why
Borrowed from Anthropic's `engineering:incident-response` skill. Our marketplace previously covered debugging (active troubleshooting) and shipping (deploy) but had no skill for *post-deploy emergency*. Adding it as a sibling skill in `debug` reuses the existing "stop-the-line, preserve evidence, root cause" mindset and avoids creating a separate plugin for a closely related concern.

## [1.1.1] - 2026-05-06

### Changed
- Trimmed `debugging-strategies` skill description to fit Claude Code's skill-listing budget.

## [1.1.0] - 2026-04-16

### Changed
- Rewrote skill/command descriptions to contain only triggering conditions and boundaries, removing workflow step summaries that caused the model to shortcut skill bodies

## [1.0.0] - 2026-04-04

### Added

- `debug` command: Systematic 6-step debugging workflow with Stop-the-Line Rule and regression guard enforcement
- `triage` command: Quick error classification with decision trees for test, build, and runtime failures
- `debugging-strategies` skill: Structured triage methodology, error output safety rules, anti-rationalization table
- Reference: Error patterns for test failures, build errors, runtime issues, non-reproducible bugs, and git bisect
