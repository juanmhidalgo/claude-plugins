# Spec template

The one definition of what a `SPEC-<slug>.md` contains. `/feature-dev:spec`
writes from it, the `spec-driven-development` skill explains why it is shaped
this way, and `spec-plan-validator` checks against it. Change the shape here;
the others point at this file.

A spec says **what** gets built and **why**, in the domain's language. **How**
it gets built — commands, file layout, code conventions, test strategy,
implementation order — is the plan's job: `/feature-dev:explore-plan` derives it
from the code (Exploration Findings, Baseline, Implementation Order). A spec that
names a method or a file path in a rule or a criterion has slipped into the plan.

## Frontmatter

```markdown
---
type: specification
feature: [Human-readable Feature Name]
slug: [feature-slug]
date: [YYYY-MM-DD]
branch: [current branch]
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

One single block. The feature's state (draft, approved, …) lives in
`feature.json`, written only by `features.py`, never in the frontmatter.

## Sections, in this order

### `## Objective`

What we're building, why, and who it is for. A few sentences.

### `## Non-Goals`

What the scope answer ruled out, one line each with why. It feeds the review
brief's "Out of scope" group, and it is what a scope change after approval has
to argue against.

### `## Business Rules`

The domain rules the feature must uphold, each a declarative statement with a
stable id:

```markdown
- **BR-1** — A task is overdue when it is open and its due date is before today.
- **BR-2** — A done task is never overdue, whatever its due date.
```

- **Domain language only.** No method names, endpoints, tables or UI widgets: a
  rule holds whichever code path reaches the data — the API, the admin, a bulk
  import, a background job.
- **A rule is not a criterion.** A rule states what is always true; an
  acceptance criterion is one example that exercises it. "Done tasks are never
  overdue" is a rule; "the overdue list shows the open task and not the done
  one" is a criterion.
- **Not Boundaries.** Boundaries constrain how the work is done ("don't change
  the `status` values"); rules constrain the domain ("a cancelled booking frees
  its slot").
- **Optional in substance, not in form.** A feature with no domain logic (a UI
  tweak, an infra change) writes `None — <why>` on one line, so a reader can
  tell "no rules" from "forgot the rules".
- Ids follow the AC id policy below.

### `## Acceptance Criteria`

Observable, user-facing criteria, each with a stable id and the rules it
exercises:

```markdown
- **AC-1** (BR-1, BR-2) — Given an open task and a done task, both due yesterday,
  when the user lists overdue tasks, then only the open one appears.
- **AC-2** — An invalid due date is rejected with a message naming the field.
```

- **Ids are stable.** Never renumber on edit: a new criterion takes the next free
  number and a removed one retires its id. Plans (`Covers:`), `/feature-dev:tdd`
  and the plan review cite criteria by id. The same holds for `BR-n`.
- **Cite the rules** a criterion exercises in parentheses after its id. Every
  rule is cited by at least one criterion, and a rule that forbids something
  (never, only, cannot) has a criterion showing the forbidden case.
- **Given / when / then on one line** for a criterion that depends on a prior
  state. A criterion with no precondition stays a plain sentence. Write the
  steps declaratively ("when the recruiter publishes the job"), not as UI
  actions ("when I click Save").
- At least one **failure or error-state** criterion, not only happy paths.
- No unmeasured adjectives (fast, easy, intuitive, …): see the skill's
  "Reframe vague requirements".

### `## QA Checklist`

QA-facing, four groups, each a list of `- [ ]` items, one behavior a human
verifies per item:

```markdown
### Happy path
### Edge cases
### Empty states
### Error states
```

The user ticks an item (`- [x]`) as they verify it; `/feature-dev:cleanup`
rescues the unticked ones. Every error-state criterion gets a matching item
under Error states. Empty states are what each view, list or response shows
when there is nothing to show: no records yet, a filter that matches nothing,
a first-time user, an absent optional relation. Give each one an item, and an
AC when its wording or behavior is decided here (copy, call to action, `[]` vs
`404`).

### `## Boundaries`

Always do / Ask first / Never do, each Never-do item with a one-line rationale.

### `## Cross-Repo Contracts` — multi-repo only

Endpoint(s), request/response shape, error codes, breaking-change flag,
versioning notes. Every in-scope repo builds against it.

### `## Decisions Log` — multi-repo always; otherwise added during implementation

Decisions taken after the spec was approved. Entry format and what qualifies:
the skill's "Decisions Log" section.

## Where architectural decisions go

When the spec itself commits to an architectural choice (a new pattern, data
store, integration), record its **Consequences** next to the decision, in the
section that makes it: Easier / Harder / Revisit when. Format in the skill's
"Consequences" section.

## Specs written before 3.0.0

They may carry `## Commands`, `## Project Structure`, `## Code Style`,
`## Testing Strategy`, and, from `--with-tasks`, `## Implementation Plan` and a
Tasks list, and they have no `## Business Rules`. They stay valid: downstream
commands read what is there, and editing one does not require migrating it.
