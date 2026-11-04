---
allowed-tools:
  - Bash(git *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/herdr-pane.sh *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/find-spec.sh *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tree-hash.sh)
  - Agent
  - Workflow
  - Read
disallowed-tools:
  - Edit
  - Write
  - NotebookEdit
argument-hint: "[low|medium|high|max] [--spec <path|#N>] [--pane|--no-pane]  (a --spec path cannot contain spaces)"
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
- **Arguments**: !`bash "${CLAUDE_PLUGIN_ROOT}/scripts/args.sh" '$ARGUMENTS'`
- **All arguments**: $ARGUMENTS

## Staged Changes Summary
!`git diff --cached --stat`

## Effort level

The **Arguments** line is the parsed form of what the user typed: one JSON
object with `pane`, `spec`, `effort` and `positional`. Read its fields; do not
parse the raw arguments yourself. `spec` is `null` when none was given, and
`find-spec.sh` then searches on its own; a path with spaces cannot be passed.
This command takes no positional argument: anything in `positional` is a typo
to mention, not a level.

`effort` is one of `low | medium | high | max`, default `medium`. `low`/`medium`
surface only findings verified against the code path; `high`/`max` add broader
coverage including findings the reviewer could not fully confirm, each marked.

If `effort` is `null`, read `pr_effort:` from `.claude/code-review.local.md`;
else `medium`.

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

Run this review in a Herdr pane when `pane` is `true`, or when `pane` is `null`
and `review_in_pane` is configured `true` (`${user_config.review_in_pane}`).
`pane: false` always wins: it is what the pane session itself receives. In the
pane, run in **collect** mode: follow `${CLAUDE_PLUGIN_ROOT}/references/herdr-pane.md`
instead of the Dispatch below. It falls back to the normal run outside Herdr.

- **Command string**: `/code-review:staged <effort> [--spec <value>] --no-pane`
- **Report**: `<scratchpad dir>/staged-<branch>.md`
- **Present**: do not re-verify. The pane ran this effort level's verification
  in a fresh context, which beats this one. Run the two pre-presentation checks
  of `verification.md` (citations, execution claims), present the distilled
  findings, then one line: follow-ups go to the reviewer in its pane. To
  re-verify here instead (the code changed meanwhile), pass the report path to
  `/code-review:receive`.

## Dispatch

**At `high` / `max`**, follow **`references/workflow-path.md` in the
`branch-review` skill** instead of this section and the verifier dispatch below,
with scope `staged changes (git diff --cached)`. It runs the reviewer, the spec
axis and the verifiers as one workflow. Then present as below.

**At `low` / `medium`**, use the Agent tool with `subagent_type="code-review:branch-reviewer"`.

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

### Spec axis

At effort `medium` and above, also review the change against the spec it was
built from, following **`references/spec-axis.md` in the `branch-review`
skill**: run `find-spec.sh --staged [--spec <spec>]` (the flag only when `spec` is not `null`), and if it finds a source, launch
`code-review:spec-conformance-reviewer` in the same message as the reviewer
above. Its findings are verified under the same trigger as the reviewer's and
presented in their own `### Spec` section.

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
