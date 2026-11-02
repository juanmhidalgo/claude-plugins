---
disable-model-invocation: true
argument-hint: "#N"
description: |
  Use when the factory daemon, or a person testing a stage headless with `claude -p`,
  runs the spec stage for issue #N (`status:needs-spec`): it writes the spec section
  into the issue body and ends with a done, question or parked outcome on GitHub.
  Do NOT use interactively to write a spec (use /feature-dev:spec), and never invoke
  it from a conversation: it asks nothing and writes to the issue.
keywords:
  - factory
  - headless
  - spec
  - issue-store
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
  - Bash(git *)
  - Bash(gh auth status)
  - Bash(gh repo view *)
  - Bash(gh issue view *)
  - Bash(gh issue edit * --body-file *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/factory-issue.sh *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/factory-outcome.sh *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/../feature-dev/scripts/features.py *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/../feature-dev/scripts/issue_spec.py *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/../feature-dev/scripts/review_server.py snapshot *)
---

@factory/references/factory-contract.md

# `/factory:spec` — `status:needs-spec` → the spec section in the body

Stage `spec`. Caps are the daemon's (defaults 80 turns · 6 USD · 30 min; the real numbers for this run, per-repo overrides included, are the `Caps for this run` line under Context: size long steps against those, never against the defaults). No branch:
the clone stays on whatever it has checked out, and nothing is committed.

## Context

- **Arguments**: $ARGUMENTS
- **Stage variable set**: !`echo "${#FACTORY_STAGE}"`
- **Caps for this run**: !`echo "turns=${FACTORY_MAX_TURNS:-default} budget_usd=${FACTORY_BUDGET_USD:-default} timeout_min=${FACTORY_TIMEOUT_MINUTES:-default}"`
- **Issue variable set**: !`echo "${#FACTORY_ISSUE}"`
- **HEAD**: !`git rev-parse --short HEAD 2>/dev/null || echo "no git"`

## Inputs

Run the contract's stage preamble (§4). The status must be `status:needs-spec`.
Then read: the issue title, body (the repository's own sections — `## Contexto`
or `## Context`, `## Out of scope`, `## Dependencias` / `## Dependencies`, a
`<!-- source: -->` line), labels (`type:*`, `area:*`), comments, and `docs/`
plus the code at the clone's HEAD. An open `Blocked by #M` in the body whose
issue `M` carries `type:product-decision` (read it with `gh issue view M
--json labels,state`) is a question (below), before any authoring.

## Composition

1. **Verify first, for `type:bug`, `type:tech-debt` and `type:test`.** Spawn
   `github-issues:issue-verifier` (no `name`) with:

   ```
   ISSUE: <owner/repo>#<N>
   REPO_PATH: <repo root>
   RULES: ${CLAUDE_PLUGIN_ROOT}/../github-issues/skills/work/references/verification.md, ${CLAUDE_PLUGIN_ROOT}/../github-issues/skills/work/references/work-types.md
   PARTS: all
   ```

   Audit its ledger as `verification.md` says: a row claiming it *ran*
   something is downgraded to UNVERIFIED (the agent cannot run anything); an
   empty report is retried once, then the issue counts as unverified and the
   report says so. The ledger's corrections feed the spec (a DRIFTED location
   is written at its new place). Skip this step for `type:feature` and
   `type:docs`.

2. **Author the spec as `/feature-dev:spec` Phase 1 does**, with
   `${CLAUDE_PLUGIN_ROOT}/../feature-dev/skills/spec-driven-development/SKILL.md`
   as the template (read it, and `commands/spec.md` next to it for Phase 1's
   steps). Its gates take these defaults:

   | `/feature-dev:spec` gate | Headless default |
   |---|---|
   | Multi-repo detection (step 1) | Run it on the Context section and the `area:*` labels only. Two or more repos → **question** (options: this repository only, recommended / the repositories named / re-scope). The spec never carries a `repos:` block: a multi-repo feature is a v1 non-goal |
   | Scope question (step 2) | Scope = the issue's Context plus its `area:*` labels; `## Non-Goals` = the issue's Out of scope section, one line each, or `None stated in the issue` |
   | Assumptions (step 3) | Each assumption is decided with its recommended option and written to a `## Assumptions` section of the spec, one entry per assumption: `- **A-<n>** <the assumption>` with `Decided:`, `Alternative:` and `Basis:` lines (the issue text, a `docs/` file or a code path that supports it). An assumption that changes a data model, a public contract or user-visible behaviour **and** has no basis in the issue, `docs/` or the code → **question** |
   | Reframe vagueness (step 4) | Done silently; the reframed criteria become the ACs |
   | Save (step 6) | `features.py new <slug> --kind spec` with the slug from the contract (§1); if the feature already exists in the cache, snapshot it with `review_server.py snapshot` and rewrite the SPEC in place |
   | `.gitignore` (step 7) | Replaced by `.git/info/exclude` (contract §2) |
   | Review brief and approval (step 8) | Replaced by `spec-plan-validator` (next item) |
   | Publish question (Phase 4) | Always Publish to `#N` (issue-store.md's Publish, target `#N`, after `features.py approve <slug>`). On a first publish there is no recorded fingerprint. On a re-run, a mismatch between the issue's section and the recorded fingerprint means a human edited the section → `parked reason=section-edited` |

   Every other Phase 1 instruction (nine areas, AC ids, the QA checklist, the
   frontmatter block) applies as written. The spec is single-repo, so the
   multi-repo sections are out.

3. **Validate.** Spawn `feature-dev:spec-plan-validator` (no `name`) with
   `artifact_type: spec`, `artifact_path: <SPEC path>`. Read its findings the
   way `/feature-dev:spec-review` Phase 2 does (read
   `${CLAUDE_PLUGIN_ROOT}/../feature-dev/commands/spec-review.md` for the
   definition): a finding is **applicable** when the fix is mechanical and
   needs no decision (a missing section, a DRIFTED path, an AC with no
   error-state twin) — apply those in place, once, and re-run the validator
   once. A Blocking finding that **needs a decision** → **question**. Should
   Address and Nice to Have go in the report. The validator's Code claims
   table goes in the report verbatim.

   When step 1's ledger, or the validator, concludes the issue is **already
   fixed** or its **premise is wrong** → **question** quoting the ledger row,
   options: close the issue / re-scope to what still holds / proceed anyway
   (none recommended over the others unless the ledger is unambiguous, in
   which case `close the issue` is recommended for ALREADY FIXED and
   `re-scope` for a REFUTED premise).

4. **Adversarial review.** After step 3's validator pass (the structural
   fixes are already in the spec) and before Publish. Spawn
   `discuss:doc-adversary` (no `name`, never backgrounded; read
   `${CLAUDE_PLUGIN_ROOT}/../discuss/skills/adversarial-doc-review/SKILL.md`
   §Dispatch once). The prompt is paths, never content — no summary, no
   excerpt, no mention of who wrote the document:

   ```
   DOC_PATH: <SPEC path>
   MODE: design
   SOURCES: <repo root>
   OUTPUT_PATH: <session scratchpad, or /tmp when none is listed>/doc-adversary-<slug>-spec-r<n>.md
   ```

   Read `OUTPUT_PATH` first; use whatever came back inline only when the file
   is missing or empty. Before trusting a finding, spot-check one of its
   `Evidence` references (`path:line` or grep) against the clone.

   | Adversary report item | Headless rule |
   |---|---|
   | No report (file empty and nothing inline), or no findings **and** no Falsification attempts | the review did not happen: re-run once with a new `OUTPUT_PATH`; still nothing → `parked reason=adversary-unreviewed` |
   | A finding whose spot-checked `Evidence` does not hold | not a gate: kept in the report under Unverified with the check that failed |
   | A **HIGH** finding | **question**: the finding's title, `Decision at risk` and `What would be decided wrong`, verbatim; options: the reading the finding implies (recommended) / the document's reading / re-scope |
   | A **MEDIUM** finding | one fix pass: the reading the finding implies is written into the spec as an `A-<n>` entry under `## Assumptions` whose `Basis:` cites the finding's Evidence — unless it changes a data model, a public contract or user-visible behaviour **and** has no basis in the issue, `docs/` or the code, which is a **question** as the HIGH row. After the fix pass the adversary runs **once more** (the skill's after-fixes rule) with a new `OUTPUT_PATH`; a MEDIUM that survives the re-run → **question** as the HIGH row |
   | Verdict `do not implement as written` with no HIGH finding | **question** anyway; options: re-scope (recommended) / proceed as written / close the issue |
   | An item under `Needs to be resolved` not covered by a finding's question | **question**, options taken from the item |
   | Verdict `no material findings` with Falsification attempts present | proceed; the report carries the verdict and the attempt count |

   Questions from this step count toward the four of the contract (§5); more
   than four in the run → `parked reason=too-many-questions`.

   The step runs under every lane. Under `spec-gate` / `plan-gate` the owner
   sees the adversary's block in the done comment before flipping.

## Outputs

- The spec section in the issue body (Publish, slug from the contract).
- The `done` comment: `/feature-dev:spec`'s **Review brief** block (Decided,
  Assumed, Unverified claims about the code, Out of scope), the validator's
  Code claims table, the **Adversarial review** block of step 4 right after
  it, the verifier's verdict line when step 1 ran, and the contract's §7
  lines. The block:

  ```
  Adversarial review: <verdict line verbatim> — re-run: yes|no
  Material findings: <n> (<m> HIGH)
  - [HIGH|MEDIUM] <title> — decided A-<n> | asked | unverified: <failed check>
  Falsification attempts: <k>
  ```
- The flip of the contract's lane table (`needs-plan` under `factory:auto`,
  `spec-review` under either gate).

## Cannot decide → question

Multi-repo scope; an unbased contract-shaping assumption; a validator finding
that needs a decision; a verifier verdict of needs-decision or premise wrong;
an open `Blocked by #M` that is a `type:product-decision`; a HIGH adversary
finding; a MEDIUM finding that survives the re-run; a `do not implement as
written` verdict; a `Needs to be resolved` item. Each is one
numbered question with 2–4 options (contract §5); more than four → `parked
reason=too-many-questions`. The spec is **not published** when the stage ends
in a question (AC-8): the local cache keeps the draft for the re-run.

## Resume

A re-run after an answer (contract §4 preamble, step 4) authors the spec with
the answer applied and quotes it under `Answer understood:`. A re-run whose
body already holds a valid spec section for this slug and whose latest marker
is this stage's `done` runs only the flip. A re-run with no answer and no done
marker (a crash mid-authoring) starts over: nothing was written to the issue.

A re-run after an answer applies the answer, then runs the adversary **once**
(no fix pass). A finding that names a decision the answer already settled is
listed as `decided by owner` and never re-asked; a new HIGH finding is a
question like any other.
