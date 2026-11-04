# Changelog

## [2.2.0] - 2026-11-04

### Added
- **`scripts/ship-preflight.sh`: Phase 1 as one deterministic step.** It prints one JSON line (branch, default branch and where it came from, remote, upstream, ahead/behind, commits ahead of the base, staged/unstaged/untracked counts, `mode`, `gh` state, `gh-feedback`, the open PR for the branch, the PR templates) and exits 0 when /ship can go on, or with a distinct code for each early stop: 2 nothing to ship, 3 default branch with `--yes`, 4 detached HEAD, 5 no remote, 7 git failed. `--yes` is passed through so the script, not the model, applies the headless rules. Tests in `tests/test-ship-preflight.sh` (21 cases, fake `gh`, throwaway repo). **Why:** the skill decided its preconditions in prose, running `git status`, `gh repo view`, `gh pr view` and `gh feedback --version` and interpreting each; the same state could read differently from run to run, and a "no changes" or "already a PR" call was a judgement, not a fact.

### Changed
- **Phase 1 is a bash block and an exit-code table** (the shape of the pipeline's Phase 0); the later phases read the preflight fields (`upstream`/`remote` for the push form, `pr` to skip the PR, `pr_templates` for the template, `gh_feedback` for the watcher) instead of re-running those commands. The three `` !` `` git embeds in Context are gone.
- **No remote stops before anything is staged** (preflight exit 5) instead of after the commit; a detached HEAD is now an explicit stop (exit 4). A branch behind its upstream is reported up front (`behind`), and the push-rejected path is unchanged.
- `allowed-tools` gains `Bash(${CLAUDE_PLUGIN_ROOT}/scripts/*)`.
- **`evals/`: a `claude plugin eval` suite for the early stops** (four offline cases against a fake `gh`, deterministic graders only). Written and validated without a model; it has not completed a model run yet, because the eval runner's sandbox does not nest inside a Claude session. Run `evals/run.sh` from a terminal.

## [2.1.1] - 2026-11-01

### Fixed
- **The Copilot request is confirmed, or reported as not requested.** A `gh pr edit --add-reviewer @copilot` (or the REST request) that returns 0 is not a landed request: on one PR two accepted calls left nothing in `reviewRequests`, in the REST `requested_reviewers` nor in the timeline. Phase 6 now checks those three listings after the request, retries once through the REST API with the login GitHub documents (`copilot-pull-request-reviewer[bot]`, the same bot account as `Copilot`), and reports `Copilot: requested (<login>, seen in <listing>)` or `Copilot: not requested` with why. Phase 7 waits for Copilot only when it was confirmed. The old text claimed the listings never show bot reviewers and told the model not to look; that hid the failure.

## [2.1.0] - 2026-11-01

### Added
- **`--yes`**: no questions, for a headless caller (the `factory` plugin's `/factory:ship`, or a command invoking the skill). On the default branch it stops instead of asking to branch; with a clean tree ahead of the base it runs the tests and goes on to the push and the PR; mixed concerns stage every non-secret file; a missing test runner is reported in Evidence instead of asked about; the PR is created without asking (first template by name when several exist). Implies `--no-watch`. A caller that invoked the skill may name what the PR body must lead with; an existing PR is never touched.
- **`--evidence-file <path>`**: test lines from earlier runs, added verbatim under Evidence as "Earlier runs (reported by the caller)", apart from Before and After.

## [2.0.0] - 2026-10-31

### Changed (breaking)
- **The CI and Copilot watcher is `gh feedback watch`**, from the [`gh-feedback`](https://github.com/juanmhidalgo/gh-feedback) `gh` extension, instead of `scripts/pr-watch.sh`. Same flags, final block and exit codes. Without the extension, `/ship` stops after the PR and reports how to check CI and how to install it (`gh extension install juanmhidalgo/gh-feedback`). `jq` is no longer required.

### Removed
- `scripts/pr-watch.sh`, and the `scripts/*` permission it needed.

## [1.6.1] - 2026-10-28

### Fixed
- **`pr-watch.sh` no longer dies on its own `sort`/`comm` under a UTF-8 locale.** Check names with `-`, `_` or mixed case sort differently under `en_US.UTF-8`, `comm` reported "input is not in sorted order" and exited 1, and `set -e` killed the watcher before it printed its final block, so a green CI read as a failure. The script now runs with `LC_ALL=C`.

## [1.6.0] - 2026-10-14

### Added
- **PR body: Evidence and Merge Danger sections.** Evidence is a before/after pair built only from runs this session made: "After" is the Phase 4 test run, "Before" is a failing run actually observed, otherwise `not captured`. Ship never checks out the base or reverts code to manufacture one. Merge Danger is one line for the door (one-way or two-way, with the reason) and one for the blast radius. Rollback Triggers stay.
- **Summary visual.** The Summary is one sentence of why plus at most one visual (call tree, file tree, pseudocode, Mermaid, or a `diff` of the shape), derived from the diff and skipped for one-file, docs, config, or dependency-only changes. Menu in `skills/ship/references/pr-body.md`, adapted from mattpocock/skills (MIT).

### Fixed
- **The repo's own PR template is respected.** When the repo has a `pull_request_template.md` (in `.github/`, `docs/`, the root, or `.github/PULL_REQUEST_TEMPLATE/`), ship keeps its headings and order and appends Merge Danger and Rollback Triggers only when the template has no equivalent. Before, ship ignored it.

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
