---
allowed-tools:
  - Bash(gh pr view *)
  - Bash(gh pr diff *)
  - Bash(gh pr list *)
  - Bash(git *)
  - Agent
  - Read
  - Glob
  - Grep
disallowed-tools:
  - Edit
  - Write
  - NotebookEdit
argument-hint: "<PR number or URL> [low|medium|high|max]"
description: |
  Use when you need a thorough code review of a pull request, reported in this session.
  Do NOT use for staged or branch-only reviews (use /code-review:staged or :branch),
  and do NOT use to post a review to GitHub — this command never writes to the PR.
keywords:
  - pull-request
  - code-review
  - github-pr
  - multi-agent
  - bug-detection
  - effort-level
triggers:
  - "review this PR"
  - "review pull request"
  - "check PR for issues"
  - "code review my changes"
  - "run code review on PR"
skills:
  - branch-review
hooks:
  - event: Stop
    once: true
    command: |
      echo "PR review complete (findings reported in session, nothing posted to GitHub)."
      echo "  - /code-review:fixes-plan to create fix tracking"
      echo "  - /code-review:implement-fix to apply fixes"
      echo "  - Spot-check 2 cited file:line refs before acting — verifiers can fabricate them"
      echo "  - Any 'reproduced' / test output / probe result is fabricated: review agents cannot run anything"
---

## Pull Request Code Review

**Target PR**: $1
**Effort level**: $2
**Repository**: !`git remote get-url origin`
**Current branch**: !`git branch --show-current`

<output_contract priority="blocking">

**This command never writes to GitHub.** Findings are reported here, in this
session. Do not run `gh pr comment`, `gh pr review`, or any `gh api` write —
they are not in `allowed-tools` and are not an oversight. If the user wants
findings on the PR, that is a separate, explicit decision they make.

</output_contract>

---

## Step 0: Resolve effort level

`$2` sets how broadly the review looks and how much uncertainty reaches you.

| Level | Review dimensions | Surfaced |
|-------|-------------------|----------|
| `low` | Bug scan + CLAUDE.md compliance | `CONFIRMED` only |
| `medium` *(default)* | + code comments | `CONFIRMED`; `pre_existing` in a separate group |
| `high` | all five | `CONFIRMED` + `PLAUSIBLE` (each marked) |
| `max` | all five | everything, every label shown, nothing collapsed |

The trade is explicit: **low/medium give you fewer findings you can trust;
high/max give you broader coverage including findings that may not hold.** Pick
by what the diff costs to get wrong, not by how much output you want.

If `$2` is empty: read `.claude/code-review.local.md` for `pr_effort:` and reuse
that level. If neither exists, use `medium` and say so in the final report.
After the review, note the level used in that file so the next run inherits it.

---

## Step 1: Eligibility Check

Use Agent tool with `subagent_type="code-review:pr-eligibility-checker"` and `model="haiku"`.

**Stop conditions:**
- PR is closed or merged
- PR is a draft
- PR author is a bot (dependabot, renovate, github-actions)
- PR is trivial (only docs/config/lockfiles)

If not eligible, say why and stop.

> The old "already reviewed by Claude" check is gone: it existed to avoid
> double-posting, and this command no longer posts. Re-reviewing a PR in a new
> session is a normal thing to want.

---

## Step 2: CLAUDE.md Discovery

Use Glob to find CLAUDE.md files: `**/CLAUDE.md`. Read each one. Note the rules
relevant to the changed files — these are passed to the compliance reviewer.

---

## Step 3: PR Summary

Use Agent tool with `subagent_type="code-review:pr-summarizer"` and `model="haiku"`.

---

## Step 4: Parallel review

Launch the dimensions for the resolved effort level **in parallel** — multiple
Agent tool calls in a single message.

| # | Agent | Give it | Levels |
|---|-------|---------|--------|
| 1 | `code-review:claudemd-compliance-reviewer` | PR number, CLAUDE.md rules from Step 2, PR summary | all |
| 2 | `code-review:bug-scanner` | PR number | all |
| 3 | `code-review:code-comments-reviewer` | PR number, files changed | medium+ |
| 4 | `code-review:git-history-reviewer` | PR number, files changed | high+ |
| 5 | `code-review:pr-comments-reviewer` | PR number, files changed | high+ |

Give every agent an `OUTPUT_PATH` in your scratchpad directory
(`<scratchpad>/review-<dimension>-pr<N>.md`) and tell it to write its full
findings there **and** return them.

**Read the files. That is the primary channel.** Use whatever came back inline
only to fill in a file that is missing or empty. If an agent finished and left
neither, that dimension did not run — say so in the report rather than counting
it as clean.

### Deduplicate before verifying

Different dimensions routinely report the same defect. Merge findings that name
the same `file:line` and the same underlying cause into one, keeping the
clearest statement and noting which dimensions raised it. Verifying duplicates
separately wastes agents and inflates the report with what looks like
corroboration but is one observation counted twice.

---

## Step 5: Deduplicate and verify

Follow **`references/verification.md` in the `branch-review` skill** — dispatch
shape, verdict handling, the empty-refutation and silent-verifier rules, all of
it. Do not restate the protocol here.

`/code-review:pr` always verifies, at every effort level. Unlike `:branch` and
`:staged`, this command's findings come from up to five dimensions that never
read each other, so deduplication and a single verifying reader are what turn
five partial views into one report.

## Step 6: Filter by level

Apply the Step 0 table to the verdicts:

- `CONFIRMED` → always surfaced
- `PLAUSIBLE` → `high` / `max` only, each marked with what could not be verified
- `REFUTED` → dropped, and **counted**
- `REFUSED` → surfaced regardless of level, at the top
- `nit` / `pre_existing` → their own groups, never blocking; `nit` collapses to a
  count below `max`

## Step 7: Report in session

```markdown
## PR #<N> review — effort: <level>

### Refused (<count>)
<only if any — ref/location, what it tried, quoted text>

### Confirmed (<count>)
For each: **[SEVERITY]** title, `file:line`, failure scenario, suggested fix

### Plausible (<count>)   [high/max only]
For each: the claim, and precisely what could not be verified

### Pre-existing (<count>)
Real, not introduced here. Ticket material, not merge blockers.

### Nits (<count>)   [max only, else a count]

### Dropped: <count> refuted during verification

### Not reviewed
<dimensions that returned nothing at this effort level, or failed to report>
```

End with the one line that matters: **what would you fix before merging.**

### Before presenting

Both checks and the carry-the-refutation rule are in the shared
`references/verification.md` (Part 2). Run them.

### Citations

Every finding cites `file:line`. Use the PR head SHA
(`gh pr view <PR> --json headRefOid -q '.headRefOid'`) when a permalink helps,
but the citation itself is the `file:line` — the reader is in a terminal, not a
browser.

---

## False Positives to Avoid

Do NOT report as findings against this PR:
- Issues a linter/typechecker/compiler already catches
- Pedantic nitpicks — or, if you must, label them `nit`
- Issues on lines NOT modified in the PR — label them `pre_existing` instead
- Issues with lint-ignore comments (intentionally silenced)
- Intentional functionality changes

Note the shift: **pre-existing issues get labeled, not suppressed.** The old
rule dropped them silently, which is indistinguishable from not having looked.

---

## Important Notes

- Do NOT run build/typecheck (CI handles this)
- Keep output brief, no emojis
- Create a todo list to track progress through the steps
- Every finding needs a **failure scenario** — concrete inputs → wrong result.
  If one cannot be written, the finding does not ship. See the `branch-review`
  skill for the format and the vagueness filter.
