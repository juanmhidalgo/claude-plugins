---
disable-model-invocation: true
model: opus
allowed-tools:
  - Read
  - Write
  - Agent
  - Workflow
  - Glob
  - Bash(gh auth status)
  - Bash(gh repo view --json nameWithOwner*)
  - Bash(gh issue view *)
  - Bash(git branch --show-current)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/issue_spec.py *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py snapshot *)
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

1. **Resolve the feature:**
   - **If `$ARGUMENTS` is the path of an existing `SPEC-*.md`** → use that spec as if it had been auto-selected below (the closing lines of `/feature-dev:spec` and `/feature-dev:spec-review` print this form). A spec of **this** repo must sit in `.feature-dev/features/<slug>/`; refuse any other path (a root `SPEC-*.md`, or the layout older than 2.0.0) in one line and name `.feature-dev/features/<slug>/` as the only place specs live.
   - **If `$ARGUMENTS` is `#N`, `owner/repo#N`, or an issue URL** → resolve it per [issue-store.md's Argument parsing](../skills/spec-driven-development/references/issue-store.md#argument-parsing), then run [issue-store.md's Import algorithm](../skills/spec-driven-development/references/issue-store.md#import-ac-8-ac-9-ac-10-ac-11-ac-12) against it, start to finish. Do not restate Import's steps here — follow the reference. A failed `gh` preflight, or a failed `gh issue view` call, stops here and names the issue that could not be read. On success, continue as if `$ARGUMENTS` had been the resulting `SPEC-<slug>.md` path (the reference's own step 6).
   - **If `$ARGUMENTS` is any other text** → use it as the feature description. There is no spec: this is a plan-only feature (see step 3).
   - **If `$ARGUMENTS` is empty** → run `${CLAUDE_PLUGIN_ROOT}/scripts/features.py list --json --root <repo root>` and keep the features that have a SPEC artifact and whose `status` is not `implemented` (those features are already shipped). A missing `.feature-dev/features/` is an empty list. From the remaining candidates:
     - **0 specs** → **STOP** and ask the user for a feature description.
     - **1 spec** → use it. Read its frontmatter, use `feature:` as the feature description, and take the spec path from its `artifacts`. Inform the user: "Auto-selected spec: `<spec path>` (feature: <name>, status: <status>)".
     - **2+ specs** → use AskUserQuestion to let the user pick (label = `feature:` value, description = `<slug> — status: <status>`). Use the chosen spec's `feature:` as the feature description.
2. **Check the chosen spec's state.** Read its `status` from `list --json`.
   - **If the spec's status is `draft`**:
     - Ask once with AskUserQuestion: "This spec is still a draft. Mark it approved and plan it?" (options: approve and continue / stop).
     - **Yes** → run `${CLAUDE_PLUGIN_ROOT}/scripts/features.py approve <slug> --root <repo root>` and continue.
     - **No** → **STOP** and point the user to `/feature-dev:review <spec path>` to approve it first. Never plan from `draft`.
   - **If the spec lives in a sibling repo** (a path outside this repo's `.feature-dev/features/`, e.g. `../other-repo/.feature-dev/features/<slug>/SPEC-<slug>.md`):
     - Treat it as a plan-only feature: run `new <slug> --kind plan` without `--spec` (step 3), because the spec has no folder here.
     - Read the sibling spec for the feature description and ACs, and reference it by path in the PLAN body (a `Source spec: <path>` line under the Summary). The path is a reference, not a key.
   - **Any other status** (`approved`, `planned`, `running`, `halted`) → continue.
3. Parse the feature into a one-line summary for agent prompts. Pick the slug: lowercase, hyphenated, max 4 words from the feature name (E.g., `scheduled-notifications`); with a spec in this repo, reuse its `slug:` value. The **plan path** comes from the script, never composed by hand:
   - **Spec in this repo, no plan yet** → `${CLAUDE_PLUGIN_ROOT}/scripts/features.py new <slug> --kind plan --spec <spec-slug> --root <repo root>` prints `.feature-dev/features/<spec-slug>/PLAN-<slug>.md`.
   - **Plan-only feature** (description only, or a sibling-repo spec) → `features.py new <slug> --kind plan --root <repo root>` prints the path in its own folder.
   - **A plan already exists** (the feature's `artifacts` in `list --json` lists a PLAN) → that path is rewritten in place and `new` is not called.

   Every `PLAN-<slug>.md` below means this path. A plan-only feature has no spec to hold decisions, so they go in a `## Decisions Log` section in the PLAN body.
4. **Select the explorers.** Four always run: `backend-explorer`, `frontend-explorer`, `test-explorer`, `history-explorer`. Add any of the four below whose signal is present in the feature description or, if a spec was chosen, in the spec body (read it — the frontmatter alone is not enough signal).

   | Explorer | Add when the feature… |
   |---|---|
   | `schema-explorer` | touches persistence: a new/changed model, table, column, index, constraint, or migration; a data backfill; anything with a storage shape |
   | `config-explorer` | introduces or reads a setting, an environment variable, a credential, or a feature flag; behaves differently per environment; needs a rollout toggle |
   | `api-contract-explorer` | is consumed across a repo boundary: the spec's frontmatter has 2+ `repos:` entries, or the feature changes a declared contract (OpenAPI, GraphQL SDL, tRPC router, protobuf, JSON Schema) |
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
When the feature is already past `approved` (a plan existed, or it is a
plan-only feature), add `--replace`. A refusal (`refused: …`) names the state
and the valid events; report it instead of editing `feature.json`.

Keep `review` for Phase 3. Do not print the report in full.

## Phase 2: Fallback when workflows are disabled

Only when `Workflow` is not available. Say that the workflow path was not used.

1. **Generate.** Launch one anonymous `general-purpose` Agent (do **not** pass
   `name`: a named spawn is a teammate, and a teammate cannot spawn the
   explorers). Its prompt gives the feature summary, repo, branch, plan path,
   source spec, the selected explorers, `PLUGIN_ROOT: ${CLAUDE_PLUGIN_ROOT}` and
   `RULES: ${CLAUDE_PLUGIN_ROOT}/references/plan-generation.md`, and tells it to:
   - launch every selected explorer (`feature-dev:<name>-explorer`, prompt
     "Explore <layer> for: <summary>") plus the four base ones in a single
     response, none with `name`. A refused spawn is retried once without
     `name`; if it is refused again, the generator explores that layer itself
     and writes the `Degraded exploration` line, quoting the refusal;
   - then follow Steps 2, 2b, 2c and 3 of RULES.
2. **Review.** Spawn `feature-dev:spec-plan-validator` (no `name`) with
   `artifact_type: plan` and `artifact_path: <plan path>`. On Blocking findings,
   re-dispatch one anonymous `general-purpose` Agent with the plan path, the
   Blocking findings verbatim, PLUGIN_ROOT and RULES: snapshot the plan with
   `${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py snapshot <plan path>`, fix
   each finding in place touching only what it names, follow Steps 2b and 2c
   for changed steps, leave a finding that needs a user decision. Then validate
   once more. No second re-dispatch.
3. **Record** the plan in the feature store as Phase 1 says.

## Phase 3: Review Brief

Read `PLAN-<slug>.md` from disk and end with a review brief instead of re-printing the plan. Users approve from the chat; a plan printed in full gets approved unread, while a short numbered list gets answered item by item. Give the full plan only on request.

1. **If the plan carries a `Degraded exploration` line, lead with it** — say which layers had no explorer and that those findings had a single reader. A plan the user reviews as if eight agents cross-checked it, when one did not, is the failure mode worth a sentence at the top.
2. Then the brief: at most ~15 lines, numbering continuous across groups so the user can answer "2: no, 5: ok", empty groups omitted.

```markdown
### Review brief — PLAN-<slug>.md (<N> lines, <T> steps)
**Plan review** — <B> Blocking left (<F> fixed in one pass), <S> Should Address · AC coverage <c>/<t>
1. Blocking: <finding, section>
2. <Should Address finding, section>
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

The **Plan review** group leads because a remaining Blocking finding is the one thing that stalls /tdd. Blocking findings come first, then Should Address. A finding that restates a Baseline row already listed under Unverified is not repeated. When the validator found nothing, the group is one line: `**Plan review** — clean`. `AC coverage` is copied from the validator's summary; leave it out when the source spec has no numbered ACs. An uncovered AC is one of the Should Address findings in the group.

Every Baseline row that gates a step — `hollow`, or `not-run` for `missing` — goes under **Unverified**, with a note that /tdd will ask about it before its first dispatch (fix the environment, give a replacement `Verify`, or accept the step as unverifiable by its gate). `not-run` for `slow` or `writes` goes there too, without the note: it does not gate, but nothing checked it on HEAD.

3. End with the next commands, using the plan path from Phase 0, then stop:

   ```
   Next: answer the brief, then /clear and /feature-dev:tdd <plan path>   (a fresh context leaves /tdd's budget to the steps)
   /feature-dev:plan-review <plan path> only if you edit the plan by hand
   ```
