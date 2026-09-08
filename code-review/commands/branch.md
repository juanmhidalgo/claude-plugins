---
allowed-tools:
  - Bash(git *)
  - Agent
  - Read
disallowed-tools:
  - Edit
  - Write
  - NotebookEdit
argument-hint: "[base-branch] [low|medium|high|max]"
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
      echo "Branch review complete."
      echo "  - Spot-check 2 cited file:line refs before acting — reviewers can fabricate them"
      echo "  - Any 'reproduced' / test output / probe result in the report is fabricated: the reviewer cannot run anything"
      echo "  - /code-review:fixes-plan to create fix tracking"
      echo "  - /code-review:tech-debt for maintainability analysis"
---

## Context
- **Current branch**: !`git branch --show-current`
- **Specified base**: $1
- **Effort level**: $2

## Base branch

Use `$1` if provided. Otherwise `main`, falling back to `master`.

## Effort level

`$2` is one of `low | medium | high | max`, default `medium`. It sets how much
uncertainty reaches you:

- `low` / `medium` — only findings the reviewer verified against the code path
- `high` / `max` — broader coverage, including findings resting on context the
  reviewer could not confirm, each marked as such

If `$2` is empty, read `pr_effort:` from `.claude/code-review.local.md` and
reuse it; else `medium`.

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
why, then offer: run it in a fresh session, or run it inline and mark the
report as context-contaminated. Do not silently downgrade.

## Dispatch

Use the Agent tool with `subagent_type="code-review:branch-reviewer"`.

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
