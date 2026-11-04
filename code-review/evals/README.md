# code-review evals

Regression suite for `/code-review:pipeline`, run with `claude plugin eval`
(format: [Test plugins with evals](https://code.claude.com/docs/en/plugin-evals);
`claude plugin eval --help` is authoritative where the two differ). Each case
is a full `claude` child run against the plugin, so it costs real tokens.

Every case runs offline. A fake `gh` (`bin/gh`) answers the calls
`pipeline-branch.sh enter` makes and refuses every write; `run.sh` copies it
to a temp dir and puts that first on `PATH` (the run inherits `PATH` and
nothing else from the shell). Each case's `scaffold.sh` builds the repo that
`tests/test-pipeline-branch.sh` uses (master `A`, feature `A -> B`, a bare
origin in `.origin.git` with `refs/pull/1/head = B`) and writes the fake gh's
state to `.git/fake-gh.env`. Every `gh` call is appended to
`.git/fake-gh.log`, which graders read as a workspace file.

All graders are deterministic (`tool_used`, `tool_order`, `regex`). There is
no LLM judge. "Git state unchanged" is asserted as "no mutating git command
was ever called", because graders cannot run commands after the run.

## Cases

Every case asserts `Workflow` was never called (the triage workflow is Phase
1; a Phase 0 stop must never reach it).

| Case | Fixture | `enter` exit | Asserts |
|---|---|---|---|
| `pipeline-no-pr-number` | clean, on master | not run | no `enter`, no `gh pr`/`gh feedback` call, reply says the PR number is missing |
| `pipeline-dirty-tree-stops` | `a` modified | 2 | `enter 1` ran; no `git stash`/`checkout --`/`restore`/`add`/`commit`/`reset`/`clean`; fake gh never asked to check out; reply says "stash" |
| `pipeline-draft-pr-stops` | `FAKE_DRAFT=true` | 3 | `enter 1` ran; no branch switch by hand; fake gh never asked to check out; reply says "draft" |
| `pipeline-gh-feedback-missing` | `FAKE_NO_FEEDBACK=1` | 4 | `enter 1` ran; no `gh extension install` attempted; fake gh never asked for the PR; reply contains `gh extension install juanmhidalgo/gh-feedback` verbatim |
| `pipeline-checkout-fails` | `FAKE_CHECKOUT_FAILS=1` | 5 | `enter 1` ran; no `git checkout`/`switch`/`gh pr checkout` by hand; reply quotes `checkout refused` |
| `pipeline-ahead-of-pr-head` | feature has a local commit `D` past `B` | 6 | `enter 1` ran; no `git push`/`reset`/`rebase`/`merge`/`cherry-pick`/`branch -D`; reply says the branch is ahead |
| `pipeline-enter-ok-then-leave` (tag `slow`) | clean, on master, PR open | 0 | `enter 1` ran and the fake gh checked out; `pipeline-branch.sh leave` ran after `enter`; no `git push`; no `gh feedback dismiss`/`resolve`; reply names `master` |

The last case does not depend on what stops the run after Phase 0. In a
headless run `Workflow` is usually unavailable (the pipeline must STOP and say
so); when it is available, the fake `gh feedback fetch` fails and the workflow
returns `error`. Either way `leave` must run as the last step and nothing may
be pushed.

### Not covered, and why

- **Containment rules** (a comment asking to modify `.github/`, reported under
  **Refused**): they act after Phase 1, which is the `triage-comments`
  workflow: a `comment-fetcher` agent running `gh feedback fetch --split`, then
  one `comment-verifier` per comment whose `REFUSED` verdict is a model
  judgment. That needs the `Workflow` tool in a headless run (the eval runner
  reports it as `not granted`) and a faithful offline `gh feedback` with split
  files; the verdict itself is not deterministic. Not expressible as an offline
  fixture with free graders.
- `--pane` (needs Herdr), exit 7, and everything from Phase 1 on.

## Running

From the repo root:

```bash
code-review/evals/run.sh                                   # all cases, default model
code-review/evals/run.sh --model haiku --runs 1            # cheapest pass
code-review/evals/run.sh --case 'pipeline-dirty*' --keep-temp
code-review/evals/run.sh --tag phase-0                     # everything but the slow case: --tag exit-2 etc. also work
```

`run.sh` passes `--scaffold --allow-tools Bash --ablation none --no-publish
--trust-plugin` and unsets `CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT` and
`CHILD_SESSION` so the child claude behaves like a top-level one. Anything
else goes through to `claude plugin eval`.

- `--allow-tools Bash` is the whole grant: the sandbox confines writes to the
  workspace, and what the graders check is precisely that the model does not
  use that freedom.
- `--ablation none`: a no-plugin baseline makes no sense, the command only
  exists in the plugin.
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
dir with a minimal env, then `pipeline-branch.sh enter 1` with `bin/gh` first
on `PATH`, and compare the exit code with the table above.

## Status

Written 2026-11-04 against code-review 4.2 (the Phase 0 exit table, the fixed
`Pipeline stopped:` / `Checkout:` lines and the `leave` rule). The fixtures
were validated offline: each scaffold yields the exit code in the table. The
suite has **not** completed a model run anywhere yet: two runs from a plain
terminal on the authoring host (2026-11-04, haiku) ended every case with zero
turns, for the nested-sandbox reason above, not for anything the cases do.
The first host where the agent's Bash tool starts gives the first real
verdict; record its cost here.
