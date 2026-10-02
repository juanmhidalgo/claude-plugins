# Changelog

## [0.3.0] - 2026-10-02

### Added

- `scripts/memory-check.sh`: flags auto-memory files that may be stale. `STALE` when a memory's optional `verify:` frontmatter command exits non-zero or times out (5 s, whole process group killed); `MISSING-REF` for backticked repo paths that do not exist, commit hashes `git cat-file -e` cannot find, and `MEMORY.md` links to missing files; `UNVERIFIED-OLD` for `type: project` memories with no `verify:` older than `--days` (default 30); `OPEN-CLAIM` for "not yet fixed" / "pending" / "flagged" / "TODO" with no `verify:`. Flags: `--json`, `--quiet-unless-stale`, `--max-predicates`, `--no-predicates`, `--memory-dir`, `--project-root`, `--timeout`. Always exits 0 unless usage error. GNU and BSD userlands; `timeout`, `gtimeout` or a `perl` fallback.
- Predicates run only from regular files directly inside the project's own memory dir; symlinked files are reported as `SKIPPED-VERIFY` and never executed.
- `SessionStart` hook (`hooks/hooks.json`, `scripts/memory-check-hook.sh`): runs the check with `--quiet-unless-stale --max-predicates 20` and, only when there are findings, adds `additionalContext` telling Claude to verify, update or delete those memories before relying on them. Silent otherwise. Disable with `RETRO_MEMORY_CHECK=off`.
- `/memory-check` command from a hooks module (`hooks/register.ts`): runs the script and shows the result as command output, no Claude turn. Tested in `tests/memory-check.test.ts`.
- `scripts/test_memory_check.sh`: every finding kind, a predicate that flips after a commit, a predicate that hangs (both timeout implementations), output modes, the symlink and cap guards, worktree memory-dir derivation, and the hook.
- `/retro:session` runs memory-check in Phase 1 and routes `STALE` / `MISSING-REF` to "update or delete memory file X" actions; README documents the `verify:` convention.

### Changed

- The cwd → `~/.claude/projects/<name>` encoding moved to `scripts/project-dir.sh`, sourced by both `session-digest.sh` and `memory-check.sh`.

### Why

A memory said this repo's two hooks had a bug "not yet fixed". The hook files kept their names but a later commit fixed their content, and the stale memory was recalled and acted on. Only a check of the claim itself catches that.

## [0.2.0] - 2026-10-02

### Added

- Plugin mode: `scripts/plugin-runs.sh <plugin>` (also `session-digest.sh --plugin <plugin>`) reads the `plugin-recorder` mod's metadata-only files from every project and reports invocations by command and version, subagent calls and spawn failures by `subagent_type`, turn durations, and a per-project breakdown. `--days N`, `--project <basename>`, `--list`. Prints a notice and exits 0 when plugin-recorder has recorded nothing.
- The skill routes "how did plugin X behave" and pasted session IDs from other projects to plugin mode instead of asking for IDs.
- Light mode: CLAUDE.md / memory suggestions from the current session only, with no log analysis.
- `userConfig.default_sessions` (default 1): how many recent sessions a run digests when none is named, referenced in the skill as `${user_config.default_sessions}`.
- README "Needs" section.

### Changed

- Scope guard documents plugin mode as the one cross-project exception: it reads names, counts, durations and statuses, never another project's transcript.

### Why

A retro over 196 sessions found session IDs from other projects pasted seven times to reconstruct how a plugin behaved there.

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
