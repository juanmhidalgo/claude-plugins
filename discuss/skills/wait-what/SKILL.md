---
name: wait-what
description: Your last message did not land. Re-explain it simply, with the context I was missing.
disable-model-invocation: true
argument-hint: "[the part that lost me]"
allowed-tools: [Read, Glob]
---

I did not follow your last message. The part that lost me, if I named it: $ARGUMENTS

Re-explain it:

- In the same language as this conversation.
- Start with one or two lines of context: what we are doing, and why this point matters now.
- Short sentences, one idea each, active voice, everyday words.
- Define each technical term the first time it appears, or replace it with the plain word. If the repo has a glossary (`GLOSSARY.md`, `CONTEXT.md`, `docs/glossary*`), use its terms; otherwise use the words I have used.
- When the point is a sequence, a flow, or a comparison, a small table or diagram may replace the prose, but only when it is shorter than the prose.
- Add only what I need to follow. Aim for shorter than the original; when the original was short and dense, defining its terms wins over length.
- End with what you need from me, if anything, as one question.

<!-- Adapted from mattpocock/skills `wait-what`. Copyright (c) 2026 Matt Pocock, MIT License. -->
