# Changelog

## 1.11.3 (2026-10-28)

### Fixed
- `verify-issues` audit: a CONFIRMED or REFUTED row now needs evidence that cites a `path:line`, a commit or a search, as `verification.md` requires; any non-empty text used to pass, so "the issue says so" went unflagged. A REFUSED report with no rows is returned as is instead of being retried and reported as "no ledger", which lost the verdict and the quoted text. Both found by Copilot on the org port of this workflow.

## 1.11.2 (2026-10-28)

### Fixed
- `verify-issues` returns a compact `summary` (verdict, `verified` and audit flags per issue) before the full ledgers, and `/github-issues:verify` reads it first. A long result reaches the session cut off at the end: in a live run the audit flags of the second issue were lost with its ledger, and the session had to dig them out by hand.

## 1.11.1 (2026-10-28)

### Changed
- `issue-verifier` gets a "Working efficiently" section: search with `git ls-files` / `git grep -E` for several terms at once instead of guessing paths, read ranges, batch independent calls, and stop once the verdict is settled. Its tools add `git ls-files`, `git status *`, `grep` (for untracked dependencies that `git grep` cannot see) and `ls -d` for sibling repos. The output section now says a status is exactly one of the five, with any nuance in Evidence.

## 1.11.0 (2026-10-28)

### Changed
- `/github-issues:work`'s review re-runs the spec reviewer against the plan and the issue after each fix round, on the whole change (via `references/review-loop.md`). Needs code-review 3.13.0.

## 1.10.0 (2026-10-28)

### Added
- **The `verify-issues` workflow** (`workflows/verify-issues.js`). `/github-issues:verify` runs it, and so does `/github-issues:work` Phase 3 for its one issue. It starts one `issue-verifier` per issue in parallel and gets each ledger back as structured data. Then it applies "Auditing an agent's ledger" in code instead of leaving it to the reader:
  - a `ran` row is downgraded to `read`;
  - a CONFIRMED or REFUTED row without evidence becomes UNVERIFIED;
  - an actionable verdict over a refuted load-bearing row is flagged as contradictory;
  - an empty report is retried once, then reported as not verified.
  Issues come back most urgent first. Each correction is listed in `audit_flags`. With workflows disabled, the commands fall back to the direct agent dispatch.

## 1.9.0 (2026-10-28)

### Changed
- **`/github-issues:work` Phase 6 runs code-review's `review` workflow** through the shared review loop (`references/review-loop.md`). Before, one reviewer checked the diff, the same session that wrote the code verified its findings, and there was one round with no re-review of the fixes. Now:
  - A defect reviewer runs with a focus on the work type's tests and the plan's consumers, and a spec reviewer checks the diff against the approved plan and the issue.
  - A separate opus agent verifies each finding.
  - You pick which findings to fix. Fixes run one at a time, and their delta is reviewed again, two rounds at most.
  - A confirmed finding that would change what the plan approved goes to you as a question.
  - A tree hash before and after each review run stops the loop if a reviewer changed the tree.
  - With workflows disabled, the old single reviewer (`review-prompt.md`) is the fallback.
- Declares `code-review` in `dependencies`. `scripts/tree-hash.sh` and `references/review-loop.md` are synced from `shared/`.

## 1.8.0 (2026-10-28)

### Changed
- **`/github-issues:work` approves its plan with AskUserQuestion (Approve / Change the plan / Stop) instead of plan mode.** Plan mode is not deprecated, but as an approval gate inside a command it blocked edits for the whole presentation and its approval prompt offers to switch the session's permission mode, so approving a plan could silently move the user into auto mode.

## 1.7.0 (2026-10-06)

### Added
- **`/github-issues:verify --pane`** resolves the issue list here (so a `--label` query cannot drift), then verifies in a separate Claude Code session in a sibling Herdr pane. Posting approvals happen in the pane; the ledger comes back here.
- `scripts/herdr-pane.sh` and `references/herdr-pane.md`. The script and its reference are synced copies of `shared/herdr-pane/` in the marketplace repo (`shared/sync.sh`); edit them there.

## 1.6.1 (2026-10-02)

### Changed
- README gains a **Needs** section listing prerequisites (`gh`, MCP servers, browser, external CLIs), replacing the old Requirements list.

## 1.6.0 (2026-09-29)

### Added
- `work` checks the issue's assignees in Phase 1, before verifying anything: if someone else is assigned, it stops and asks whether to continue (adding you alongside them, never replacing them). **Why:** an assigned issue is probably being worked on, and verifying and planning it in parallel duplicates that work.
- `work` assigns you (`gh issue edit --add-assignee @me`) in Phase 5, right before the first edit, after re-checking the assignees. Not earlier: verification can end the run, and an assignment would then claim work nobody is doing. Approving the plan approves the assignment; a failure does not stop the work and is reported in the close-out. Allowlist: `gh issue edit * --add-assignee @me`, `gh api user --jq .login`.
- Verification reads the issue as its body **amended by its comments** (`references/verification.md`, "Comments amend the issue"): a comment that re-verified the issue at a commit is the baseline for the claims it covers, a comment that widened the scope widens the ledger, a check a comment completed is not reported as open, and what a comment splits off goes under Out of scope. Ledger rows name their source (body or comment), and drafted corrections leave out what an existing comment already says. **Why:** on an issue whose re-verification comment had moved every location, widened the fix from one call site to about ten, and completed the requested cross-repo check, verifying the body alone would re-report stale drift and size the fix to the original, smaller scope.

## 1.5.0 (2026-09-23)

### Added
- `work` Phase 6, Review: after the tests pass, a reviewer that has not seen the conversation (`code-review:branch-reviewer`, overridden to `opus`) reviews the diff against the approved plan — defects, plan conformance, whether the tests prove what the work type needs, and consumers the plan missed. Findings are verified before acting; confirmed defects inside the plan's scope are fixed, ones that would change what the plan approved go to the user, and there is one round, not a loop. Prompt in `references/review-prompt.md`.
- `work` keeps the diff to what the plan calls for: no repo-wide formatters or reflows, and the rule travels with the plan when implementation is delegated to a subagent.

### Changed
- Close-out is now Phase 7 and reports what the review found, fixed, escalated, and discarded.

## 1.4.0 (2026-09-23)

### Added
- `verify` skill: checks one or more issues — or an open-issue label, `--label tech-debt --limit N` — against HEAD without implementing anything. One read-only `issue-verifier` agent per issue, in parallel; the skill audits each report (no `ran` claims, evidence on every CONFIRMED/REFUTED row), presents a verdict table, offers to run the probes the agents proposed, and drafts issue comments for approval.
- `issue-verifier` agent: classifies one issue and builds its claim ledger. Cannot run anything, and its contract forbids claiming it did — probes are written out *(not run)* for the caller. Pinned to `opus`: in an A/B on a real issue, `sonnet` confirmed a suggested fix that `opus` showed would lock users out — it checked the code pattern but not what the permission meant to its consumers.
- `work` accepts `#N` or `N` for an issue in the current repo, and `--part N[,M]` to take only some items of an issue that bundles several.
- `work` delegates the reading half of verification to `issue-verifier` — or reuses a ledger `verify` produced earlier in the conversation — and keeps the running half: it reproduces bugs, runs the probes the agent proposed, and promotes those rows to `ran`. One verification implementation instead of two, and the code exploration stays out of the conversation that implements. Falls back to verifying inline when it cannot spawn an agent.
- Issue comments drafted from a ledger lead with what was checked and how (`ran` / `read`), and list unverified rows with the command that would settle them.
- `work` classifies the issue before planning — bug, performance, tech debt, refactor, test defect, follow-up, needs-decision, epic — from the body as well as the labels (`references/work-types.md`). The type sets the branch prefix and the test strategy: a refactor no longer gets asked for a regression test that fails first.
- Verification phase before planning (`references/verification.md`): every claim the work relies on — locations, behavior, absences, measurements, flags, the suggested fix — is checked against HEAD and recorded in a ledger with its status and how it was checked (`ran` / `read` / `not checked`). A verdict gate stops the run when the issue is already fixed, its premise is wrong, or it needs a decision.
- Rationalization defenses in `references/critical-rules.md` for the ways a detailed, AI-written issue invites skipping verification.
- Verification checks how consumers interpret what the issue names (a field, a permission, an endpoint), including sibling repos checked out locally, and treats comments as claims too. Sibling-repo evidence records that repo's HEAD and whether it was fetched.
- An issue whose parts land differently (fix refuted, residual gap needing a decision) gets a verdict per part.
- Impact (callers, frequency, stated priority) is a claim with its own ledger row: an incomplete caller list can hide the path that matters.
- Allowlist: `gh pr list`, `git show`, `git blame`, `npx vitest`, `uv run`, `pipenv run`, `poetry run`.

### Changed
- **`fix` renamed to `work`**: the skill now covers tech debt, refactors, and follow-ups, not only bugs. `/github-issues:fix` stays as a deprecated alias that loads `work`, and is removed in 2.0.
- The branch is created after the plan is approved, not before exploring, so a stale or non-actionable issue leaves no branch behind.
- Plan template now carries the verification ledger, deviations from the issue's suggested fix, consumers checked, and an explicit out-of-scope list.
- `needs-decision` issues stop with the options and evidence; the skill never picks one.
- Close-out distinguishes `Closes #N` from `Refs #N`, and offers to post the ledger's corrections to the issue (only with approved text).
- PR lookup searches `#N` and treats hits as candidates: a PR addresses the issue only if its diff touches the code in question.
- The Stop hook no longer assumes a PR is next: a run that stopped at the gate gets different next steps.

## 1.2.3 (2026-09-22)

### Changed
- Removed the `SUBAGENT-STOP` guard from `fix`: the skill has `disable-model-invocation: true`, so no subagent can reach it.

## 1.2.2 - 2026-05-27

### Added
- `fix` skill allowlist now includes `mcp__clickup-local__link_pr_to_task`. When a GitHub Issue is mirrored in a ClickUp task, the skill can link the resulting PR back to the task after `gh pr create`. No-op when ClickUp MCP isn't configured.

## 1.2.1 - 2026-05-06

### Changed
- Trimmed `fix` skill description to fit Claude Code's skill-listing budget.

## 1.2.0 - 2026-04-16

### Changed
- Rewrote skill/command descriptions to contain only triggering conditions and boundaries, removing workflow step summaries that caused the model to shortcut skill bodies
- Added SUBAGENT-STOP tag to the `fix` skill to prevent premature termination

## 1.1.0

### Changed

- Migrated from `commands/` to `skills/` with progressive disclosure pattern
- Rewrote skill description to follow "Use when / Do NOT use for" convention
- Added `disable-model-invocation: true` to prevent auto-triggering
- Narrowed `Bash(python *)` to `Bash(python -m pytest *)` for tighter security
- Extracted plan template and critical rules into `references/` for leaner core skill
- Clarified 10-minute exploration limit rationale vs global 15-minute limit

## 1.0.0

### Added

- `fix` command: fetch a GitHub Issue, explore the codebase, plan and implement the fix
- Multi-repo handoff support via `/handoff:prompt` when the fix spans repositories
- Automatic branch creation from issue metadata
