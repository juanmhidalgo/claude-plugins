---
name: session
description: |
  Use when asked for a retrospective or post-mortem of a Claude Code session — "how did that
  session go", "what should we change about how we worked", "analyze the last N sessions".
  Reads the session logs for THIS project, reports measured cost/friction, and turns each
  friction point into a concrete config change (CLAUDE.md rule, memory file, permission rule,
  hook, or a fix to a plugin in this repo).
  Do NOT use to review the code that was written (use /code-review:*), to summarize git history,
  or to analyze sessions from another project without being pointed at it explicitly.
argument-hint: "[--last N] [--session <id>] [--project <dir>]"
keywords:
  - retrospective
  - post-mortem
  - session-analysis
  - workflow-improvement
  - friction
triggers:
  - "do a retrospective"
  - "how did that session go"
  - "what could we improve about how we worked"
  - "analyze my last sessions"
  - "post-mortem of this session"
allowed-tools:
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/session-digest.sh *)
  - Read
  - Edit
  - Write
  - Grep
  - Glob
  - AskUserQuestion
---

# Session Retrospective

Turns a Claude Code session into **config changes**, not a report nobody reads.

## Scope guard

One project at a time. `~/.claude/projects/` holds transcripts from every repo ever
opened here, including work ones — never widen to all projects, and never read another
project's logs unless the user names it.

## Phase 1 — Measure

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/session-digest.sh --list                 # what's available
${CLAUDE_PLUGIN_ROOT}/scripts/session-digest.sh --prompts              # most recent session
${CLAUDE_PLUGIN_ROOT}/scripts/session-digest.sh --last 3 --prompts     # a trend
```

Everything the digest prints is measured from the log. See
[digest-fields.md](references/digest-fields.md) for what each section means and for the
log-schema facts the script relies on (they are not obvious and are easy to get wrong).

**When running inside the session being analyzed**, do not re-read the transcript — the
conversation is already in context. Run the digest anyway: wall clock, denials and hook
blocks are not visible from inside the conversation. Expect **no cost figure** — that record
is flushed at session end — so rank by wall clock and denials, and say cost was unavailable
rather than estimating it.

## Phase 2 — Find friction

Rank by cost, in this order:

1. **Denials and hook blocks** — every one is a round trip that produced nothing.
2. **Repeated corrections** — the same instruction given twice is a missing standing rule.
   Read the human turns in order; a correction is a turn that redirects the previous one.
3. **Slow turns** — cross-check the slowest turns against what was happening in those turns.
4. **Tool errors** — clustered errors on one tool mean a wrong approach, not bad luck.
5. **Abandoned work** — a thread started and never finished.

<evidence_rule priority="critical">
Every finding cites its evidence: a turn number from `--prompts`, a digest line, or a
timestamp. A finding you cannot cite is a finding you invented — drop it. Do not claim to
have measured something the digest does not print.
</evidence_rule>

## Phase 3 — Route each finding to a destination

Each finding must name **where the fix lives**. A finding with no destination is an
observation, and observations do not change the next session. Mapping table and the repo
rules that apply when the destination is a plugin:
[action-mapping.md](references/action-mapping.md).

## Phase 4 — Report, then apply

Report format, one block per finding:

```
FINDING — <one line>
  Evidence:    turn 7, turn 11 | digest: "permission denials: 2 — Bash | permission-rule"
  Cost:        <what it cost: minutes, dollars, a failed thread>
  Destination: <file to change>
  Change:      <the concrete edit, quoted>
```

Close with a **Keep doing** section — one or two things the digest shows worked — and then
ask which changes to apply. Apply only what the user picks; edit the named files directly.

## What this is not

Not a code review of what was built. Not a git-history summary. Not a satisfaction survey —
do not ask the user to rate the session on a scale; the log already says what it cost.
