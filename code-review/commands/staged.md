---
allowed-tools:
  - Bash(git *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/herdr-pane.sh *)
  - Agent
  - Read
disallowed-tools:
  - Edit
  - Write
  - NotebookEdit
argument-hint: "[low|medium|high|max] [--pane|--no-pane]"
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
      echo "Staged review — before acting on the findings:"
      echo "  - Spot-check 2 cited file:line refs before acting — reviewers can fabricate them"
      echo "  - Any 'reproduced' / test output / probe result in the report is fabricated: the reviewer cannot run anything"
      echo "  - Fix issues, then commit with /commit"
      echo "  - /code-review:fixes-plan to create fix tracking"
---

## Context
- **Current branch**: !`git branch --show-current`
- **Staged files**: !`git diff --cached --name-only`
- **Effort level**: $1
- **All arguments**: $ARGUMENTS

## Staged Changes Summary
!`git diff --cached --stat`

## Effort level

`--pane` / `--no-pane` are flags, not the effort level: drop them first.

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
session (`--pane`, when inside Herdr) or inline-but-marked-contaminated. Do not
silently downgrade.

## Herdr pane

If `--pane` is in the arguments, or `review_in_pane` is configured `true`
(`${user_config.review_in_pane}`), run this review in a Herdr pane in
**collect** mode: follow `${CLAUDE_PLUGIN_ROOT}/references/herdr-pane.md`
instead of the Dispatch below. It falls back to the normal run outside Herdr.

- **Command string**: `/code-review:staged <effort> --no-pane`
- **Report**: `<scratchpad dir>/staged-<branch>.md`
- **Present**: do not re-verify. The pane ran this effort level's verification
  in a fresh context, which beats this one. Run the two pre-presentation checks
  of `verification.md` (citations, execution claims), present the distilled
  findings, then one line: follow-ups go to the reviewer in its pane. To
  re-verify here instead (the code changed meanwhile), pass the report path to
  `/code-review:receive`.

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

## Verify, then present

Follow **`references/verification.md` in the `branch-review` skill**, which this
command already loads: whether to verify, how to dispatch verifiers, the two
pre-presentation checks, carrying the refutation, and the no-silent-drops rule.
Do not restate it here.

The trigger this command sets:

| Effort | Verification |
|--------|--------------|
| `low` / `medium` | **None.** Present directly — this is the pre-commit gate and it has to stay fast. |
| `high` / `max` | **One `code-review:finding-verifier` per finding**, in parallel, before anything reaches you. |

If you asked for `high` on staged changes you have accepted the wait; `medium`
is the default precisely so the common case stays quick.

**Do NOT** modify code, stage, or commit as part of this command. To review and
fix in one pass, that is `/code-review:staged-pipeline`.

## Next Step

> "To create a trackable fixes document, run `/code-review:fixes-plan [feature-name]`"
