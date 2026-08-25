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

Use the Agent tool with `subagent_type: "discuss:doc-adversary"`.

Pass the reviewer **paths, never content**. Do not summarize the document,
do not paste excerpts, do not explain what it is trying to do, do not mention
who wrote it or that it was generated. Every one of those transmits the
framing you are trying to keep out.

The prompt is three lines and nothing else:

```
DOC_PATH: docs/adr/0007-event-bus.md
MODE: design
SOURCES: <repo root>, docs/adr/
```

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

## Known limits

- On greenfield documents with no code to read, Phase 1 has no ground truth
  and the review degrades toward opinion. It is still useful for spotting
  phantom alternatives and unstated assumptions, and weakest at anything
  requiring verification.
- The prompt demands concrete grep patterns and file paths precisely so
  fabrication is checkable — which only works if step 3 above is actually done.
- Tuned to under-report rather than over-report. It will miss things. It is a
  filter on top of human review, not a replacement for it.

## Related

- `/discuss:challenge` — same skepticism, but for a proposal still in
  conversation with no file. Runs in the main context by design.
- `/feature-dev:spec-review` — structural completeness of a SPEC/PLAN.
  Explicitly does not judge technical merit. Complementary, not overlapping.
