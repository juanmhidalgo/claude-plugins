---
name: branch-review
description: |
  Use when reviewing branch changes or PRs for merge readiness with severity classification.
  Do NOT use for general code quality advice — use dedicated linters.
keywords:
  - code-review
  - branch-comparison
  - diff-analysis
  - pr-preparation
  - security-checklist
triggers:
  - "review branch changes"
  - "compare branches"
  - "analyze diff"
  - "prepare PR for merge"
  - "check code before merge"
allowed-tools:
  - Bash(git *)
  - Read
  - Grep
agent: code-review:branch-reviewer
user-invocable: true
---

# Branch Review

## Severity Classification

| Level | Block Merge? | Examples |
|-------|--------------|----------|
| CRITICAL | Yes | Security vulnerabilities, data loss risks, breaking changes without migration |
| HIGH | Should fix | Bugs affecting users, performance regressions, missing error handling |
| MEDIUM | Recommend | Code smells, minor perf issues, missing non-critical tests |
| LOW | Optional | Style issues, refactoring opportunities, docs |

## Labels (orthogonal to severity)

Two labels change how a finding is *read*, not how severe it is. Both exist so
that findings get **surfaced and marked** instead of silently dropped — a
dropped finding is indistinguishable from a review that never looked.

| Label | Meaning | Effect |
|-------|---------|--------|
| `nit` | Correct, but below the bar a senior engineer would raise in review | Never blocks. Reported in its own group, collapsed by default. |
| `pre_existing` | Real, but not introduced by these changes | Never blocks *this* merge. Reported so it can become a ticket. |

Do not use `nit` as a hedge on a finding you believe matters — that is what
LOW severity is for. `nit` means *"I am reporting this only for completeness"*.

**Never suppress a `pre_existing` finding to keep the report clean.** The rule
is "do not *block* on pre-existing issues", not "do not mention them". If the
changes made an existing problem materially worse, it is not `pre_existing` —
it is a finding against these changes.

## Confidence Classification

Severity answers "should this block merge?". Confidence answers "how strong is the evidence?". They are orthogonal — always pair both on every finding.

| Level | Meaning |
|-------|---------|
| HIGH | Verified by reading the code path end to end. Evidence is direct: cited `file:line` you opened. Not "reproducible" — you cannot run anything; see **Evidence provenance**. |
| MEDIUM | Strong inference from code patterns or framework behavior; would benefit from runtime confirmation before fixing. |
| LOW | Speculation or pattern-based concern; may not apply in this specific context. Worth flagging, not over-weighting. |

A HIGH-severity / LOW-confidence finding ("this *might* be a security bug") needs different handling than HIGH-severity / HIGH-confidence ("this *is* a security bug — block merge"). Calibrate the response to both dimensions.

## Counter-Case (Bias Check)

Every finding requires an explicit argument against itself, written *before* assigning Confidence. State the strongest case that this is a false positive, an intentional design choice, or an edge case that does not apply here.

The counter-case determines the Confidence label — it is not decorative prose:

| What the counter-case looks like | Confidence |
|---|---|
| No plausible counter-case; you read the code path and the defect holds | HIGH |
| A counter-case exists but depends on context you did **not** verify in the code | MEDIUM at most |
| The counter-case is as strong as the finding | LOW — or drop the finding entirely |

Two failure modes to avoid: a token counter-case written to satisfy the format ("this could be intentional" with no mechanism), and a counter-case that survives scrutiny but leaves Confidence at HIGH anyway. If you can articulate a real reason the code is correct, the Confidence label must move.

## Feedback Format

```markdown
**[SEVERITY] · [CONFIDENCE]** Brief title  `[nit]` `[pre_existing]` (labels only if they apply)

📍 `path/to/file.py:42`

**Issue:** Clear description of the problem

**Failure scenario:** Concrete inputs or state → the wrong output, crash, or corrupted state that results. Required on every finding.

**Evidence:** `[read]` or `[derived]` — what in the code proves (or suggests) this. Required for HIGH; recommended for MEDIUM; explicit "speculation only" if LOW

**Counter-case:** The strongest reason this may be a false positive or a deliberate choice — and what you would need to read to rule it out

**Suggestion:**
```python
# Recommended fix
```
```

### Failure scenario is the vagueness filter

`**Failure scenario:**` replaces the old `**Risk:**` field, and the change is
not cosmetic. "Risk" accepts an abstraction — *"this could cause data
integrity problems"* — which is exactly the shape a plausible-sounding false
positive takes. A failure scenario does not: it demands specific inputs or
state, and the specific wrong result.

**If you cannot write one, you do not have a finding yet.** Either go read
enough code to write it, or drop the finding. Do not fall back to restating the
issue in the future tense.

| Not a failure scenario | A failure scenario |
|---|---|
| "Could lead to a race condition" | "Two requests calling `claim()` between the `SELECT` at :41 and the `UPDATE` at :47 both see `status='open'`; both succeed; the row is assigned twice" |
| "Missing validation could cause errors" | "`POST /items` with `qty: -1` passes the serializer, reaches `reserve_stock()`, and increments available stock" |
| "May not handle empty input" | "`summarize([])` hits `max()` on an empty sequence at :88 and raises `ValueError` instead of returning 0" |

For a `nit` or a maintainability finding where nothing *fails* at runtime, state
the concrete cost instead: what a future change will get wrong, and where.

## Evidence provenance

<iron_law priority="blocking">

**Never claim to have executed anything. Your tools are your evidence ceiling:
if you could not run it, you did not run it.**

</iron_law>

A review agent is read-only. It cannot run a test suite, a linter, a script, or
a probe, and it cannot write one. Every piece of evidence therefore carries one
of two labels, and there is no third:

| Label | Means |
|-------|-------|
| `[read]` | You opened the file and the cited lines say what you claim. Cite `path:line`. |
| `[derived]` | You reasoned from what you read — a data path traced across files, an inferred call order. Name the reads it rests on. |

**Forbidden, in any phrasing:** "Reproduced." · "I ran the tests, all pass." ·
"ruff reports 3 findings." · "A probe test fails with `AssertionError: …`" ·
"Verified by executing…" · quoting output, exit codes, timings, or test counts.

Not a loophole: describing a probe *in the subjunctive* is fine and useful.
Write it as something the reader should run, and say plainly that you have not:

> **Suggested probe (not run):** patch the transport, call the function twice,
> assert one POST. If dedup is working this passes; I predict it fails at 2.

### Why this rule exists

It was written after a real review that got the finding right and invented the
corroboration — *"Reproduced. A probe test … fails with `AssertionError:
expected dedup to suppress the second post, got 2`"* — from an agent whose
tools made all of it impossible. The defect was genuine and independently
confirmed by reading the file.

That combination is worse than a false positive, not better. A wrong finding
dies the first time someone checks it. A **true** finding wrapped in fabricated
proof teaches the reader that checking is unnecessary, and the habit it builds
is the thing that eventually ships a bug.

Note what was actually happening: the tool restrictions worked — nothing ran.
The agent narrated the verification it could not perform. **Restricting
capability without constraining claims produces fabricated compliance**, so the
constraint has to be stated, not implied by the tool list.

| Rationalization | Why It's Wrong |
|----------------|----------------|
| "The finding is true, so the evidence framing is a detail" | The framing is what tells the reader whether to check. Getting it wrong on a true finding is how you disarm the next check. |
| "Saying I verified it makes the report more useful" | It makes it more *persuasive*, which is the opposite of useful when it is not true. |
| "I can tell what the test would do, so reporting the result is equivalent" | A prediction and a result are different objects. Label it a prediction and it stays useful; label it a result and it is a fabrication. |

## Reporting nothing

If no finding survives verification, say so explicitly: **"No findings."**
plus what was actually examined (files, and what you looked for).

An empty result is a real, reportable outcome — but a silent one is
indistinguishable from a review that failed to run. Never let dropped findings
vanish without a count: report `N dropped (M incorrect, K pre-existing)`.

## After the findings exist

What happens between a reviewer producing findings and a user reading them —
verification at `high`/`max`, the two pre-presentation checks, carrying the
refutation, and the no-silent-drops rule — is defined once in
[verification.md](references/verification.md).

It is not restated in the commands. Six copies of a protocol is one copy that
drifts, which already happened to this plugin's analysis-focus block.

## Accounting block

Close every report with this, even an empty one:

```
Effort:   <the level you were given>
Examined: <files, and what you looked for>
Findings: <n> (<n> critical, <n> high, <n> medium, <n> low)
Labels:   <n> pre_existing, <n> nit
Dropped:  <n> — <one line each on why>
```

**`Effort` is not optional.** A reader cannot interpret `Dropped: 6` without
it: at `low` a drop may mean "out of reporting range", at `max` it can only
mean "refuted". Same number, opposite meanings. If a finding was dropped
*because of* the level rather than on the merits, say so in its line.

## Focus Areas (Non-Obvious)

**Security** - Hardcoded secrets, missing input validation, SQL injection, auth gaps. For deeper threat modeling and OWASP-aligned analysis, delegate to the **`security:security-hardening`** skill rather than expanding this section — that skill is the canonical security reference.

**Bugs** - Race conditions in concurrent code, resource leaks (connections, file handles)

**Performance** - N+1 queries, blocking calls in async contexts, missing pagination. For load profiling and Core Web Vitals analysis, delegate to **`performance:performance-optimization`** rather than diagnosing here.

## Review Anti-Patterns

1. **Nitpicking** - Don't block on minor style issues
2. **Rubber stamping** - Actually read the code
3. **Bike-shedding** - Focus on important issues
4. **No context** - Understand the "why" before criticizing

## Request Changes vs Comment

**Request Changes:** Security issues, bugs affecting users, breaking changes, missing critical tests

**Comment Only:** Suggestions, questions about approach, style preferences, future considerations
