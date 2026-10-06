# Ship Plugin

End-to-end shipping workflow for Claude Code. Takes your changes from working directory to remote with minimal interaction.

## What it does

`/ship` orchestrates the full git workflow in 8 phases:

1. **Status & Branch Detection** — detects default branch, offers to create feature branch if on main
2. **Smart Staging** — analyzes change cohesion; auto-stages if cohesive, groups and asks if mixed concerns
3. **Commit Message** — generates conventional commit automatically
4. **Test Gate** — detects and runs your test suite
5. **Commit & Push** — commits and pushes to remote
6. **Pull Request** — offers to create PR on feature branches and requests a Copilot review
7. **Watch** — waits in the background for CI and Copilot's review
8. **Act** — reports CI failures; hands Copilot's comments to `/code-review:pipeline`

## Smart Staging

The key feature. Instead of always asking what to stage, the plugin analyzes your changes:

- **Single concern** (e.g., all files relate to the same feature): auto-stages everything, no question asked
- **Mixed concerns** (e.g., a bug fix + unrelated feature work): groups changes by concern and asks which group to ship

This means zero friction in the common case, but still catches the "I fixed a bug while working on a feature" scenario.

## Usage

Say "let's ship it" (or "ship it", "ship this") in the conversation, or type `/ship`. Flags can be said in words: "ship it as a draft", "ship it, don't wait for CI".

```
/ship                    # Full workflow
/ship --skip-tests       # Skip test phase
/ship --no-pr            # Don't offer to create PR
/ship --draft            # Create PR as draft
/ship --no-watch         # Don't wait for CI or Copilot after the PR
/ship --no-notify        # Don't notify sibling sessions after push
/ship --skip-tests --draft  # Combine flags
```

## Watching CI and Copilot

Once the branch has a PR, `/ship` starts `scripts/pr-watch.sh` in the background and ends its turn; the session is re-invoked when the script exits. The script waits until every check has finished and, if Copilot's review was requested in this run, until Copilot has reviewed the PR's current head commit (30-minute cap).

- **CI failed**: the failing step's log is shown. `/ship` does not fix it.
- **Copilot left inline comments**: `/code-review:pipeline <PR#>` runs on them (triage, fix, test, push, resolve). Then CI is watched once more on the fix commit — no second Copilot round.
- **Copilot reviewed with no comments**, or **no checks**: reported, nothing else runs.

Draft PRs are watched for CI only. Without the `code-review` plugin, `/ship` stops and tells you to run the pipeline yourself.

## Sibling Session Notification

After a successful push to the default branch, `/ship` looks for other live Claude Code sessions working on the same repository (e.g., parallel worktrees) via [cross-session messaging](https://code.claude.com/docs/en/cross-session-messaging) and sends each one a short heads-up: what landed and whether rebasing is advisable. Best-effort by design — it's skipped for feature-branch pushes, with `--no-notify`, or when messaging isn't available (Claude Code < v2.1.224, Bedrock/Vertex/Foundry), and it can never fail the ship workflow.

## Needs

- `gh`, installed and authenticated
- A git remote
- Optional: Copilot code review enabled on the repo (skip the request with `--skip-copilot-review`)
- Optional: the `code-review` plugin, for the hand-off of Copilot's comments to `/code-review:pipeline`
- `jq`, for the watcher
- No MCP servers or browser

## Installation

```
/plugin install ship@juanmhidalgo-plugins
```
