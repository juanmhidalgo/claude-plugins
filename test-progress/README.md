# test-progress

A mod (a plugin of function hooks) that draws a one-line band above the prompt while
Claude runs a test command through the Bash tool:

```
🧪 pytest ████░░░░░░ 412/980 · 3 failed · 1m10s     # pytest with the progress plugin
🧪 go test · running 1m10s                          # any other runner, or no progress file
```

When the command ends, the band turns into a summary row that stays until your next
prompt (or until you press **Dismiss**):

```
🧪 pytest done · 977 passed · 3 failed · 2m10s
🧪 cargo test done · exit code 101 · 2m10s          # counts unknown
```

The failed count is drawn in red. The band sits **above** whatever the engine or other
plugins draw in that slot; it does not replace them, and it does not touch your status
line, so an existing status line segment for tests keeps working alongside it.

## Needs

- Claude Code **2.1.287+** (hooks modules / mods).
- The **terminal CLI**. The band is drawn on the terminal surface (and the desktop Code
  tab); `claude -p` and the VS Code extension run the hooks but draw nothing.
- For live counts: the bundled **pytest plugin** (below). Without it the band shows the
  runner and elapsed time only. Other runners (`go test`, `cargo test`, `vitest`, ...)
  always show that form; their summary uses the exit code.

## Enabling the pytest plugin

`pytest/claude_progress.py` writes the progress file. A plugin cannot set environment
variables for the Bash tool, so load it yourself, once, in your shell profile:

```bash
export PYTHONPATH="/path/to/test-progress/pytest${PYTHONPATH:+:$PYTHONPATH}"
export PYTEST_ADDOPTS="-p claude_progress"
```

or per project, with that directory on `PYTHONPATH`, in `pytest.ini`:

```ini
[pytest]
addopts = -p claude_progress
```

Outside a Claude Code session (`CLAUDE_CODE_SESSION_ID` unset) the plugin does nothing.
It works with pytest-xdist (only the controller writes).

### The progress file

```
${TMPDIR:-/tmp}/claude-<uid>/test-progress/<CLAUDE_CODE_SESSION_ID>.progress
```

One tab-separated line, `runner  done  total  failed  started_epoch`, rewritten
atomically after each test and removed when the run ends. Any runner may write the same
file to get counts in the band. A mod cannot read the uid, so the mod finds the
`claude-<uid>` directory by listing `$TMPDIR` and `/tmp` for `claude-<digits>`
directories. A file whose `started_epoch` predates the command (left by a killed run)
is ignored.

## What counts as a test command

Matched at **command position** only, after `&&`, `;`, `|`, `(`, a newline, leading
`VAR=value` assignments, and wrappers such as `uv run`, `poetry run`, `npx`, `time`,
`timeout 600`, `env`:

`pytest`, `py.test`, `python -m pytest`, `uv run pytest`, `poetry run pytest`,
`make test` (and `make test-*`), `npm test` / `npm run test*`, `pnpm test`, `yarn test`,
`bun test`, `vitest`, `jest`, `npx vitest`, `pnpm vitest`, `go test`, `cargo test`.

Not matched: a runner named as an argument (`grep pytest`, `pip install pytest`), inside
quotes (`echo "make test"`, `bash -c "pytest"`), inside a heredoc body or a comment, and
project scripts that wrap a runner under another name (`python manage.py test`, `./ci.sh`).

## Background runs

- `run_in_background: true` returns at once, so there is nothing to time: the band
  shows `🧪 pytest · started in background` until the next prompt, and does not poll.
- A run moved to the background mid-way (Ctrl+B, or a timeout) ends the band's tracking:
  `🧪 pytest · moved to background after 1m10s`.

Your status line segment, if you have one, keeps covering both.

## What it stores

Nothing. State lives in the session's memory (`$.state`) and is gone when the session
ends. No `$.store`, no files written.

## Security

Mods are **unsandboxed JavaScript running with your user's permissions** inside the
Claude Code process. This one reads `TMPDIR`, lists `$TMPDIR` and `/tmp`, and reads only
`claude-<uid>/test-progress/<session-id>.progress` there. It reads the Bash tool's
output text in memory to parse pytest's summary line, and keeps only the counts. It
writes nothing. `claude plugin validate test-progress` lists exactly what it hooks and
calls. Read `hooks/` before installing, as you would any code you run.

## Development

```bash
claude plugin validate --strict test-progress
claude plugin test test-progress
claude --plugin-dir test-progress         # try it live
```

Run `claude plugin test` from a plain shell. Started from inside a Claude Code session,
it inherits that session's child-process environment and reports hooks modules as
turned off; clear it first, e.g.
`env -u CLAUDECODE -u CLAUDE_CODE_CHILD_SESSION -u CLAUDE_CODE_ENTRYPOINT claude plugin test test-progress`.
