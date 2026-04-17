# Changelog

## 1.8.0 (2026-04-17)

### Added
- `/feature-dev:spec` Phase 1 now detects multi-repo scope when the feature description spans concerns owned by different repos AND either `additionalDirectories` (`.claude/settings.local.json`) or a parent-directory `CLAUDE.md` catalog corroborates sibling-repo access. The inferred repo set is folded into the step's assumption list for a single user confirmation round-trip.
- Spec frontmatter gains an optional `repos:` block (name, path, role: `owns-contract` | `consumes-contract`) that declares which repositories are in scope — single-repo features omit it, no behavior change
- Spec body gains a **Cross-Repo Contracts** section (endpoint, request/response shape, error codes, breaking-change flag) for multi-repo features so the API contract is written down before tasks are broken out
- Tasks in multi-repo specs are tagged with `Repo:` and ordered so contract-owning repo tasks land before contract-consuming repo tasks
- `spec-driven-development` skill documents the multi-repo detection signals and per-repo spec structure

## 1.7.1 (2026-04-17)

### Changed
- `/feature-dev:spec` Phase 4 clarifies that `SPEC-*.md` is a local working artifact, not committed to the repo. Explicitly forbids git commands and defers next-step choice to the Stop hook.

## 1.7.0 (2026-04-17)

### Added
- `/feature-dev:spec` now emits required YAML frontmatter (`type`, `feature`, `slug`, `date`, `branch`, `status`) on `SPEC-*.md` files so downstream commands can auto-discover them
- `/feature-dev:explore-plan` auto-discovers `SPEC-*.md` files when called without arguments (same 0/1/2+ pattern as tdd)
  - Filters out specs with `status: implemented` so shipped features don't re-surface
  - Warns when the only candidate is `status: draft` (not yet approved) before proceeding
  - Generated `PLAN-*.md` now records the `source_spec:` path and `slug:` for traceability from SPEC → PLAN → implementation
- `/feature-dev:tdd` closes the loop: on successful completion, updates the linked SPEC's `status:` to `implemented` before deleting the PLAN
- `/feature-dev:tdd` drift detection: warns when the source spec was modified after the plan was generated, so stale plans don't silently drive implementation

## 1.6.0 (2026-04-17)

### Added
- `/feature-dev:tdd` auto-discovers `PLAN-*.md` files when called without arguments
  - 0 plans → stop and ask for a feature description
  - 1 plan → auto-select and use its `feature:` frontmatter as the spec
  - 2+ plans → prompt user to pick one via AskUserQuestion
  - Supports the common workflow `/feature-dev:explore-plan` → clear context → `/feature-dev:tdd` without having to re-type the feature name

## 1.5.0 (2026-04-16)

### Changed
- Rewrote skill/command descriptions to contain only triggering conditions and boundaries, removing workflow step summaries that caused the model to shortcut skill bodies
- Added rationalization defense table to `tdd-patterns` skill
- Added SUBAGENT-STOP tags to `explore-plan`, `tdd`, and `spec` commands to prevent premature termination

## 1.4.1 (2026-04-13)

### Changed
- Upgrade `backend-explorer`, `frontend-explorer`, and `test-explorer` agents from haiku to sonnet for better codebase exploration quality

## 1.4.0 (2026-04-04)

### Added
- `spec` command: Spec-driven development with gated workflow (Specify → Plan → Tasks → Implement), assumption surfacing, and success criteria reframing
- `spec-driven-development` skill: Structured specification methodology with six-area spec template, anti-rationalization table, and living document practices

## 1.3.1 (2026-03-13)

### Fixed
- Remove all compound shell operators (`||`, `|`) from shell embeddings in `explore-plan` and `tdd` commands to fix "Bash command permission check failed" errors

## 1.3.0 (2026-03-13)

### Changed
- `explore-plan` now runs all exploration inside a forked general-purpose agent
  - 4 explorer subagents run inside the fork, keeping main conversation context clean
  - Fork writes `PLAN-<slug>.md` to disk, then its context is discarded
  - Main context only reads the saved plan file for user review
  - Eliminates context exhaustion that prevented running `tdd` after exploration
- Removed Write/Edit/Bash tools from `explore-plan` frontmatter (only the forked agent needs them)

## 1.2.1 (2026-03-13)

### Fixed
- `explore-plan` now explicitly prohibits `run_in_background` for parallel agents — background task outputs were expiring before being read, causing silent data loss

## 1.2.0 (2026-03-13)

### Added
- `explore-plan` now saves the implementation plan to `PLAN-<feature-slug>.md` (Phase 3)
- `tdd` now checks for `PLAN-*.md` and skips redundant exploration when a plan exists
- Plan file includes frontmatter (`type`, `feature`, `date`, `branch`) for identification
- `explore-plan` adds `PLAN-*.md` to `.gitignore` if not already present

### Changed
- `explore-plan` stop hook now suggests starting a new conversation for TDD to maximize context
- `tdd` Phase 1 is now "Load Plan or Explore Codebase" — uses saved plan when available, only does minimal test-infrastructure exploration
- `tdd` deletes the plan file after successful completion (cleanup)

## 1.1.1 (2026-03-13)

### Fixed
- Simplified `git remote` shell embedding in `explore-plan` and `tdd` commands to avoid `bwrap` sandbox errors (removed piped `sed` commands)

## 1.1.0 (2026-03-11)

### Added
- `backend-explorer` agent: Dedicated agent for backend/API layer exploration (models, views, serializers, endpoints)
- `frontend-explorer` agent: Dedicated agent for frontend/UI layer exploration (components, hooks, routing, state)
- `test-explorer` agent: Dedicated agent for test suite exploration (frameworks, fixtures, patterns, coverage)
- `history-explorer` agent: Dedicated agent for git history and open PR exploration (conflicts, patterns)
- `tdd-patterns` skill: Institutional knowledge for TDD workflows (iteration limits, coverage gates, phase constraints)
- Stop hooks on `explore-plan` and `tdd` commands for next-step guidance

### Changed
- `explore-plan` command now spawns named agents instead of inline Explore subagents
- `tdd` command now references `tdd-patterns` skill for consistent TDD constraints

## 1.0.0 (2026-03-11)

### Added
- `tdd` command: Test-driven feature development with RED-GREEN-REFACTOR cycle and coverage gates
- `explore-plan` command: Parallel 4-agent codebase exploration with synthesized implementation plan
