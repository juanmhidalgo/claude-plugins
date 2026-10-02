# Changelog

## [0.1.0] - 2026-10-02

### Added

- Mod (`hooks/register.tsx`) that records metadata-only events per session to `plugins/data/plugin-recorder-*/sessions/<session-id>.jsonl`: session start/end (cwd basename only), plugin command and skill invocations with the plugin's installed version, Agent tool calls (`subagent_type`, status, duration, tool-use and token totals), refused spawns, and turn completions (duration, reason, token usage, subagent type).
- Progress band above the prompt while subagents run: last plugin invocation, subagents done/failed this turn, the longest-running one and its age, and the turn's age. Quiet when nothing runs.
- Toast as soon as an Agent call errors or is denied, or a background subagent ends in an error.
- Tests (`tests/recorder.test.ts`): the privacy rule (no prompt text or full path reaches disk), append-not-overwrite, command/skill de-duplication, and the band's quiet and busy states.

### Why

A retro over two weeks of sessions found the user pasting session IDs from other projects to reconstruct how a plugin behaved, multi-hour `/feature-dev:tdd` turns with dozens of subagents and no progress signal, and a batch of explorer subagents that failed to spawn unnoticed.
