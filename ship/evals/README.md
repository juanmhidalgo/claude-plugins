# ship evals

Regression suite for `/ship:ship`'s early stops, run with `claude plugin eval`
(format: [Test plugins with evals](https://code.claude.com/docs/en/plugin-evals);
`claude plugin eval --help` is authoritative where the two differ). Each case
is a full `claude` child run against the plugin, so it costs real tokens.

Every case runs offline. A fake `gh` (`bin/gh`) answers the read-only lookups
`ship-preflight.sh` makes (`auth status`, `repo view` → `master`, `pr list` →
nothing, `feedback --version` → missing) and refuses every write; `run.sh`
copies it to a temp dir and puts that first on `PATH`. Each case's
`scaffold.sh` builds a two-commit repo (`README.md`, `src/app.py`) and, where
the case needs one, a bare origin in `.origin.git` (hidden through
`.git/info/exclude`) with an upstream.

All graders are deterministic (`tool_used`, `regex`). There is no LLM judge.
"Git state unchanged" is asserted as "no mutating git command was ever
called", because graders cannot run commands after the run.

## Cases

| Case | Fixture | Prompt | Preflight exit | Asserts |
|---|---|---|---|---|
| `ship-nothing-to-commit-feature-branch` | `feat/widget`, clean, pushed, 0 ahead of master | `/ship:ship` | 2 | preflight ran; no AskUserQuestion; no `git commit`/`push`/`checkout -b`/`switch -c`; no `gh pr create`; reply says nothing to ship |
| `ship-default-branch-yes-stops` | master, `README.md` modified, upstream set | `/ship:ship --yes` | 3 | preflight ran with `--yes`; no AskUserQuestion; no `git add`/`commit`/`push`/`checkout -b`; reply mentions `--yes` and the default branch |
| `ship-no-remote-stops-before-push` | `feat/widget`, `README.md` modified, no remote | `/ship:ship --yes` | 5 | preflight ran; no `git add`/`commit`/`push`; no `git remote add`; no `gh pr create`; reply says there is no remote |
| `ship-default-branch-clean-nothing-to-push` | master, clean, on origin | `/ship:ship` | 2 | preflight ran; no AskUserQuestion; no `git commit`/`push`/`checkout -b`; no `gh pr create`; reply says nothing to ship |

The `says-*` graders are the loosest part: they match a family of phrasings
("nothing to ship", "working tree clean", "up to date", "no remote"...). Tighten
them to the exact phrase once the skill prints one.

### Not covered, and why

Everything from Phase 2 on (staging, the commit, the push, the PR, the
watcher) needs a push target and a model-written commit, and the PR phase
needs GitHub. Preflight exits 4 (detached HEAD) and 7 are covered by
`tests/test-ship-preflight.sh` without a model.

## Running

From the repo root:

```bash
ship/evals/run.sh                                   # all cases, default model
ship/evals/run.sh --model haiku --runs 1            # cheapest pass
ship/evals/run.sh --case 'ship-no-remote*' --keep-temp
```

`run.sh` passes `--scaffold --allow-tools Bash --ablation none --no-publish
--trust-plugin` and unsets `CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT` and
`CHILD_SESSION` so the child claude behaves like a top-level one. Anything
else goes through to `claude plugin eval`.

- The runner needs `bubblewrap` and `socat` on Linux. **It cannot run from
  inside a sandboxed Claude Code Bash tool**: the eval's own sandbox then fails
  with `apply-seccomp: write /proc/self/setgroups (nested userns is
  capability-restricted)` on every command. The agent reports that and stops,
  so the `no-*` graders pass vacuously and the `says-*` graders fail. Run it
  from a plain terminal.

Fixtures can be checked without a model: run each `scaffold.sh` in an empty
dir with a minimal env, then `ship-preflight.sh` (with `--yes` where the
prompt has it) with `bin/gh` first on `PATH`, and compare the exit code with
the table above.

## Status

Written 2026-11-04 against the preflight-based Phase 1 (ship 2.2, in
progress). The fixtures were validated offline: each scaffold yields the
preflight exit in the table. The suite has **not** completed a real model
run: in the only environment available (a sandboxed Claude session) the
runner loaded every case, ran every scaffold and spent about 2 cents on haiku
turns, but the agent's Bash tool could not start, so no verdict is
meaningful. Run it once from a terminal and record the cost here.
