---
disable-model-invocation: true
argument-hint: "#N"
description: |
  Use when the factory daemon, or a person testing a stage headless with `claude -p`,
  runs the plan stage for issue #N (`status:needs-plan`): it imports the spec section,
  explores and plans the way /feature-dev:explore-plan does, writes the plan section
  into the issue body and ends with a done, question or parked outcome on GitHub.
  Do NOT use interactively (use /feature-dev:explore-plan), and never invoke it from
  a conversation: it asks nothing and writes to the issue.
keywords:
  - factory
  - headless
  - plan
  - issue-store
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
  - Workflow
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

# `/factory:plan` — `status:needs-plan` → the plan section in the body

Stage `plan`. Caps are the daemon's (100 turns · 9 USD · 40 min). No branch
exists yet: the plan's Baseline must run on the base, so the clone is put on
`origin/<default>` first.

## Context

- **Arguments**: $ARGUMENTS
- **Stage variable set**: !`echo "${#FACTORY_STAGE}"`
- **Working tree**: !`git status --short | head -20`

## Inputs

Run the contract's stage preamble (§4). The status must be `status:needs-plan`.
Then:

1. `git fetch origin`. The tree must be clean (`git status --short` empty
   apart from `.feature-dev/`, which is excluded): a dirty tree here is not
   this stage's work → `parked reason=dirty-tree` with `git status --short`.
   Check out the default branch's commit **detached** (`git checkout --detach
   origin/<default>`): the plan is generated against the base, and rule 1
   forbids a local default branch that could be committed to.
2. Import (issue-store.md, contract §2) → `.feature-dev/features/<slug>/SPEC-<slug>.md`.
   No spec section on the issue → `parked reason=no-spec-section` (the `spec`
   stage did not run, or someone removed it).
3. `features.py approve <slug>`: the draft gate. Approval is the lane's job
   (a `spec-gate` or `plan-gate` issue only reaches `needs-plan` through the
   owner's flip), so the stage approves without reading the spec again. A
   refusal because the feature is already past `approved` is fine.
4. Labels and comments, for the explorer mapping and the answer.

## Composition

`/feature-dev:explore-plan` is `disable-model-invocation`, so this stage runs
its phases itself. Read `${CLAUDE_PLUGIN_ROOT}/../feature-dev/commands/explore-plan.md`
once and follow it with these substitutions:

1. **Plan path**: `features.py new <slug> --kind plan --spec <slug>` prints it;
   when a plan already exists in the cache (a re-run), it is rewritten in place.
2. **Explorer selection** as explore-plan Phase 0 step 4, plus the repository's
   own mapping when its `CLAUDE.md` or the `area:*` labels give one (for
   example `area:db` → `schema-explorer`, `area:platform` → `config-explorer`;
   `frontend-explorer` is dropped unless `area:ui` is present or the spec
   names a view, component or page). State the selection in the report.
3. **The workflow**: `Workflow({ name: "feature-dev:plan-fanout", … })` exactly
   as explore-plan Phase 1, with `plugin_root` and `rules` pointing at
   `${CLAUDE_PLUGIN_ROOT}/../feature-dev` (its `references/plan-generation.md`).
   `Workflow` unavailable or denied → explore-plan's Phase 2 Agent fallback,
   and the report says the workflow path was not used. `written: false` →
   `parked reason=plan-not-written` with the result's `notes`.
4. **Record**: `features.py plan <slug> --steps <steps>` (`--replace` on a
   re-run), as explore-plan says.
5. **Read the plan and resolve its brief.** Key Decisions take the generator's
   recommendation; each is listed in the report under Decided. Then:

   | explore-plan brief item | Headless rule |
   |---|---|
   | A Blocking finding left after the one fix pass | **question**: the finding verbatim; options: the fix the validator implies (recommended) / leave as is / re-scope |
   | `review.ran: false` or `review.revalidated: false` | spawn `feature-dev:spec-plan-validator` (`artifact_type: plan`) once directly; still nothing → `parked reason=plan-unreviewed` |
   | A Baseline row `hollow` or `not-run: missing` for a step (gate-blocked) | **question**, one item per step (at most four, contract §5), with the step-loop's three options: fix the environment (name the host, package or variable, so the owner can allow it in the sandbox policy) / replace `Verify` with a command the answer gives / accept as verified by runner tests only (recommended when the step has a test file) |
   | `not-run: slow` or `not-run: writes` | accepted; listed under Unverified |
   | AC coverage below the total | Should Address in the report, not a gate |
   | `generator_notes`, `fix_notes` | Assumed or Unverified in the report |

   A Key Decision whose options differ in data model or public contract, and
   whose recommendation the spec contradicts, is a **question** too (options:
   the recommendation / the spec's reading, recommended / re-scope).

6. **Adversarial review.** After step 5 (the validator's fixes and the Key
   Decisions are already in the plan) and before Publish. Spawn
   `discuss:doc-adversary` (no `name`, never backgrounded; read
   `${CLAUDE_PLUGIN_ROOT}/../discuss/skills/adversarial-doc-review/SKILL.md`
   §Dispatch once). The prompt is paths, never content — no summary, no
   excerpt, no mention of who wrote the document:

   ```
   DOC_PATH: <PLAN path>
   MODE: design
   SOURCES: <repo root>, <SPEC path>
   OUTPUT_PATH: <session scratchpad, or /tmp when none is listed>/doc-adversary-<slug>-plan-r<n>.md
   ```

   Read `OUTPUT_PATH` first; use whatever came back inline only when the file
   is missing or empty. Before trusting a finding, spot-check one of its
   `Evidence` references (`path:line` or grep) against the clone.

   | Adversary report item | Headless rule |
   |---|---|
   | No report (file empty and nothing inline), or no findings **and** no Falsification attempts | the review did not happen: re-run once with a new `OUTPUT_PATH`; still nothing → `parked reason=adversary-unreviewed` |
   | A finding whose spot-checked `Evidence` does not hold | not a gate: kept in the report under Unverified with the check that failed |
   | A **HIGH** finding | **question**: the finding's title, `Decision at risk` and `What would be decided wrong`, verbatim; options: the reading the finding implies (recommended) / the document's reading / re-scope |
   | A **MEDIUM** finding | one fix pass: the reading the finding implies is written into the plan as a Key Decision, rewritten with the finding's Evidence as its basis — unless it changes a data model, a public contract or user-visible behaviour **and** has no basis in the issue, `docs/` or the code, which is a **question** as the HIGH row. After the fix pass the adversary runs **once more** (the skill's after-fixes rule) with a new `OUTPUT_PATH`; a MEDIUM that survives the re-run → **question** as the HIGH row |
   | Verdict `do not implement as written` with no HIGH finding | **question** anyway; options: re-scope (recommended) / proceed as written / close the issue |
   | An item under `Needs to be resolved` not covered by a finding's question | **question**, options taken from the item |
   | Verdict `no material findings` with Falsification attempts present | proceed; the report carries the verdict and the attempt count |

   Questions from this step count toward the four of the contract (§5); more
   than four in the run → `parked reason=too-many-questions`.

   The step runs under every lane. Under `spec-gate` / `plan-gate` the owner
   sees the adversary's block in the done comment before flipping.

7. **Publish the plan section** to `#N` (issue-store.md's Publish with
   `--kind plan`, after the answers below are written into the plan). The
   `features.py` state stays in the clone.

## Outputs

- The plan section in the issue body.
- The `done` comment: explore-plan's Phase 3 brief (the `Degraded
  exploration` line first when present, the **Plan review** line, Decided,
  Assumed, Unverified, Out of scope), the **Adversarial review** block of
  step 6 right after it, the explorer selection, whether the workflow or the
  fallback ran, and the contract's §7 lines. The block:

  ```
  Adversarial review: <verdict line verbatim> — re-run: yes|no
  Material findings: <n> (<m> HIGH)
  - [HIGH|MEDIUM] <title> — decided (Key Decision <k>) | asked | unverified: <failed check>
  Falsification attempts: <k>
  ```
- The flip of the lane table (`ready`, or `plan-review` under `factory:plan-gate`).

## Cannot decide → question

A surviving Blocking finding; a gate-blocked Baseline row; a Key Decision
whose options differ in data model or contract and whose recommendation the
spec contradicts; a HIGH adversary finding; a MEDIUM finding that survives
the re-run; a `do not implement as written` verdict; a `Needs to be resolved`
item. The plan is **not published** when the stage ends in a question: the
local cache keeps it for the re-run.

## Resume

A re-run after an answer writes it into the plan the way the step loop
expects — `accepted by user: <answer>` appended to the Baseline row's Detail,
or the step's `Verify:` line replaced and the row re-run once — or applies
the chosen fix, then continues from step 5 through step 7 and publishes, so
`implement` never re-asks. A re-run with a plan section already published
and the done marker latest runs only the flip.

A re-run after an answer applies the answer, then runs the adversary **once**
(no fix pass). A finding that names a decision the answer already settled is
listed as `decided by owner` and never re-asked; a new HIGH finding is a
question like any other.
