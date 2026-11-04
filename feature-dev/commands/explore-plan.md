---
disable-model-invocation: true
model: opus
allowed-tools:
  - Read
  - Write
  - Workflow
  - Glob
  - AskUserQuestion
  - Bash(gh auth status)
  - Bash(gh repo view --json nameWithOwner*)
  - Bash(gh issue view *)
  - Bash(gh issue edit *)
  - Bash(git branch --show-current)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/issue_spec.py *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/features.py *)
argument-hint: "[SPEC-*.md path or feature description — optional; picks from the feature store if omitted]"
description: |
  Use when starting a feature that touches multiple parts of the codebase and you need a
  structured implementation plan before coding.
  Do NOT use for simple bug fixes or single-file changes.
keywords:
  - exploration
  - planning
  - parallel-agents
  - implementation-plan
  - architecture
triggers:
  - "explore and plan"
  - "plan this feature"
  - "parallel exploration"
  - "implementation plan for"
  - "understand the codebase for"
---

## Context
- **Repository**: !`git remote get-url origin`
- **Current branch**: !`git branch --show-current`
- **Feature**: $ARGUMENTS
- **Feature store**: each feature lives in `.feature-dev/features/<slug>/`, managed by `${CLAUDE_PLUGIN_ROOT}/scripts/features.py` (every call below passes `--root <repo root>`). Layout: [artifact-locations.md](../skills/spec-driven-development/references/artifact-locations.md).

## Phase 0: Resolve Feature and Validate

**Requires the `Workflow` tool.** If it is not available, **STOP** and say so:
Phase 1 runs as the `feature-dev:plan-fanout` workflow, and under `claude -p`
or the SDK it needs a `Workflow(feature-dev:plan-fanout)` allow rule. There is
no in-session fallback: a generator spawned from here cannot fan out to the
explorers (a named spawn is a teammate, and a teammate cannot spawn agents),
and a plan written by one reader that looks like eight cross-checked it is the
failure the workflow exists to prevent.

1. **Resolve the feature.** Run, once:

   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/features.py resolve spec '<argument>' --skip-implemented --root <repo root>
   ```

   `<argument>` is `$ARGUMENTS` as given (omit it when empty). The script takes
   a `SPEC-*.md` path (a `PLAN-*.md` path resolves to the spec beside it), `#N`,
   `owner/repo#N` or an issue URL, a feature slug or title, or nothing (every
   feature with a spec, implemented ones skipped since they are already shipped;
   several are narrowed to the current branch). It prints one JSON line. On
   success: `path`, `slug`, `feature`, `branch`, `repos` (the names in the
   frontmatter's `repos:` block), `status`, `plan` (progress, or null), `issue`
   (ref, or null), `plan_path` (a PLAN already beside the spec, or null),
   `external` (the spec sits in another repo's `.feature-dev/features/`) and
   `matched` (how it was found). On failure: `error`, plus `reason` (exit 2) or
   `candidates` (exit 3).

   | Exit | Meaning | Do |
   |------|---------|----|
   | `0` | Resolved | Continue with the JSON. When `matched` is not `path`, say: "Auto-selected spec: `<path>` (feature: <feature>, status: <status>)" |
   | `2` | `reason: issue_unlinked` | No local feature is linked to `issue` (`repo` null means this repo: resolve it per [issue-store.md's Argument parsing](../skills/spec-driven-development/references/issue-store.md#argument-parsing)). Run [issue-store.md's Import algorithm](../skills/spec-driven-development/references/issue-store.md#import-ac-8-ac-9-ac-10-ac-11-ac-12) against it, start to finish; do not restate Import's steps here. A failed `gh` preflight, or a failed `gh issue view` call, stops here and names the issue that could not be read. Then re-run `resolve spec` with the `SPEC-<slug>.md` path Import produced (the reference's own step 6) and read that result |
   | `2` | `reason: unknown_name` | `$ARGUMENTS` is a feature description. There is no spec: this is a **plan-only feature** (step 3) |
   | `2` | `reason: no_candidates` | **STOP** and ask the user for a feature description or a spec path |
   | `2` | `reason: file`, `outside_store` or `no_sibling` | **STOP** and refuse it in one line, quoting `error`, naming `.feature-dev/features/<slug>/` as the only place specs live (a root `SPEC-*.md`, or the layout older than 2.0.0, is `outside_store`) |
   | `3` | Ambiguous | AskUserQuestion over `candidates` (label = `feature`, description = `<slug> — status: <status>`), then re-run `resolve spec` with the chosen `path` |
   | `4` | Malformed | **STOP** and quote `error`: the spec, or its `feature.json`, has to be fixed before planning |

2. **Check the chosen spec's state**, from the JSON's `status` and `external`.
   - **If the spec's status is `draft`**:
     - Ask once with AskUserQuestion: "This spec is still a draft. Mark it approved and plan it?" (options: approve and continue / stop).
     - **Yes** → run `${CLAUDE_PLUGIN_ROOT}/scripts/features.py approve <slug> --root <repo root>` and continue.
     - **No** → **STOP** and point the user to `/feature-dev:review <spec path>` to approve it first. Never plan from `draft`.
   - **If `external` is `true`** (the spec lives in a sibling repo, e.g. `../other-repo/.feature-dev/features/<slug>/SPEC-<slug>.md`):
     - Treat it as a plan-only feature: run `new <slug> --kind plan` without `--spec` (step 3), because the spec has no folder here.
     - Read the sibling spec for the feature description and ACs, and reference it by path in the PLAN body (a `Source spec: <path>` line under the Summary). The path is a reference, not a key.
   - **Any other status** (`approved`, `planned`, `running`, `halted`) → continue.
3. Parse the feature into a one-line summary for agent prompts. Pick the slug: lowercase, hyphenated, max 4 words from the feature name (E.g., `scheduled-notifications`); with a spec in this repo, reuse the JSON's `slug`. The **plan path** comes from the script, never composed by hand:
   - **Spec in this repo, no plan yet** (`plan_path` is null) → `${CLAUDE_PLUGIN_ROOT}/scripts/features.py new <slug> --kind plan --spec <spec-slug> --root <repo root>` prints `.feature-dev/features/<spec-slug>/PLAN-<slug>.md`.
   - **Plan-only feature** (description only, or an external spec) → `features.py new <slug> --kind plan --root <repo root>` prints the path in its own folder.
   - **A plan already exists** (`plan_path` is not null) → that path is rewritten in place and `new` is not called.

   Every `PLAN-<slug>.md` below means this path. A plan-only feature has no spec to hold decisions, so they go in a `## Decisions Log` section in the PLAN body.
4. **Select the explorers.** Four always run: `backend-explorer`, `frontend-explorer`, `test-explorer`, `history-explorer`. Add any of the four below whose signal is present in the feature description or, if a spec was chosen, in the spec body (read it — the frontmatter alone is not enough signal).

   | Explorer | Add when the feature… |
   |---|---|
   | `schema-explorer` | touches persistence: a new/changed model, table, column, index, constraint, or migration; a data backfill; anything with a storage shape |
   | `config-explorer` | introduces or reads a setting, an environment variable, a credential, or a feature flag; behaves differently per environment; needs a rollout toggle |
   | `api-contract-explorer` | is consumed across a repo boundary: the JSON's `repos` has 2+ names, or the feature changes a declared contract (OpenAPI, GraphQL SDL, tRPC router, protobuf, JSON Schema) |
   | `observability-explorer` | ships something whose failure is silent: a background job, queue consumer, scheduled task, webhook handler, payment or auth path — anywhere post-ship visibility is how you learn it broke |

   These are cheap (read-only, parallel, `maxTurns: 30`) and the cost of omitting one is planning blind on the highest-risk layer. **When a signal is borderline, include the explorer.** Record the selected list; you pass it to the Phase 1 workflow as `explorers`.

   State the selection to the user in one line: "Explorers: backend, frontend, test, history + schema (new model), config (feature flag)."

## Phase 1: Explore, generate and review the plan (workflow)

Launch the `feature-dev:plan-fanout` workflow and wait for its notification:

```
Workflow({ name: "feature-dev:plan-fanout", args: {
  feature: "<one-line summary>", repo: "<repo URL>", branch: "<branch>",
  plan_path: "<plan path from Phase 0>", spec_path: "<spec path, or none>",
  explorers: [<extra explorers from Phase 0: schema | config | api-contract | observability>],
  rules: "${CLAUDE_PLUGIN_ROOT}/references/plan-generation.md",
  plugin_root: "${CLAUDE_PLUGIN_ROOT}" } })
```

It runs the four base explorers plus the selected ones in parallel, retrying
one that returns nothing once. One generator then synthesizes their reports,
runs the Baseline and writes the plan by the rules in
`references/plan-generation.md`. An explorer that failed twice is named to the
generator, which covers that layer itself and writes the `Degraded exploration`
line. Then `spec-plan-validator` reviews the plan; Blocking findings get one fix
pass and one re-validation. There is no second pass: a Blocking finding that
survives one fix needs the user. None of the explorer reports reach this
conversation, only the plan file and the result.

**Read the result:**

- `written: false` → the plan was not written. Show `notes` and stop.
- `explorers`: any with status `failed` must match `degraded`; if a failed
  explorer is missing from `degraded`, add the line to the plan yourself.
- `review.ran: false` → the validator returned nothing twice. Say so: the plan
  is unreviewed, and `/feature-dev:plan-review <plan path>` runs it again.
- `review.revalidated: false` → the fix pass edited the plan, but the
  re-validation returned nothing. The report shown is from before the fixes:
  say so.
- `generator_notes` and `fix_notes` go in the brief (Assumed, or Unverified).

**Record the plan in the feature store** once the result is in: run
`${CLAUDE_PLUGIN_ROOT}/scripts/features.py plan <slug> --steps <steps> --root <repo root>`.
When the feature is already past `approved` (`plan_path` was not null, or it
is a plan-only feature), add `--replace`. A refusal (`refused: …`) names the state
and the valid events; report it instead of editing `feature.json`.

Keep `review` for Phase 2. Do not print the report in full.

## Phase 2: Review Brief

Read `PLAN-<slug>.md` from disk and end with a review brief instead of re-printing the plan. Users approve from the chat; a plan printed in full gets approved unread, while a short numbered list gets answered item by item. Give the full plan only on request.

1. **If the plan carries a `Degraded exploration` line, lead with it** — say which layers had no explorer and that those findings had a single reader. A plan the user reviews as if eight agents cross-checked it, when one did not, is the failure mode worth a sentence at the top.
2. Then the brief: at most ~15 lines, numbering continuous across groups so the user can answer "2: no, 5: ok", empty groups omitted.

```markdown
### Review brief — PLAN-<slug>.md (<N> lines, <T> steps)
**Plan review** — <B> Blocking left (<F> fixed in one pass), <S> Should Address · AC coverage <c>/<t>
1. Blocking: <finding, section>
2. <Should Address finding: what /tdd does if it is left (stops at step N, runs a missing file, …)> — fix: <one clause>, section
- Nice to Have: <n> — <short list, one line>
**Decided** (review if you disagree)
3. <a Key Decision and its recommendation, one line>
**Assumed — confirm**
4. <an assumption a step relies on that exploration did not settle; a `pre-existing-fail` Baseline row /tdd will treat as baseline>
**Unverified claims about the code**
5. Step 9 `make run-api` — Baseline `not-run`: missing — pipenv not installed
**Out of scope**
- <what the plan deliberately leaves out>
Reply with the numbers you want changed, or "approved".
Or review it in the browser: /feature-dev:review <plan path>
```

The **Plan review** group leads because a remaining Blocking finding is the one thing that stalls /tdd. Blocking findings come first, then Should Address. Each finding is written as its consequence for the run plus the fix, not in the validator's terms: "Steps 11/12 Pins on a file written by step 9" went unread, while "/tdd would make steps 11/12 edit step 9's test file, so their RED never fails — fix: move the pins to step 9" gets an answer. A finding that restates a Baseline row already listed under Unverified is not repeated. When the validator found nothing, the group is one line: `**Plan review** — clean`. `AC coverage` is copied from the validator's summary; leave it out when the source spec has no numbered ACs. An uncovered AC is one of the Should Address findings in the group.

Every Baseline row that gates a step — `hollow`, or `not-run` for `missing` — goes under **Unverified**, with a note that /tdd will ask about it before its first dispatch (fix the environment, give a replacement `Verify`, or accept the step as unverifiable by its gate). `not-run` for `slow` or `writes` goes there too, without the note: it does not gate, but nothing checked it on HEAD.

3. **Publish the plan** when the Phase 0 JSON's `issue` is not null.
   Ask once with AskUserQuestion: **Publish the plan to #N (Recommended)** /
   **Keep it local**. Publishing runs [issue-store.md's Publish algorithm](../skills/spec-driven-development/references/issue-store.md#publish-ac-1-ac-2-ac-3-ac-4-ac-5-ac-7)
   with kind `plan` against `PLAN-<slug>.md` and the feature's `#N`, start to
   finish — its `gh` preflight, scratch file, `splice --kind plan` and
   fingerprint verification. Do not restate those steps here — follow the
   reference. The issue then carries both sections, and `/feature-dev:tdd #N`
   on another checkout imports the plan with the spec. A failed publish is
   reported; the local plan is untouched.
4. End with the next commands, using the plan path from Phase 0, then stop:

   ```
   Next: answer the brief, then /clear and /feature-dev:tdd <plan path>   (a fresh context leaves /tdd's budget to the steps)
   /feature-dev:plan-review <plan path> only if you edit the plan by hand
   ```
