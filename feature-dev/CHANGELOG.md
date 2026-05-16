# Changelog

## 1.14.0 (2026-05-16)

### Added
- **`config-explorer` agent** — locates environment/config surface for a feature: `.env*` files, settings modules, env-var reads, typed-settings loaders (pydantic-settings, viper, zod env schemas), feature-flag providers (LaunchDarkly, GrowthBook, Unleash), secrets handling (vault, SSM, KMS), and per-environment overrides. Read-only; same frontmatter contract as the existing explorers (`tools: Read, Grep, Glob`, `model: sonnet`, `maxTurns: 15`, `background: true`).
- **`schema-explorer` agent** — maps DB schema and migration state for a feature's domain: migration tool detection (Django / Alembic / Prisma / Knex / Flyway / sqlx / Diesel), domain-touching migrations, current schema definitions, indexes/constraints, naming conventions, pending migrations (detected without executing), and safety patterns (squashing, multi-tenancy, backfills, online-DDL). Read-only; complements `backend-explorer` on the highest-risk layer.
- **`api-contract-explorer` agent** — maps declared API contracts (OpenAPI, GraphQL SDL, tRPC routers, protobuf, JSON Schema) as a layer distinct from endpoint *code*. Reports operations in the domain, shared DTOs / generated clients, versioning strategy, contract testing (Pact, Dredd, Schemathesis), codegen pipelines, and consumer repos. Critical for multi-repo features that `/feature-dev:spec` already supports via `repos:` frontmatter.
- **`observability-explorer` agent** — maps logging stack, metrics, tracing SDK, error reporting, alerting config, dashboards, and the codebase's conventions for adding new signals. Helps new feature code match existing logging/metric/trace naming so post-ship visibility doesn't degrade.

### Notes
- All four agents are **opt-in primitives** — not auto-spawned by `/feature-dev:explore-plan`. They are invokable directly from any skill (in this plugin or elsewhere) via `subagent_type: "feature-dev:<name>"`, matching how the existing explorers are reused outside `explore-plan`.
- README's agent section gains an "Opt-in explorers" subsection documenting the new agents.
- No changes to `/feature-dev:explore-plan` — the default 4-agent fan-out stays universal. Wiring an opt-in flag (e.g., `--with=config,schema`) is deferred.

## 1.13.0 (2026-05-13)

### Added
- **`plan-step-executor` agent** — focused implementation specialist that executes ONE step of an approved plan in isolation. Restricted tools (`Read, Edit, Write, Grep, Glob, Bash, NotebookEdit`), explicit Spawner contract (step description, file paths, verification, carry-over), and a fixed return format (Files changed / Verification / Deviations / Carry-over / Blockers).
- **`feature-implementer` agent** — orchestrator that drives an approved `PLAN-*.md` end-to-end by dispatching each step to `plan-step-executor`, threading carry-over deltas forward, and halting cleanly on blockers. Tools: `Read, Bash, Agent`. Links the `spec-driven-development` skill.
- **`tdd-runner` agent** — strict red-green-refactor enforcer for one bounded behavior. Caps at 5 cycles, validates the RED failure mode is legitimate before allowing GREEN, gates promotion on coverage. Stack-agnostic (pytest / vitest / jest from path). Links the `tdd-patterns` skill.

### Changed
- **`/feature-dev:spec` Phase 2**: clarified that the Plan section gets appended to the SPEC file (high-level outline only) and explicitly defers the file-level, codebase-aware plan to `PLAN-<slug>.md` produced by `/feature-dev:explore-plan`. Previously the phase described an activity but did not name its deliverable, leaving the model unsure whether to write to the spec, verbalize, or generate a separate PLAN.
- **Model selection on new agents**: `feature-implementer`, `plan-step-executor`, and `tdd-runner` set `model: sonnet` (was `inherit`) to align with the 20+ sonnet agents across the marketplace and keep cost/latency predictable when the agents run in loops (TDD cycles, multi-step plans).
- **`history-explorer` agent**: promoted from `haiku` to `sonnet`. As an exploration agent spawned by `/feature-dev:explore-plan` for parallel codebase analysis, it must produce findings the synthesizer can integrate into a PLAN. The user's global CLAUDE.md states: *"Explore agents use sonnet — Haiku lacks the analysis depth needed for accurate pattern recognition and synthesis across a codebase."* Now matches `backend-explorer`, `frontend-explorer`, `test-explorer`.
- **`/feature-dev:spec` and `/feature-dev:explore-plan` now run on Opus** (`model: opus` in frontmatter). Both are reasoning-heavy phases — spec formalization with multi-repo detection and gated user reviews, exploration synthesis across four parallel agents into a coherent plan. Pre-setting the model on the command guarantees quality regardless of the caller's default. Implementation-side workhorses (`/feature-dev:tdd`, `feature-implementer`, `plan-step-executor`, `tdd-runner`) intentionally stay on sonnet — they're bounded by tests and acceptance criteria, not by reasoning depth.
- **`maxTurns` on the three new agents**: `plan-step-executor` (20), `tdd-runner` (25), `feature-implementer` (30). Aligns with the existing pattern (explorers, refactor agents, comment-verifier, fix-implementer all set `maxTurns`) and guards against runaway loops on degenerate plans / TDD cycles.
- **`feature-implementer` commit discipline section**: documented explicit rules for `commit_per_step` — never `--no-verify`, halt on pre-commit hook failure (no amend, no retry), commit subject = step acceptance criteria, new commit per step (no `--amend`). Inherits the repo's CLAUDE.md commit safety protocol.
- **`feature-implementer` parallelization clarification**: the "Do not parallelize steps" hard rule now explicitly states that the "Parallelization Hints" section of a PLAN is informational for human readers, not an instruction to dispatch parallel executors.
- **README workflow**: added an "Alternative implementation path (agent-driven)" subsection documenting `feature-implementer` / `plan-step-executor` / `tdd-runner` as an alternative to the interactive `/feature-dev:tdd` command path.
- **Example languages**: normalized examples in `feature-implementer.md` and `tdd-runner.md` to English to match the rest of the marketplace.

### Why
The three compose naturally with the existing `feature-dev` surface: `/feature-dev:spec` and `/feature-dev:explore-plan` produce the artifacts `feature-implementer` consumes; `/feature-dev:tdd` and the `tdd-patterns` skill define the discipline `tdd-runner` enforces; `plan-step-executor` is the atomic unit both higher-level agents (and the main agent) can dispatch to without polluting the orchestrator's context budget. Co-locating them with `backend-explorer`, `frontend-explorer`, `spec-plan-validator` keeps the feature-dev workflow self-contained instead of scattered across user-scope `~/.claude/agents/`.

## 1.12.2 (2026-05-12)

### Changed
- Removed unsupported `permissionMode: default` frontmatter field from `spec-plan-validator` agent. Plugin agents do not support `permissionMode`, `hooks`, or `mcpServers` — they are silently ignored by the harness.

## 1.12.1 (2026-05-07)

### Changed
- `/feature-dev:spec` now recommends running in plan mode (`Shift+Tab` to toggle) so the spec is reviewed before files land on disk.

### Why
Aligns with Anthropic's Claude Code "explore → plan → implement" workflow: planning surfaces should default to plan mode, not write mode.

## 1.12.0 (2026-05-06)

### Added
- **Consequences** three-way split in `spec-driven-development` Phase 2 (Plan), required when the plan makes an architectural choice (new pattern, framework, data store, integration, or significant refactor): *what becomes easier* / *what becomes harder* / *what we'll need to revisit later*. Includes a worked example (event sourcing for billing reconciliation).

### Why
Borrowed from Anthropic's `engineering:architecture` ADR template. Most spec/ADR templates stop at pros/cons; the third clause (`revisit when`) is the operational gold — it forces the plan to name the conditions that would invalidate the choice, rather than letting the decision drift into "permanent" by default. Surfaces scale thresholds, integration points, and cross-domain coupling that pros/cons hide.

## 1.11.0 (2026-05-06)

### Changed
- `spec-driven-development` Phase 4 now explicitly delegates to the **`feature-dev:tdd-patterns`** skill rather than describing TDD inline. Avoids duplicating the cycle rules (5-cycle limit, stuck-after-3, coverage gate) in two places — `tdd-patterns` becomes the single canonical reference. Pattern borrowed from Anthropic's `engineering` plugin where `architecture` delegates depth to `system-design`.

## 1.10.0 (2026-05-06)

### Added
- **Decision Rules** section in `spec-driven-development` skill — operational tests applied in real time when writing a spec or pushing back on stakeholders. Includes the P0 cut-test ("if removed, does the feature still solve the core problem?"), the "if everything is P0, nothing is P0" rule, the scope-trade-only rule (any addition requires a removal or timeline extension), time-boxed investigations, and the genuinely-open-questions rule (open questions must be unanswerable from context, owner-tagged, and marked blocking vs non-blocking).
- **Common Spec Mistakes** section in `spec-driven-development` skill — anti-pattern catalog covering bad-spec failure modes (vague criteria, solution-prescriptive stories, internal-focus stories, everything-is-P0, padded open questions, perfunctory boundaries, post-hoc specs). Complements the existing Anti-Rationalizations table, which catches *skipping* the spec; this catches *writing it badly*.

### Changed
- Phase 1's "Reframe vague requirements" step now bans nine specific vague words from acceptance criteria (`fast`, `slow`, `easy`, `simple`, `user-friendly`, `intuitive`, `seamless`, `better`, `improved`) unless immediately defined concretely. Added a second worked example showing the reframe for "intuitive."
- Verification checklist expanded with three new gates: no banned vague words without concrete definitions, P0 list passes the cut-test (≤5 items each truly required), and open questions are genuinely open, owner-tagged, and blocking-vs-non-blocking marked. Boundaries verification now requires one-line rationale per Never-do item.

### Why
Borrowed from a comparable Anthropic spec-writing skill we studied. Our previous skill defined what a good spec contains; the new content adds operational decision rules and an anti-pattern catalog so the model can self-correct mid-conversation rather than only catch issues in review.

## 1.9.2 (2026-05-06)

### Changed
- Trimmed `cleanup`, `plan-review`, `spec-review` command descriptions and `spec-driven-development` skill description to fit Claude Code's skill-listing budget. Workflow detail remains in command/skill bodies.

## 1.9.1 (2026-05-01)

### Fixed
- `/feature-dev:spec` no longer fails with `Shell command failed` when `.claude/settings.local.json` is absent. The Context block's `jq` call previously exited non-zero on a missing file (stderr was silenced but the exit code was not), tripping the harness. Appended `|| true` so a missing settings file just produces an empty `Additional directories` value, which is the intended single-repo signal.

## 1.9.0 (2026-04-22)

### Added
- `/feature-dev:spec-review` — opt-in validator that reads a `SPEC-*.md` and emits a Blocking / Should Address / Nice to Have gap checklist. Modeled on `prd-toolkit`'s validate pattern but checks SPEC-specific structure: acceptance criteria observability, multi-repo `Cross-Repo Contracts` presence, `Repo:` task tagging, frontmatter validity. Auto-discovers `SPEC-*.md` in repo root when called without arguments.
- `/feature-dev:plan-review` — opt-in validator for `PLAN-*.md`. Checks `source_spec:` linkage (and that the linked SPEC file still exists), Files-to-Modify table presence, Implementation Order rationale, Risks, Estimated Test Cases. Auto-discovers `PLAN-*.md` in repo root when called without arguments.
- `spec-plan-validator` subagent — shared backend for both new commands. Routes by `artifact_type` (`spec` or `plan`). Categorical findings only — no numerical scoring (scoring invites rubber-stamping). Findings are advisory and never written back into the artifact.
- `### Parallelization Hints` section in the plan template emitted by `/feature-dev:explore-plan`. Informational only — flags independent steps from the Implementation Order so a human or future executor can decide where parallel work is safe. Does NOT contain executable subagent prompts (TDD requires sequential discipline, and concurrent edits to overlapping files would collide).
- `/feature-dev:cleanup` — opt-in bulk deletion of SPEC/PLAN artifacts that are no longer in active use. Categorizes files by safety (implemented specs and orphan plans → safe; in-flight specs/plans → never offered; ambiguous standalone plans → surfaced but not auto-included), then requires a single explicit Y/N confirmation before deletion. `disable-model-invocation: true` so it can never auto-trigger; allowed-tools scoped to `Bash(rm SPEC-*.md)` and `Bash(rm PLAN-*.md)` only. Solves long-term clutter without forcing a delete prompt at every TDD completion.

### Changed
- `/feature-dev:spec` Stop hook now lists `/feature-dev:spec-review` as an optional next step.
- `/feature-dev:spec` Phase 4 handoff text updated to include `spec-review` in the next-step parenthetical.
- `/feature-dev:spec` now adds `SPEC-*.md` to the project's `.gitignore` (new Phase 1 step 6, mirroring the existing `/feature-dev:explore-plan` behavior for `PLAN-*.md`). Closes the `git add .` loophole that previously let SPEC files be committed accidentally despite the documented "local artifact" convention.
- `/feature-dev:explore-plan` Stop hook now lists `/feature-dev:plan-review` as an optional next step.
- `/feature-dev:spec-review` and `/feature-dev:plan-review` rules now explicitly state that SPEC/PLAN files are local working artifacts and must not be committed.

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
