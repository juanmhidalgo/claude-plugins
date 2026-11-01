# Changelog

## 0.1.0 (2026-11-01)

### Added
- The five stage commands the factory daemon runs headless, one per tick: `/factory:spec`, `/factory:plan`, `/factory:implement`, `/factory:harden`, `/factory:ship`. Each reads everything from the issue and the branch, composes `feature-dev`, `code-review`, `ship` and `github-issues`, and ends with exactly one outcome on GitHub (`done`, `question`, `parked`) before it stops. None of them asks.
- `references/factory-contract.md`: the shared contract every command includes (identity, the issue-store body sections, the marker rule, outcomes and the lane table, the question protocol, the hard rules).
- `scripts/factory-issue.sh` (status, lane, last-marker, answer, next-status) and `scripts/factory-outcome.sh` (done, question, parked, progress, decision, flip): the only place a `<!-- factory:… -->` marker is typed. `scripts/test_factory_scripts.sh` tests both offline against a stubbed `gh`.
- `references/review-loop.md`, `references/step-loop.md` and `scripts/tree-hash.sh` are synced copies from `shared/`.
