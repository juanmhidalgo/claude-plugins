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
  - AskUserQuestion
---

# Spec-Driven Development

## When to Use

- Starting a new feature or project
- Requirements are ambiguous or incomplete
- Change touches multiple files or modules
- Task would take more than 30 minutes to implement
- About to make an architectural decision

## The Gated Workflow

Do not advance until the current phase is validated by the user.

```
SPEC (what, why) ──→ PLAN (how, from the code) ──→ IMPLEMENT
/feature-dev:spec    /feature-dev:explore-plan     /feature-dev:tdd
      │                      │                          │
      ▼                      ▼                          ▼
    Review                 Review                     Review
```

The spec never carries a plan: commands, file layout, code conventions, test strategy and implementation order all come from `/feature-dev:explore-plan`, which reads the code. A second plan inside the spec drifts from that one. For a small feature, `/feature-dev:tdd` derives its steps straight from the spec's ACs.

Each gate ends with a short review brief (decided / assumed / unverified claims about the code / out of scope — the format is in `/feature-dev:spec`), not the whole artifact re-printed: the user approves from what they read in the chat.

### Phase 1: Specify

The first interaction is one scope question, asked alone (AskUserQuestion, a single question) before assumptions and before exploring any code: which repos and components are in, what is explicitly out, with a recommended option inferred from the description (the multi-repo detection below feeds it). Scope sizes everything after it, and a scope question bundled with others gets answered last; scope that moves after approval means a re-plan. What the answer rules out becomes the spec's `## Non-Goals`.

Then surface assumptions, in their own round-trip: one AskUserQuestion call with one question per assumption (up to 4), each a single decision with the assumption as the recommended option and a concrete alternative beside it. A single question that lists every assumption with "confirm all / correct some" makes the answer all-or-nothing, and a correction means typing which item and how. Facts about the code are checked, not asked.

```
Q "Auth"   — Sessions use the existing cookie auth?  [Yes (Recommended)] [New token per link]
Q "Expiry" — Links expire after 30 days?            [30 days (Recommended)] [Never] [Configurable]
```

Then write the spec. Its sections, their order and the id rules are defined once, in [spec-template.md](references/spec-template.md): Objective, Non-Goals, Business Rules, Acceptance Criteria, QA Checklist, Boundaries, plus Cross-Repo Contracts and Decisions Log when multi-repo.

#### Rules before criteria

Write the business rules (`BR-n`) before the acceptance criteria (`AC-n`). A rule is what is always true of the domain; a criterion is one example that exercises it, and cites it by id. The split matters downstream:

- **A rule covers paths nobody listed.** An AC is tested on one path; a rule holds on every path that reaches the data (API, admin, import, a background job), and the spec-conformance review checks the diff against each rule on all of them. Rules buried inside ACs get checked only where the AC's example happens to go.
- **Rules are what make the spec high level.** They are in the domain's language, so the spec stops naming methods and endpoints; those belong in the plan.
- **An unnamed rule is a silent assumption.** If a criterion only makes sense because of something "everyone knows" (done tasks are never overdue), that something is a rule; name it, and the user gets to disagree with it in the review brief.

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

When the spec itself commits to an architectural choice — new pattern, framework, data store, integration, or significant refactor — record its **Consequences** next to the decision in the spec. Choices the plan adds get theirs in the plan's Key Decisions.

#### Consequences

Three-way split:
- **What becomes easier** — capabilities or future work this unlocks
- **What becomes harder** — costs the team takes on
- **What we'll need to revisit later** — the conditions under which this decision should be reopened (scale threshold, new use case, contract change)

The third clause is the operational gold. Most spec/ADR templates stop at pros/cons; "revisit when" forces the decision to name the conditions that would invalidate the choice, rather than letting the decision drift into "permanent" by default.

Example:

> **Decision**: Adopt event sourcing for billing reconciliation.
> - **Easier**: Audit trail comes for free; replay-on-bug-fix is built in.
> - **Harder**: Schema migrations require event upcasters; consumers see eventual consistency.
> - **Revisit when**: Event volume exceeds 10k/sec (storage cost), or a non-billing domain wants to read the events (cross-domain coupling concern).

### Then: Plan and Implement

`/feature-dev:explore-plan` writes `PLAN-<slug>.md` from the code. Implementation executes from that plan (or, without one, `/feature-dev:tdd` derives criteria from the spec's AC ids) using the **`feature-dev:tdd-patterns`** skill (RED-GREEN-REFACTOR cycle, 5-cycle iteration limit, stuck-after-3 rule, coverage gate workflow). One task at a time, verify before advancing. Do not duplicate the cycle's rules here — `tdd-patterns` is the canonical reference.

## Multi-Repo Features

A feature is multi-repo when a single change must land in two or more repositories to be useful (e.g., backend exposes a new field, frontend renders it). Detect this in Phase 1, before the scope question it feeds, using **description intent plus at least one infrastructure signal**:

- **A (required)**: The feature description spans concerns owned by different repos ("API + UI", "service + worker").
- **B**: `additionalDirectories` in `.claude/settings.local.json` lists sibling repos as accessible.
- **C**: A parent `CLAUDE.md` (one level up from cwd) catalogs sibling repos with their purpose.

Recommend multi-repo only when **A AND (B OR C)**. `additionalDirectories` alone is a false positive — sibling access is often granted for reference, not feature scope. Detection only shapes the recommended scope option; the scope answer decides. When that answer names two or more repos, the spec gains:

- A `repos:` block in frontmatter listing each in-scope repo with `name`, `path` (relative to spec's repo), and `role` (`owns-contract` | `consumes-contract`).
- A **Cross-Repo Contracts** section: endpoint(s), request/response shape, error codes, breaking-change flag. This is the artifact every repo commits to.
- A **Decisions Log** section (see below). In a multi-repo feature this is not optional bookkeeping: each repo is implemented by a separate run, and the log is the only thing those runs share besides the contract.

Ordering the work so contract-owners ship before consumers is the plan's job.

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

### Issue Store (optional)

By default the spec stays a local, uncommitted file. A project can opt into a
GitHub-issue store instead: `spec_store: issue` in `.claude/feature-dev.local.md`
(or the plugin option `spec_store`, which the project file overrides) makes `/feature-dev:spec --publish` write the spec into an issue, and
`/feature-dev:explore-plan`, `/feature-dev:tdd`, `/feature-dev:spec-review` and
`/feature-dev:review` all accept an issue argument (`#N`, `owner/repo#N`, or an
issue URL) to read it back. The local file stays the working copy; the issue
becomes its durable home once published. Format, fingerprints, and the
publish/import algorithm are in [issue-store.md](references/issue-store.md) —
every command that touches the store links there instead of restating it.

### Decisions Log

The spec states what was decided *before* the work. The Decisions Log records what got decided *during* it — and it lives in the spec because the spec is the one artifact that outlives the run. The `PLAN-<slug>.md` is a working document of the run; a decision written only there is easy to lose, and an implementation session's context dies sooner than that.

Append to a `## Decisions Log` section at the end of the spec, newest last:

```
- **[repo: <repo name> · step <N>]** <the decision, one sentence>
  **Because:** <why it went this way and not the other>
  **Binds:** <who must obey — a repo name, a later step, or `this repo only`>
```

`/feature-dev:tdd` writes these automatically during Phase 3 and reads them back in Phase 1. Add entries by hand when a decision is taken outside a run.

**What belongs here.** A decision qualifies when it is not already written in the spec or plan **and** it constrains code outside the step that produced it. Deviations accepted mid-run, contract-touching changes (a new error code, a renamed field a consumer reads, a schema change), and user answers that unblocked a halt — those. Not implementation detail that lives fine in the diff.

**Why it matters most in multi-repo features.** The contract-owning repo and the consuming repo are implemented by separate runs, often on separate days. Without the log, every decision the first run took reaches the second one only if a human carries it. `Binds:` is what makes the carry automatic: a run reading the log sees which entries name its repo.

## Anti-Rationalizations

Catches *skipping the spec entirely*:

| Excuse | Reality |
|--------|---------|
| "This is simple, no spec needed" | If scope is genuinely self-evident, skip the spec. If you can't state the acceptance criterion in one line, it isn't simple. |
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
| **Internal-focus stories** | "As an engineer, I want to refactor the database..." | That is a task, not a user story. It belongs in the plan (`PLAN-<slug>.md`). |
| **Rule written as implementation** | "BR-1 — `Task.is_overdue()` returns False when `status == done`" | State what is true of the domain: "a done task is never overdue". The method is the plan's choice. |
| **Rule hidden in a criterion** | "AC-2 — lists open tasks due before today; done tasks are never overdue" | Lift the "never" into a BR, and let the AC cite it with one example. |
| **Everything is P0** | All requirements marked must-have | Apply the cut-test to each. Real P0 lists are short. |
| **Padded open questions** | Questions you could answer yourself | Move answerable items to assumptions. Open questions are genuine unknowns. |
| **Perfunctory boundaries** | "Never do: anything not listed above" | Name 3-5 specific adjacent capabilities you will *not* build, with one-line rationale per item. |
| **Spec written post-implementation** | Spec describes what was already built | That is documentation. Write a short retrospective instead — the spec's value is alignment *before* code. |

## Verification

Before proceeding to implementation:
- [ ] Spec has every section of [spec-template.md](references/spec-template.md), with scope settled by its own question before assumptions
- [ ] User has reviewed and approved the spec
- [ ] Business rules (`BR-n`) are in domain language, or the section says `None — <why>`; every rule is cited by at least one AC
- [ ] Success criteria live in a dedicated **Acceptance Criteria** section (not buried in Objective), each with a stable `AC-n` id, and include at least one failure/error-state criterion
- [ ] A **QA Checklist** (`### Happy path` / `### Edge cases` / `### Empty states` / `### Error states`, each a list of `- [ ]` items) exists
- [ ] Success criteria are specific and testable (no banned vague words without concrete definitions)
- [ ] Boundaries (Always / Ask First / Never) are defined with one-line rationale per Never-do item
- [ ] P0 list passes the cut-test (≤5 items, each truly required to solve the core problem)
- [ ] Open questions are genuinely open, owner-tagged, and marked blocking vs non-blocking
- [ ] Spec is saved as a local working artifact (`.feature-dev/features/<slug>/SPEC-<slug>.md`, not committed, state in `feature.json` written only by `features.py`; see [artifact-locations.md](references/artifact-locations.md))
- [ ] **Multi-repo only**: `repos:` frontmatter and Cross-Repo Contracts section are present and confirmed by user
- [ ] **Multi-repo only**: a `## Decisions Log` section exists (may be empty at spec time — it is filled during implementation)
