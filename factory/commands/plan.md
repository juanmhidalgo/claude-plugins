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
  - Bash(gh pr list *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/factory-issue.sh *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/factory-outcome.sh *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/../feature-dev/scripts/features.py *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/../feature-dev/scripts/issue_spec.py *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/../feature-dev/scripts/review_server.py snapshot *)
---

@factory/references/factory-contract.md

# `/factory:plan` — `status:needs-plan` → the plan section in the body

Stage `plan`. Caps are the daemon's (defaults 80 turns · 6 USD · 30 min; the real numbers for this run, per-repo overrides included, are the `Caps for this run` line under Context: size long steps against those, never against the defaults). No branch
exists yet: the plan's Baseline must run on the base, so the clone is put on
`origin/<default>` first.

## Context

- **Arguments**: $ARGUMENTS
- **Stage variable set**: !`echo "${#FACTORY_STAGE}"`
- **Caps for this run**: !`echo "turns=${FACTORY_MAX_TURNS:-default} budget_usd=${FACTORY_BUDGET_USD:-default} timeout_min=${FACTORY_TIMEOUT_MINUTES:-default}"`
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
5. **A pending replan.** `factory-issue.sh replan <N>` prints the daemon's
   `<!-- factory:replan by=daemon reason=base-moved sha=<old> base=<new>
   files="…" run=<id> -->` attributes when that comment is newer than the
   plan's `done` (exit 1: none pending). Keep `sha=` and `files=`: the Resume
   section says what they change. The clone's HEAD is already the new base
   (step 1).
6. **Open factory PRs.** `gh pr list --repo <owner/repo> --state open --json
   number,headRefName,title,files` (read-only; one call). Keep the PRs whose
   `headRefName` starts with `factory/`, with their `files[].path`; the
   intersection with this plan's files is computed once exploration has named
   them (Composition step 6). A `gh pr list` failure is not a park: the
   subsection says `unknown (gh pr list failed: <message>)` and the report
   lists it under Unverified.

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

6. **Open PRs touching this area.** Collect this plan's files (every path in
   `### Files to Modify`, `### Files to Create`, every step's `Impl:` and
   `Test:`, and every file a step deletes; tests included). Intersect them
   with each open `factory/*` PR's files (Inputs step 6) and append to the
   plan, as its last section:

   ```markdown
   ## Open PRs touching this area
   - #<n> <title> — <shared paths, comma-separated>
   ```

   or `## Open PRs touching this area` followed by `none` when no PR shares a
   path (or no factory PR is open). The plan is still written against the
   clone's HEAD, `origin/<default>`: the only base that exists. The daemon's
   gate holds the issue in `status:ready` until a listed PR merges or closes,
   and its replan (Resume) brings the plan back here once master moved on a
   file the plan names. A listed PR is also a Risk row: what the overlap is
   and which side should land first.
7. **Publish the plan section** to `#N` (issue-store.md's Publish with
   `--kind plan`, after the answers below are written into the plan). The
   `features.py` state stays in the clone. Publish is an upsert: `issue_spec.py
   splice` replaces the existing `feature-dev:plan:start`/`:end` section in
   place, so a re-run (and a re-plan) never leaves two plan sections.
8. **The files list.** Write the same paths as step 6, one per line, to a
   file in the session scratchpad (`/tmp` when none is listed), and pass it as
   `--files-file` on the `done` call: `factory-outcome.sh done <N> --stage
   plan --run <id> --body-file <report> --files-file <paths>`. The script
   validates, sorts and dedupes them into the marker's `files="…"` (contract
   §3); a refused path (`refused: bad path in --files-file: <line>`, exit 2)
   means the plan names a path that is not repo-relative or carries a glob,
   so fix the plan's table and the list together, then call again. The list
   must match the plan's steps: a reviewer compares the two, and the daemon's
   gate only sees what the marker names. No files at all (a plan with no
   steps) omits the flag.

## Outputs

- The plan section in the issue body, ending with `## Open PRs touching this
  area`.
- The `done` comment, with `files="…"` on its marker: explore-plan's Phase 3
  brief (the `Degraded exploration` line first when present, the **Plan
  review** line, Decided, Assumed, Unverified, Out of scope), the explorer
  selection, whether the workflow or the fallback ran, `Files: <n>` (the
  count of paths passed with `--files-file`), `Open PRs: none` or `Open PRs:
  #<n> (<k> shared)` per PR, `Re-planned after <daemon run id>: …` on a
  re-plan (Resume), and the contract's §7 lines.
- The flip of the lane table (`ready`, or `plan-review` under `factory:plan-gate`).

## Cannot decide → question

A surviving Blocking finding; a gate-blocked Baseline row; a Key Decision
whose options differ in data model or contract and whose recommendation the
spec contradicts. The plan is **not published** when the stage ends in a
question: the local cache keeps it for the re-run.

## Resume

A re-run after an answer writes it into the plan the way the step loop
expects — `accepted by user: <answer>` appended to the Baseline row's Detail,
or the step's `Verify:` line replaced and the row re-run once — or applies
the chosen fix, then continues from step 5 and publishes, so `implement`
never re-asks. A re-run with a plan section already published and the done
marker latest runs only the flip.

**Re-plan.** A `factory:replan` comment newer than the plan's `done` (Inputs
step 5 prints it; first line `<!-- factory:replan by=daemon
reason=base-moved sha=<old> base=<new> files="…" run=<id> -->`) means the
plan is stale: master moved on files it names, usually because another
factory PR merged. Then, instead of the flip:

1. Read the merged change on the files the marker names: `git log -p
   <sha>..HEAD -- <each path in files=>` (HEAD is the new base, Inputs
   step 1). Its summary goes in the report under `Re-planned after <daemon
   run id>:` with the PR number the comment's body quotes.
2. Re-run the exploration against the current clone (Composition from step 1;
   `features.py new` rewrites the cached plan in place and `features.py plan
   --replace` re-records the steps) and plan on top of the merged change: a
   step the merge already did is dropped, a step whose `Impl:`/`Test:` moved
   follows it, a conflict a merge would raise is resolved in the plan, not
   left for `implement`.
3. **Replace** the published plan section (Composition step 7: Publish is an
   upsert, the old section is spliced out) and post a fresh `done` with the
   new `sha` (the script reads HEAD, which is the new base) and the new
   `files="…"` (Composition step 8). The old `done` stays in the thread; the
   daemon reads the latest.

The flip-only rule above applies to every other re-run: a done marker that
is the latest marker and a published section mean the stage already ran.

**When both a question and a replan are present, the newest marker wins.**
`factory-issue.sh replan` already encodes it: a `question` marker newer than
the replan means the re-plan ran, asked, and now waits, so the answer rule
applies and the re-plan it continues publishes as step 3 says (new `sha`,
new `files`); a replan newer than the question cannot come from the daemon
(it replans only `status:ready` issues) but, found anyway, it wins: the
re-plan runs from scratch and the earlier answers are quoted under `Answer
understood:` and applied only to a Baseline row or step the new plan still
has. A `parked` newer than the replan does not clear it: the re-plan is
still owed.
