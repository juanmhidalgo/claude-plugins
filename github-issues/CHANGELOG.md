# Changelog

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
