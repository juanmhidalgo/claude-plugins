# feature-dev

Feature development workflows with structured phases and quality gates.

## Commands

| Command | Purpose |
|---------|---------|
| `/feature-dev:spec <feature>` | Create a structured specification before coding with gated review workflow |
| `/feature-dev:tdd <spec>` | Test-driven feature development: write failing tests, implement, coverage gate, refactor |
| `/feature-dev:explore-plan <feature>` | Parallel codebase exploration with 4 agents, synthesized implementation plan |
| `/feature-dev:spec-review [file]` | Validate a `SPEC-*.md` for structural gaps and check its claims about the existing code; emits Blocking / Should Address / Nice to Have checklist |
| `/feature-dev:plan-review [file]` | Validate a `PLAN-*.md` for structural gaps, step contract and baseline; emits Blocking / Should Address / Nice to Have checklist |
| `/feature-dev:review <SPEC\|PLAN>` | Review a spec or plan in a local browser page: outline, AC and Key Decision cards, comments anchored to selected text, diff against the previous version, and a verdict (Approve / Approve with notes / Request changes) that the command then applies |
| `/feature-dev:cleanup` | Bulk-delete implemented `SPEC-*.md` and stale `PLAN-*.md` artifacts; also removes the slug's local review history, and first offers to save a spec's Decisions Log and unticked QA items as a comment on the spec's PR or to `docs/decisions/`; explicit Y/N confirmation required |

## Agents

**Exploration** — spawned by `explore-plan` for parallel codebase analysis:

| Agent | Focus |
|-------|-------|
| `backend-explorer` | Models, views, serializers, endpoints, services, database patterns |
| `frontend-explorer` | Components, hooks, API clients, routing, state management, UI patterns |
| `test-explorer` | Test files, fixtures, factories, coverage config, test patterns |
| `history-explorer` | Git history, open PRs, recent changes, conflict risk assessment |

**Conditional explorers** — `explore-plan` selects these in Phase 0 from signals in the feature description and spec body, and dispatches them in the same parallel batch as the four above. Also invocable directly via `subagent_type: "feature-dev:<name>"` from any skill in any repo:

| Agent | Focus |
|-------|-------|
| `config-explorer` | Settings modules, environment variables, feature flags, credential handling, per-environment overrides — selected when the feature reads or introduces any of them |
| `schema-explorer` | DB migrations, current schema, indexes/constraints, naming conventions, pending migrations — selected when the feature touches persistence |
| `api-contract-explorer` | OpenAPI, GraphQL, tRPC, protobuf, JSON Schema contracts, distinct from endpoint code — selected for multi-repo features or declared-contract changes |
| `observability-explorer` | Logging, metrics, tracing, error reporting, alerting, dashboards — selected when the feature can fail silently (jobs, consumers, webhooks, auth/payment paths) |

**Review** — backend for `spec-review` and `plan-review`:

| Agent | Focus |
|-------|-------|
| `spec-plan-validator` | Structural gap detection on `SPEC-*.md` / `PLAN-*.md`, plus a read-only check of the spec's claims about the existing code (opus) |

**Implementation** — dispatched by the main agent (or each other) once a plan is approved:

| Agent | Focus |
|-------|-------|
| `plan-step-executor` | Executes ONE step of an approved plan in isolation; returns a fixed-format report (Files / Verification / Deviations / Carry-over / Blockers) |
| `feature-implementer` | Orchestrates an approved `PLAN-*.md` end-to-end by dispatching steps to `plan-step-executor`, threading carry-over forward, halting on blockers |
| `tdd-runner` | Strict red-green-refactor enforcer for one bounded behavior; caps at 5 cycles, validates RED failure mode, gates promotion on coverage. Stack-agnostic (pytest / vitest / jest). **Dispatched per acceptance criterion by `/feature-dev:tdd`** |
| `cross-repo-advisor` | Read-only decision brief for ONE bounded cross-repo question (who owns a field, does this break the contract). Recommends with cited evidence; never edits and never decides. Spawned by `/feature-dev:tdd` when a halt is a question rather than a defect, or invocable directly |

## Skills

| Skill | Purpose |
|-------|---------|
| `spec-driven-development` | Gated specification workflow: assumption surfacing, numbered acceptance criteria, spec template |
| `tdd-patterns` | Institutional TDD knowledge: iteration limits, coverage gates, phase constraints |

## Workflow

The commands are designed to chain:

1. **`/feature-dev:spec`** — Define requirements and create a specification. It asks for scope and non-goals first, on their own, then stops at the spec: what, why, numbered acceptance criteria (`AC-1`…), QA checklist and boundaries. Pass `--with-tasks` to also append a high-level plan and task list, for when you will not run `explore-plan`.
2. **`/feature-dev:spec-review`** *(optional)* — Structural check plus a **code-claims pass**: the spec's load-bearing claims about the existing code (paths, symbols, nullability, relationship direction, migration numbers) are checked against the repo and reported as CONFIRMED / DRIFTED / REFUTED / UNVERIFIED. It offers to apply the fixes that need no decision.
3. **`/feature-dev:explore-plan`** — Understand the codebase and create the plan. The plan is the only place implementation steps live, and it carries a **Baseline**: every `Verify` command run once on HEAD, so broken or hollow gates surface at planning time instead of mid-run. It then reviews its own plan (`plan-review` runs automatically) and fixes Blocking findings once before showing you the brief.
4. **`/feature-dev:tdd`** — Execute the plan with test-driven development

At any approval gate, **`/feature-dev:review <path>`** is the alternative to answering in the chat. It serves the artifact on `127.0.0.1` and opens it in your browser. The page uses the Python 3 standard library only and loads nothing from the network, so it is safe on proprietary code. For a plan, each Key Decision becomes a card you accept or change, and the Baseline is highlighted. For a spec, the acceptance criteria are. Select any text to comment on it. The **Changes** tab diffs against the previous version, which the commands copy to `.feature-dev/history/<slug>/` before each overwrite. Your verdict is written to `.feature-dev/reviews/` and applied by the command:

- **Approve** marks a spec `approved`.
- **Approve with notes** records the notes and changes nothing unless a note asks.
- **Request changes** checks each comment against the artifact and the code before editing, then offers another round that shows the diff.

Both `.feature-dev/` and the artifacts are added to `.gitignore`.

### Where the files go

```
.feature-dev/
├── specs/SPEC-<slug>.md     # /feature-dev:spec, issue imports
├── plans/PLAN-<slug>.md     # /feature-dev:explore-plan
├── reviews/                 # /feature-dev:review verdicts, .<slug>.url pointers
└── history/<slug>/          # snapshots the review page diffs against
```

The plugin option **`artifacts_dir`** (default `.feature-dev`) moves `specs/` and `plans/` to another folder inside the project. `reviews/` and `history/` stay in `.feature-dev/`. Set it in `/config` or with `/plugin configure feature-dev@juanmhidalgo-plugins`.

Specs and plans written at the project root before 1.32.0 are still found: every command lists the folder first, then the root, through `review_server.py artifacts`. A name present in both places is taken from the folder. Nothing is moved; new files are only written to the folder. The full rules are in [artifact-locations.md](skills/spec-driven-development/references/artifact-locations.md).

### Review band

In the interactive terminal, a band above the prompt lists each `SPEC-*.md` / `PLAN-*.md` that changed after its latest browser review: `<name> · not reviewed since last change`, with two buttons:

- **Open review** runs `/feature-dev:review <path>`, the same as typing it, so the verdict is applied as usual. While a review server for that artifact is running, a link to its page replaces the button.
- **Dismiss** hides that artifact until it changes again, in this session and the next ones. Dismissals are kept per repository in `.feature-dev/band-dismissed.json` (artifact name and mtime; gitignored with the rest of `.feature-dev/`). An entry is dropped once its artifact is gone or has changed, and `/feature-dev:cleanup` drops the entries of the artifacts it deletes.

Only recent changes are listed: an artifact modified within the last **`review_band_window_hours`** (plugin option, default `24`, minimum `1`), or at any point since this session started. An older file that was never reviewed in the browser stays out of the band. It comes back the next time it is edited. A SPEC whose frontmatter says `status: approved` (what the `approve` verdict of `/feature-dev:review` writes) is not listed either.

With two or more pending artifacts the band shows a single row: `<N> not reviewed`, with **Open `<name>`** for the most recently modified one, **Show all**, **Dismiss all** and **Clean up**. **Show all** lists one row per artifact, as above, with **Collapse** and **Clean up** buttons. The expanded view lasts for the session. **Dismiss all** works like **Dismiss** on every listed artifact. **Clean up** runs `/feature-dev:cleanup`, which lists its own candidates and asks before deleting anything; the band itself never deletes a file.

Dismissals are a plain file write (the mods API has no rename): two sessions of the same repository dismissing at the same moment can lose one entry, and that row shows up again. A file left unreadable reads as nothing dismissed.

The band is rescanned at the end of every turn of the main conversation (not of subagents) and at session start. A review counts only if its `artifact:` names that exact file, so a SPEC review never clears the PLAN of the same slug. The `status: approved` edit that `/feature-dev:review` makes itself does not count as a change.

It is a hooks module (`hooks/register.tsx`), so it needs a Claude Code build that loads plugin hooks modules. **It does not appear** under `claude -p`, `--safe-mode` or `disableAllHooks`, nor in the VS Code extension. Without it, the "Or review it in the browser: …" line that `spec` and `explore-plan` print is still the way in. **To turn it off**, set the plugin option `review_band` to `false` in `/config` (or `/plugin configure feature-dev@juanmhidalgo-plugins`).

Each command can also be used independently.

**Acceptance criteria are traced end to end.** Spec criteria carry ids (`AC-1`…). When the spec numbers them, every behavior step in the plan says which ones it makes true (`Covers:`). The plan review flags an AC that no step covers and a `Covers:` that cites an id the spec does not define, and reports `AC coverage: covered/total`. `/tdd`'s final report lists the ACs covered by met steps and names the uncovered or halted ones. Runners put the id in the test's name or docstring where the project's style allows.

Every approval gate ends with a short **review brief** instead of re-printing the artifact: what was decided, what was assumed, which claims about the code are unverified, and what is out of scope — numbered, so you can answer "2: no, 5: ok".

### How `/feature-dev:tdd` executes

The command is an **orchestrator, not an implementer**. After loading the plan it decomposes the feature into ordered acceptance criteria and dispatches one **`tdd-runner`** per criterion, sequentially, threading carry-over forward and halting on the first blocker. Test bodies and implementation diffs stay in the runners' contexts; the main agent keeps the criteria list, the reports, and the final lint/coverage pass.

Dispatch is sequential by design — later criteria depend on symbols earlier ones introduce, and concurrent runners collide on overlapping files.

Steps whose `Test:` is `n/a` (migrations, config wiring, dependency bumps) route to **`plan-step-executor`** instead — nothing to drive test-first, but the step's `Verify` command still gates it.

Two step shapes keep plans short:

- **`Pins:`** — tests that only lock in behavior that already exists ride on the step whose test file they belong to, instead of becoming steps of their own. The runner writes them after the step's criterion is green and proves each one can fail.
- **`Kind: characterization`** — refactors, deprecations and removals whose tests are expected to pass on the first run. `tdd-runner` runs them in characterization mode: write the tests, see them green, prove each can fail with a temporary mutation, restore the tree.

The plan's **Baseline** tells `/tdd` which failures were already on HEAD, so a pre-existing red test is attributed to the baseline instead of halting the run, and a step whose gate checks nothing (`hollow`) or cannot run here (`not-run: missing`) is settled with you once, before the first dispatch — fix the environment, replace the `Verify`, or accept the step as verified by its own tests — and the answer is written into the plan so a resumed run does not ask again.

### Resuming a halted run

`/feature-dev:tdd` records progress in the plan's frontmatter (`run_status`, `completed_steps`) as it goes. When a step halts, the plan and spec stay on disk and the working tree keeps the finished steps.

The same resume lets you free context on a long run: at each milestone boundary (or every ~8 steps) `/tdd` prints one line saying progress is recorded and that `/clear` then `/feature-dev:tdd PLAN-<slug>.md` continues from there. It does not stop or ask.

Re-running `/feature-dev:tdd` picks it up: it re-runs the `Verify` command of each recorded step, skips the ones that are still green, re-dispatches any that regressed, and resumes from the halt point. A dirty working tree is only a hard stop when there is no in-progress plan to explain it.

**Do not `git stash` a halted run** — the recorded progress points at work that would no longer be in the tree. `/feature-dev:cleanup` will not offer an `in-progress` or `halted` plan for deletion, for the same reason.

### Alternative implementation path (non-TDD)

When a `PLAN-*.md` is approved but the work isn't test-first (migrations, config wiring, mechanical refactors), dispatch the plan agents directly instead of running `/feature-dev:tdd`:

- **`feature-implementer`** drives the whole plan: dispatches each step to `plan-step-executor`, threads carry-over forward, halts on blockers.
- **`plan-step-executor`** can be dispatched directly for a single qualifying step (multi-file scope, own verification).

Neither enforces red-green-refactor — that's `tdd-runner`'s job, and `/feature-dev:tdd` is how you reach it.

### Decisions Log

Decisions taken *during* implementation land in a `## Decisions Log` section of the `SPEC-*.md`, not in the plan — the plan is deleted when it completes, the spec is not. `/feature-dev:tdd` appends to it in Phase 3 and reads it back in Phase 1, so a run in the consuming repo starts already knowing what the contract-owning repo decided. Each entry carries a `Binds:` field naming who has to obey it.

This is what removes the need to keep a second session open as the feature's memory across repos. For the *judgement* half of that role — a bounded question you want a second read on — spawn `cross-repo-advisor`; it produces a brief, the decision stays yours, and once you take it `/feature-dev:tdd` records it.

### Coordinator session

If you keep a session open as the feature's coordinator, name it at invocation:

```
/feature-dev:tdd --coordinator <session-name>
```

On a halt that is a cross-repo *question* (not a defect), the run sends that session one message — the step, the question, and the `cross-repo-advisor` brief if one was produced — with `notify_when_idle: true`, and carries on handing the halt to you. Never per-step progress: one message per halt that needs one.

**The command does not go looking for a session, by design.** `ListAgents` reports name, kind and status but no working directory, so matching falls back to the name — and a coordinator for a multi-repo feature has no single repo to be named after. Name-matching finds the implementer sessions and misses the coordinator. You name it or it is not used.

**The log is the record; the message is a notification.** A decision is written to the spec's Decisions Log before it is announced, and only after you accept it. A session can be compacted, restarted or closed; the spec cannot.

## GitHub Issue Store (optional)

By default a spec stays a local, uncommitted `SPEC-*.md`. A project can opt into
storing it on a GitHub issue instead — the issue becomes the durable copy, the
local file stays the working copy. Format, fingerprints and the publish/import
algorithm are in [issue-store.md](skills/spec-driven-development/references/issue-store.md);
this section only covers how to turn it on and use it day to day.

**Publish**: `/feature-dev:spec --publish <SPEC> new|#N` (also `owner/repo#N` or an
issue URL for `#N`) skips the authoring phases and writes the spec straight into
the issue. `new` creates one; targeting `#N` re-reads it first and, on a
fingerprint mismatch (someone edited the issue since the last publish), asks
overwrite the issue / import the issue's version instead / cancel — nothing is
written silently over someone else's edit.

**Import**: `/feature-dev:explore-plan`, `/feature-dev:tdd`, `/feature-dev:spec-review`
and `/feature-dev:review` all accept an issue reference in place of a `SPEC-*.md`
path — `#N` (current repo), `owner/repo#N`, or a full issue URL. Each resolves it,
imports the marked section into a local `SPEC-<slug>.md` (creating it, or
reconciling it with an existing one via a three-way fingerprint compare), and
continues as if that path had been given directly. A closed issue asks for
confirmation first.

**Opting in**: set the plugin option `spec_store` to `issue` (in `/config`) for every project, or set `spec_store: issue` in a project's `.claude/feature-dev.local.md`, which wins over the option:

```markdown
spec_store: issue
```

Any other value, an absent key, or a missing file is treated as "not set" (local
only). With it set, `/feature-dev:spec`'s Phase 4 asks about publishing by
default — "publish to #N" if the spec already has `issue:` in its frontmatter,
otherwise "create an issue" — instead of defaulting to "keep local". A spec that
already carries `issue:` is asked about publishing even without the setting.
`.claude/feature-dev.local.md` is project config, not a generated working
artifact like `SPEC-*.md` or `.feature-dev/` — whether to gitignore it is your
call: commit it to make `spec_store: issue` a team default, or gitignore it to
keep it a per-developer preference.

**gh permissions**: the issue store calls `gh` only from command prose, never
from a script, and only these six forms:

```
gh auth status
gh repo view --json nameWithOwner*
gh issue view *
gh issue create *
gh issue edit *
gh issue comment *
```

None of these are pre-approved in this repo's [`settings.example.json`](../settings.example.json) —
`gh issue create` / `edit` / `comment` write to GitHub, and pre-approving issue
writes marketplace-wide is a bigger grant than the rest of that allowlist makes.
Add the ones you want to your own `.claude/settings.json` (or
`~/.claude/settings.json`) if you'd rather not approve each call by hand:

```json
"Bash(gh auth status)",
"Bash(gh repo view --json nameWithOwner*)",
"Bash(gh issue view *)",
"Bash(gh issue create *)",
"Bash(gh issue edit *)",
"Bash(gh issue comment *)"
```

## Needs

- **python3** (standard library only) for `scripts/review_server.py` and `scripts/issue_spec.py`: the review page, artifact listing and cleanup.
- **A browser** on the same machine for `/feature-dev:review`. Over SSH, `review_server.py url <artifact>` prints the URL to open with a port forward.
- **`gh`**, authenticated, only for the GitHub Issue Store and for `cleanup`'s rescue to a PR comment.
- **Claude Code 2.1.287 or later** for the review band. Everything else works without it.

## Installation

```bash
/plugin install feature-dev@juanmhidalgo-plugins
```

## Evals

`feature-dev/evals/` holds a plugin eval that checks `/feature-dev:explore-plan` really fans out to its explorer subagents. The failure it guards against is silent: a plan written by one reader looks like one written by eight. See [evals/README.md](evals/README.md) for the command. It costs a full Claude run, so run it when `explore-plan` or the explorer agents change.

