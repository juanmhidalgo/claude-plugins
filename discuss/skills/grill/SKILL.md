---
name: grill
description: |
  Use when the user wants to be interviewed until every decision in a plan, design, or
  idea is settled: "grill me", "interview me about this", "what do I still need to
  decide", "ask me everything before we start". Asks in rounds, each question with a
  recommended answer, and ends with a ledger of decisions. Does not implement.
  Do NOT use to argue against a proposal (/discuss:challenge), for a one-pass critique
  (/discuss:feature), to compare known options (/discuss:tradeoffs), or to write the
  spec (/feature-dev:spec).
argument-hint: "<plan, decision, or idea>"
allowed-tools: [Read, Glob, Grep, Agent]
keywords:
  - interview
  - grilling
  - decisions
  - alignment
triggers:
  - "grill me"
  - "interview me about this"
  - "what do I still need to decide"
---

# Grill

Interview the user until you both share one understanding of: **$ARGUMENTS**

## The design tree

Model the topic as a **design tree**: each decision branches into the decisions that depend on it. The **frontier** is every open decision whose prerequisites are already settled, the questions you can ask now without guessing at answers you have not heard yet.

## Rounds

Each round, ask the whole frontier at once, in plain text, in the conversation's language:

```
**Q1 - <title>**: <the question; options if there are any>
→ Recommended: <answer> - <one-line why>

**Q2 - <title>**: ...
```

- Word each question so "yes" accepts the recommendation.
- Number questions across rounds (round 2 starts where round 1 ended), so the user can reply `1 yes, 3 no: <reason>`.
- A question whose answer depends on another question open in this round belongs to a later round.
- Ask in plain text, not AskUserQuestion: a picker pushes the question toward canned choices, and a frontier is often larger than one picker holds.

A question the user skipped stays open: ask it again next round, never record it as accepted. After each reply, recompute the frontier: settled decisions unblock the ones that hung on them. Then ask the next round.

## Facts are yours, decisions are the user's

When a question needs a fact from the code, the repo, or the environment, find it yourself: dispatch an Agent with `subagent_type: "Explore"` and `model: "sonnet"`. Only the questions downstream of that fact wait for it; ask the rest of the frontier now.

There is no cap on questions. Every question must be a decision that changes the outcome; a fact you could look up is never a question. The user can end early by saying "wrap up": then go straight to the ledger and list what is still open.

## Done

Done when the frontier is empty: every branch visited, nothing silently assumed. Then:

1. Print the **decision ledger**: `# | decision | answer | decided by (user / accepted recommendation)`, plus any branch left open.
2. Ask the user to confirm it.
3. End with: `Next: /feature-dev:spec <topic> to turn these decisions into a spec.`

Write no code and no files.

<!-- Adapted from mattpocock/skills `grilling`. Copyright (c) 2026 Matt Pocock, MIT License. -->
