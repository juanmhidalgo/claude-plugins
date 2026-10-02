# Changelog

## [0.1.0] - 2026-10-02

### Added

- Mod (`hooks/register.tsx`) that draws a band above the prompt while a Bash test command runs: live `done/total`, failed count (red) and elapsed time from the session's progress file, polled every second, or `<runner> · running <elapsed>` without one.
- Summary row after the run (`pytest done · 977 passed · 3 failed · 2m10s`, or the exit code when counts are unknown), cleared by the next prompt or a Dismiss button. Background runs show `started in background`; runs moved to the background mid-way show `moved to background after <elapsed>`.
- Command detection at command position only (leading assignments and wrappers such as `uv run`, `npx`, `timeout` skipped; quotes, heredoc bodies and comments ignored) for pytest, `make test`, npm/pnpm/yarn/bun test, vitest, jest, `go test` and `cargo test`.
- Bundled pytest plugin (`pytest/claude_progress.py`) writing `${TMPDIR:-/tmp}/claude-<uid>/test-progress/<session-id>.progress`, removed when the run ends; xdist-aware.
- The band draws above what the engine and other plugins draw in that slot instead of replacing it, and leaves the status line alone.
- Tests (`tests/test-progress.test.ts`): detection positives and negatives, progress and summary parsing, running/progress/summary render, a stale progress file ignored, background runs, Dismiss, clearing on `prompt.submit`.
