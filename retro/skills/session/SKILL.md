---
name: session
description: |
  Use when asked for a retrospective or post-mortem of a Claude Code session — "how did that
  session go", "what should we change about how we worked", "analyze the last N sessions".
  Reads the session logs for THIS project, reports measured cost/friction, and turns each
  friction point into a concrete config change (CLAUDE.md rule, memory file, permission rule,
  hook, or a fix to a plugin in this repo).
  Also answers "how did plugin X behave (in other projects)?" from plugin-recorder's
  metadata, and a light "what should go in CLAUDE.md/memory from this session" pass.
  Do NOT use to review the code that was written (use /code-review:*), to summarize git history,
  or to read another project's transcripts without being pointed at it explicitly.
argument-hint: "[--last N] [--session <id>] [--project <dir>] [--plugin <name>] [--light]"
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
  - "how did the feature-dev plugin behave"
  - "what should I add to CLAUDE.md from this session"
allowed-tools:
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/session-digest.sh *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/plugin-runs.sh *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/memory-check.sh *)
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

**The one exception is plugin mode** (below): it reads plugin-recorder's files from every
project, which hold names, counts, durations and statuses only — no prompts, no tool
inputs, no paths beyond a project's basename. It never opens another project's transcript.

## Pick the mode

| The user asks | Mode |
|---------------|------|
| "how did that session go", "analyze the last N sessions" | **Full** — Phases 1–4 |
| "how did `<plugin>` behave", "why was `/x:y` slow over there", or pastes a session ID from another project | **Plugin** — below, then Phases 2–4 on its output |
| "what should go in CLAUDE.md / memory from this session", `--light` | **Light** — below; no log analysis |

## Plugin mode

Do not ask for session IDs. Run:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/plugin-runs.sh <plugin> [--days N] [--project <basename>]
${CLAUDE_PLUGIN_ROOT}/scripts/plugin-runs.sh --list      # which plugins were recorded
```

It reports invocations by command and version, subagent calls and failures by
`subagent_type`, turn durations, and a per-project breakdown. If it prints `No
plugin-recorder data found`, say so, suggest installing the `plugin-recorder` plugin, and
fall back to asking which project to read — the old path, one project at a time. Cite the
script's lines as evidence; a failure row with no session in this project cannot be read
deeper, so do not guess at its cause.

## Light mode

Only the current session, from the conversation already in context — no digest, no log
reads. List what a fresh session would have needed to know: corrections the user gave,
facts discovered the hard way, commands that turned out to be the right ones. For each,
name the destination (project `CLAUDE.md`, a memory file, or nothing if it is one-off) and
quote the exact text to add. Then ask which to apply. Skip Phases 1–3.

## Phase 1 — Measure

With no `--last` or `--session` given, digest the **${user_config.default_sessions}** most
recent session(s) (the `default_sessions` option; `/plugin configure retro` changes it).

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/session-digest.sh --list                 # what's available
${CLAUDE_PLUGIN_ROOT}/scripts/session-digest.sh --last ${user_config.default_sessions} --prompts
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

Then check the project's auto-memory, which every future session recalls:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/memory-check.sh            # prints nothing when clean
```

Each line is `<KIND> <file> — <detail>`. `STALE` (its `verify:` command failed) and
`MISSING-REF` (a path or commit it cites is gone) are findings for Phase 3. `UNVERIFIED-OLD`
and `OPEN-CLAIM` are weaker: report them as one grouped line, not one finding each.

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

**memory-check findings route to the memory file itself.** For each `STALE` or `MISSING-REF`
line, read the memory file and the code it describes, then propose exactly one of:

- **Update memory file `<file>`** — the fact changed; quote the corrected text, the matching
  `MEMORY.md` line, and a `verify:` command that would have caught it.
- **Delete memory file `<file>`** — the fact no longer holds or no longer matters; also drop
  its `MEMORY.md` line.

Never apply either from the checker's line alone: a failing `verify:` can be a predicate
that was written wrong. The evidence is what you read in the current code.

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
