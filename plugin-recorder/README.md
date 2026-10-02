# plugin-recorder

A mod (a plugin of function hooks) that keeps a **metadata-only** log of how plugins run,
so a later `/retro:session --plugin <name>` can answer "how did that plugin behave over
there?" without anyone pasting session IDs from another project. While it is loaded it also:

- draws a one-line **progress band** above the prompt while subagents run, e.g.
  `tdd · 12 subagents done · tdd-runner running 4m · turn 38m` — quiet when nothing runs;
- shows a **toast the moment a subagent call fails** (error, denied, or refused at spawn),
  naming the `subagent_type`, so a batch of failed spawns is not discovered afterwards.

## Needs

- Claude Code **2.1.287+** with hooks modules (mods) turned on for your account. They are
  behind a rollout switch: when it is off, Claude Code prints
  `hooks module not loaded: ... the rollout switch served off` and nothing is recorded.
- Terminal CLI. The band and toasts are drawn on the terminal surface; a `claude -p` run
  records (when mods load there) but draws nothing.
- To read the data: the `retro` plugin (`/retro:session --plugin <name>`), or `jq`.

## What it stores

One JSON object per line, one file per session. Every line carries `v` (schema version),
`ts` (ISO time) and `sid` (session id), plus:

| `ev` | Fields |
|------|--------|
| `session.start` | `project` (**basename** of the cwd only), `interactive`, `cc` (Claude Code version) |
| `invoke` | `kind` (`command`/`skill`), `plugin`, `name` (`feature-dev:tdd`), `version` (from `installed_plugins.json`, or null) |
| `agent` | `subagent_type`, `plugin`, `ctx` (last plugin command/skill invoked), `status` (`completed`/`async_launched`/`error`/`denied`), `durationMs`, `agentId`, `inSubagent`, `toolUses`, `tokens` |
| `agent.spawn` | a spawn the engine refused: `subagent_type`, `plugin`, `status: "denied"` |
| `turn` | `agentId` (null on the main loop), `subagent_type`, `ctx`, `reason`, `durationMs`, `model`, `usage` (`in`/`out`/`cacheRead`/`cacheWrite` token counts) |
| `session.end` | `reason` |

Only namespaced invocations (`plugin:name`) are recorded; your own un-namespaced skills
and built-in commands are not.

## What it never stores

Prompt text, command arguments, skill text, tool inputs (other than `subagent_type`), tool
results, error messages, file contents, or any full path. The project is its directory's
basename only. This matters because the same files collect sessions from every project on
the machine — work and personal.

## Where the files live

```
~/.claude/plugins/data/plugin-recorder-<marketplace>/sessions/<session-id>.jsonl
~/.claude/plugins/data/plugin-recorder-inline/sessions/<session-id>.jsonl   # --plugin-dir
```

(`$CLAUDE_CONFIG_DIR` replaces `~/.claude` when set.) This is the directory Claude Code
hands a plugin as `${CLAUDE_PLUGIN_DATA}`. A mod's `$` has no accessor for it, and the
process environment's `CLAUDE_PLUGIN_DATA` can belong to *another* plugin, so the mod
derives the path from its own install location (`plugins/cache/<marketplace>/...`).
Writes go through `$.fs.write`; each process writes only its own session's file, so
parallel sessions never share a writer. A file that outgrows the 4 MiB read cap is
continued in `<session-id>.<ms>.jsonl` rather than overwritten.

## Clearing it

```bash
rm -r ~/.claude/plugins/data/plugin-recorder-*/sessions
```

Uninstalling the plugin from its last scope also deletes its data directory.

## Security

Mods are **unsandboxed JavaScript running with your user's permissions** inside the
Claude Code process. This one reads `installed_plugins.json` (for version strings only),
reads `HOME`/`CLAUDE_CONFIG_DIR`, and writes under its data directory; `claude plugin
validate plugin-recorder` lists exactly what it hooks and calls. Read `hooks/` before
installing, as you would any code you run.

## Development

```bash
claude plugin validate --strict plugin-recorder
claude plugin test plugin-recorder          # needs the mods rollout switch on
claude --plugin-dir plugin-recorder         # try it live
```
