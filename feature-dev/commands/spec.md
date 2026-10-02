---
description: |
  Use before writing code when requirements are ambiguous or a feature has non-obvious scope.
  Do NOT use for simple, self-evident changes.
argument-hint: "<feature or project description> [--with-tasks] | --publish <SPEC> new|#N|owner/repo#N|URL"
model: opus
keywords:
  - spec
  - specification
  - requirements
  - planning
triggers:
  - "write a spec"
  - "create specification"
  - "define requirements first"
  - "spec-driven development"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - Edit
  - Agent
  - AskUserQuestion
  - Bash(gh auth status)
  - Bash(gh repo view --json nameWithOwner*)
  - Bash(gh issue view *)
  - Bash(gh issue create *)
  - Bash(gh issue edit *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/issue_spec.py *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py snapshot *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py artifacts *)
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this command and proceed with your assigned task.
</SUBAGENT-STOP>

## Context

- **Branch**: !`git branch --show-current`
- **Recent commits**: !`git log --oneline -5`
- **Additional directories**: !`jq -r '.permissions.additionalDirectories[]? // empty' .claude/settings.local.json 2>/dev/null || true`
- **Parent context file**: !`test -f ../CLAUDE.md && echo "../CLAUDE.md exists (read for repo catalog)" || echo "no ../CLAUDE.md"`
- **Artifacts folder**: `${user_config.artifacts_dir}` (a literal `${user_config...}` here means `.feature-dev`). Where specs are written and found: [artifact-locations.md](../skills/spec-driven-development/references/artifact-locations.md).
- **Spec store option**: `${user_config.spec_store}` (a literal `${user_config...}` here means `file`).

<best_practices>
@feature-dev/skills/spec-driven-development/SKILL.md
</best_practices>

> **Recommended:** run in plan mode (`Shift+Tab` to toggle) so you can review the spec before any files are written.

## Spec-Driven Development Workflow

**First, check for `--publish <SPEC> <target>`.** If `$ARGUMENTS` starts with `--publish`, strip `--publish <SPEC> <target>` from `$ARGUMENTS` before anything else parses it, then go straight to [Publish Mode](#publish-mode) below — it skips the authoring phases (Specify, Plan, Tasks, Handoff) entirely and never reads the rest of `$ARGUMENTS` as a feature description. Otherwise, continue below.

**Then strip the remaining flags from `$ARGUMENTS`.** `--with-tasks` turns on the optional Plan and Tasks phases below. Remove it before anything else reads `$ARGUMENTS` — what remains is the feature description. Record whether it was passed.

You are creating a structured specification for the feature description left after stripping flags: **$ARGUMENTS**

By default this command ends at the spec: Phase 1, then Handoff. The step-level plan is `/feature-dev:explore-plan`'s job, and a spec that also carries its own plan and task list ends up holding a second plan that explore-plan re-derives with different numbering. With `--with-tasks` (for when explore-plan will not be run), Phases 2 and 3 run between Specify and Handoff.

Each phase that runs requires user approval before advancing.

### Phase 1: Specify

1. **Detect multi-repo scope** (runs silently — feeds the recommendation in step 2). A feature is multi-repo only when the description clearly spans concerns owned by different repos (e.g., "API + UI", "service + worker"). Confirm that first, then corroborate with at least one infrastructure signal:

   - **Signal A (required)**: the feature description spans concerns owned by different repos.
   - **Signal B**: `additionalDirectories` (Context block above) lists sibling repos as accessible.
   - **Signal C**: `../CLAUDE.md` exists and catalogs sibling repos with their purpose — read it to learn the repo set.

   Recommend multi-repo only when **A AND (B OR C)** hold. `additionalDirectories` alone is a false positive (users grant access for reference, not feature scope). Detection only shapes the recommended option in step 2; the scope answer decides. If the answer names two or more repos, the multi-repo sections (frontmatter `repos:`, "Cross-Repo Contracts", repo task tags) are in for the rest of this command, whatever detection concluded; if it leaves one repo in, they are out.

2. **Ask the scope question — first, and on its own.** Before surfacing assumptions and before reading any code, ask one AskUserQuestion with a single question: which repos and components are in, and what is explicitly out. Offer a recommended option inferred from the description and step 1 (e.g. "<backend-name> API + <frontend-name> page; out: admin UI, other tenants") and one or two real alternatives — a narrower and a wider cut. Record what the answer rules out: it becomes the spec's `## Non-Goals`.

   Scope goes first because everything after it is sized by it: a scope change after approval (a backend endpoint added, "not tied to one customer") has meant re-planning. It goes alone because a scope question bundled with other questions gets answered last — one sat unanswered for almost 7 hours.

3. **Surface assumptions.** Now list 3-5 assumptions about the tech stack, architecture, and behavior within the agreed scope. Ask the user to confirm or correct — its own round-trip, after the scope answer.

4. **Reframe vague requirements.** If the input is vague, translate it into concrete, testable success criteria. Present these to the user for validation.

5. **Write the spec** covering these nine areas:
   - **Objective**: What we're building, why, who it's for
   - **Non-Goals**: A `## Non-Goals` section right after Objective — what the scope answer ruled out, one line each with why. It feeds the brief's "Out of scope" group, and it is what a scope change after approval has to argue against.
   - **Acceptance Criteria**: A dedicated, scannable `## Acceptance Criteria` section of observable, user-facing criteria — do NOT bury these as a "what success looks like" aside inside Objective. Give each criterion a stable id: `- **AC-1** — <criterion>`. Ids are never renumbered when the spec is edited: a new criterion takes the next free number and a removed one retires its id, because plans (`Covers:`) and `/feature-dev:tdd` cite criteria by id. Include **at least one failure/error-state criterion**, not only happy-path outcomes (e.g., "a draft requisition never appears via `GET /public/jobs`", "an invalid/absent `jobId` falls back to `jobTitle` without erroring"). This is the single artifact downstream review, planning, and QA anchor to.
   - **Commands**: Full executable commands (build, test, lint, dev). For multi-repo features, group commands per repo.
   - **Project Structure**: Where code, tests, and docs live (explore each in-scope repo first). For multi-repo features, render one subsection per repo.
   - **Code Style**: One real snippet from each in-scope repo showing conventions
   - **Testing Strategy**: Framework, test location, coverage expectations (per repo when multi-repo) — the *engineering* view of what gets tested and how.
   - **QA Checklist**: A separate, QA-facing `## QA Checklist` with four groups — `### Happy path`, `### Edge cases`, `### Empty states`, `### Error states` — each a list of `- [ ]` items, one behavior a human verifies per item. The user ticks an item (`- [x]`) as they verify it, which is how `/feature-dev:cleanup` later tells verified checks from ones nobody ran. Distinct from the engineering-oriented Testing Strategy. Every error-state acceptance criterion should have a matching item under Error states. Empty states are what each view, list or response shows when there is nothing to show: no records yet, a filter or search that matches nothing, a first-time user, an optional relation that is absent. Give each one an item, and an AC when its wording or behavior is decided here (copy, call to action, `[]` vs `404`).
   - **Boundaries**: Always do / Ask first / Never do

   **Multi-repo features only** add one more section after Boundaries:
   - **Cross-Repo Contracts**: Endpoint(s), request/response shape, error codes, breaking-change flag, versioning notes. This is the artifact every in-scope repo commits to and the anchor for coordination. It belongs to the spec, so it is written with or without `--with-tasks`.

6. **Save the spec** to the path `${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py artifacts --dir "<artifacts folder>" --new SPEC-<feature-slug>.md` prints (`<folder>/specs/SPEC-<feature-slug>.md`); this is the **spec path** used below. If you are revising a spec that `artifacts` lists at the project root (written before 1.32.0), keep it there and edit it in place. If that file already exists, first copy it to `.feature-dev/history/<dir>/SPEC-<feature-slug>.<n>.md`, where n is one more than the highest n already there (1 if none): Read it, then Write the copy. `<dir>` is the slug as `review_server.py` sanitizes it — the frontmatter `slug:` with every run of characters outside `A-Za-z0-9._-` replaced by `-`, leading and trailing `-`/`.` stripped, and `artifact` if nothing is left — so a slug with a space or a `/` still lands in the folder `/feature-dev:review` diffs against and `/feature-dev:cleanup` groups by. Do the same once per review round before editing a spec the user has already seen. `/feature-dev:review` diffs against that copy, and without it nobody can see what changed between versions. The file MUST begin with this frontmatter block (one single block — merge the optional `repos:` lines inside the `---` delimiters when multi-repo):

   ```markdown
   ---
   type: specification
   feature: [Human-readable Feature Name]
   slug: [feature-slug]
   date: [YYYY-MM-DD]
   branch: [current branch]
   status: draft  # draft | approved | implemented
   # repos: omit this block entirely for single-repo features.
   # Include for multi-repo features. Roles: owns-contract (defines the
   # API/data shape) | consumes-contract (depends on it). Paths are
   # relative to this spec's repo.
   repos:
     - name: backend
       path: .
       role: owns-contract
     - name: frontend
       path: ../my-frontend-app
       role: consumes-contract
   ---
   ```

   Update `status:` to `approved` after the user validates the spec in step 8.

7. **Update `.gitignore`.** If the project's `.gitignore` does not already include `.feature-dev/` (review files, version history, and the default specs and plans folder), add it; if the artifacts folder is not under `.feature-dev/`, add that folder too. Keep an existing `SPEC-*.md` line: it still covers specs written at the root before 1.32.0. The spec is a local working artifact, not a repo deliverable — this prevents accidental commits via `git add .`. (Mirrors the same step performed by `/feature-dev:explore-plan` for `PLAN-*.md`.)

8. **Present the review brief** (below) — not the spec itself. Do NOT proceed until the user approves.

### Review brief

Every approval gate in this command ends with this block instead of re-printing the spec. Users answer from the chat, not from the file: a several-hundred-line spec pasted back buries the few decisions they actually need to rule on. Keep it to ~15 lines, number items continuously across groups so the user can answer "2: no, 5: ok", and omit a group that would be empty. Give the path; show full content only when asked.

```markdown
### Review brief — SPEC-<slug>.md (<line count> lines)
**Decided** (review if you disagree)
1. <a choice the spec makes that the user did not state — scope cut, contract shape, error behavior>
**Assumed — confirm**
2. <an assumption from step 3 that the user has not confirmed, or one added while writing>
**Unverified claims about the code**
3. `<Model.field>` is nullable — not checked
**Out of scope**
- <each `## Non-Goals` item, one line>
Reply with the numbers you want changed, or "approved".
Or review it in the browser: /feature-dev:review <spec path>
```

"Unverified claims about the code" lists the facts about existing code the spec relies on — paths, symbols, field nullability, FK direction, endpoint paths, migration numbers, config keys — that you did not open the file to confirm. Say "not checked" rather than guessing; `/feature-dev:spec-review` checks them against the code.

For Phases 2 and 3, the brief covers only what that phase added (its decisions, assumptions and unverified claims), with the same header.

### Phase 2: Plan (only with `--with-tasks`)

With the approved spec, append an **Implementation Plan** section to the SPEC file (after Boundaries, or after Cross-Repo Contracts when multi-repo). It must cover:

1. Major components and their dependencies
2. Implementation order
3. Risks and mitigations
4. Verification checkpoints

This is a high-level outline only — the codebase-aware, file-level plan lives in `PLAN-<slug>.md` produced by `/feature-dev:explore-plan`. Save the updated SPEC and end with the review brief.

### Phase 3: Tasks (only with `--with-tasks`)

Break the plan into discrete tasks:
- Each completable in one session
- Explicit acceptance criteria, citing the AC ids they satisfy
- Verification step (test command, build, manual check)
- Ordered by dependency
- No task changes more than ~5 files

```markdown
- [ ] Task: [Description]
  - Accept: [What must be true]
  - Covers: [AC ids, e.g. AC-2, AC-4]
  - Verify: [How to confirm]
  - Files: [Which files]
```

**Multi-repo features**: tag every task with the owning repo and order tasks so contract-owning repo tasks land before contract-consuming repo tasks (otherwise the consumer has nothing real to integrate against):

```markdown
- [ ] Task: [Description]
  - Repo: [name from frontmatter `repos:`]
  - Accept: [What must be true]
  - Covers: [AC ids]
  - Verify: [How to confirm]
  - Files: [Which files, paths relative to that repo]
```

Add tasks to the spec file and end with the review brief.

### Phase 4: Handoff

After every phase that ran is approved:
- The spec file is a **local working artifact**, not a repo deliverable. Do NOT commit it, and do NOT run any git commands. Downstream commands read it directly from the working tree.
- Confirm the spec's frontmatter `status:` is `approved` (it will be flipped to `implemented` automatically when `/feature-dev:tdd` finishes).
- **Ask about publishing — once, gated, right here.** Read `.claude/feature-dev.local.md` (Read tool; a missing file is simply absent, no fallback value). This is the only place this question is asked: never on edits or review rounds — not when the user asks you to change something in an already-approved spec, and not at the end of any Phase 1/2/3 review brief. Phase 4 runs once, after the last phase that ran is approved, so asking only here already satisfies that.
  - **The store setting**: `spec_store` in `.claude/feature-dev.local.md` when that file sets it (project setting, wins); otherwise the **Spec store option** in Context. `issue` is the only value that means "issue"; anything else, or nothing set anywhere, is `file`.
  - **Skip silently, changing nothing else in Handoff,** unless the store setting is `issue` or the spec's own frontmatter already has `issue:`. Either condition alone is enough to ask.
  - Otherwise ask one AskUserQuestion with the options "keep local", "publish to #N" (target `#N`; offered only when the spec's frontmatter already has `issue:`), and "create an issue" (target `new`).
  - **Default**: default when the store setting is `issue` is the publishing option — "publish to #N" if the spec already has `issue:`, otherwise "create an issue" (there is no `#N` yet to publish to). When the question was asked only because the spec already has `issue:` (store setting `file`), default to "keep local".
  - "Publish to #N" or "create an issue" runs [Publish Mode](#publish-mode) against this spec path and the chosen target (`#N` or `new`), start to finish, then continues below with its result. "Keep local" changes nothing and continues below immediately.
- End with the next command, using the spec path you just wrote, then stop and let the user choose:

  ```
  Next: /feature-dev:spec-review <spec path> (optional) or /feature-dev:explore-plan <spec path>
  ```

  Recommend explore-plan: it writes a reviewed step-level plan from the code. `/feature-dev:tdd <spec path>` (straight from the spec's ACs, or its Tasks with `--with-tasks`) is the fallback for a small feature, so mention it only when the spec is small enough that a plan adds nothing.

## Publish Mode

Entered only when `$ARGUMENTS` started with `--publish <SPEC> <target>` (parsed and stripped above). This mode skips the authoring phases: it never asks the scope question, never surfaces assumptions, never writes Specify/Plan/Tasks content, and never presents a review brief.

1. Resolve `<target>` (`new`, `#N`, `owner/repo#N`, or an issue URL) per [issue-store.md's Argument parsing](../skills/spec-driven-development/references/issue-store.md#argument-parsing).
2. Run [issue-store.md's Publish algorithm](../skills/spec-driven-development/references/issue-store.md#publish-ac-1-ac-2-ac-3-ac-4-ac-5-ac-7) against `<SPEC>` and the resolved target, start to finish, including its `gh` preflight, its scratch-file handling, and its fingerprint verification. Do not restate those steps here — follow the reference.
3. If the reference's mismatch branch (its step 3, target `#N`) offers "import the issue's version instead," and the user picks it, run [issue-store.md's Import algorithm](../skills/spec-driven-development/references/issue-store.md#import-ac-8-ac-9-ac-10-ac-11-ac-12) against that issue, start to finish, then stop — this invocation does not also publish. Do not restate Import's steps here — follow the reference.
4. A failed `gh` preflight or a failed verification (the reference's steps 1 and 6) leaves the local spec untouched and reports that nothing was published.
5. On a verified publish, report the issue URL from the reference's step 7 and stop.

## Rules

- **Never skip the scope question or assumption surfacing, and never merge them.** Silent assumptions are the most dangerous form of misunderstanding, and scope is the one that re-plans everything downstream when it moves.
- **Never advance phases without user approval.** Each gate exists to catch misalignment early.
- **Stop at the spec unless `--with-tasks` was passed.** Without the flag, no Implementation Plan or Tasks section is written — explore-plan produces the plan from the code, and a second plan in the spec only diverges from it.
- **End each gate with the review brief, not the artifact.** The brief is what the user actually reads before approving; its "Unverified claims" group is where a wrong assumption about the code gets caught before it becomes an AC.
- **Reframe, don't accept vagueness.** Convert "make it better" into measurable criteria.
- **The spec is a living document.** Update it when decisions change, don't abandon it. Keep AC ids stable across edits.
- **Multi-repo: declare scope explicitly in frontmatter.** The `additionalDirectories` setting grants access; the spec's `repos:` block declares intent. It is the canonical record of which repos are in scope — future downstream tooling will read it rather than re-inferring from settings.
- **Multi-repo: write the contract in the spec.** The Cross-Repo Contracts section is the coordination anchor — both sides build against it, and with `--with-tasks` it is written before the tasks. Skipping it lets the two repos drift.
