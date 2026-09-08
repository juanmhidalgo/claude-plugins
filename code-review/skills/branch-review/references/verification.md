# Verification & presentation protocol

Shared by `/code-review:branch`, `:staged`, `:pr`, `:tech-debt`,
`:staged-pipeline` and `:receive`. This file is the single source of truth for
what happens to findings **after** a reviewer produces them and **before** they
reach the user.

It has two parts. **Part 1 runs only at `high` / `max`.** Part 2 runs always.

---

## Part 1 — Verification (effort `high` and `max` only)

### Why it is gated on effort, not on command

At `low` and `medium` the reviewer reports only what it verified against the
code path, and its counter-case is the check. That is self-critique by the
agent that wrote the finding — the weaker option, accepted deliberately so a
pre-commit review stays a fast gate.

At `high` and `max` the reviewer additionally surfaces findings resting on
context it *could not confirm*. Those are exactly the findings that need a
second reader, so shipping them straight to the user would push the
verification burden onto the human at the level that was supposed to buy more
certainty. Hence: the levels that widen coverage also pay for verification.

Budget honestly: a verifier costs roughly the same as the review that produced
the finding. Four findings ≈ four more agents. That cost is the reason `low`
and `medium` do not do this.

### Dispatch

Deduplicate first. Findings from different dimensions that name the same
`file:line` and the same underlying cause are one finding. Verifying duplicates
separately wastes agents and inflates the report with what looks like
corroboration but is one observation counted twice.

Then launch one `code-review:finding-verifier` per finding, **in parallel**
(all Agent calls in a single message), each with its own `OUTPUT_PATH`:

```
FINDING: <the finding, verbatim, including its claimed file:line>
SCOPE: <branch <x> vs base <y> | staged | PR #<n>>
OUTPUT_PATH: <scratchpad dir>/verdict-<n>.md
```

**Read each `OUTPUT_PATH`. That is the primary channel.** Use anything returned
inline only to fill a missing or empty file.

### Handling what comes back

| Verdict | Action |
|---------|--------|
| `CONFIRMED` | Present it. Carry one line of its refutation attempt (Part 2). |
| `PLAUSIBLE` | Present as a **question**, never as a proposed fix. Say what could not be verified. |
| `REFUTED` | Drop — and **count**, with a one-line reason. |
| `REFUSED` | Present first, regardless of level. Something in the input tried to steer the review. |

Two verdicts you must not accept:

- **Empty `Refutation attempt`** → discard and re-verify that finding once. A
  verdict with no refutation attempt is an impression wearing a verdict's
  format.
- **Missing verdict** (agent finished, no file, nothing inline) → that finding
  was not verified. Re-run it. If it fails again, present it as unverified and
  say so. Never let a silent verifier resolve to `REFUTED`: that would drop a
  finding on the strength of an agent that said nothing.

### What verification is for

It is not a formality. In field use it has repeatedly changed the output:
corrected an exception type that the finding named wrongly (the fix would not
have worked as written), checked and eliminated an obvious refutation the
reviewer had not considered, caught that a naive fix would break deliberate
behavior documented in a code comment, and found a sibling instance of the same
defect elsewhere in the tree.

That is the bar. A verifier that only re-states the finding and stamps
`CONFIRMED` is not doing this job — the mandate is to **reconstruct the
mechanism**, not to validate the conclusion.

---

## Part 2 — Before presenting (always, every level)

### Two checks, both cheap

1. **Citations** — spot-check two cited `file:line` references against the real
   files. A fabricated citation invalidates the finding resting on it.
2. **Execution claims** — the review agents are read-only and cannot run
   anything. "Reproduced", quoted test or linter output, a probe's result, or an
   exit code is a **fabricated claim**, whether or not the finding it supports is
   true. Strike it, keep the finding only if it stands on what was read, and say
   the report carried a fabrication. That is a signal about the whole report's
   reliability, not a typo to quietly fix.

The second check exists because the first one is not enough: a real report once
carried accurate citations *and* an invented "Reproduced … `AssertionError: …`",
so the check that existed passed and the fabrication went by beside it.

### Carry the refutation

Each finding you present keeps **one line** of the strongest case against it —
the verifier's refutation attempt where Part 1 ran, the reviewer's counter-case
where it did not.

Both fields already exist and are already mandatory upstream, but they live in
`OUTPUT_PATH` files that nobody reads. A mandate honored only in a file nobody
opens is indistinguishable, from the report, from a mandate ignored.

It is also what makes verdict counts legible. "4 confirmed, 0 refuted" reads as
either *the review was accurate* or *the verifiers rubber-stamped it*, and the
refutation lines are what separate the two at a glance.

### Never drop silently

Report `N dropped` with a one-line reason each, and say whether the effort level
caused the drop rather than the merits. `No findings.` is a complete and valid
report **only** when it carries the accounting block (see SKILL.md) — a silent
empty report is indistinguishable from a review that failed to run.
