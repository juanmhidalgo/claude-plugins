---
disable-model-invocation: true
argument-hint: "#N"
description: |
  Use when the factory daemon, or a person testing a stage headless with `claude -p`,
  runs the ship stage for issue #N (`status:in-progress`, last done marker `harden`):
  it runs /ship --yes on the factory branch, opens the PR against the default branch
  and flips the issue to `status:in-review`. Do NOT use interactively (use /ship),
  and never invoke it from a conversation: it asks nothing, pushes and opens a PR.
keywords:
  - factory
  - headless
  - ship
  - pull-request
allowed-tools:
  - Read
  - Glob
  - Grep
  - Skill
  - Bash(git *)
  - Bash(gh *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/factory-issue.sh *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/factory-outcome.sh *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/../feature-dev/scripts/features.py *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/../feature-dev/scripts/issue_spec.py *)
  - Bash(npm *)
  - Bash(yarn *)
  - Bash(pnpm *)
  - Bash(bun *)
  - Bash(pytest *)
  - Bash(python *)
  - Bash(uv *)
  - Bash(make *)
  - Bash(cargo *)
  - Bash(go *)
---

@factory/references/factory-contract.md

# `/factory:ship` — last done = `harden` → the PR is open

Stage `ship`. Caps are the daemon's (40 turns · 3 USD · 15 min). It does not
wait for CI (daemon §15): the PR is opened, no Copilot review is requested
(the factory never asks for one: the PR review is the human gate), and the
stage ends.

## Context

- **Arguments**: $ARGUMENTS
- **Stage variable set**: !`echo "${#FACTORY_STAGE}"`
- **Current branch**: !`git branch --show-current`
- **Working tree**: !`git status --short | head -20`

## Inputs

Run the contract's stage preamble (§4). The status must be
`status:in-progress` and `factory-issue.sh last-marker` must be `done
stage=harden …` or this stage's own `done`. Then:

1. `git fetch origin`; check out `FACTORY_BRANCH` tracking `origin`
   (missing there → `parked reason=no-branch`). If the clone is on the
   default branch after that, something is wrong with the identity: `parked
   reason=on-default-branch`, nothing pushed.
2. The issue: title, the spec section's `## Acceptance Criteria` list, the
   `done` comments of `implement` and `harden` (their URLs, from the comment
   list, and harden's close block).
3. An existing PR: `gh pr list --head FACTORY_BRANCH --state open --json
   number,url`. One found → **Resume** below.

## Composition

Invoke `/ship` with the Skill tool: `Skill("ship:ship", "--yes --no-watch
--no-notify --skip-copilot-review --evidence-file <path>")`, where the evidence file holds one line
per test run the earlier stages reported (implement's test run line, harden's
test selection), taken from their done comments. The skill's `--yes` makes
every gate a default; this stage adds what the PR body must lead with:

| `/ship` phase | Factory behaviour |
|---|---|
| Phase 1 | Never on the default branch (checked above). A clean tree with commits ahead of the base goes straight to the push and the PR |
| Phase 2 staging | Leftovers from `harden` (none expected) are staged per the contract's rule 4, excluded paths listed |
| Phase 4 tests | The detected runner runs once; red → the skill stops before committing: `parked reason=tests-red` with the failing output, no PR (AC-21). No runner → continue, `Tests skipped (no test runner detected)` in Evidence |
| Phase 5 push | `git push`; rejected → `parked reason=push-rejected` |
| Phase 6 PR | base = the default branch; title = the issue title (under 70 characters: cut at a word and add `(#N)` only if room); body built by **The PR body** below, which replaces the skill's steps 3 and 7 (its steps 4–6 still produce the Evidence, Merge Danger and Rollback Triggers text that the body places): `Closes #<N>` first, then the factory's sections through the repo's PR template when the repo has one, in the factory layout otherwise. Written to a scratch file and created with `gh pr create --base <default> --title "<title>" --body-file <file>`. No Copilot request: the skill runs with `--skip-copilot-review` (its step 8 is skipped), because the factory never asks for Copilot; the PR review is the human gate |
| Phases 7–8 | Skipped (`--no-watch`) |

### The PR body

The stage has these pieces, in this order of precedence: the `Closes #<N>`
line; **Summary** (ship's one sentence of why); **Acceptance criteria** (the
spec section's list, copied); **Evidence** (ship's After line, its Before
line, the `--evidence-file` lines as Earlier runs, and any lint or format run
the stages reported); **Merge Danger**; **Rollback Triggers**; **Harden**
(harden's close block, verbatim); **Factory** (a table with the run id of
every stage, from the done markers, and the link to each stage comment).

**With a repo template.** Look for, in this order, the first found wins:
`.github/PULL_REQUEST_TEMPLATE.md`, `.github/pull_request_template.md`,
`PULL_REQUEST_TEMPLATE.md`, `pull_request_template.md`,
`docs/pull_request_template.md`, then the first file by name in
`.github/PULL_REQUEST_TEMPLATE/`. Keep every heading of the template, in its
order and at its level, and fill them with the pieces:

1. **Line 1 is `Closes #<N>`**, before any heading. A `Closes #` placeholder
   the template carries is removed, never left empty or duplicated.
2. **The "what changes" heading** (the first heading that asks what the PR
   does or why: `What changes`, `Qué cambia`, `Summary`, `Description`,
   `Changes`, `Motivation`, `Context`, or alike) gets Summary, then a bold
   `**Acceptance criteria**` line and the list.
3. **A checklist heading** (`Checklist`, or the first heading whose template
   body is `- [ ]` items) keeps the template's own items: tick one (`- [x]`)
   only when an Evidence line is that command or plainly covers it (a full
   `uv run pytest` run ticks a `make test` item whose target wraps it; a
   lint run ticks the lint item); the others stay `- [ ]` as written, which
   is the honest state. Then the Evidence bullets follow as ticked items,
   one per line: `- [x] <command> — <result>`, Earlier runs ending with
   `(reported by <stage>)`. A `not captured` Before is not an item: leave it
   out.
4. **A reviewer-notes heading** (`Notes for the reviewer`, `Notas para el
   reviewer`, `Reviewer notes`, `Additional context`, `Review focus`, or
   alike) gets Merge Danger (its two lines), Rollback Triggers and the harden
   close block, each under a bold label (`**Merge Danger**`, `**Rollback
   Triggers**`, `**Harden**`) or a heading one level below the template's.
5. **`## Factory`** (at the template's heading level) is appended last, after
   every template heading.
6. **A heading with no mapping stays with its template text**, verbatim. The
   template's `<!-- … -->` placeholder comments are dropped from a filled
   section and kept in an unmapped one. Headings match case-insensitively in
   any language; when two could take the same piece, the first wins and the
   other stays as written. A piece with no heading to go to is appended under
   its own heading (`## Merge Danger`, `## Rollback Triggers`, `## Harden`),
   at the template's level, before `## Factory`.

**Without a template**: `Closes #<N>`, `## Acceptance criteria`, then ship's
sections (`## Summary`, `## Evidence`, `## Merge Danger`, `## Rollback
Triggers`), `## Harden`, `## Factory`.

Either way the body stays under ~60 lines (a long acceptance list or close
block goes in a `<details>` block), with no preamble and nothing the pieces
do not hold.

The skill reports what it did; the stage reads the PR URL from it (or from
`gh pr list --head FACTORY_BRANCH` when the output is unclear). A `/ship`
that stopped for any other reason (no remote, `gh` unavailable, a pre-commit
hook) → `parked reason=ship-stopped` with its last message.

No rebase and no merge from the default branch: a base that moved is left for
the person at the merge gate (GitHub shows mergeability on the PR).

## Outputs

- The PR.
- The `done` comment: the PR URL, the commit list (`git log --oneline
  origin/<default>..HEAD`), the test command and its result line (or `Tests
  skipped`), the line `Copilot: skipped (the factory does not request
  Copilot; the PR review is the human gate)`, and the contract's §7 lines.
- The flip `status:in-progress → status:in-review`. The daemon's "PR opened"
  notification is fed by this flip.
- The done call takes no `--sha`: the script reads the clone's HEAD, which is
  the PR's head after `/ship`'s push. A typed hash that differs is refused, so
  never type one.

## Cannot decide

Nothing: everything that needs a decision was decided upstream or is for the
PR reviewer. This stage ends `done` or `parked`, never `question`.

## Resume

An existing open PR for the branch → straight to the done outcome: no second
PR, nothing edited on the first (AC-20); the done comment names it. A re-run
whose latest marker is this stage's `done` runs only the flip.
