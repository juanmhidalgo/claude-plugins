---
name: ship
description: |
  Use when ready to ship code changes to remote. Orchestrates the full workflow:
  git status → smart staging → conventional commit → run tests → push → optional PR.
  Handles both main/master (direct push) and feature branch (PR) workflows.
  Do NOT use for: partial workflows like just committing (use /commit), just pushing,
  or code review before committing (use /code-review:staged first).
disable-model-invocation: true
argument-hint: "[--skip-tests] [--no-pr] [--draft]"
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
  - "ready to ship"
  - "push and create PR"
  - "commit push and PR"
allowed-tools:
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
hooks:
  - event: Stop
    once: true
    command: |
      BRANCH=$(git branch --show-current 2>/dev/null)
      DEFAULT_BRANCH=$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name 2>/dev/null || echo "main")
      echo "Ship complete on $BRANCH."
      if [ "$BRANCH" != "$DEFAULT_BRANCH" ] && [ "$BRANCH" != "prod" ]; then
        PR_URL=$(gh pr view --json url -q .url 2>/dev/null)
        if [ -n "$PR_URL" ]; then
          echo "  PR: $PR_URL"
        fi
      fi
      echo "  CI: gh run list --limit 3"
---

# Ship Workflow

Execute these phases in order. Stop and report at any failure.

## Context

- **Branch**: !`git branch --show-current`
- **Remote tracking**: !`git rev-parse --abbrev-ref @{upstream} 2>/dev/null || echo "no upstream"`
- **Uncommitted changes**: !`git status --short | head -20`
- **Arguments**: $ARGUMENTS

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

Unless `$ARGUMENTS` contains `--skip-tests`:

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
   - Generate body with summary bullets and test plan
3. Create PR:
   ```bash
   gh pr create --base <default-branch> --title "<title>" --body "$(cat <<'EOF'
   ## Summary
   <bullets>

   ## Test plan
   <checklist>
   EOF
   )"
   ```
   - If `$ARGUMENTS` contains `--draft`, add the `--draft` flag to `gh pr create`
4. Report the PR URL

## Error Recovery

| Error | Action |
|-------|--------|
| Nothing to commit | Stop, inform user |
| Tests fail | Stop before commit, show failures |
| Push rejected | Suggest `git pull --rebase`, never force push |
| Pre-commit hook fails | Show error, do NOT use `--no-verify`, let user fix |
| gh CLI not available | Skip PR step, suggest manual PR |
| No remote configured | Stop before push, inform user |
