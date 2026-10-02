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

## Stale memory check

Claude Code's auto-memory (`~/.claude/projects/<project>/memory/*.md`, indexed by
`MEMORY.md`) is recalled by every session, and nothing re-checks it. A memory that said "this
repo's hooks write to stderr, not yet fixed" stays in the index after the commit that fixed
them — the hook files keep their names, so a path-existence check never notices. retro checks
memories three ways, and runs at session start, from `/memory-check`, and inside
`/retro:session`.

### `scripts/memory-check.sh`

```bash
retro/scripts/memory-check.sh                         # this project's memory, derived from $PWD
retro/scripts/memory-check.sh --days 14               # age threshold (default 30)
retro/scripts/memory-check.sh --quiet-unless-stale    # only STALE and MISSING-REF
retro/scripts/memory-check.sh --json                  # [{kind, file, detail}]
retro/scripts/memory-check.sh --memory-dir <dir> --project-root <dir>
retro/scripts/memory-check.sh --no-predicates         # never run verify: commands
```

One line per finding, `<KIND> <file> — <detail>`, and nothing at all when clean. It always
exits 0 (it is advisory); 2 means a usage error.

| Kind | Meaning |
|---|---|
| `STALE` | The memory's `verify:` command exited non-zero, or ran past the 5 s timeout. |
| `MISSING-REF` | A backticked repo path that does not exist, a 7–40 char commit hash `git cat-file -e` cannot find, or a `MEMORY.md` link to a missing file. |
| `UNVERIFIED-OLD` | A `type: project` memory with no `verify:`, unmodified (`metadata.modified`, else file mtime) for more than `--days`. |
| `OPEN-CLAIM` | No `verify:`, and the text says "not yet fixed", "pending", "flagged" or "TODO". |
| `SKIPPED-VERIFY` | A `verify:` that was not run: a symlinked file, or more predicates than `--max-predicates`. |

The memory dir is found the way Claude Code keys it: from the git repository, so every
worktree and subdirectory of a repo shares the main checkout's memory. Paths resolve
against the current git top level. A path whose first segment does not exist in the repo
(`some-package/sub`) is treated as not a repo path and skipped, and fenced code blocks are
not scanned.

### The `verify:` convention

Add an optional single-line `verify:` field to a memory's frontmatter: a shell command that
**exits 0 while the memory's claim is still true**. Single-quote it in YAML (a literal `'`
is written `''`), keep it on one line, and put no comment after it.

A file still lacks a fix (the real case above):

```yaml
---
name: hook-writes-stderr
description: "hooks/check.sh writes advice to stderr, which never reaches Claude — not yet fixed"
verify: '! grep -q additionalContext hooks/check.sh'
metadata:
  type: project
---
```

A function still exists, and a flag is still in `--help`:

```yaml
verify: 'grep -qE "^def legacy_export\(" app/export.py'
verify: './bin/tool --help 2>&1 | grep -q -- "--dry-run"'
```

When the fix lands, the predicate fails, the next session starts with a `STALE` warning, and
the memory gets updated or deleted instead of acted on. A memory with a `verify:` is exempt
from the `UNVERIFIED-OLD` and `OPEN-CLAIM` heuristics — the predicate is the better check.

**Security.** A `verify:` is a shell command run with your permissions, at every session
start. memory-check only runs predicates from regular files directly inside the project's
own memory dir — never from a symlink or any other location — with `bash -c` from the project
root, stdin closed, output discarded, and a 5 s timeout that kills the whole process group.
Write predicates that are fast, read-only and offline. Memory files are written by Claude, so
review a `verify:` line the first time you see one; `--no-predicates` turns them all off.

### Session-start hook

`hooks/hooks.json` registers a `SessionStart` command hook that runs
`memory-check.sh --quiet-unless-stale --max-predicates 20` (with more than 20 predicates it
runs none). Only when there are findings it adds context telling Claude which memories may
be stale and to verify, update or delete them before relying on them. Otherwise it is silent;
about 0.5 s on a project with a dozen memories and no predicates.

To disable it: set `RETRO_MEMORY_CHECK=off` in the environment (e.g. `"env"` in
`~/.claude/settings.json`), or disable the plugin with `/plugin`.

### `/memory-check`

A command registered by the plugin's hooks module (`hooks/register.ts`). It runs
`memory-check.sh` in the session's directory and shows the result as command output — no
Claude turn. Flags pass through: `/memory-check --days 7`. Needs Claude Code 2.1.287+ (mods);
everywhere else, run the script.

## Needs

- `bash` and `jq`; `git` and `awk` for memory-check. A predicate timeout uses `timeout`
  (GNU coreutils), `gtimeout` (Homebrew coreutils) or, failing both, `perl`.
- For plugin mode: the `plugin-recorder` plugin, installed and recording (a mod; Claude Code
  2.1.287+).

## Notes on the log format

The script depends on several undocumented facts about the session-log format — the cwd
encoding, how human turns are distinguishable from tool results, where measured cost lives.
They are written down in `skills/session/references/digest-fields.md`, with what was verified
and against what. Read that before changing the script.
