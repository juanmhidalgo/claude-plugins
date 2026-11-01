# Changelog

## 0.2.0 (2026-11-01)

### Changed
- **`factory-outcome.sh done` reads the sha from git, never from the stage.** The marker's `sha=` is `git -C "${FACTORY_WORKDIR:-$PWD}" rev-parse HEAD`; outside a git repository `done` dies (exit 2). `--sha` is now optional and only a cross-check: a value that is not HEAD (or an abbreviation of it) is refused with `refused: --sha differs from git HEAD` (exit 2, nothing posted). In the first end-to-end run the implement stage typed a hash with one wrong character and needed a second done comment to correct it. The contract (§3, §4) and the three stage commands say the call takes no `--sha`. `test_factory_scripts.sh`: 81 → 95 tests (no `--sha`, equal, abbreviated, differing, mistyped, not a repository, `FACTORY_WORKDIR`).

## 0.1.0 (2026-11-01)

### Added
- The five stage commands the factory daemon runs headless, one per tick: `/factory:spec`, `/factory:plan`, `/factory:implement`, `/factory:harden`, `/factory:ship`. Each reads everything from the issue and the branch, composes `feature-dev`, `code-review`, `ship` and `github-issues`, and ends with exactly one outcome on GitHub (`done`, `question`, `parked`) before it stops. None of them asks.
- `references/factory-contract.md`: the shared contract every command includes (identity, the issue-store body sections, the marker rule, outcomes and the lane table, the question protocol, the hard rules).
- `scripts/factory-issue.sh` (status, lane, last-marker, answer, next-status) and `scripts/factory-outcome.sh` (done, question, parked, progress, decision, flip): the only place a `<!-- factory:… -->` marker is typed. `scripts/test_factory_scripts.sh` tests both offline against a stubbed `gh`.
- `references/review-loop.md`, `references/step-loop.md` and `scripts/tree-hash.sh` are synced copies from `shared/`.
