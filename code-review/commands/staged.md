---
allowed-tools:
  - Bash(git *)
  - Agent
  - Read
disallowed-tools:
  - Edit
  - Write
  - NotebookEdit
argument-hint: "[low|medium|high|max]"
description: |
  Use to review staged changes before committing, in a reviewer that has NOT seen this
  conversation — the right choice when this session wrote the code being staged.
  Do NOT use for branch-wide review (use /code-review:branch), full PR review
  (use /code-review:pr), or to also fix what it finds (use /code-review:staged-pipeline).
keywords:
  - staged-changes
  - pre-commit
  - git-diff
  - code-quality
  - fresh-context
triggers:
  - "review staged changes"
  - "check before commit"
  - "review what I'm about to commit"
  - "code review staged"
skills:
  - branch-review
hooks:
  - event: Stop
    once: true
    command: |
      echo "Staged changes review complete."
      echo "  - Spot-check 2 cited file:line refs before acting — reviewers can fabricate them"
      echo "  - Fix issues, then commit with /commit"
      echo "  - /code-review:fixes-plan to create fix tracking"
---

## Context
- **Current branch**: !`git branch --show-current`
- **Staged files**: !`git diff --cached --name-only`
- **Effort level**: $1

## Staged Changes Summary
!`git diff --cached --stat`

## Effort level

`$1` is one of `low | medium | high | max`, default `medium`. `low`/`medium`
surface only findings verified against the code path; `high`/`max` add broader
coverage including findings the reviewer could not fully confirm, each marked.

If `$1` is empty, read `pr_effort:` from `.claude/code-review.local.md`; else
`medium`.

## Why this is dispatched and not done inline

<iron_law priority="blocking">

**Run the reviewer in a subagent. Never review the staged diff yourself in this
conversation.**

</iron_law>

This command is most often run in the session that just wrote the code. That
session holds every reason the code looks right, which is exactly the framing a
reviewer must not start from. A subagent sees the diff and the repo and nothing
else.

If subagents are unavailable, say so plainly and offer to run it in a fresh
session or inline-but-marked-contaminated. Do not silently downgrade.

## Dispatch

Use the Agent tool with `subagent_type="code-review:branch-reviewer"`.

Pass **scope, not content**. No summaries of the change, no explanation of
intent, no excerpts:

```
SCOPE: staged changes (git diff --cached)
EFFORT: <level>
OUTPUT_PATH: <scratchpad dir>/staged-review-<branch>.md
```

The reviewer writes its full report to `OUTPUT_PATH` **and** returns it.
**Read the file first — it is the primary channel.** If the agent finished and
left neither file nor inline report, the review did not run: say so and re-run.
Never present a missing report as a clean one.

Keeping the full report in the file is also what keeps this conversation clean
for the commit you are about to make.

## Presenting the report

The finding format, severity/confidence rubric, labels, and the mandatory
failure-scenario field live in the **`branch-review` skill**. Do not restate
them here.

Spot-check two cited `file:line` references before presenting. Report `N
dropped` explicitly rather than quietly discarding.

**Do NOT** modify code, stage, or commit as part of this command. To review and
fix in one pass, that is `/code-review:staged-pipeline`.

## Next Step

> "To create a trackable fixes document, run `/code-review:fixes-plan [feature-name]`"
