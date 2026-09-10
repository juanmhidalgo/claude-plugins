# Changelog

## 1.18.0 (2026-09-10)

### Changed
- **`/feature-dev:explore-plan` now selects its explorers instead of hardcoding four.** v1.14.0 added `config-explorer`, `schema-explorer`, `api-contract-explorer` and `observability-explorer`, documented as "opt-in primitives — invoke directly from any skill". Nothing invoked them: no command and no skill in the plugin referenced any of the four, and `explore-plan` dispatched exactly `backend` / `frontend` / `test` / `history`, always the same four regardless of the feature. The practical cost was not dead code but blind planning — a feature with a migration got planned without anyone reading the migration state, and a multi-repo feature got planned without anyone reading the API contracts, with the right agent sitting unused next door.
  - **New Phase 0 step 4** picks the additional explorers from signals in the feature description and, when `source_spec` is set, the spec **body** (frontmatter alone is too thin a signal). Selection table: persistence → `schema-explorer`; settings / environment variables / credentials / feature flags → `config-explorer`; 2+ `repos:` entries or a declared-contract change → `api-contract-explorer`; silent-failure surfaces (background jobs, queue consumers, scheduled tasks, webhook handlers, auth and payment paths) → `observability-explorer`. Ties break toward including the explorer — they are read-only, parallel, and capped at `maxTurns: 15`.
  - The selection is stated to the user in one line before the fork, and passed into the Phase 1 agent prompt. All selected explorers launch in the **same** response as the base four, so the added ones cost wall-clock only, not extra rounds.
  - **Plan template** gained matching optional subsections under Exploration Findings (Schema & Migrations, Configuration, API Contracts, Observability), emitted only for explorers that actually ran — no "N/A" placeholder headings.
  - Template placeholders now name the explorers (`[Key findings from backend-explorer]`) instead of positions (`[Key findings from Agent 1]`), which stopped being stable once the batch size varies.

## 1.17.0 (2026-09-10)

### Changed
- **`PLAN-*.md` steps now carry a dispatchable contract.** `/feature-dev:explore-plan` emitted its Implementation Order as free prose (`1. [Step 1 — with rationale]`) — one sentence per step, no acceptance criterion, no file paths, no verification command. Every consumer requires those: `plan-step-executor` demands *"exact commands that prove the step works"*, and `feature-implementer` has it as a hard rule — *"A step's verification command is missing from the plan → halt. Verification is non-negotiable."* The plugin's own generator was producing plans its own implementer agent was contractually required to reject on step 1, which is why the agent path was effectively unreachable. Each step now emits `Accept` / `Impl` / `Test` / `Verify` / `Depends on` / `Rationale`, mirroring the `Task / Accept / Verify / Files` convention the SPEC template has used since v1.0.
  - Five non-negotiable generation rules added to the plan-writing agent's prompt: `Verify` must be a real runnable command derived from test-explorer findings (never "run the tests"), `Accept` must be a single criterion (an "and" means split the step), `Impl`/`Test` must be paths that also appear in the Files tables, non-behavioral steps still need `Verify` with `Test: n/a — <reason>`, and ordering follows dependency rather than layer.
- **`spec-plan-validator` now enforces the step contract.** The plan checklist replaced one prose-quality row ("with rationale or dependency note") with six structural rows — `Accept`, `Verify`, `Impl`/`Test` as Blocking; path cross-reference, `Depends on`/`Rationale`, and compound-criterion detection as Should Address. Previously `/feature-dev:plan-review` returned "ready for `/feature-dev:tdd`" on plans that no agent could execute.
- **`/feature-dev:tdd` Phase 2 reads the contract instead of inferring it.** With a plan in use it takes the six fields verbatim and halts if a step lacks `Accept`/`Verify` or if `Verify` is a description rather than a command, pointing the user at `/feature-dev:plan-review`. Inference is now confined to the no-plan path (`$ARGUMENTS` only). Re-deriving fields from a reviewed plan silently discards that review.

### Added
- **`/feature-dev:tdd` routes non-behavioral steps to `plan-step-executor`.** A step whose `Test:` is `n/a` (migration, config wiring, dependency bump) has nothing to assert test-first, but still has a `Verify` gate. Previously the command had no path for these at all — it dispatched `tdd-runner` for everything or nothing. This also makes `plan-step-executor` reachable from a command for the first time.

## 1.16.0 (2026-09-10)

### Changed
- **`/feature-dev:tdd` now delegates implementation to the `tdd-runner` agent instead of doing it in the main context.** The command shipped three implementation agents (`tdd-runner`, `plan-step-executor`, `feature-implementer`) that no command ever dispatched — they were reachable only by the user naming them directly. Phases 2–6 were written as imperatives to whoever ran the command, so every run implemented the whole feature inline, burning the main context on test bodies and impl diffs. The Agent tool was already in `allowed-tools` and used in Phase 1 for `Explore`; only the implementation half was missing.
  - **New Phase 2 — Decompose into Acceptance Criteria**: the main agent breaks the feature into ordered, independently verifiable criteria and resolves the six fields `tdd-runner`'s spawner contract requires (behavior, spec reference, test target, impl target, verification command, cycle cap) *before* dispatching. A runner halts on a missing contract field, so resolving up front converts a mid-loop halt into an early stop.
  - **New Phase 3 — Execute TDD Cycles**: one `tdd-runner` per criterion, dispatched sequentially with accumulated carry-over deltas threaded forward. Explicit halt-reason routing table (`criteria met` / `RED passed early` / `cycle cap` / `GREEN unreachable` / `scope mismatch` / `blocker`) so the orchestrator's decision is not left to judgment.
  - **Stricter RED**: the old Phase 2 wrote the full test suite up front and expected all of it to fail — big-bang RED. Each `tdd-runner` now does incremental RED per behavior *and* validates the failure mode (test fails because the behavior is missing, not because of an import error or a missing fixture). That check — which `tdd-runner.md` calls "the most common way TDD agents fail" — had no equivalent in the command.
  - **Phase 5 (Refactor) removed as a standalone phase**: `tdd-runner` runs REFACTOR inside every cycle, gated on green. A separate end-of-run refactor pass would have been a second, unsynchronized one.
  - **Coverage (now Phase 4) is aggregate-only**: per-line coverage is gated inside each runner; the command checks the union of changed files and dispatches an extra runner per meaningful gap rather than writing catch-up tests inline.
  - **Report (now Phase 6)** gains a per-criterion table (cycles run, outcome) and a Blockers section. Spec `status:` flipping and `PLAN-*.md` deletion now happen **only** when every criterion was met — a halted run leaves both intact so it can be resumed.
- **README**: the "Alternative implementation path (agent-driven)" section no longer lists `tdd-runner` as an alternative to the command — it is now the command's execution engine. `feature-implementer` / `plan-step-executor` remain the non-TDD agent path.

- **`tdd-patterns` skill**: the iteration limit now reads "5 cycles per bounded behavior (one acceptance criterion), not per feature". The skill is loaded by both the orchestrator and every `tdd-runner`; under the old wording a feature with N criteria would have read as sharing a single 5-cycle budget.

### Notes
- Sequential dispatch is deliberate and unchanged in spirit from `explore-plan.md`'s note that "TDD requires sequential discipline": criteria depend on symbols earlier criteria introduce, and concurrent runners collide on overlapping files. The delegation is for context hygiene and RED discipline, not for parallelism.
- No change to `tdd-runner.md` itself — its contract was already correct and complete; the command was simply never calling it.


## 1.15.0 (2026-07-02)

### Changed
- **`/feature-dev:spec` now writes eight spec areas instead of six** — added a dedicated `## Acceptance Criteria` section and a `## QA Checklist` section. Previously the command folded "what success looks like" into `## Objective` and left QA-facing checks implicit inside `## Testing Strategy`, so **every** `/feature-dev:spec-review` run reported the same two findings: a Blocking "no dedicated Acceptance Criteria section" and a Should-Address "no QA Checklist". The generator now emits exactly the sections the `spec-plan-validator` agent checks for, closing the recurring feedback loop.
  - **Acceptance Criteria**: dedicated, scannable, user-observable criteria — must include at least one failure/error-state criterion, not only happy-path outcomes (matches the validator's Blocking + Should-Address checks).
  - **QA Checklist**: QA-facing list grouped as happy path / edge cases / error states, distinct from the engineering-oriented Testing Strategy.
- **`spec-driven-development` skill** updated in lockstep: the Phase 1 area list (six → eight) and the Verification checklist now name the Acceptance Criteria and QA Checklist requirements, keeping the imported best-practices source of truth aligned with the command.

### Notes
- No change to `spec-plan-validator` / `/feature-dev:spec-review` — the validator's bar was already correct; the generator was under-producing. Alignment was done by raising the generator, not lowering the checker.

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
