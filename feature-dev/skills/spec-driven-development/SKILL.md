---
name: spec-driven-development
description: |
  Use when starting a new feature or significant change with no spec yet. Covers single-repo and multi-repo features.
  Do NOT use for typos, single-line fixes, or post-hoc documentation of finished work.
keywords:
  - spec
  - specification
  - requirements
  - planning
  - acceptance-criteria
triggers:
  - "write a spec"
  - "define requirements"
  - "what should we build"
  - "create a specification"
  - "spec-driven"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
---

# Spec-Driven Development

## When to Use

- Starting a new feature or project
- Requirements are ambiguous or incomplete
- Change touches multiple files or modules
- Task would take more than 30 minutes to implement
- About to make an architectural decision

## The Gated Workflow

Four phases. Do not advance until the current phase is validated by the user.

```
SPECIFY ──→ PLAN ──→ TASKS ──→ IMPLEMENT
   │          │        │          │
   ▼          ▼        ▼          ▼
 Review     Review   Review    Review
```

### Phase 1: Specify

Surface assumptions immediately before writing anything:

```
ASSUMPTIONS I'M MAKING:
1. This is a web application (not native mobile)
2. Authentication uses session-based cookies
3. The database is PostgreSQL
→ Correct me now or I'll proceed with these.
```

Write a spec covering six areas:
1. **Objective** — What, why, who, and what success looks like
2. **Commands** — Full executable commands (build, test, lint, dev)
3. **Project Structure** — Where source, tests, and docs live
4. **Code Style** — One real snippet showing conventions
5. **Testing Strategy** — Framework, location, coverage, test levels
6. **Boundaries** — Always do / Ask first / Never do

Reframe vague requirements as testable success criteria. Ban these words from acceptance criteria unless you immediately define them concretely: **fast**, **slow**, **easy**, **simple**, **user-friendly**, **intuitive**, **seamless**, **better**, **improved**.

```
"Make the dashboard faster"
→ LCP < 2.5s on 4G, initial data load < 500ms, CLS < 0.1
→ Are these the right targets?

"Make onboarding intuitive"
→ ≥80% of new users complete the first three steps without help-text dwell > 3s
→ Or: define what "intuitive" means here in plain language.
```

If you cannot define it, you cannot test it. Push back on the user rather than ship a vague criterion.

### Phase 2: Plan

With validated spec, generate a technical plan:
- Major components and dependencies
- Implementation order
- Risks and mitigations
- What can parallelize vs. must be sequential
- Verification checkpoints between phases

### Phase 3: Tasks

Break into discrete, implementable tasks:
- Completable in one focused session
- Explicit acceptance criteria and verification step
- Ordered by dependency, not importance
- No task changes more than ~5 files

```markdown
- [ ] Task: [Description]
  - Accept: [What must be true]
  - Verify: [Test command or check]
  - Files: [Which files]
```

### Phase 4: Implement

Execute tasks using the **`feature-dev:tdd-patterns`** skill (RED-GREEN-REFACTOR cycle, 5-cycle iteration limit, stuck-after-3 rule, coverage gate workflow). One task at a time, verify before advancing. Do not duplicate the cycle's rules here — `tdd-patterns` is the canonical reference.

## Multi-Repo Features

A feature is multi-repo when a single change must land in two or more repositories to be useful (e.g., backend exposes a new field, frontend renders it). Detect this in Phase 1 using **description intent plus at least one infrastructure signal**:

- **A (required)**: The feature description spans concerns owned by different repos ("API + UI", "service + worker").
- **B**: `additionalDirectories` in `.claude/settings.local.json` lists sibling repos as accessible.
- **C**: A parent `CLAUDE.md` (one level up from cwd) catalogs sibling repos with their purpose.

Trigger multi-repo mode only when **A AND (B OR C)**. `additionalDirectories` alone is a false positive — sibling access is often granted for reference, not feature scope.

When detected, the spec gains:

- A `repos:` block in frontmatter listing each in-scope repo with `name`, `path` (relative to spec's repo), and `role` (`owns-contract` | `consumes-contract`).
- A **Cross-Repo Contracts** section: endpoint(s), request/response shape, error codes, breaking-change flag. This is the artifact every repo commits to.
- Per-repo subsections under Commands, Project Structure, Code Style, and Testing Strategy.
- Tasks tagged with `Repo:` and ordered so contract-owners ship before consumers.

Single-repo features omit all of the above — no behavior change.

## Decision Rules

Operational tests, not definitions. Apply them in real time when writing a spec or pushing back on stakeholders.

### Scope and priority

- **P0 cut-test**: If we removed this requirement, would the feature still solve the core problem? If no, P0. If yes, P1 or lower.
- **If everything is P0, nothing is P0.** A P0 list with more than ~5 items is almost always wrong. Challenge each: "Would we really not ship without this?"
- **Scope-trade-only rule**: Any scope addition during implementation requires either (a) explicit scope removal or (b) a re-stated timeline. Additions without trades are how specs die.
- **Time-box investigations**: For unresolved questions, set a fixed window (e.g., 2 days). If unresolved at the deadline, cut the dependent requirement — do not let one unknown stall the whole spec.

### Open questions

- **Genuinely-open rule**: Open questions should be questions you *cannot* answer from context. Do not pad the list to look thorough — answerable items belong in assumptions, not open questions.
- **Tag each question with an owner**: who unblocks it (engineering, design, legal, data, stakeholder).
- **Mark blocking vs non-blocking**: blocking questions must resolve before implementation starts; non-blocking can resolve mid-flight.

### Future considerations

- **"Never do" is architectural insurance, not a wishlist.** Items in the Never-do boundary exist to guide *today's* design decisions — documenting them prevents you from accidentally choosing an architecture that makes them expensive later. If a Never-do item would not influence a current design choice, drop it.

## Keeping the Spec Alive

- Update when decisions or scope change
- Keep as a local working artifact; do not commit
- Reference spec sections in PRs

## Anti-Rationalizations

Catches *skipping the spec entirely*:

| Excuse | Reality |
|--------|---------|
| "This is simple, no spec needed" | Simple tasks need short specs, not no specs. Two lines is fine. |
| "I'll write the spec after coding" | That's documentation, not specification. The value is clarity before code. |
| "The spec will slow us down" | A 15-minute spec prevents hours of rework. |
| "Requirements will change anyway" | That's why it's a living document. Outdated spec > no spec. |
| "The user knows what they want" | Even clear requests have implicit assumptions. Surface them. |

## Common Spec Mistakes

Catches *writing a bad spec*. Different failure mode from skipping. Catch yourself:

| Mistake | What it looks like | Fix |
|---------|-------------------|-----|
| **Vague criteria** | "Should be fast / easy / intuitive / seamless" | Replace with measurable thresholds. If you cannot define it, you cannot test it. |
| **Solution-prescriptive stories** | "As a user, I want a dropdown menu so that..." | Describe the need, not the UI. The dropdown is one of many possible solutions. |
| **Internal-focus stories** | "As an engineer, I want to refactor the database..." | That is a task, not a user story. Move it to the Plan phase. |
| **Everything is P0** | All requirements marked must-have | Apply the cut-test to each. Real P0 lists are short. |
| **Padded open questions** | Questions you could answer yourself | Move answerable items to assumptions. Open questions are genuine unknowns. |
| **Perfunctory boundaries** | "Never do: anything not listed above" | Name 3-5 specific adjacent capabilities you will *not* build, with one-line rationale per item. |
| **Spec written post-implementation** | Spec describes what was already built | That is documentation. Write a short retrospective instead — the spec's value is alignment *before* code. |

## Verification

Before proceeding to implementation:
- [ ] Spec covers all six core areas
- [ ] User has reviewed and approved the spec
- [ ] Success criteria are specific and testable (no banned vague words without concrete definitions)
- [ ] Boundaries (Always / Ask First / Never) are defined with one-line rationale per Never-do item
- [ ] P0 list passes the cut-test (≤5 items, each truly required to solve the core problem)
- [ ] Open questions are genuinely open, owner-tagged, and marked blocking vs non-blocking
- [ ] Spec is saved as a local working artifact (`SPEC-<slug>.md`, not committed)
- [ ] **Multi-repo only**: `repos:` frontmatter, Cross-Repo Contracts section, and `Repo:` task tags are present and confirmed by user
