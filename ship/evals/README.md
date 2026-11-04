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

- The runner needs `bubblewrap` and `socat` on Linux, and **on a host where
  Claude Code's own Bash sandbox cannot start inside the runner's sandbox the
  suite cannot run at all.** Measured on Claude Code 2.1.317 / Linux 7.0 from a
  plain terminal: the runner wraps the whole `claude` process in bubblewrap and
  writes a settings.json with `sandbox.enabled: true`,
  `failIfUnavailable: true` and `allowUnsandboxedCommands: false`; every Bash
  call and every `` !` `` context line of the command then fails with
  `apply-seccomp: write /proc/self/setgroups (nested userns is
  capability-restricted)`, because once the outer namespace's `gid_map` is
  written, `setgroups` cannot be written again and the inner sandbox runtime
  gives up. A command whose Context has a `` !` `` line ends with zero turns
  and no cost; a skill without one runs, its scripts fail, and the agent reports
  that it is stuck. `claude plugin eval --help` has no option to relax that
  sandbox, and the runner does not read `~/.claude/settings.json`
  (`allowNestedUserNamespaces`, `enableWeakerNestedSandbox`). Run the suite on
  a host where the nested sandbox starts (a CI runner or a container that the
  runner's sandbox can nest in); a kept run's `out/trace.jsonl` shows the error
  on the first tool call when it does not.

Fixtures can be checked without a model: run each `scaffold.sh` in an empty
dir with a minimal env, then `ship-preflight.sh` (with `--yes` where the
prompt has it) with `bin/gh` first on `PATH`, and compare the exit code with
the table above.

## Status

Written 2026-11-04 against the preflight-based Phase 1 (ship 2.2) and its
fixed `Nothing to ship:` / `Ship stopped:` lines. The fixtures were validated
offline: each scaffold yields the preflight exit in the table. The suite has
**not** produced a meaningful verdict yet: two runs from a plain terminal on
the authoring host (2026-11-04, haiku, about 2 cents each) loaded every case
and the agent ran, but `ship-preflight.sh` failed on every call for the
nested-sandbox reason above, so the agent answered that it was stuck: the
`no-*` graders passed vacuously and the `says-*` graders failed. The first
host where the agent's Bash tool starts gives the first real verdict; record
its cost here.
