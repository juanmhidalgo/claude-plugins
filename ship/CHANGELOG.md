# Changelog

## [1.5.0] - 2026-10-06

### Added
- **Phase 7 — watch CI and Copilot**: once the branch has an open PR, `/ship` runs `scripts/pr-watch.sh` in the background and ends its turn. The script exits when every check has finished and, if Copilot's review was requested in this run (and the PR is not a draft), when Copilot has reviewed the current head commit. Older Copilot reviews do not count. It gives up after 30 minutes (exit 3). It was tested against a real PR, where it found a Copilot review and counted its 5 inline comments.
- **Phase 8 — act on the result**: a CI failure is reported with the failing log and not fixed. Copilot's inline comments go to `/code-review:pipeline <PR#>`, and CI is then watched once more on the fix commit (no second Copilot round). A review with no inline comments is only reported.
- `--no-watch` skips both phases.
- **Natural-language trigger**: `disable-model-invocation` removed, so "let's ship it", "ship it", "ship this" or "ready to ship" start the skill without typing `/ship`. The description excludes requests to only commit or only push, and questions about whether the work is ready. Flags are read from the wording ("as a draft" → `--draft`, "don't wait" → `--no-watch`). This is a deliberate exception to the side-effects rule in `.claude/rules/plugin-creation.md`: "ship it" is the explicit instruction the rule protects. Tested with `claude -p` in a scratch repo with no remote and Bash disallowed: "looks good, let's ship it" invoked `ship`, "commit this please" invoked `commit`, and "is this ready to ship?" invoked no skill.

### Changed
- When `gh pr edit --add-reviewer @copilot` fails, the Copilot request is retried through `gh api .../requested_reviewers` with `Copilot` capitalized, and confirmed in the issue timeline: `reviewRequests` never lists bot reviewers.

### Removed
- The `Stop` hook. It printed "Ship complete" at the end of the first turn, which ends before the PR question is answered and long before the watcher finishes. Phase 8 now writes the final report.

### Why
The same instruction ("after the PR, check CI, wait for Copilot, run /code-review:pipeline on its feedback") was being typed by hand at the end of most sessions. In one of them the hand-off failed because the pipeline could not be invoked by the model. code-review 3.7.0 fixes that.

## [1.4.3] - 2026-10-02

### Changed
- README gains a **Needs** section listing prerequisites (`gh`, MCP servers, browser, external CLIs), replacing the old Requirements list.

## [1.4.2] - 2026-09-22

### Changed
- Removed the `SUBAGENT-STOP` guard: the skill has `disable-model-invocation: true`, so no subagent can reach it.

## [1.4.1] - 2026-08-23

### Fixed
- Sibling-session matching no longer assumes the `ListAgents` listing shows working directories: dogfooding showed some versions list only name and status. Matching now uses the working directory when shown, falls back to the session's name, and only messages sessions confidently attributable to this repo.

## [1.4.0] - 2026-08-23

### Added
- **Sibling-session notification** after a default-branch push: Phase 5 now uses `ListAgents` to find other local sessions working on the same repo (parallel worktrees included) and sends each one a single concise `SendMessage` saying what landed and whether rebasing is advisable. Best-effort by design: skipped on feature-branch pushes, with `--no-notify`, or when cross-session messaging is unavailable, and a failure never fails the ship workflow.

### Why
This is the "coordinate parallel worktrees" use case from Claude Code's cross-session messaging: when master moves, sessions building on it should hear about it before their next rebase surprises them.

## [1.3.0] - 2026-05-06

### Added
- **Rollback Triggers** section in the PR body template (Phase 6). For runtime-impacting changes, the PR now lists 2-4 concrete thresholds (error rate, p99 latency, synthetic check failures, customer-reported regressions) that would warrant reverting the change post-merge. For non-runtime changes (docs, tests, config without behavior change), uses `N/A — non-runtime change` honestly rather than fabricating triggers. Database migrations always include a reversal procedure trigger.

### Why
Borrowed from Anthropic's `engineering:deploy-checklist` skill, which makes the operational point explicit: rollback criteria must be decided *before* deploying, not during an incident. Capturing them in the PR body puts the criteria where reviewers see them and where on-call can find them later.

## [1.2.1] - 2026-05-06

### Changed
- Trimmed `ship` skill description to fit Claude Code's skill-listing budget.

## [1.2.0] - 2026-04-16

### Changed
- Rewrote skill/command descriptions to contain only triggering conditions and boundaries, removing workflow step summaries that caused the model to shortcut skill bodies
- Added SUBAGENT-STOP tag to the `ship` skill to prevent premature termination

## [1.1.0] - 2026-04-14

### Added
- Request Copilot code review by default when creating PRs (`gh pr edit --add-reviewer @copilot`)
- `--skip-copilot-review` flag to opt out of automatic Copilot review
- Graceful fallback: warns if Copilot review is unavailable on the repo's plan

## [1.0.1] - 2026-03-30

### Fixed
- Skip test phase when only non-code files are staged (docs, config, markdown, etc.)
- Prevents unnecessary test suite runs for documentation-only changes

## [1.0.0] - 2026-03-27

### Added

- Initial release of ship plugin
- End-to-end shipping workflow: status → smart staging → commit → test → push → PR
- Smart staging with change cohesion analysis: auto-stages when all changes are related, groups and asks when mixed concerns detected
- Auto-generated conventional commit messages (no user confirmation needed)
- Auto-generated branch names when creating feature branches from default branch
- Auto-detection of repo's default branch via `gh repo view`
- Test runner auto-detection (npm, pytest, make, cargo, go)
- `--skip-tests` flag to bypass test phase
- `--no-pr` flag to skip PR creation
- `--draft` flag to create draft PRs
- Stop hook showing PR URL and CI status
- Secret file exclusion (.env, credentials, tokens, private keys)
