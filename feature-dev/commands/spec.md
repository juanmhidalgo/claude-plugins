---
description: |
  Use before writing code when requirements are ambiguous or a feature has non-obvious scope.
  Do NOT use for simple, self-evident changes.
argument-hint: "<feature or project description> [--with-tasks]"
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
  - Agent
hooks:
  - event: Stop
    once: true
    command: |
      echo "Spec complete. Next steps:"
      echo "  - /feature-dev:spec-review to check the spec for gaps and its claims against the code (optional)"
      echo "  - /feature-dev:explore-plan to explore the codebase and write the step-level plan"
      echo "  - /feature-dev:tdd SPEC-<slug>.md to implement straight from the spec (it auto-discovers only PLAN files; without one it derives criteria from the spec's tasks or AC ids)"
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this command and proceed with your assigned task.
</SUBAGENT-STOP>

## Context

- **Branch**: !`git branch --show-current`
- **Recent commits**: !`git log --oneline -5`
- **Additional directories**: !`jq -r '.permissions.additionalDirectories[]? // empty' .claude/settings.local.json 2>/dev/null || true`
- **Parent context file**: !`test -f ../CLAUDE.md && echo "../CLAUDE.md exists (read for repo catalog)" || echo "no ../CLAUDE.md"`

<best_practices>
@feature-dev/skills/spec-driven-development/SKILL.md
</best_practices>

> **Recommended:** run in plan mode (`Shift+Tab` to toggle) so you can review the spec before any files are written.

## Spec-Driven Development Workflow

**First, strip flags from `$ARGUMENTS`.** `--with-tasks` turns on the optional Plan and Tasks phases below. Remove it before anything else reads `$ARGUMENTS` — what remains is the feature description. Record whether it was passed.

You are creating a structured specification for the feature description left after stripping flags: **$ARGUMENTS**

By default this command ends at the spec: Phase 1, then Handoff. The step-level plan is `/feature-dev:explore-plan`'s job, and a spec that also carries its own plan and task list ends up holding a second plan that explore-plan re-derives with different numbering. With `--with-tasks` (for when explore-plan will not be run), Phases 2 and 3 run between Specify and Handoff.

Each phase that runs requires user approval before advancing.

### Phase 1: Specify

1. **Detect multi-repo scope** (runs silently — feeds into step 2). A feature is multi-repo only when the description clearly spans concerns owned by different repos (e.g., "API + UI", "service + worker"). Confirm that first, then corroborate with at least one infrastructure signal:

   - **Signal A (required)**: the feature description spans concerns owned by different repos.
   - **Signal B**: `additionalDirectories` (Context block above) lists sibling repos as accessible.
   - **Signal C**: `../CLAUDE.md` exists and catalogs sibling repos with their purpose — read it to learn the repo set.

   Treat as multi-repo only when **A AND (B OR C)** hold. `additionalDirectories` alone is a false positive (users grant access for reference, not feature scope). If only one repo is in scope, skip the multi-repo sections (frontmatter `repos:`, "Cross-Repo Contracts", repo task tags) for the rest of this command.

2. **Surface assumptions.** List 3-5 assumptions you're making about the tech stack, architecture, and scope. For multi-repo features, include the inferred repo set as one of the assumptions (e.g., "Scope: <backend-name> + <frontend-name>"). Ask the user to confirm or correct — single round-trip.

3. **Reframe vague requirements.** If the input is vague, translate it into concrete, testable success criteria. Present these to the user for validation.

4. **Write the spec** covering these eight areas:
   - **Objective**: What we're building, why, who it's for
   - **Acceptance Criteria**: A dedicated, scannable `## Acceptance Criteria` section of observable, user-facing criteria — do NOT bury these as a "what success looks like" aside inside Objective. Give each criterion a stable id: `- **AC-1** — <criterion>`. Ids are never renumbered when the spec is edited: a new criterion takes the next free number and a removed one retires its id, because plans (`Covers:`) and `/feature-dev:tdd` cite criteria by id. Include **at least one failure/error-state criterion**, not only happy-path outcomes (e.g., "a draft requisition never appears via `GET /public/jobs`", "an invalid/absent `jobId` falls back to `jobTitle` without erroring"). This is the single artifact downstream review, planning, and QA anchor to.
   - **Commands**: Full executable commands (build, test, lint, dev). For multi-repo features, group commands per repo.
   - **Project Structure**: Where code, tests, and docs live (explore each in-scope repo first). For multi-repo features, render one subsection per repo.
   - **Code Style**: One real snippet from each in-scope repo showing conventions
   - **Testing Strategy**: Framework, test location, coverage expectations (per repo when multi-repo) — the *engineering* view of what gets tested and how.
   - **QA Checklist**: A separate, QA-facing `## QA Checklist` grouped as **happy path / edge cases / error states** — a scannable list of behaviors a human verifies, distinct from the engineering-oriented Testing Strategy. Every error-state acceptance criterion should have a matching check here.
   - **Boundaries**: Always do / Ask first / Never do

   **Multi-repo features only** add one more section after Boundaries:
   - **Cross-Repo Contracts**: Endpoint(s), request/response shape, error codes, breaking-change flag, versioning notes. This is the artifact every in-scope repo commits to and the anchor for coordination. It belongs to the spec, so it is written with or without `--with-tasks`.

5. **Save the spec** to `SPEC-<feature-slug>.md` in the project root. The file MUST begin with this frontmatter block (one single block — merge the optional `repos:` lines inside the `---` delimiters when multi-repo):

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

   Update `status:` to `approved` after the user validates the spec in step 7.

6. **Update `.gitignore`.** If the project's `.gitignore` does not already include `SPEC-*.md`, add it. The spec is a local working artifact, not a repo deliverable — this prevents accidental commits via `git add .`. (Mirrors the same step performed by `/feature-dev:explore-plan` for `PLAN-*.md`.)

7. **Present the review brief** (below) — not the spec itself. Do NOT proceed until the user approves.

### Review brief

Every approval gate in this command ends with this block instead of re-printing the spec. Users answer from the chat, not from the file: a several-hundred-line spec pasted back buries the few decisions they actually need to rule on. Keep it to ~15 lines, number items continuously across groups so the user can answer "2: no, 5: ok", and omit a group that would be empty. Give the path; show full content only when asked.

```markdown
### Review brief — SPEC-<slug>.md (<line count> lines)
**Decided** (review if you disagree)
1. <a choice the spec makes that the user did not state — scope cut, contract shape, error behavior>
**Assumed — confirm**
2. <an assumption from step 2 that the user has not confirmed, or one added while writing>
**Unverified claims about the code**
3. `<Model.field>` is nullable — not checked
**Out of scope**
- <the Never-do / out-of-scope items, one line each>
Reply with the numbers you want changed, or "approved".
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
- The `SPEC-<slug>.md` file is a **local working artifact**, not a repo deliverable. Do NOT commit it, and do NOT run any git commands. Downstream commands read it directly from the working tree.
- Confirm the spec's frontmatter `status:` is `approved` (it will be flipped to `implemented` automatically when `/feature-dev:tdd` finishes).
- Stop here. The Stop hook will surface the next-step options (`/feature-dev:spec-review`, `/feature-dev:explore-plan`, or `/feature-dev:tdd`) — let the user choose.

## Rules

- **Never skip assumption surfacing.** Silent assumptions are the most dangerous form of misunderstanding.
- **Never advance phases without user approval.** Each gate exists to catch misalignment early.
- **Stop at the spec unless `--with-tasks` was passed.** Without the flag, no Implementation Plan or Tasks section is written — explore-plan produces the plan from the code, and a second plan in the spec only diverges from it.
- **End each gate with the review brief, not the artifact.** The brief is what the user actually reads before approving; its "Unverified claims" group is where a wrong assumption about the code gets caught before it becomes an AC.
- **Reframe, don't accept vagueness.** Convert "make it better" into measurable criteria.
- **The spec is a living document.** Update it when decisions change, don't abandon it. Keep AC ids stable across edits.
- **Multi-repo: declare scope explicitly in frontmatter.** The `additionalDirectories` setting grants access; the spec's `repos:` block declares intent. It is the canonical record of which repos are in scope — future downstream tooling will read it rather than re-inferring from settings.
- **Multi-repo: write the contract in the spec.** The Cross-Repo Contracts section is the coordination anchor — both sides build against it, and with `--with-tasks` it is written before the tasks. Skipping it lets the two repos drift.
