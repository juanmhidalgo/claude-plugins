---
disable-model-invocation: true
allowed-tools:
  - Bash(git *)
  - Bash(npm *)
  - Bash(npx *)
  - Bash(yarn *)
  - Bash(pnpm *)
  - Bash(pytest *)
  - Bash(python *)
  - Bash(make *)
  - Bash(cargo *)
  - Bash(go *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/features.py *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/tree-hash.sh)
  - Read
  - Glob
  - Workflow
  - AskUserQuestion
argument-hint: "[feature slug | SPEC-*.md path] [--base <branch>] [--effort high|max] [--spec <path|#N>]"
description: |
  Use after an implementation is finished — typically right after /feature-dev:tdd — to review it in
  fresh context (defects, spec conformance and tech debt at once), verify every finding, fix the ones
  you approve, and re-review what the fixes changed. Replaces running /code-review:staged,
  /code-review:receive and /code-review:tech-debt by hand.
  Do NOT use for a PR with bot comments (/code-review:triage), for a read-only review
  (/code-review:staged or :branch), or before the implementation is done.
keywords:
  - review-loop
  - harden
  - fresh-context
  - verify-findings
  - workflow
triggers:
  - "harden this feature"
  - "review and fix before shipping"
  - "run the review loop"
---

## Context
- **Current branch**: !`git branch --show-current`
- **Working tree**: !`git status --short`
- **Arguments**: $ARGUMENTS

This command resolves what to review, then runs the review loop: code-review's
`code-review:review` workflow, an approval gate, fixes and a delta review. The
reviewers never see this conversation; the session that wrote the code holds
every reason it looks right.

## 1. Resolve the scope

Strip `--base <branch>`, `--effort <level>` (default `high`) and `--spec <value>`
first; what remains is the feature, possibly empty.

- **`--base <branch>`** → the work is committed. Scope: `branch <current> vs base <branch>`.
  The working tree must be clean: fixes are told apart from the reviewed code
  by `git diff`, so edits already there would be taken for fixes. If it is
  dirty, stop and ask the user to commit or stash.
- **Otherwise** the work is the uncommitted tree (`/feature-dev:tdd` leaves it
  there). If the working tree is clean, stop: there is nothing to review.
  Run `git add -u` for modified tracked files. If there are untracked files
  (not ignored), list them and ask once with AskUserQuestion which to stage:
  **All of them (Recommended)** / **None**, or the paths through Other. A new
  module is usually part of the feature; a scratch file or a stray `.env` is
  not, and only the user can tell them apart. Scope: `staged changes (git diff --cached)`.

The index becomes the reviewed state. Fixes land in the working tree on top of
it, so `git diff` is exactly what the fixes changed, and that is what the delta
review reads.

**Spec sources.** The spec axis needs `spec-file <path>` or `issue <N> closes`
lines:

1. `--spec <path>` → `spec-file <path>`; `--spec #N` → `issue <N> closes`.
2. Else the feature: a slug or `SPEC-*.md` path in the arguments, or else the
   single entry of `${CLAUDE_PLUGIN_ROOT}/scripts/features.py list --json --root <repo root>`
   whose status is `implemented` or `running` (several → AskUserQuestion; none →
   no feature). From its folder `.feature-dev/features/<slug>/`, add
   `spec-file` for its `SPEC-*.md` and, if `feature.json` has an `issue`,
   `issue <N> closes`.
3. Else none: the spec axis is skipped, and the report says so.

## 2. Review, gate, fix

Follow `${CLAUDE_PLUGIN_ROOT}/references/review-loop.md` with:

- **scope** and **spec_sources** from step 1, **effort** from `--effort`
- **axes**: all three; no **focus**
- **title**: `Harden`

## 3. Close

```
## Harden: done
Fixed: n · declined: n · left open: n (ids)
Tests: <selection> — passing
Next: /ship
```

List what was left open by id, with its one-line title, so it can go to a
follow-up ticket.
