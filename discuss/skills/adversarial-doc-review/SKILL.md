---
name: adversarial-doc-review
description: |
  Use to adversarially review a technical document that already exists as a file —
  PRD, ADR, technical spec, design doc, RFC, or system/architecture documentation —
  to catch what would lead to a bad architecture, design, or implementation decision.
  Also use when asked to "review", "sanity check", "poke holes in", "red team", or
  "get a second opinion on" such a document, even without the word adversarial.
  Do NOT use for: proofreading, completeness checklists (/feature-dev:spec-review),
  code review (/code-review:*), an idea still in conversation with no file
  (/discuss:challenge), READMEs, changelogs, or runbooks and operational procedures.
argument-hint: "<doc-path> [design|descriptive]"
allowed-tools:
  - Read
  - Glob
  - Agent
  - AskUserQuestion
keywords:
  - adversarial-review
  - doc-review
  - red-team
  - design-doc
  - adr
  - rfc
  - spec-review
triggers:
  - "poke holes in this doc"
  - "red team this design doc"
  - "review this ADR"
  - "sanity check this spec"
  - "second opinion on this architecture doc"
hooks:
  - event: Stop
    once: true
    command: |
      echo "Adversarial doc review complete. Before acting on it:"
      echo "  - Spot-check 2 entries in 'Falsification attempts' — grep patterns can be fabricated"
      echo "  - Empty falsification log + zero findings = failed review, re-run it"
      echo "Next steps:"
      echo "  - Fixed the doc? Re-run this review on it — fix rounds introduce defects too"
      echo "  - /discuss:tradeoffs   if a finding opened a real choice"
      echo "  - /feature-dev:spec-review   for structural completeness (different axis)"
---

# Adversarial Doc Review

Dispatches a reviewer that hunts for the subset of documentation problems
that actually matter: the ones that cause a bad architecture, design, or
implementation decision. It is not a proofreader and not a completeness
checker.

The reviewer is the `discuss:doc-adversary` subagent.

## Why this is dispatched and not inlined

The review depends on the reviewer forming an independent model of the
problem **before** absorbing the document's framing. That is impossible in a
context window that already contains the document, its drafts, or the
discussion that produced it — the framing is already there and the blind-read
phase becomes theater.

**Therefore: always run the reviewer in a fresh context.** Never perform this
review yourself in the main conversation.

If subagents are unavailable, tell the user plainly that the review will be
weaker and why, and offer these fallbacks in order:

1. Run the reviewer in a new session with only the doc path and the repo.
2. Run it inline anyway, and mark the report as context-contaminated.

Do not silently downgrade. The contamination is the single largest failure
mode of this skill.

## Dispatch

Use the Agent tool with `subagent_type: "discuss:doc-adversary"`. **Do not
give it a `name:`, and do not deliberately background it.**

Do not assume that gets you a blocking call that hands back the report inline.
Depending on the harness, an Agent call may run async no matter how you invoke
it, returning a task id and notifying you later. **Never build the review
around the report coming back in the tool result.** `OUTPUT_PATH` below is the
channel that works everywhere; treat anything the tool result happens to
contain as a bonus.

Pass the reviewer **paths, never content**. Do not summarize the document,
do not paste excerpts, do not explain what it is trying to do, do not mention
who wrote it or that it was generated. Every one of those transmits the
framing you are trying to keep out.

The prompt is four lines and nothing else:

```
DOC_PATH: docs/adr/0007-event-bus.md
MODE: design
SOURCES: <repo root>, docs/adr/
OUTPUT_PATH: <scratchpad dir>/doc-adversary-0007-event-bus.md
```

`OUTPUT_PATH` is a file you choose, in your scratchpad directory — never
inside the repo. The reviewer writes its report there **and** returns it as
its final message.

**Read the file. That is the primary channel, not a fallback.** Use whatever
came back inline only to fill in a file that is missing or empty. This
ordering is deliberate: the inline path has been observed to carry nothing at
all on a real harness, while the file has not failed. Do not invert it on the
assumption that your harness returns the report directly — verify by reading
the file first, every time.

If the agent has finished and the file is still empty with nothing inline,
the review did not happen. Say so and re-run it. Never report a silent agent
as a clean review: a report that does not arrive is indistinguishable from a
review that found nothing, and this skill tells you to treat "no findings" as
suspicious — so a lost report would be read as a clean bill of health.

Running several reviews at once: one Agent call per document, each with its
own `OUTPUT_PATH`. Never one agent for several documents — the independent
model in Phase 1 is per-problem, and merging documents merges their framing.

### Choosing MODE

- **`design`** — the document proposes decisions not yet made or not yet
  built: PRDs, ADRs under consideration, RFCs, specs. Materiality is judged
  by cost of reversal.
- **`descriptive`** — the document claims to describe a system that exists:
  architecture docs, integration docs, data model docs. Materiality is judged
  by cost of reversal *plus* divergence from the code, which is almost always
  material because later decisions rest on that base state.

When both apply (a spec that also describes current state), run `descriptive`
first — a wrong base state invalidates the design review that would follow.
When the mode is genuinely unclear from the doc's path and title alone, use
AskUserQuestion rather than reading the document to decide.

Runbooks and operational procedures are **out of scope**. Their failure mode
is an operator doing the wrong thing under pressure, which is a different
severity model. Say so rather than reviewing them badly.

## After the report

Do not act on the findings automatically.

1. Present the report as-is. Do not soften it and do not re-argue it.
2. Check the **Falsification attempts** section. A report with zero findings
   and zero falsification attempts is not a clean bill of health — it is a
   failed review. Re-run it.
3. Spot-check a couple of the cited grep patterns or `path:line` references
   before trusting a clean report. The reviewer can fabricate plausible ones.
4. Check whether the independent model was code-verified or domain-derived.
   Domain-derived findings on greenfield docs are the least reliable and
   should be treated as questions for the author, not defects.
5. Findings name decisions at risk, not fixes. Deciding is the user's job.

## After fixes are applied — re-run the review

**When the document is edited in response to the findings, review it again.**
This is not optional polish and it is where a large share of the value is.

The fix round is written by someone who has just been told what was wrong and
now believes they understand the problem. That is a worse starting position
than the original authoring, not a better one: the edits are narrow, made
under the framing of the findings, and nobody re-reads the whole document
afterward. Defects introduced while fixing are routinely as material as the
ones being fixed — a control silently dropped from a section that was only
meant to be reworded, an interface changed on one side of a contract.

Mechanics:

- Fresh dispatch, new `OUTPUT_PATH`. Same rules — paths, never content, and
  **do not tell the reviewer that this is a second pass or what the first
  round found.** That is the strongest framing you could possibly transmit,
  and it would steer the reviewer straight past whatever the fix round broke.
- Re-run at the same `MODE`, unless the edits turned a proposal into a
  description of something now built.
- Re-review after each round of edits that touches a decision. Editing prose
  in response to a finding does not start a new round.

Stop when **any** of these is true:

1. The round produces no HIGH or MEDIUM findings.
2. The round's findings are all in territory an earlier round already flagged.
   The reviewer is re-finding, not finding, and further rounds will circle.
3. You have run three rounds and the third still opens **new** HIGH territory.

Condition 3 is not a budget, it is a diagnosis. A document that yields fresh
material defects every time it is patched is not converging on correctness —
the fixes are landing on a base that was wrong further up. Stop reviewing and
say that: the finding is *about* the document, not *in* it, and the answer is
to rewrite it from the decisions it is trying to make rather than to patch it
for a fourth time. Re-reviewing a patch of a patch measures the wrong thing.

## Known limits

- On greenfield documents with no code to read, Phase 1 has no ground truth
  and the review degrades toward opinion. It is still useful for spotting
  phantom alternatives and unstated assumptions, and weakest at anything
  requiring verification.
- The prompt demands concrete grep patterns and file paths precisely so
  fabrication is checkable — which only works if step 3 above is actually done.
- Tuned to under-report rather than over-report. It will miss things. It is a
  filter on top of human review, not a replacement for it.
- The reviewer has exactly one job and one outbox. If you dispatch it in a
  shape it was not built for — named, backgrounded, or handed several
  documents — the failure is silent: you get an agent that finishes and a
  report that never arrives.

## Related

- `/discuss:challenge` — same skepticism, but for a proposal still in
  conversation with no file. Runs in the main context by design.
- `/feature-dev:spec-review` — structural completeness of a SPEC/PLAN.
  Explicitly does not judge technical merit. Complementary, not overlapping.
