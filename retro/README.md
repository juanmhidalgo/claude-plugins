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

## The digest script

`scripts/session-digest.sh` is usable on its own:

```bash
retro/scripts/session-digest.sh --list                  # sessions for this project
retro/scripts/session-digest.sh --prompts               # digest + the human turns in order
retro/scripts/session-digest.sh --last 3                # digest three sessions + a rollup
retro/scripts/session-digest.sh --project ../other-repo # a different project
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
script never reads outside the project directory you point it at.

## Requirements

`jq`.

## Notes on the log format

The script depends on several undocumented facts about the session-log format — the cwd
encoding, how human turns are distinguishable from tool results, where measured cost lives.
They are written down in `skills/session/references/digest-fields.md`, with what was verified
and against what. Read that before changing the script.
