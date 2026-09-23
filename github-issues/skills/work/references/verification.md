# Verification

The goal is to find out, before planning, whether the issue still describes the code at
HEAD — and where it doesn't, what it should say instead.

## What counts as a claim

Anything the implementation would rely on:

- **Locations** — `path/file.py:123`, function and class names.
- **Behavior** — "X returns None when…", "Y is never called", "Z raises on…".
- **Absence** — "no migration seeds…", "nothing enforces…", "a grep shows no caller".
  These are the easiest to get wrong and the most expensive when wrong: re-run the search.
- **Measurements** — query counts, timings, row counts.
- **Environment** — feature flags, settings, "while FLAG is off", rollout state. Check that
  the flag or setting still exists; issues outlive the flags they describe.
- **Cross-references** — "fixed by #N", "blocked by #N", "after #N merges". Check the
  current state of #N.
- **Comments** — a triage comment saying "re-checked, fix still valid" checked something;
  find out what, and whether it is what the fix depends on.
- **Consumer interpretation** — when the change alters something other code reads: what
  that field, permission, or endpoint *means* to the code that reads it (a frontend route guard, a role grant in another service). An issue can be
  right about the code and wrong about what it is for.
- **Impact** — who hits it and how often, the stated priority, the caller list. A code claim
  can be right while its impact is overstated or, worse, understated: an incomplete caller
  list hides the path that matters. Give the impact its own row.
- **The suggested fix** — that it compiles against current signatures, that its callers
  accept the change, that it follows the repo's own rules.

## Statuses

| Status | Meaning |
|---|---|
| CONFIRMED | Holds at HEAD. |
| DRIFTED | True, but the location or name moved. Record the current one. |
| REFUTED | False at HEAD. Record the evidence. |
| ALREADY FIXED | Was true, a later commit or PR changed it. Name the commit. |
| UNVERIFIED | Not checked, or cannot be checked locally (needs prod data, credentials, another service). Say what would check it. |

Every row also records **how**: `ran` (a test, a probe, a query — include the command),
`read` (code at HEAD), or `not checked`. A row that says `ran` must correspond to a command
you actually executed in this session. When a claim was only read, write `read` — reading a
plausible code path is not a reproduction. A row checked both ways is `read + ran`; say in
Evidence which part was run.

Evidence from a sibling repo records that repo's HEAD and whether it was fetched — a stale
checkout is weaker evidence than the repo under work, and the verdict should say so.

## Ledger format

```
### Verification ledger — #{number} at {HEAD sha}

| # | Claim (as the issue states it) | Status | How | Evidence |
|---|---|---|---|---|
| 1 | `report.py:147` dereferences `report.is_v3` without a None check | DRIFTED | read | now `report.py:152`, same code |
| 2 | "require_permission is a no-op while FLAG is off" | REFUTED | read | FLAG removed in abc1234; the call enforces unconditionally |
| 3 | 7 queries per row | CONFIRMED | ran | `pytest tests/test_x.py::test_counts` → 29 / 78 |
| 4 | Suggested fix: annotate `score` | CONFIRMED | read | same annotation used by the v2 list queryset |

**Verdict:** Actionable with corrections — row 2 changes the rollout: the change takes
effect on deploy, so the tests must not be parametrized on the removed flag.
```

## How to be fast

- Verify the claims the fix depends on first. A wrong peripheral claim is a note; a wrong
  load-bearing claim ends the phase.
- If the issue includes a reproduction command, it is the cheapest check — read it, show it
  to the user if it does anything beyond running tests, then run it.
- Use `git log -S'<identifier>'` to find when a symbol the issue relies on appeared or disappeared.
- When a claim needs access you don't have, don't guess its status — mark it UNVERIFIED,
  write the query or request that would settle it, and continue with the rest.

## Auditing an agent's ledger

A ledger built by `issue-verifier` is read before anyone relies on it:

- A `How` of `ran`, or any claim of having executed something — the agent cannot run
  anything. Downgrade the row to `read` or UNVERIFIED and say so.
- A CONFIRMED or REFUTED row without `path:line`, commit, or search evidence — treat it as
  UNVERIFIED.
- A verdict of *actionable* while a row the change depends on is REFUTED — contradictory;
  say so instead of choosing.
- An empty report — the agent hit its turn limit. The issue is not verified; don't guess.

## Posting corrections

When the ledger contains REFUTED, DRIFTED, or ALREADY FIXED rows, offer to post them to
the issue so the next reader doesn't repeat the check. Draft the comment, show it, and post
only the text the user approved.

The comment is held to the standard the issue should have met:

- Its first line states only what was checked, and says how (`ran` or `read`). A correction
  that was only read is written as one: "reading HEAD, X no longer…", not "X is fixed".
- Each correction cites the commit it was checked at and the evidence (`path:line`, commit,
  command and output).
- UNVERIFIED rows are listed as open, with the query or command that would settle them,
  ready to paste.
- It proposes, it doesn't decide: relabelling, closing, or picking an option stays with the
  maintainers.
