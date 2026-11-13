---
description: |
  Use before writing code when requirements are ambiguous or a feature has non-obvious scope.
  Do NOT use for simple, self-evident changes.
argument-hint: "<feature or project description> | --publish <SPEC> new|#N|owner/repo#N|URL"
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
  - Bash(git check-ignore *)
  - Bash(gh auth status)
  - Bash(gh repo view --json nameWithOwner*)
  - Bash(gh issue view *)
  - Bash(gh issue create *)
  - Bash(gh issue edit *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/issue_spec.py *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py snapshot *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/features.py *)
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this command and proceed with your assigned task.
</SUBAGENT-STOP>

## Context

- **Branch**: !`git branch --show-current`
- **Recent commits**: !`git log --oneline -5`
- **Additional directories**: !`jq -r '.permissions.additionalDirectories[]? // empty' .claude/settings.local.json 2>/dev/null || true`
- **Parent context file**: !`test -f ../CLAUDE.md && echo "../CLAUDE.md exists (read for repo catalog)" || echo "no ../CLAUDE.md"`
- **Feature store**: each feature lives in `.feature-dev/features/<slug>/`, managed by `${CLAUDE_PLUGIN_ROOT}/scripts/features.py` (pass `--root <repo root>`). Layout: [artifact-locations.md](../skills/spec-driven-development/references/artifact-locations.md).
- **Spec store option**: `${user_config.spec_store}` (a literal `${user_config...}` here means `file`).
- **Arguments**: !`bash "${CLAUDE_PLUGIN_ROOT}/scripts/args.sh" '$ARGUMENTS'`

<best_practices>
@feature-dev/skills/spec-driven-development/SKILL.md
</best_practices>

## Spec-Driven Development Workflow

**First, check for `--publish <SPEC> <target>`.** `--publish` is a flag the parser does not know, so it stays in `positional`: when `positional[0]` is `--publish`, `positional[1]` is `<SPEC>` and `positional[2]` is `<target>`. Go straight to [Publish Mode](#publish-mode) below — it skips the authoring phases (Specify, Handoff) entirely and never reads the rest of the arguments as a feature description. Otherwise, continue below.

**Then read the description.** `positional`, joined with spaces, is the feature description. `--with-tasks` was removed in 3.0.0: if it is there, drop it and say in one line that the plan comes from `/feature-dev:explore-plan` (or, for a small feature, `/feature-dev:tdd` straight from the ACs). If the Arguments line in Context is a shell error instead of JSON (an apostrophe in the description does that: "the user's profile"), read the description from the bold line below and strip the flags by hand.

You are creating a structured specification for the feature description left after stripping flags: **$ARGUMENTS**

This command ends at the spec: Phase 1, then Handoff. It never writes an implementation plan or a task list: the step-level plan is `/feature-dev:explore-plan`'s job, and a second plan inside the spec drifts from the one explore-plan derives from the code.

Phase 1 requires user approval before Handoff.

### Phase 1: Specify

1. **Detect multi-repo scope** (runs silently — feeds the recommendation in step 2). A feature is multi-repo only when the description clearly spans concerns owned by different repos (e.g., "API + UI", "service + worker"). Confirm that first, then corroborate with at least one infrastructure signal:

   - **Signal A (required)**: the feature description spans concerns owned by different repos.
   - **Signal B**: `additionalDirectories` (Context block above) lists sibling repos as accessible.
   - **Signal C**: `../CLAUDE.md` exists and catalogs sibling repos with their purpose — read it to learn the repo set.

   Recommend multi-repo only when **A AND (B OR C)** hold. `additionalDirectories` alone is a false positive (users grant access for reference, not feature scope). Detection only shapes the recommended option in step 2; the scope answer decides. If the answer names two or more repos, the multi-repo sections (frontmatter `repos:`, "Cross-Repo Contracts", "Decisions Log") are in for the rest of this command, whatever detection concluded; if it leaves one repo in, they are out.

2. **Ask the scope question — first, and on its own.** Before surfacing assumptions and before reading any code, ask one AskUserQuestion with a single question: which repos and components are in, and what is explicitly out. Offer a recommended option inferred from the description and step 1 (e.g. "<backend-name> API + <frontend-name> page; out: admin UI, other tenants") and one or two real alternatives — a narrower and a wider cut. Record what the answer rules out: it becomes the spec's `## Non-Goals`.

   Scope goes first because everything after it is sized by it: a scope change after approval (a backend endpoint added, "not tied to one customer") has meant re-planning. It goes alone because a scope question bundled with other questions gets answered last — one sat unanswered for almost 7 hours.

3. **Surface assumptions.** Now list 3-5 assumptions about the tech stack, architecture, and behavior within the agreed scope, and ask about them in their own round-trip, after the scope answer. Each assumption is one question so each can be answered on its own:
   - **One AskUserQuestion call, one question per assumption** (up to 4). The question states the assumption in one or two sentences; the options are the assumption itself, marked "(Recommended)", and one or two concrete alternatives, so a correction takes a click, not a note. Never a single question listing the assumptions with "confirm all" / "correct some" options: it forces an all-or-nothing answer, and correcting one item means typing out which one and how.
   - **One decision per assumption.** If it joins two choices (token audience *and* expiry, status codes *and* the field that triggers them), split it, or keep the one that shapes the model or the contract and move the rest to the review brief's "Decided" group.
   - **Don't ask what you can check.** A fact about the code or the infrastructure is not an assumption for the user to confirm: read the file, or list it under "Unverified claims about the code" in the review brief.
   - **More than 4:** ask the ones that change the data model or a contract; the rest go to the brief's "Assumed — confirm" group.

4. **Reframe vague requirements.** If the input is vague, translate it into concrete, testable success criteria. Present these to the user for validation.

5. **Write the spec** following [spec-template.md](../skills/spec-driven-development/references/spec-template.md) — Read it now; it is the only definition of the sections, their order and their id rules. In short: Objective, Non-Goals, Business Rules (`BR-n`), Acceptance Criteria (`AC-n`, citing the rules they exercise), QA Checklist, Boundaries, plus Cross-Repo Contracts and Decisions Log when multi-repo. Write the rules before the criteria: a criterion that exercises no rule and states no error case is often a rule that was never named. Do not write commands, file layout, code conventions or a test strategy — the plan derives those from the code.

6. **Save the spec** to the path `${CLAUDE_PLUGIN_ROOT}/scripts/features.py new <feature-slug> --kind spec --root <repo root>` prints (`.feature-dev/features/<feature-slug>/SPEC-<feature-slug>.md`); this is the **spec path** used below. The script creates the feature as a `draft`. If it refuses because the feature already exists, you are revising: edit the existing SPEC in place. Before editing a spec the user has already seen, snapshot it once per review round with `${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py snapshot <spec path>` — it copies the file to `.feature-dev/features/<feature-slug>/history/SPEC-<feature-slug>.<n>.md`, which `/feature-dev:review` diffs against; without it nobody can see what changed between versions. **Refuse an old-layout path:** if `$ARGUMENTS` or a spec path points outside `.feature-dev/features/` (a root `SPEC-*.md`, or the layout older than 2.0.0), refuse it in one line and name `.feature-dev/features/<slug>/` as the only place specs live. The file begins with the template's frontmatter block.

   The feature's state (draft, approved, implemented) lives in `feature.json`, not in the frontmatter: after the user validates the spec in step 8, run `${CLAUDE_PLUGIN_ROOT}/scripts/features.py approve <feature-slug> --root <repo root>`.

7. **Update `.gitignore`.** Run `git check-ignore -q .feature-dev` first: exit 0 means the folder is already excluded (by `.gitignore`, or by `.git/info/exclude` as a headless caller sets it) and nothing is edited. Otherwise add `.feature-dev/` to the project's `.gitignore` (features, review files and version history). The spec is a local working artifact, not a repo deliverable — this prevents accidental commits via `git add .`. (Mirrors the same step performed by `/feature-dev:explore-plan` for the plan.)

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

A business rule the user did not state is a "Decided" item: a rule is the easiest place for a silent assumption to become binding.

### Phase 2: Handoff

After the spec is approved:
- The spec file is a **local working artifact**, not a repo deliverable. Do NOT commit it, and do NOT run any git commands. Downstream commands read it directly from the working tree.
- Confirm the feature is approved (`${CLAUDE_PLUGIN_ROOT}/scripts/features.py approve <feature-slug> --root <repo root>` has run; `/feature-dev:tdd` marks it implemented when it finishes).
- **Ask about publishing — once, gated, right here.** Read `.claude/feature-dev.local.md` (Read tool; a missing file is simply absent, no fallback value). This is the only place this question is asked: never on edits or review rounds — not when the user asks you to change something in an already-approved spec, and not at the end of a review brief. Handoff runs once, after the spec is approved, so asking only here already satisfies that.
  - **The store setting**: `spec_store` in `.claude/feature-dev.local.md` when that file sets it (project setting, wins); otherwise the **Spec store option** in Context. `issue` is the only value that means "issue"; anything else, or nothing set anywhere, is `file`.
  - **Skip silently, changing nothing else in Handoff,** unless the store setting is `issue` or the feature is already linked to an issue (its `issue` in `features.py list --json` is not null). Either condition alone is enough to ask.
  - Otherwise ask one AskUserQuestion with the options "keep local", "publish to #N" (target `#N`; offered only when the feature is already linked to an issue), and "create an issue" (target `new`).
  - **Default**: default when the store setting is `issue` is the publishing option — "publish to #N" if the feature is already linked to an issue, otherwise "create an issue" (there is no `#N` yet to publish to). When the question was asked only because the feature is already linked to an issue (store setting `file`), default to "keep local".
  - "Publish to #N" or "create an issue" runs [Publish Mode](#publish-mode) against this spec path and the chosen target (`#N` or `new`), start to finish, then continues below with its result. "Keep local" changes nothing and continues below immediately.
- End with the next command, using the spec path you just wrote, then stop and let the user choose:

  ```
  Next: /feature-dev:spec-review <spec path> (optional) or /feature-dev:explore-plan <spec path>
  ```

  Recommend explore-plan: it writes a reviewed step-level plan from the code. `/feature-dev:tdd <spec path>` (straight from the spec's ACs) is the fallback for a small feature, so mention it only when the spec is small enough that a plan adds nothing.

## Publish Mode

Entered only when `positional[0]` was `--publish` (`<SPEC>` and `<target>` read above). This mode skips the authoring phases: it never asks the scope question, never surfaces assumptions, never writes spec content, and never presents a review brief.

1. Resolve `<target>` (`new`, `#N`, `owner/repo#N`, or an issue URL) per [issue-store.md's Argument parsing](../skills/spec-driven-development/references/issue-store.md#argument-parsing).
2. Run [issue-store.md's Publish algorithm](../skills/spec-driven-development/references/issue-store.md#publish-ac-1-ac-2-ac-3-ac-4-ac-5-ac-7) against `<SPEC>` and the resolved target, start to finish, including its `gh` preflight, its scratch-file handling, and its fingerprint verification. Do not restate those steps here — follow the reference.
3. If the reference's mismatch branch (its step 3, target `#N`) offers "import the issue's version instead," and the user picks it, run [issue-store.md's Import algorithm](../skills/spec-driven-development/references/issue-store.md#import-ac-8-ac-9-ac-10-ac-11-ac-12) against that issue, start to finish, then stop — this invocation does not also publish. Do not restate Import's steps here — follow the reference.
4. A failed `gh` preflight or a failed verification (the reference's steps 1 and 6) leaves the local spec untouched and reports that nothing was published.
5. On a verified publish, report the issue URL from the reference's step 7 and stop.

## Rules

- **Never skip the scope question or assumption surfacing, and never merge them.** Silent assumptions are the most dangerous form of misunderstanding, and scope is the one that re-plans everything downstream when it moves.
- **Never advance phases without user approval.** Each gate exists to catch misalignment early.
- **Stop at the spec.** No Implementation Plan, Tasks, commands, file layout or test strategy — explore-plan produces those from the code, and a second copy in the spec only diverges from it.
- **Rules in domain language.** A business rule that names a method, an endpoint or a table has slipped into the plan; restate it as what is always true of the domain.
- **End each gate with the review brief, not the artifact.** The brief is what the user actually reads before approving; its "Unverified claims" group is where a wrong assumption about the code gets caught before it becomes an AC.
- **Reframe, don't accept vagueness.** Convert "make it better" into measurable criteria.
- **The spec is a living document.** Update it when decisions change, don't abandon it. Keep AC and BR ids stable across edits.
- **Multi-repo: declare scope explicitly in frontmatter.** The `additionalDirectories` setting grants access; the spec's `repos:` block declares intent. It is the canonical record of which repos are in scope — future downstream tooling will read it rather than re-inferring from settings.
- **Multi-repo: write the contract in the spec.** The Cross-Repo Contracts section is the coordination anchor — both sides build against it. Skipping it lets the two repos drift.
