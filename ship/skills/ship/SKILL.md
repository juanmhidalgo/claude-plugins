---
name: ship
description: |
  Use when the user tells you to ship the current work — "ship it", "let's ship it",
  "ship this", "ready to ship", "send it", or asks to commit, push and open the PR in
  one go. Commits, pushes, opens the PR, then waits for CI and Copilot's review.
  Do NOT use when the user asks only to commit or only to push, or is asking whether
  the work is ready to ship rather than telling you to ship it.
argument-hint: "[--skip-tests] [--no-pr] [--draft] [--skip-copilot-review] [--no-watch] [--no-notify] [--yes] [--evidence-file <path>]"
keywords:
  - ship
  - commit-push-pr
  - conventional-commit
  - pull-request
  - git-workflow
triggers:
  - "ship my changes"
  - "commit and push"
  - "ship it"
  - "let's ship it"
  - "ship this"
  - "ready to ship"
  - "push and create PR"
  - "commit push and PR"
allowed-tools:
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/*)
  - Bash(git *)
  - Bash(gh *)
  - Bash(npm test*)
  - Bash(npm run test*)
  - Bash(yarn test*)
  - Bash(pnpm test*)
  - Bash(bun test*)
  - Bash(pytest*)
  - Bash(python -m pytest*)
  - Bash(make test*)
  - Bash(cargo test*)
  - Bash(go test*)
  - Read
  - Grep
  - Glob
  - ListAgents
  - SendMessage
---

# Ship Workflow

Execute these phases in order. Stop and report at any failure.

## Context

- **Arguments**: $ARGUMENTS

The branch, the remote, the dirty tree and the rest of the repository state come from the preflight script in Phase 1, not from commands you run yourself.

When you invoked this skill from the conversation rather than the user typing `/ship`, read the flags from what the user said: "as a draft" → `--draft`, "no PR" → `--no-pr`, "skip tests" → `--skip-tests`, "don't wait" / "no need to watch CI" → `--no-watch`. Anything not mentioned keeps its default.

## `--yes`: no questions

`--yes` is for a caller that cannot answer (a headless stage, a command that invoked this skill with the Skill tool). It replaces every question in this workflow with the choice below and implies `--no-watch`. Nothing else changes: the tests still gate the commit, a rejected push still stops, secrets are still excluded.

| Phase | Without `--yes` | With `--yes` |
|---|---|---|
| 1, on the default branch | asks whether to branch | **stops** (preflight exit `3`): never branches and never pushes to the default branch; says so and ends. The caller decides |
| 1, clean tree with commits ahead of the base | stops: nothing to ship (preflight exit `2`) | preflight reports `mode` `push`: skips Phases 2–3 (nothing to stage or commit), runs Phase 4 against the files changed since the base (`git diff --name-only <default-branch>...HEAD` decides the non-code skip), pushes when the upstream is behind (Phase 5, step 2) and goes to Phase 6 |
| 2, mixed concerns | asks which group to ship | stages every non-secret changed and untracked file, listing the excluded ones |
| 4, no test runner found | asks whether to proceed | continues; Evidence says `Tests skipped (no test runner detected)` |
| 6, feature branch | asks whether to create the PR | creates it, base = the default branch; when the repo has several PR templates, takes the first by file name |

A caller that invoked this skill with content the PR body must lead with (a `Closes #N` line, a section of its own) puts it before Summary; the template's sections follow it. A PR that already exists for the branch is left exactly as it is: nothing is created and nothing is edited.

**`--evidence-file <path>`**: lines of test evidence from earlier runs (a harden's scoped selection, an implement's suite), one per line, each `command — result`. Phase 6 appends them under Evidence as `- **Earlier runs:**`, verbatim, marked as reported by the caller: they are not runs this session made.

## Phase 1: Preflight

Run once, adding `--yes` when `$ARGUMENTS` contains it:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/ship-preflight.sh [--yes]
```

It reads the repository state this phase used to work out by hand, changes nothing, and prints one JSON line:

| Field | Meaning |
|-------|---------|
| `branch`, `default_branch`, `on_default_branch` | the current branch and the repo's default one (`default_branch_source` says where it came from: `gh`, `origin-head`, `local`, or `guess` when nothing answered and `main` was assumed) |
| `remote`, `upstream` | the remote to push to, and the tracking branch (`null` when the branch has none) |
| `ahead`, `behind` | commits vs the upstream as git knows it, without fetching |
| `ahead_of_base` | commits in `<default_branch>..HEAD` |
| `staged`, `unstaged`, `untracked` | counts from `git status` |
| `mode` | `commit` (something to stage or commit) or `push` (clean tree ahead of the base, `--yes` only) |
| `gh`, `gh_feedback` | `ok`, `missing` or `unauthenticated`; whether the `gh-feedback` extension is installed |
| `pr` | the open PR for this branch (`number`, `url`, `isDraft`), or `null` |
| `pr_templates` | the repo's PR template paths, sorted (folder entries by file name) |

Later phases read these fields; do not re-run the commands behind them.

| Exit | Meaning | Do |
|------|---------|----|
| `0` | Ready | `on_default_branch` true → ask about branching (below). Then `mode` `commit` → Phase 2; `mode` `push` → skip Phases 2–3, run Phase 4 over `git diff --name-only <default_branch>...HEAD`, continue with Phase 5 step 2 (push when the upstream is behind) and Phase 6. A red suite still stops before the push |
| `2` | Nothing to ship: clean tree, nothing staged (with `--yes`: and no commits ahead of the base either) | **STOP**: `Nothing to ship: <stderr line>` |
| `3` | On the default branch with `--yes` | **STOP**: `Ship stopped: --yes on the default branch (<default_branch>); /ship never branches or pushes there. Nothing staged or committed.` The caller decides |
| `4` | Detached HEAD | **STOP**: `Ship stopped: detached HEAD. Check out a branch first.` |
| `5` | No remote configured | **STOP** before anything is staged: `Ship stopped: no remote configured, nothing to push to. Nothing staged.` |
| `7` | git failed (not a repository, or the message on stderr) | **STOP**: `Ship stopped: <stderr line>` |

Every stop begins the reply with the fixed line shown, so a person or a test
can recognise the outcome without reading the rest.

**On the default branch** (exit `0` with `on_default_branch` true; `--yes` never gets here): ask the user with AskUserQuestion:
- "Create a new feature branch" — auto-generate a descriptive branch name from the changes (e.g., `fix/null-check-auth-middleware`, `feat/add-billing-export`). Use the conventional commit type as prefix. Create with `git checkout -b <name>`. The new branch has no upstream: Phase 5 pushes it with `-u`.
- "Continue on current branch" — proceed with direct push workflow

If the user creates a new branch, the rest of the workflow follows the **feature branch** path (PR offered at the end).

## Phase 2: Smart Staging

If preflight counted unstaged or untracked files:

1. List them with `git status` (never use `-uall`) and `git diff --stat`; `git diff --cached --stat` shows what was already staged
2. **Exclude secrets automatically**: skip `.env`, credentials, tokens, private keys — warn the user about excluded files
3. **Analyze change cohesion** — determine if all changes relate to a single concern or multiple:

   **Signals for mixed/unrelated changes:**
   - Files in different modules or directories with no logical connection
   - Mix of change types (e.g., a bug fix in existing code + new feature files)
   - Changes that touch different domains (e.g., auth code + billing logic)
   - Diff content showing unrelated modifications (e.g., a typo fix + a refactor)

4. **Branch based on analysis:**

   - **All changes are cohesive** (single concern): auto-stage all non-secret files. No question needed. Show `git diff --cached --stat` as confirmation.
   - **Mixed concerns detected** with `--yes`: stage every non-secret file; the commit message names the concerns. Without it, group changes by concern and present them to the user with AskUserQuestion. Example:

     > I detected changes belonging to different concerns:
     >
     > **A) fix: null check in auth middleware**
     >   - `src/auth/middleware.py`
     >   - `tests/auth/test_middleware.py`
     >
     > **B) feat: add billing export endpoint**
     >   - `src/billing/views.py`
     >   - `src/billing/serializers.py`
     >   - `tests/billing/test_export.py`
     >
     > Which group should I ship? (remaining changes stay unstaged for a separate /ship)

5. Stage only the selected group with `git add <specific-files>` (never `git add -A` or `git add .`)
6. Show final `git diff --cached --stat` to confirm

## Phase 3: Generate Commit Message

1. Read the staged diff: `git diff --cached`
2. For large diffs, review file-by-file: `git diff --cached -- <file>`
3. Check recent commit style: `git log --oneline -10`
4. Generate a **conventional commit** message:

```
<type>(<scope>): <subject>

<body>
```

**Types**: feat, fix, refactor, docs, test, chore, perf, ci, build, style

**Rules**:
- Subject line: imperative mood, no period, under 72 chars
- Scope: optional, the module or component affected
- Body: explain "why" not "what", wrap at 72 chars

5. Use the generated message directly — do NOT ask the user to confirm, edit, or regenerate. Just show the message inline as part of the workflow output.

## Phase 4: Run Tests

**Skip this phase if:**
- `$ARGUMENTS` contains `--skip-tests`, OR
- **Only non-code files were staged** — check `git diff --cached --name-only` and skip if all files are docs, config, or non-source files (e.g., `*.md`, `*.txt`, `*.json`, `*.yaml`, `*.yml`, `*.toml`, `*.cfg`, `*.ini`, `*.lock`, `LICENSE`, `*.rst`, `.gitignore`). Log "Tests skipped: only non-code files changed" and continue to Phase 5.

Otherwise:

1. **Detect test runner** by checking (in order):
   - `package.json` → `scripts.test` → `npm test`
   - `pytest.ini` / `pyproject.toml` [tool.pytest] / `setup.cfg` → `pytest`
   - `Makefile` with `test` target → `make test`
   - `Cargo.toml` → `cargo test`
   - `go.mod` → `go test ./...`
2. Run the detected test command
3. If tests **fail**: stop workflow, show failures, do NOT commit
4. If tests **pass**: continue

If no test runner is detected, warn the user and ask whether to proceed without tests (with `--yes`: continue, and Phase 6 writes `Tests skipped (no test runner detected)` as the After evidence).

## Phase 5: Commit & Push

1. Commit using HEREDOC format:
   ```bash
   git commit -m "$(cat <<'EOF'
   <message>
   EOF
   )"
   ```
2. Push to remote:
   - Preflight's `upstream` is set: `git push`
   - It is `null` (or Phase 1 created the branch): `git push -u <remote> <branch>`, with preflight's `remote`
3. Verify with `git status`

If push fails (rejected), inform the user and suggest `git pull --rebase`. Never force push. Preflight's `behind` > 0 already says the push will be rejected: say so before trying.

### Notify sibling sessions (default-branch pushes only, best-effort)

After a successful push **to the default branch**, tell other live sessions working on this repo that it moved, so parallel worktrees know to rebase. Skip this entirely if `$ARGUMENTS` contains `--no-notify`, if the push went to a feature branch, or if the `ListAgents` tool is unavailable (older Claude Code or unsupported provider) — and never let a failure here fail the ship workflow.

1. Call `ListAgents` and find **local** sessions working on this repository or another worktree of it. Match by working directory when the listing shows one; if it doesn't (some versions list only name and status), fall back to the session's name, which usually references its repo. Only message sessions you can attribute to this repo confidently. Exclude subagents, teammates, and remote/cloud sessions.
2. If none match, say nothing and continue.
3. For each matching session, send ONE concise plain-text message with `SendMessage`: the commit subject(s) that landed, the branch, and whether rebasing is now advisable (e.g., "`feat(auth): add token refresh` landed on `master` — rebase before continuing if your work touches auth"). Batch multiple commits into a single message per session; never send bursts.
4. A held or refused message is normal (the receiving session controls its inbox): mention it briefly and move on — do not resend.

## Phase 6: Pull Request (Feature Branches Only)

Skip if:
- On the default branch (preflight's `on_default_branch`, unless Phase 1 created a branch)
- `$ARGUMENTS` contains `--no-pr`
- A PR already exists (preflight's `pr` is not `null`; Phase 7 watches it)
- Preflight's `gh` is not `ok`: say how to open the PR by hand (`gh auth login` first when it is `unauthenticated`)

If on a feature branch:

1. Ask user with AskUserQuestion whether to create a PR (with `--yes`: create it without asking)
2. If yes:
   - Use the default branch detected in Phase 1 as the base
   - Run `git log <default-branch>..HEAD --oneline` to gather commit history
   - Generate a concise PR title (under 70 chars)
   - Generate the body with the template below, picking the Summary visual from [pr-body.md](references/pr-body.md)
3. **Repo template first.** If preflight's `pr_templates` is not empty (it lists `.github/pull_request_template.md`, `.github/PULL_REQUEST_TEMPLATE.md`, `docs/pull_request_template.md`, `pull_request_template.md` and the files in `.github/PULL_REQUEST_TEMPLATE/`; when it holds several, ask the user which one, or with `--yes` take the first), read the template, keep its headings and their order and fill them using the rules below. Append **Merge Danger** and **Rollback Triggers** only when the template has no equivalent section.
4. **Evidence is only what this session ran.**
   - **After**: the Phase 4 test command and its pass line. If Phase 4 was skipped, or no test runner was found and the user agreed to proceed, write `Tests skipped (<reason>)`.
   - **Before**: a failing run whose output appears verbatim in a Bash result in this conversation (the test name and its key failure line, copied, not retyped). A failure a subagent reported, or one remembered from a summary of earlier context, does not count. Otherwise write `not captured`.
   - Never check out the base, revert code, or re-run anything to manufacture a "before", and never present pseudo-output as real output. `not captured` is the honest answer, the same way `N/A` is for Rollback Triggers.
   - **Earlier runs** (only with `--evidence-file <path>`): read the file and add its lines verbatim under Evidence as `- **Earlier runs (reported by the caller):**`, one bullet per line. They are the caller's claims, kept apart from Before and After.
5. **Merge Danger** — one line each:
   - **Door**: `one-way` or `two-way`, with the reason. One-way: a migration that drops or rewrites data, a change to a published API or schema contract, external side effects (emails, payments, webhooks), a major dependency bump. Everything else is two-way.
   - **Blast radius**: one word, then who or what breaks if this is wrong.
6. **Rollback Triggers** — decide before merging what objective signals would warrant reverting this change post-merge. This is *the* time to write them; deciding mid-incident is too late.
   - For runtime-impacting changes, list 2-4 concrete thresholds:
     - "Error rate on `<endpoint>` exceeds X% sustained for 5 min"
     - "p99 latency on `<endpoint>` exceeds Yms for 5 min"
     - "Synthetic check on `<critical user flow>` fails"
     - "Customer-reported regression on `<feature>` within 24h of deploy"
   - For non-runtime changes (docs, tests, config without behavior change, dev tooling), use `N/A — non-runtime change`. Don't fabricate triggers; honest N/A is more useful than ceremonial ones.
   - For database migrations, always include rollback SQL or migration-reversal procedure as a trigger, even if the rest is N/A.
7. Create PR. Keep the body under ~40 lines, with no preamble. If step 3 found a repo template, its headings replace the ones below:
   ```bash
   gh pr create --base <default-branch> --title "<title>" --body "$(cat <<'EOF'
   ## Summary
   <one sentence of why>
   <optional: one visual, derived from `git diff <default-branch>...HEAD`>

   ## Evidence
   - **Before:** <failing run observed this session | not captured>
   - **After:** <Phase 4 command + pass line | Tests skipped (<reason>)>

   ## Merge Danger
   **Door:** <one-way | two-way> — <why>
   **Blast radius:** <one word> — <who/what breaks if wrong>

   ## Rollback Triggers
   <concrete thresholds, OR "N/A — non-runtime change">
   EOF
   )"
   ```
   - If `$ARGUMENTS` contains `--draft`, add the `--draft` flag to `gh pr create`
8. **Request Copilot review** (unless `$ARGUMENTS` contains `--skip-copilot-review`), with the form GitHub documents for the CLI:
   ```bash
   gh pr edit <number> --add-reviewer @copilot
   ```
   Then **confirm**: a call that returns 0 is not a landed request (two accepted calls on one PR left no trace at all). Check these listings; Copilot is requested when any of them names it (`copilot`, case-insensitive; the bot's login reads `Copilot` or `copilot-pull-request-reviewer[bot]` depending on the endpoint):
   ```bash
   gh pr view <number> --json reviewRequests --jq '.reviewRequests[] | .login // .name'
   gh api repos/{owner}/{repo}/pulls/<number>/requested_reviewers --jq '.users[].login'
   gh api repos/{owner}/{repo}/issues/<number>/timeline --jq '.[] | select(.event=="review_requested") | .requested_reviewer.login'
   ```
   If none names it, retry once through the REST API with the login GitHub documents for it, then check the three listings again:
   ```bash
   gh api repos/{owner}/{repo}/pulls/<number>/requested_reviewers -X POST -f 'reviewers[]=copilot-pull-request-reviewer[bot]'
   ```
   Still nothing → report `Copilot: not requested` with why (the exit code and output of both calls, and that none of the three listings shows it; the usual cause is Copilot code review not being available to the account or the repo's plan), warn the user and continue — do not fail the workflow and never issue a third request. Report `Copilot: requested (<login>, seen in <listing>)` otherwise. Phase 7 waits for Copilot only when it was confirmed.
9. Report the PR URL

## Phase 7: Watch CI and Copilot (Feature Branches Only)

Skip if `$ARGUMENTS` contains `--no-watch` or `--yes`, or if the branch has no open PR (none was created and none existed).

The watcher is the `gh-feedback` extension. If preflight's `gh_feedback` is `false`, skip this phase and Phase 8: report the PR URL, `gh pr checks <number>` to check CI later, and `gh extension install juanmhidalgo/gh-feedback` to get the watcher.

Start the watcher **in the background** (Bash with `run_in_background`); you are re-invoked when it exits, so do not poll or sleep in the meantime:

```bash
gh feedback watch <number> [--copilot]
```

Pass `--copilot` only if the Phase 6 request landed in this run and the PR is not a draft. It exits once every check has finished and, with `--copilot`, once Copilot has reviewed the current head commit — or after 30 minutes (exit 3). Tell the user in one line what you are waiting for, then end the turn.

## Phase 8: Act on the Results

Read the final block the watcher printed (`CI:`, `FAILED:`, `COPILOT:` lines).

| Result | Action |
|--------|--------|
| `CI: fail` | For each `FAILED:` line, take the run id from its link (`/actions/runs/<run-id>/`) and show the failing step with `gh run view <run-id> --log-failed \| tail -50`. A link outside GitHub Actions is an external check: give the link. Report it. Do not fix it as part of `/ship` — a CI failure is a new problem for the user to scope. |
| `CI: none` | Say the PR reported no checks; nothing to wait for. |
| `COPILOT: N inline comments`, N > 0 | Invoke `/code-review:pipeline <number>` with the Skill tool. It triages, fixes, tests, pushes and resolves on its own. If the Skill call fails (the code-review plugin is not installed), tell the user to run it. |
| `COPILOT: 0 inline comments` | Report that Copilot reviewed with no comments. Its summary review body alone does not warrant the pipeline. |
| Exit 3 (timeout) | Report what is still pending (`CI: pending` and/or `COPILOT: pending`) with the PR URL. Do not restart the watcher on your own. |

When CI failed **and** Copilot commented, report the failure first, then run the pipeline: its fixes do not depend on the CI result.

If the pipeline pushed a commit, run the watcher once more **without** `--copilot` to report CI on that commit. Do not request another Copilot review and do not run the pipeline again — one round, no loop.

End with a short report: branch, PR URL, CI result, and what happened to Copilot's feedback. When Phase 7 was skipped, end with the PR URL and `gh pr checks <number>` to check CI later.

## Error Recovery

| Error | Action |
|-------|--------|
| Nothing to commit | Preflight exit `2`: stop, inform user |
| Detached HEAD | Preflight exit `4`: stop, ask for a branch |
| No remote configured | Preflight exit `5`: stop before anything is staged, inform user |
| Tests fail | Stop before commit, show failures |
| Push rejected | Suggest `git pull --rebase`, never force push |
| Pre-commit hook fails | Show error, do NOT use `--no-verify`, let user fix |
| gh CLI not available or not logged in | Preflight's `gh` is `missing` or `unauthenticated`: skip the PR step, suggest a manual PR (and `gh auth login`) |
| `gh-feedback` not installed | Preflight's `gh_feedback` is `false`: skip the watcher, report the PR URL and how to install it |
