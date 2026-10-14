# Changelog

## [1.3.0] - 2026-10-14

### Added
- **`/debug:debug` Step 1 is now a gate: build a feedback loop.** No Step 2 until there is one command, already run and shown with its output, that asserts the user's exact symptom, gives the same verdict every run, takes seconds, and runs without a human. If one cannot be built, the command stops, lists what it tried, and asks for an environment, a captured artifact, or permission to instrument. Adapted from mattpocock/skills `diagnosing-bugs` (MIT).
- `references/feedback-loops.md`: ten ways to build a loop (failing test, curl, CLI diff, headless browser, replayed capture, harness, fuzz, bisect harness, differential run, human-run script), how to tighten it, and the flaky and performance branches.
- Step 4 asks for 3-5 ranked hypotheses, each with a prediction, shown to the user without blocking, tested one variable at a time. Debug logs carry one `[DEBUG-xxxx]` tag and Step 6 greps them out.
- Step 3 ends when every remaining element of the repro is load-bearing. Step 5 reports "no good place to test this" as a finding instead of writing a test too shallow to catch the bug.
- `allowed-tools`: `diff`, `npx playwright`, `npx vitest`, and `git branch --show-current` (used by the context line). `curl` is left to prompt, since this workflow reads possibly hostile log output.

### Changed
- `/debug:incident`: mitigation comes before the feedback-loop gate during an outage.
- `/debug:triage` and `error-patterns.md` tell the agent to tag the logs it adds, so they can be removed.
- Verification runs the tests for the changed code and its callers instead of the full suite.

### Fixed
- `/debug:debug` and `/debug:incident` lose their `Stop` hooks: both can stop to ask the user (incident asks which phase you are in), which ended the first turn early and printed "complete" before the work was done. Each now ends its final message with the next steps. `/debug:triage` keeps its hook: it never asks and finishes in one turn.

## [1.2.2] - 2026-10-02

### Changed
- README gains a **Needs** section listing prerequisites (`gh`, MCP servers, browser, external CLIs), replacing the old Requirements list.

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
