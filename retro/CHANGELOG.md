# Changelog

## [0.1.2] - 2026-09-15

### Changed

- Documented that `cost-state` is flushed at session end, not written continuously — 2 of 9 sessions in a sampled project have no record at all. A retro on the *current* session therefore gets no cost figure, which is the common case and removes the number that ranks findings best.
- `SKILL.md` Phase 1 no longer promises cost for the session being analyzed from inside. It now says to rank by wall clock, denials and hook blocks when the `COST & EFFORT` block is absent, and to report cost as unavailable rather than estimating it.

## [0.1.1] - 2026-09-15

### Fixed

- A permission denial no longer counts twice. It arrives as an `is_error` tool_result *and* as a `toolDenialKind` entry, so it was reported under both `tool errors` and `permission denials` — inflating the bucket Phase 2 of the skill ranks first.
- Slash-command wrappers are no longer listed as human turns. `HUMAN_TURN_FILTER` now drops `<command-name>`, `<command-message>` and `<local-command-caveat>` entries, while the new `HUMAN_RAW_FILTER` keeps them for the slash-command histogram. A session driven by slash commands reported several times its real human-turn count and buried the prose the retro cites.
- A failing command's stdout no longer bleeds into its error message. Only the first non-empty line is kept, so `Exit code 1` stays readable instead of trailing 160 characters of output.

### Why

Found by running `/retro:session` on the session that built this plugin, in a session that had not seen it built. Two of the three defects affected that run's own output.

## [0.1.0] - 2026-09-15

### Added

- `/retro:session` skill: reads this project's Claude Code session logs, reports measured cost and friction, and routes each finding to a destination file (CLAUDE.md rule, memory file, permission rule, hook, or a plugin in this repo).
- `scripts/session-digest.sh`: streaming digest of `~/.claude/projects/<encoded-cwd>/*.jsonl` — cost, wall/API/tool time, token usage per model, turn shape, tool histogram, slash commands and skills invoked, subagents spawned, tool errors, permission denials by kind, hook blocks, slowest turns, and the human turns in order. Modes: `--list`, `--session`, `--last N`, `--project`, `--prompts`.
- Reference: `digest-fields.md` documents the session-log schema the script depends on — the `[/._] → -` cwd encoding, why `{"type":"user"}` over-reports human turns ~6x, why `isSidechain` can't measure delegation, and where measured cost lives.
- Reference: `action-mapping.md` maps each friction type to the file that fixes it, including the repo's version-bump rule when the destination is a plugin here.

### Why

Existing session-retrospective plugins interview the user and fill a template. The signal
worth having is already in the logs and is measured: what the session cost, what got denied,
what blocked, where the time went. A retrospective that ends in an unapplied report changes
nothing — every finding here names a file.

### Notes

- Scoped to one project per run on purpose: `~/.claude/projects/` holds transcripts from every repo opened on this machine. There is no "all projects" mode.
- Requires `jq`.
