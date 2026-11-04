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
argument-hint: "[base-branch] [low|medium|high|max] [--spec <path|#N>] [--pane|--no-pane]  (a --spec path cannot contain spaces)"
description: |
  Use to review branch changes for merge readiness in a reviewer that has NOT seen
  this conversation — the reviewer forms its own read of the code, so it is the right
  choice when this session wrote or planned the code under review.
  Do NOT use for staged-only review (use /code-review:staged) or PR feedback triage
  (use /code-review:triage).
keywords:
  - branch-review
  - branch-comparison
  - git-diff
  - pre-merge
  - fresh-context
triggers:
  - "review my branch"
  - "review branch changes"
  - "compare branches"
  - "review before merge"
  - "code review current branch"
skills:
  - branch-review
hooks:
  - event: Stop
    once: true
    command: |
      echo "Branch review — before acting on the findings:"
      echo "  - Spot-check 2 cited file:line refs before acting — reviewers can fabricate them"
      echo "  - Any 'reproduced' / test output / probe result in the report is fabricated: the reviewer cannot run anything"
      echo "  - /code-review:fixes-plan to create fix tracking"
      echo "  - /code-review:tech-debt for maintainability analysis"
---

## Context
- **Current branch**: !`git branch --show-current`
- **Arguments**: !`bash "${CLAUDE_PLUGIN_ROOT}/scripts/args.sh" '$ARGUMENTS'`
- **All arguments**: $ARGUMENTS

The **Arguments** line is the parsed form of what the user typed: one JSON
object with `pane`, `spec`, `effort` and `positional`. Read its fields; do not
parse the raw arguments yourself. `spec` is `null` when none was given, and
`find-spec.sh` then searches on its own; a path with spaces cannot be passed.

## Base branch

Use `positional[0]` if present. Otherwise `main`, falling back to `master`.

## Effort level

`effort` is one of `low | medium | high | max`, default `medium`. It sets how
much uncertainty reaches you:

- `low` / `medium` — only findings the reviewer verified against the code path
- `high` / `max` — broader coverage, including findings resting on context the
  reviewer could not confirm, each marked as such

If `effort` is `null`, read `pr_effort:` from `.claude/code-review.local.md`
and reuse it; else `medium`.

## Why this is dispatched and not done inline

<iron_law priority="blocking">

**Run the reviewer in a subagent. Never review the branch yourself in this
conversation.**

</iron_law>

A reviewer that already holds the conversation which produced the code inherits
its framing — every reason the code looks correct is already in the window, and
the review degrades into confirming decisions it watched being made. A subagent
starts from the diff and the repo, with no memory of why anything was written.

This is the property that distinguishes this command from an inline review, and
it is the reason to reach for it when **this session wrote the code**.

If subagents are unavailable, say plainly that the review will be weaker and
why, then offer: run it in a fresh session (`--pane`, when inside Herdr), or run
it inline and mark the report as context-contaminated. Do not silently downgrade.

## Herdr pane

Run this review in a Herdr pane when `pane` is `true`, or when `pane` is `null`
and `review_in_pane` is configured `true` (`${user_config.review_in_pane}`).
`pane: false` always wins: it is what the pane session itself receives. In the
pane, run in **collect** mode: follow `${CLAUDE_PLUGIN_ROOT}/references/herdr-pane.md`
instead of the Dispatch below. It falls back to the normal run outside Herdr.

- **Command string**: `/code-review:branch <base> <effort> [--spec <value>] --no-pane`
- **Report**: `<scratchpad dir>/branch-<branch>.md`
- **Present**: do not re-verify. The pane ran this effort level's verification
  in a fresh context, which beats this one. Run the two pre-presentation checks
  of `verification.md` (citations, execution claims), present the distilled
  findings, then one line: follow-ups go to the reviewer in its pane. To
  re-verify here instead (the code changed meanwhile), pass the report path to
  `/code-review:receive`.

## Dispatch

**At `high` / `max`**, follow **`references/workflow-path.md` in the
`branch-review` skill** instead of this section and the verifier dispatch below,
with scope `branch <current> vs base <base>`. It runs the reviewer, the spec axis
and the verifiers as one workflow. Then present as below.

**At `low` / `medium`**, use the Agent tool with `subagent_type="code-review:branch-reviewer"`.

Pass it **scope, not content** — the base branch, the effort level, and an
`OUTPUT_PATH`. Do not summarize the changes, explain the intent, paste excerpts,
or mention who wrote them or why. Each of those transmits the framing the fresh
context exists to exclude.

```
SCOPE: branch <current> vs base <base>
EFFORT: <level>
OUTPUT_PATH: <scratchpad dir>/branch-review-<branch>.md
```

The reviewer writes its full report to `OUTPUT_PATH` **and** returns it.

**Read the file — that is the primary channel**, not a fallback. Use anything
that came back inline only to fill in a file that is missing or empty. If the
agent finished and left neither, the review did not happen: say so and re-run
it. A report that never arrives is indistinguishable from a clean review, and
must never be reported as one.

`OUTPUT_PATH` also keeps this conversation clean: the full report lives in the
file, and what you bring back here is the distilled finding list.

### Spec axis

At effort `medium` and above, also review the change against the spec it was
built from, following **`references/spec-axis.md` in the `branch-review`
skill**: run `find-spec.sh --base <base> [--spec <spec>]` (the flag only when `spec` is not `null`), and if it finds a source, launch
`code-review:spec-conformance-reviewer` in the same message as the reviewer
above. Its findings are verified under the same trigger as the reviewer's and
presented in their own `### Spec` section.

## Verify, then present

Everything from here — whether to verify, how to dispatch verifiers, the two
pre-presentation checks, carrying the refutation, and the no-silent-drops rule
— follows **`references/verification.md` in the `branch-review` skill**, which
this command already loads. Follow it; do not restate it here.

The one thing this command decides is the trigger:

| Effort | Verification |
|--------|--------------|
| `low` / `medium` | **None.** The reviewer's counter-case is the check. Present directly. |
| `high` / `max` | **One `code-review:finding-verifier` per finding**, in parallel, before anything reaches the user. |

The split is deliberate. `low`/`medium` keep this a fast gate. `high`/`max`
surface findings the reviewer *could not confirm*, and shipping those straight
to you would hand the verification burden to the human at exactly the level
meant to buy more certainty.

The finding format, severity, confidence and labels also come from that skill —
it is the single source of truth for all of it.

## Next Step

> "To create a trackable fixes document, run `/code-review:fixes-plan [feature-name]`"
