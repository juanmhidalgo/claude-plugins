# Digest fields and the log schema behind them

Facts verified against real local session logs (Claude Code 2.1.272). They are not
documented anywhere and every one of them is a trap someone has already fallen into.

## Where the logs live

`~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`

The encoding replaces **`/`, `.` and `_`** with `-`. Verified against every local project
directory that has logs: 26 matches, 0 mismatches. Replacing only `/` — the obvious
implementation — silently finds nothing for any path containing a dot (`~/.claude`
becomes `-home-<user>--claude`, note the double dash).

## Entry types in one file

A session file is not just a conversation. Types seen in practice:

| Type | What it is |
|------|-----------|
| `assistant` / `user` | the conversation |
| `attachment` | injected file/context payloads — often the most numerous type |
| `cost-state` | the measured totals (see below) |
| `system` | `subtype`: `turn_duration`, `stop_hook_summary`, `local_command`, `away_summary` |
| `file-history-snapshot` / `file-history-delta` | edit tracking |
| `permission-mode`, `mode`, `last-prompt`, `ai-title`, `queue-operation` | UI/session state |

## Counting human turns

**Do not count `{"type":"user"}` entries.** In a measured sample, 484 of 587 user entries
were `tool_result` payloads, 15 were injected meta, and only ~88 were actually the person
typing. Counting the raw type over-reports human input by roughly 6x.

A human turn is: `type == "user"`, `isMeta != true`, `isSidechain != true`, content is a
string or `text` block (never `tool_result`), and does not start with
`<local-command-stdout>`, `Caveat:` or `<task-notification>`.

Slash-command invocations arrive as human turns wrapping `<command-name>…</command-name>`.

## Subagents

`isSidechain` is **false on every entry** in current versions — subagent transcripts are not
inlined into the parent session file. Any metric that splits "main thread vs subagent" on
that flag will report 0 forever. Delegation is measured instead by counting `Agent`/`Task`
tool calls and reading their `subagent_type`.

## cost-state — the only measured cost

The last `cost-state` entry carries `totalCostUSD`, `totalDuration` (wall clock, ms),
`totalAPIDuration`, `totalToolDuration`, `totalLinesAdded` / `totalLinesRemoved`, and a
`modelUsage` map with per-model input/output/thinking/cache tokens.

It is flushed at session end, not continuously: 2 of 9 sessions in one sampled project have
none at all, and a session that is still open — including the one you are running the digest
from — will usually have no record yet. The digest says so rather than reporting zero.

**This is the common case when running a retro on the current session**, and it removes the
one number that ranks findings best. When there is no `COST & EFFORT` block, rank by wall
clock (`slowest turns`), denials and hook blocks instead, and say in the report that cost was
unavailable — do not estimate it. For a cost figure, target a finished session by id.

## Friction signals

- **`toolDenialKind`** on a user entry: `user-rejected` (the person said no),
  `permission-rule` (a settings rule blocked it), `automode-blocked` (the auto-mode
  classifier blocked it). The tool name is on the matching assistant `tool_use`, joined by
  `tool_use_id`.
- **`is_error: true`** on a `tool_result`: failed tool call. Hook denials also surface here,
  with the hook's message as the error text.
- **`preventedContinuation`** / **`hookErrors`**: a Stop hook blocked or errored.
- **`system` / `turn_duration`** with `durationMs`: per-turn wall clock. The slowest turns
  are where the session actually spent its time.

## Performance

The script streams: `grep -m1` for header fields, per-line `jq` elsewhere, and a
`tool_use_id` join through sorted temp files rather than slurping the file. A 2.8 MB
session digests without loading into memory.
