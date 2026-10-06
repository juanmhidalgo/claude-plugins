---
name: ship
description: |
  Use when the user tells you to ship the current work — "ship it", "let's ship it",
  "ship this", "ready to ship", "send it", or asks to commit, push and open the PR in
  one go. Commits, pushes, opens the PR, then waits for CI and Copilot's review.
  Do NOT use when the user asks only to commit or only to push, or is asking whether
  the work is ready to ship rather than telling you to ship it.
argument-hint: "[--skip-tests] [--no-pr] [--draft] [--skip-copilot-review] [--no-watch] [--no-notify]"
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

- **Branch**: !`git branch --show-current`
- **Remote tracking**: !`git rev-parse --abbrev-ref @{upstream} 2>/dev/null || echo "no upstream"`
- **Uncommitted changes**: !`git status --short | head -20`
- **Arguments**: $ARGUMENTS

When you invoked this skill from the conversation rather than the user typing `/ship`, read the flags from what the user said: "as a draft" → `--draft`, "no PR" → `--no-pr`, "skip tests" → `--skip-tests`, "don't wait" / "no need to watch CI" → `--no-watch`. Anything not mentioned keeps its default.

## Phase 1: Status & Branch Detection

1. Run `git status` (never use `-uall`)
2. Run `git diff --stat` for unstaged changes summary
3. Run `git diff --cached --stat` for already-staged changes
4. Detect the repo's default branch: `gh repo view --json defaultBranchRef -q .defaultBranchRef.name 2>/dev/null || echo "main"`
5. Detect branch type:
   - **Default branch** (main, master, prod, or whatever the repo uses) → ask about branching (see below)
   - **Feature branch**: anything else → PR workflow

If there are no changes (working tree clean, nothing staged), stop and inform the user.

**If on the default branch**, ask user with AskUserQuestion:
- "Create a new feature branch" — auto-generate a descriptive branch name from the changes (e.g., `fix/null-check-auth-middleware`, `feat/add-billing-export`). Use the conventional commit type as prefix. Create with `git checkout -b <name>`.
- "Continue on current branch" — proceed with direct push workflow

If the user creates a new branch, the rest of the workflow follows the **feature branch** path (PR offered at the end).

## Phase 2: Smart Staging

If there are unstaged changes:

1. List all changed and untracked files
2. **Exclude secrets automatically**: skip `.env`, credentials, tokens, private keys — warn the user about excluded files
3. **Analyze change cohesion** — determine if all changes relate to a single concern or multiple:

   **Signals for mixed/unrelated changes:**
   - Files in different modules or directories with no logical connection
   - Mix of change types (e.g., a bug fix in existing code + new feature files)
   - Changes that touch different domains (e.g., auth code + billing logic)
   - Diff content showing unrelated modifications (e.g., a typo fix + a refactor)

4. **Branch based on analysis:**

   - **All changes are cohesive** (single concern): auto-stage all non-secret files. No question needed. Show `git diff --cached --stat` as confirmation.
   - **Mixed concerns detected**: group changes by concern and present them to the user with AskUserQuestion. Example:

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

If no test runner is detected, warn the user and ask whether to proceed without tests.

## Phase 5: Commit & Push

1. Commit using HEREDOC format:
   ```bash
   git commit -m "$(cat <<'EOF'
   <message>
   EOF
   )"
   ```
2. Push to remote:
   - If upstream exists: `git push`
   - If no upstream: `git push -u origin <branch-name>`
3. Verify with `git status`

If push fails (rejected), inform the user and suggest `git pull --rebase`. Never force push.

### Notify sibling sessions (default-branch pushes only, best-effort)

After a successful push **to the default branch**, tell other live sessions working on this repo that it moved, so parallel worktrees know to rebase. Skip this entirely if `$ARGUMENTS` contains `--no-notify`, if the push went to a feature branch, or if the `ListAgents` tool is unavailable (older Claude Code or unsupported provider) — and never let a failure here fail the ship workflow.

1. Call `ListAgents` and find **local** sessions working on this repository or another worktree of it. Match by working directory when the listing shows one; if it doesn't (some versions list only name and status), fall back to the session's name, which usually references its repo. Only message sessions you can attribute to this repo confidently. Exclude subagents, teammates, and remote/cloud sessions.
2. If none match, say nothing and continue.
3. For each matching session, send ONE concise plain-text message with `SendMessage`: the commit subject(s) that landed, the branch, and whether rebasing is now advisable (e.g., "`feat(auth): add token refresh` landed on `master` — rebase before continuing if your work touches auth"). Batch multiple commits into a single message per session; never send bursts.
4. A held or refused message is normal (the receiving session controls its inbox): mention it briefly and move on — do not resend.

## Phase 6: Pull Request (Feature Branches Only)

Skip if:
- On the default branch (detected in Phase 1)
- `$ARGUMENTS` contains `--no-pr`
- A PR already exists (`gh pr view` succeeds)

If on a feature branch:

1. Ask user with AskUserQuestion whether to create a PR
2. If yes:
   - Use the default branch detected in Phase 1 as the base
   - Run `git log <default-branch>..HEAD --oneline` to gather commit history
   - Generate a concise PR title (under 70 chars)
   - Generate body with summary bullets, test plan, and rollback triggers (see below)
3. **Rollback Triggers** — decide before merging what objective signals would warrant reverting this change post-merge. This is *the* time to write them; deciding mid-incident is too late.
   - For runtime-impacting changes, list 2-4 concrete thresholds:
     - "Error rate on `<endpoint>` exceeds X% sustained for 5 min"
     - "p99 latency on `<endpoint>` exceeds Yms for 5 min"
     - "Synthetic check on `<critical user flow>` fails"
     - "Customer-reported regression on `<feature>` within 24h of deploy"
   - For non-runtime changes (docs, tests, config without behavior change, dev tooling), use `N/A — non-runtime change`. Don't fabricate triggers; honest N/A is more useful than ceremonial ones.
   - For database migrations, always include rollback SQL or migration-reversal procedure as a trigger, even if the rest is N/A.
4. Create PR:
   ```bash
   gh pr create --base <default-branch> --title "<title>" --body "$(cat <<'EOF'
   ## Summary
   <bullets>

   ## Test plan
   <checklist>

   ## Rollback Triggers
   <concrete thresholds, OR "N/A — non-runtime change">
   EOF
   )"
   ```
   - If `$ARGUMENTS` contains `--draft`, add the `--draft` flag to `gh pr create`
5. **Request Copilot review** (unless `$ARGUMENTS` contains `--skip-copilot-review`):
   ```bash
   gh pr edit --add-reviewer @copilot
   ```
   If it fails, retry once through the API, with `Copilot` capitalized (the lowercase login can resolve without triggering a review):
   ```bash
   gh api repos/{owner}/{repo}/pulls/<number>/requested_reviewers -X POST -f 'reviewers[]=Copilot'
   ```
   `reviewRequests` and the POST's response never list bot reviewers, so an empty list there is not a failure — do not re-request on it. Confirm in the timeline instead: `gh api repos/{owner}/{repo}/issues/<number>/timeline --jq '.[] | select(.event=="review_requested") | .requested_reviewer.login'`. If both attempts fail (e.g., Copilot review not available on the repo's plan), warn the user and continue — do not fail the workflow. Remember whether the request landed: Phase 7 waits for Copilot only if it did.
6. Report the PR URL

## Phase 7: Watch CI and Copilot (Feature Branches Only)

Skip if `$ARGUMENTS` contains `--no-watch`, or if the branch has no open PR (none was created and none existed).

Start the watcher **in the background** (Bash with `run_in_background`); you are re-invoked when it exits, so do not poll or sleep in the meantime:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/pr-watch.sh <number> [--copilot]
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
| Nothing to commit | Stop, inform user |
| Tests fail | Stop before commit, show failures |
| Push rejected | Suggest `git pull --rebase`, never force push |
| Pre-commit hook fails | Show error, do NOT use `--no-verify`, let user fix |
| gh CLI not available | Skip PR step, suggest manual PR |
| No remote configured | Stop before push, inform user |
