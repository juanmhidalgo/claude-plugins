# retro

Session retrospectives for Claude Code, built on what the session logs actually measured.

## Why

`~/.claude/projects/<project>/<session>.jsonl` already records what a session cost, what was
denied, what a hook blocked, and where the wall clock went. A retrospective does not need to
ask you how the session felt — it needs to read those numbers and turn them into a config
change. This plugin does the second part: every finding it reports names the file that fixes it.

## Commands

### `/retro:session`

```
/retro:session                  # the most recent session in this project
/retro:session --last 3         # a three-session trend
/retro:session --session <id>   # one specific session
```

Reports, per finding: the evidence (turn number, digest line), what it cost, the destination
file, and the exact change. Then asks which to apply.

```
/retro:session how did feature-dev behave this week   # plugin mode, across projects
/retro:session --light                                 # CLAUDE.md / memory ideas from this session only
```

With no `--last` or `--session`, it digests the `default_sessions` most recent sessions
(default 1; change it with `/plugin configure retro`).

## The digest script

`scripts/session-digest.sh` is usable on its own:

```bash
retro/scripts/session-digest.sh --list                  # sessions for this project
retro/scripts/session-digest.sh --prompts               # digest + the human turns in order
retro/scripts/session-digest.sh --last 3                # digest three sessions + a rollup
retro/scripts/session-digest.sh --project ../other-repo # a different project
retro/scripts/plugin-runs.sh feature-dev --days 14      # one plugin, every project (see Scope)
```

It prints:

- **Cost & effort** — dollars, wall clock, API time, tool time, lines added/removed, and
  per-model token usage
- **Shape** — human turns (counted correctly), assistant turns, tool calls, slash commands,
  skills invoked, subagents spawned
- **Tools** — call histogram
- **Friction** — tool errors with their messages, permission denials by kind
  (`user-rejected` / `permission-rule` / `automode-blocked`), hook blocks, slowest turns
- **Human turns** — with `--prompts`, every prompt in order, numbered, so findings can cite one

Everything is measured from the log. Nothing is inferred, and nothing is reported that the
log does not contain.

## Scope

One project per run. `~/.claude/projects/` holds transcripts from every repository opened on
this machine, including work ones, so there is deliberately no "all projects" mode and the
digest never reads outside the project directory you point it at.

Plugin mode is the one explicit exception, and it reads metadata only: plugin-recorder stores
names, counts, durations and statuses, with each project reduced to its directory's basename —
no prompt text, no tool inputs beyond `subagent_type`, no paths. It never opens a transcript.

### Plugin mode (`plugin-runs.sh`, or `session-digest.sh --plugin <name>`)

Reads the files the [`plugin-recorder`](../plugin-recorder/README.md) mod writes
(`~/.claude/plugins/data/plugin-recorder-*/sessions/*.jsonl`) and prints, for one plugin:
invocations by command/skill and version, subagent calls by `subagent_type` with their
failures (error, denied, refused at spawn), main-loop and subagent turn durations, and a
breakdown by project basename. Without plugin-recorder it prints a notice and exits 0.

## Needs

- `bash` and `jq`.
- For plugin mode: the `plugin-recorder` plugin, installed and recording (a mod; Claude Code
  2.1.287+).

## Notes on the log format

The script depends on several undocumented facts about the session-log format — the cwd
encoding, how human turns are distinguishable from tool results, where measured cost lives.
They are written down in `skills/session/references/digest-fields.md`, with what was verified
and against what. Read that before changing the script.
