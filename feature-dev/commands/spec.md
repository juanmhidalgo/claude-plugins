---
description: |
  Use before writing code when requirements are ambiguous or a feature has non-obvious scope.
  Do NOT use for simple, self-evident changes.
argument-hint: "<feature or project description>"
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
      echo "  - /feature-dev:spec-review to validate the spec for structural gaps (optional)"
      echo "  - /feature-dev:explore-plan to explore the codebase"
      echo "  - /feature-dev:tdd to start test-driven implementation"
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

You are creating a structured specification for: **$ARGUMENTS**

Follow the gated workflow. Each phase requires user review before advancing.

### Phase 1: Specify

1. **Detect multi-repo scope** (runs silently — feeds into step 2). A feature is multi-repo only when the description clearly spans concerns owned by different repos (e.g., "API + UI", "service + worker"). Confirm that first, then corroborate with at least one infrastructure signal:

   - **Signal A (required)**: the feature description spans concerns owned by different repos.
   - **Signal B**: `additionalDirectories` (Context block above) lists sibling repos as accessible.
   - **Signal C**: `../CLAUDE.md` exists and catalogs sibling repos with their purpose — read it to learn the repo set.

   Treat as multi-repo only when **A AND (B OR C)** hold. `additionalDirectories` alone is a false positive (users grant access for reference, not feature scope). If only one repo is in scope, skip the multi-repo sections (frontmatter `repos:`, "Cross-Repo Contracts", repo task tags) for the rest of this phase.

2. **Surface assumptions.** List 3-5 assumptions you're making about the tech stack, architecture, and scope. For multi-repo features, include the inferred repo set as one of the assumptions (e.g., "Scope: <backend-name> + <frontend-name>"). Ask the user to confirm or correct — single round-trip.

3. **Reframe vague requirements.** If the input is vague, translate it into concrete, testable success criteria. Present these to the user for validation.

4. **Write the spec** covering these six areas:
   - **Objective**: What we're building, why, who it's for, what success looks like
   - **Commands**: Full executable commands (build, test, lint, dev). For multi-repo features, group commands per repo.
   - **Project Structure**: Where code, tests, and docs live (explore each in-scope repo first). For multi-repo features, render one subsection per repo.
   - **Code Style**: One real snippet from each in-scope repo showing conventions
   - **Testing Strategy**: Framework, test location, coverage expectations (per repo when multi-repo)
   - **Boundaries**: Always do / Ask first / Never do

   **Multi-repo features only** add a seventh section between Boundaries and tasks:
   - **Cross-Repo Contracts**: Endpoint(s), request/response shape, error codes, breaking-change flag, versioning notes. This is the artifact every in-scope repo commits to and the anchor for coordination.

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

7. **Present to user** for review. Do NOT proceed until they approve.

### Phase 2: Plan

With the approved spec, append an **Implementation Plan** section to the SPEC file (after Boundaries, or after Cross-Repo Contracts when multi-repo). It must cover:

1. Major components and their dependencies
2. Implementation order
3. Risks and mitigations
4. Verification checkpoints

This is a high-level outline only — the codebase-aware, file-level plan lives in `PLAN-<slug>.md` produced by `/feature-dev:explore-plan` downstream. Save the updated SPEC and present the new section for review.

### Phase 3: Tasks

Break the plan into discrete tasks:
- Each completable in one session
- Explicit acceptance criteria
- Verification step (test command, build, manual check)
- Ordered by dependency
- No task changes more than ~5 files

```markdown
- [ ] Task: [Description]
  - Accept: [What must be true]
  - Verify: [How to confirm]
  - Files: [Which files]
```

**Multi-repo features**: tag every task with the owning repo and order tasks so contract-owning repo tasks land before contract-consuming repo tasks (otherwise the consumer has nothing real to integrate against):

```markdown
- [ ] Task: [Description]
  - Repo: [name from frontmatter `repos:`]
  - Accept: [What must be true]
  - Verify: [How to confirm]
  - Files: [Which files, paths relative to that repo]
```

Add tasks to the spec file. Present for review.

### Phase 4: Handoff

After all phases are approved:
- The `SPEC-<slug>.md` file is a **local working artifact**, not a repo deliverable. Do NOT commit it, and do NOT run any git commands. Downstream commands read it directly from the working tree.
- Confirm the spec's frontmatter `status:` is `approved` (it will be flipped to `implemented` automatically when `/feature-dev:tdd` finishes).
- Stop here. The Stop hook will surface the next-step options (`/feature-dev:spec-review`, `/feature-dev:explore-plan`, or `/feature-dev:tdd`) — let the user choose.

## Rules

- **Never skip assumption surfacing.** Silent assumptions are the most dangerous form of misunderstanding.
- **Never advance phases without user approval.** Each gate exists to catch misalignment early.
- **Reframe, don't accept vagueness.** Convert "make it better" into measurable criteria.
- **The spec is a living document.** Update it when decisions change, don't abandon it.
- **Multi-repo: declare scope explicitly in frontmatter.** The `additionalDirectories` setting grants access; the spec's `repos:` block declares intent. It is the canonical record of which repos are in scope — future downstream tooling will read it rather than re-inferring from settings.
- **Multi-repo: write the contract before the tasks.** The Cross-Repo Contracts section is the coordination anchor — both sides build against it. Skipping it lets the two repos drift.
