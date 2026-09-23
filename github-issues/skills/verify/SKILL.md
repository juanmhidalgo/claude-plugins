---
name: verify
description: |
  Use when the user wants one or more GitHub issues checked against the current code before
  anyone works on them — triaging a backlog of AI-written issues, or checking whether an
  issue is still true, already fixed, or wrong. Read-only; posts nothing without approval.
  Do NOT use to implement an issue (use /github-issues:work), or to review a PR (use /code-review).
argument-hint: "<issue-url | #number>... | --label <label> [--limit N]"
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

## Workflow

### 1. Resolve the list

Resolve the arguments into issue numbers. With more than 10, show the list and ask before
continuing — each issue costs one agent.

### 2. Verify in parallel

Spawn one `github-issues:issue-verifier` per issue, all in a single message. Do not pass a
`name` to the Agent tool. Each prompt is exactly:

```
ISSUE: {owner}/{repo}#{number}
REPO_PATH: {checkout path}
RULES: {base directory of this skill}/../work/references/verification.md
       {base directory of this skill}/../work/references/work-types.md
```

Resolve `{base directory of this skill}` to an absolute path before sending.

For a single issue, the same agent is still used: its context stays out of this conversation.

### 3. Check the reports

Before showing anything, audit each report as "Auditing an agent's ledger" in
[verification.md](../work/references/verification.md) describes, and say what you
downgraded or flagged.

### 4. Present

1. A summary table, most urgent first (premise wrong and already fixed before actionable):

   | Issue | Type (labels) | Verdict | What decides it |
   |---|---|---|---|

2. Each issue's full report below it.

### 5. Offer, don't act

- **Run the probes** the agents listed, when they only run tests or read-only queries —
  show them first, then run them here and update the affected rows to `ran`.
- **Draft issue comments** for issues with corrections, following "Posting corrections" in
  [verification.md](../work/references/verification.md). Show each draft; post only
  the text the user approved, one issue at a time.
- **Point to `/github-issues:work #N`** for issues that are actionable.

Never relabel, close, or edit an issue: those are the maintainers' decisions.
