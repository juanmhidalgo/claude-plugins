# Changelog

## 0.3.2 (2026-11-01)

### Changed
- **The factory never requests a Copilot review.** `/factory:ship` invokes `/ship` with `--skip-copilot-review`, and the close block says `Copilot: skipped (the factory does not request Copilot; the PR review is the human gate)`. The confirm-and-retry text from 0.3.1 stays in the `/ship` skill, which other repositories use with Copilot; it no longer applies to the stage. The contract (rule 9) and the README say so.

## 0.3.1 (2026-11-01)

### Fixed
- **`/factory:ship` confirms the Copilot request or says `Copilot: not requested`.** After `gh pr edit <n> --add-reviewer @copilot` the stage checks `reviewRequests`, the REST `requested_reviewers` and the timeline, retries once through the REST API with `copilot-pull-request-reviewer[bot]` (ship 2.1.1's step 8), and the close block says `requested (<login>, seen in <listing>)` only when a listing shows it, else `not requested` with why. In the first end-to-end run two accepted calls left no request and the stage reported it as "requested twice".

## 0.3.0 (2026-11-01)

### Added
- **`/factory:ship` honours the repository's PR template.** When `.github/PULL_REQUEST_TEMPLATE.md` (or the other names `/ship` looks for) exists, the PR body keeps the template's headings in their order and maps the factory's pieces into them: `Closes #N` stays line 1, the "what changes" heading gets Summary and the acceptance criteria, a checklist heading keeps the template's items (ticked only when an Evidence line covers them) and gets the Evidence bullets as ticked items, a reviewer-notes heading gets Merge Danger, Rollback Triggers and the harden close block, and `## Factory` is appended last. Unmapped headings keep their template text. Without a template the layout is unchanged. In the first end-to-end run the stage ignored the repository's `Qué cambia` / `Checklist` / `Notas para el reviewer` template.

## 0.2.0 (2026-11-01)

### Changed
- **`factory-outcome.sh done` reads the sha from git, never from the stage.** The marker's `sha=` is `git -C "${FACTORY_WORKDIR:-$PWD}" rev-parse HEAD`; outside a git repository `done` dies (exit 2). `--sha` is now optional and only a cross-check: a value that is not HEAD (or an abbreviation of it) is refused with `refused: --sha differs from git HEAD` (exit 2, nothing posted). In the first end-to-end run the implement stage typed a hash with one wrong character and needed a second done comment to correct it. The contract (§3, §4) and the three stage commands say the call takes no `--sha`. `test_factory_scripts.sh`: 81 → 95 tests (no `--sha`, equal, abbreviated, differing, mistyped, not a repository, `FACTORY_WORKDIR`).

## 0.1.0 (2026-11-01)

### Added
- The five stage commands the factory daemon runs headless, one per tick: `/factory:spec`, `/factory:plan`, `/factory:implement`, `/factory:harden`, `/factory:ship`. Each reads everything from the issue and the branch, composes `feature-dev`, `code-review`, `ship` and `github-issues`, and ends with exactly one outcome on GitHub (`done`, `question`, `parked`) before it stops. None of them asks.
- `references/factory-contract.md`: the shared contract every command includes (identity, the issue-store body sections, the marker rule, outcomes and the lane table, the question protocol, the hard rules).
- `scripts/factory-issue.sh` (status, lane, last-marker, answer, next-status) and `scripts/factory-outcome.sh` (done, question, parked, progress, decision, flip): the only place a `<!-- factory:… -->` marker is typed. `scripts/test_factory_scripts.sh` tests both offline against a stubbed `gh`.
- `references/review-loop.md`, `references/step-loop.md` and `scripts/tree-hash.sh` are synced copies from `shared/`.
