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
wait for CI (daemon §15): the PR is opened, Copilot's review is requested, and
the stage ends.

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
--no-notify --evidence-file <path>")`, where the evidence file holds one line
per test run the earlier stages reported (implement's test run line, harden's
test selection), taken from their done comments. The skill's `--yes` makes
every gate a default; this stage adds what the PR body must lead with:

| `/ship` phase | Factory behaviour |
|---|---|
| Phase 1 | Never on the default branch (checked above). A clean tree with commits ahead of the base goes straight to the push and the PR |
| Phase 2 staging | Leftovers from `harden` (none expected) are staged per the contract's rule 4, excluded paths listed |
| Phase 4 tests | The detected runner runs once; red → the skill stops before committing: `parked reason=tests-red` with the failing output, no PR (AC-21). No runner → continue, `Tests skipped (no test runner detected)` in Evidence |
| Phase 5 push | `git push`; rejected → `parked reason=push-rejected` |
| Phase 6 PR | base = the default branch; title = the issue title (under 70 characters: cut at a word and add `(#N)` only if room); body = `Closes #<N>` as its first line, then a `## Acceptance criteria` list copied from the spec section, then ship's template (Summary, Evidence, Merge Danger, Rollback Triggers), then `## Harden` with harden's close block, then `## Factory` with the run ids of every stage (from the done markers) and links to the stage comments. Copilot's review is requested as the skill does |
| Phases 7–8 | Skipped (`--no-watch`) |

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
  skipped`), whether Copilot's review was requested, and the contract's §7
  lines.
- The flip `status:in-progress → status:in-review`. The daemon's "PR opened"
  notification is fed by this flip.

## Cannot decide

Nothing: everything that needs a decision was decided upstream or is for the
PR reviewer. This stage ends `done` or `parked`, never `question`.

## Resume

An existing open PR for the branch → straight to the done outcome: no second
PR, nothing edited on the first (AC-20); the done comment names it. A re-run
whose latest marker is this stage's `done` runs only the flip.
