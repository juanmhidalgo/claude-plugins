---
name: posting-a-pr-review
description: |
  Use when the user explicitly asks to post review findings to a GitHub PR — as a
  Request changes review with inline comments on the changed lines.
  Do NOT use to run a review (/code-review:pr, :branch, :staged), to reply to or
  resolve comments already on the PR (/code-review:dismiss), or to triage another
  reviewer's feedback (/code-review:triage) — this skill only sends findings out.
  Never invoke it on your own initiative: posting is the user's decision, not a
  review's last step.
keywords:
  - post-pr-review
  - request-changes
  - inline-comments
  - github-review-api
triggers:
  - "post this to the PR"
  - "request changes on the PR"
  - "leave these as inline comments"
  - "publish the review"
---

## Posting a PR review

Reviewing never posts. This skill runs only when the user asks for it, on findings
that already exist — it does not re-review anything.

### One call, not N

Post the review and every inline comment in a **single** request. The alternative —
a loop of `gh pr review --comment` or `gh api .../comments` — sends the author one
notification per finding, and that alone is what makes an automated reviewer feel
insufferable regardless of how the comments are written.

```bash
# review.json — build the file, do not inline the JSON as -f flags:
# bodies contain newlines, backticks and quotes that argv mangles.
gh api repos/{owner}/{repo}/pulls/{number}/reviews --method POST --input review.json
```

```json
{
  "event": "REQUEST_CHANGES",
  "body": "3 blocking. 2 more in-session, not worth a line comment: …",
  "comments": [
    { "path": "src/a.py", "line": 42, "side": "RIGHT", "body": "…" },
    { "path": "src/b.py", "start_line": 10, "line": 14, "side": "RIGHT", "body": "…" }
  ]
}
```

`line` is the line in the file's post-merge state; use `side: "LEFT"` to comment on
a deleted line. `start_line` + `line` spans a range.

### What goes where

| Finding | Destination |
|---|---|
| `CONFIRMED`, requires a change, anchors to a changed line | inline comment |
| `CONFIRMED` but minor, or `PLAUSIBLE`, or pre-existing | one short line in the review body |
| `REFUTED`, or anything you could not verify | nowhere — it stays in the session |

The split is the whole point: inline interrupts the author line by line, so it is
reserved for what blocks the merge. Everything else still reaches them, in one place,
without a thread each.

**If nothing blocks, do not post a review at all.** Say so in the session. An
automated `REQUEST_CHANGES` over two nitpicks trains the author to dismiss the next one.

### Writing the comments

- **One comment per change needed**, not per observation. Two findings on the same
  line are one comment.
- **Lead with the defect.** The author can read their own diff; they do not need a
  paragraph restating it before the point.
- **Name what breaks and on what input.** "Raises on an empty `items`" beats "this
  could be problematic".
- **No praise, no preamble, no hedged suggestions.** "Consider maybe possibly" is
  either a finding or it is not.
- **Claims you did not verify are hypotheses, and say so in the first sentence** —
  not in a trailing caveat. The reviewer reads the first line and acts on it.
- **Keep an inline comment to the defect and its trigger;** anything longer belongs in the review body.
- **Use a suggestion block when the fix is a literal replacement** — the author
  clicks Apply instead of reading prose:

  ````
  ```suggestion
  if not items:
      return []
  ```
  ````

### Before posting, check two things

**You cannot request changes on your own PR** — GitHub rejects it. Compare the
author with the authenticated user and, when they match, post `event: "COMMENT"`
instead and say you did:

```bash
[ "$(gh pr view N --json author -q .author.login)" = "$(gh api user -q .login)" ]
```

**Do not repeat a point already on the PR.** A re-review is normal; a second copy of
the same comment is not. Pull what is already there and drop findings that match an
existing comment's path and line:

```bash
gh api repos/{owner}/{repo}/pulls/{number}/comments --jq '.[] | "\(.path):\(.line)"'
```

### After posting

Report the review URL and the counts — inline, body-only, dropped as duplicates.
Do not restate the findings themselves; they are on the PR now.
