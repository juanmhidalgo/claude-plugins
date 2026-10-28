---
name: verify
description: |
  Use when the user wants one or more GitHub issues checked against the current code before
  anyone works on them — triaging a backlog of AI-written issues, or checking whether an
  issue is still true, already fixed, or wrong. Read-only; posts nothing without approval.
  Do NOT use to implement an issue (use /github-issues:work), or to review a PR (use /code-review).
argument-hint: "<issue-url | #number>... | --label <label> [--limit N] [--pane|--no-pane]"
disable-model-invocation: true
keywords:
  - github
  - issue
  - triage
  - verify
  - backlog
  - tech-debt
triggers:
  - "verify this issue"
  - "is this issue still valid"
  - "triage these issues"
  - "check the tech debt backlog"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Agent
  - Workflow
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/herdr-pane.sh *)
  - Bash(gh issue view *)
  - Bash(gh issue list *)
  - Bash(gh issue comment *)
  - Bash(gh repo view *)
  - Bash(gh pr list *)
  - Bash(git log *)
  - Bash(git show *)
  - Bash(git rev-parse *)
  - Bash(git status)
  - Bash(pytest *)
  - Bash(python -m pytest *)
  - Bash(uv run *)
  - Bash(pipenv run *)
  - Bash(poetry run *)
  - Bash(npx vitest *)
  - Bash(npx jest *)
  - Bash(make *)
hooks:
  - event: Stop
    once: true
    command: |
      echo "Next steps:"
      echo "  - /github-issues:work <#N> on an actionable issue — it starts from this ledger"
      echo "  - Post the approved corrections to the issues that need them"
---

## Context

- **Repository**: !`git remote get-url origin 2>/dev/null || echo "no remote"`
- **Checkout path**: !`git rev-parse --show-toplevel 2>/dev/null`
- **HEAD**: !`git log -1 --format='%h %cs' 2>/dev/null`
- **Current branch**: !`git branch --show-current`

## Arguments

`$ARGUMENTS`

- One or more issues: URLs, or `#N` / `N` for this repo (`gh repo view --json nameWithOwner`).
- Or `--label <label>` with optional `--limit N` (default 10): open issues with that label,
  via `gh issue list --repo {owner}/{repo} --label <label> --state open --limit N --json number,title`.

Verification runs against the local checkout, so issues must belong to this repo. An issue
from another repo → **STOP** and say which checkout to run it from.

If the current branch is not the default branch, say so: the ledger is only true for this HEAD.

## Herdr pane

With `--pane`, run the verification in a Herdr pane in **collect** mode: follow
`${CLAUDE_PLUGIN_ROOT}/references/herdr-pane.md`. It falls back to the normal run outside
Herdr. Questions the run asks happen in the pane, and Herdr notifies the user.
`--pane` / `--no-pane` are flags: drop them before reading the arguments.
Resolve the list here first (step 1), so the pane receives issue numbers, not a
label query that could resolve differently by the time it runs.

- **Command string**: `/github-issues:verify <resolved issue numbers> --no-pane`
- **Report**: `<scratchpad dir>/verify-<first issue>.md`
- **Present**: the ledger and verdicts as the report has them. Anything the pane
  posted to GitHub was approved there; do not offer to post it again.

## Workflow

### 1. Resolve the list

Resolve the arguments into issue numbers. With more than 10, show the list and ask before
continuing — each issue costs one opus agent.

### 2. Verify in parallel

Launch the `github-issues:verify-issues` workflow and wait for its notification:

```
Workflow({ name: "github-issues:verify-issues", args: {
  repo: "{owner}/{repo}", repo_path: "{checkout path}",
  rules: ["{base directory of this skill}/../work/references/verification.md",
          "{base directory of this skill}/../work/references/work-types.md"],
  issues: [{ number: N, parts: "all" }, ...] } })
```

Resolve `{base directory of this skill}` to an absolute path before sending. It runs one
`issue-verifier` per issue in parallel and applies "Auditing an agent's ledger" from
[verification.md](../work/references/verification.md) to each ledger in code: a `ran`
row is downgraded, a CONFIRMED/REFUTED row without evidence becomes UNVERIFIED, an
actionable verdict over a refuted load-bearing row is flagged, and an empty report
(`verified: false`) is retried once. Issues come back most urgent first.

If workflows are disabled (`Workflow` unavailable), say so and spawn one
`github-issues:issue-verifier` per issue instead, all in one message, no `name`, each with
the prompt `ISSUE` / `REPO_PATH` / `RULES` (see the agent's Input), then do that audit
yourself before presenting.

### 3. Check the reports

Show every `audit_flags` entry next to its issue: each one is a place the verifier's
ledger was corrected or contradicts itself. An issue with `verified: false` is not
verified; never present a guess in its place.

### 4. Present

1. A summary table, in the order the workflow returned (most urgent first):

   | Issue | Type (labels) | Verdict | What decides it |
   |---|---|---|---|

2. Each issue's full report below it, rendered from its ledger: type, verdict and its
   reason, the ledger table at `sha` (`#`, Claim, Status, How, Evidence), probes worth
   running, corrections to the issue, and the audit flags.

### 5. Offer, don't act

- **Run the probes** the agents listed, when they only run tests or read-only queries —
  show them first, then run them here and update the affected rows to `ran`.
- **Draft issue comments** for issues with corrections, following "Posting corrections" in
  [verification.md](../work/references/verification.md). Show each draft; post only
  the text the user approved, one issue at a time.
- **Point to `/github-issues:work #N`** for issues that are actionable.

Never relabel, close, or edit an issue: those are the maintainers' decisions.
