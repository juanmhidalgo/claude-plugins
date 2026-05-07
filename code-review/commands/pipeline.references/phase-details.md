# `/code-review:pipeline` — Phase Details & Decision Rules

Loaded by `/code-review:pipeline` for autonomous PR-feedback resolution.

## Autonomous mode rules

This pipeline runs **without asking for input**. Use these decision rules:

| Situation | Action |
|-----------|--------|
| Simple fix (typo, null check, import) | Implement directly |
| Multiple valid approaches | Choose the simplest, most consistent with codebase |
| Adding dependency | Prefer stdlib/existing deps over new ones |
| Architectural decision | Choose the approach matching existing patterns |
| Tests fail | Fix and retry (up to 2 attempts), then STOP |
| Coverage below CI threshold | Write tests to improve coverage (up to 2 cycles), then STOP |
| No CI coverage config found | Skip coverage gate, note in report |
| Unclear if issue is valid | Default to false positive (conservative) |
| No comments to triage | Report "no actionable feedback" and exit |
| All comments are false positives | Dismiss all, skip to Phase 8 (report) |
| No code changes made (all dismissed or no valid bugs) | Skip Phases 5-7, go to Phase 8 |
| No test suite found | Skip test phase, warn in report |
| Linter/formatter changed unrelated files | Reset them with `git checkout -- <file>`, log in report |

**NEVER ask for input.** Only stop if tests fail after 2 retry attempts or if validation fails.

## Phase 1: Triage (detail)

Fetch comments:
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/pr-triage-comments.sh OWNER REPO PR_NUMBER
```

For each comment, spawn a `comment-verifier` agent in parallel:
```
For each comment, use Agent tool with:
- subagent_type: "comment-verifier"
- prompt: "Verify this review comment:\n\nref_id: [ref_id]\nFile: [file:line]\nReviewer: @[author]\nComment: [body]"
```

Launch ALL verifier agents in a single response (parallel tool calls). Each returns `VALID BUG` or `FALSE POSITIVE` with evidence. Collect verdicts with `ref_id` preserved.

## Phase 2: Dismiss false positives

For each FALSE POSITIVE, dismiss immediately:
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/pr-resolve-comment.sh OWNER REPO PR_NUMBER REF_ID dismiss "REASON"
```

Concise reasons: "Already handled in [location]", "YAGNI", "Misunderstands context: [brief]", "Style preference", "Pre-existing, not introduced by this PR".

## Phase 4: Implement (parallel + scope-check details)

### Parallel execution (different files)
For fixes that touch different files, spawn parallel subagents using the Agent tool with the `fix-implementer` agent type. Each agent runs in the background with a 25-turn cap:

```
For each independent fix, use Agent tool with:
- subagent_type: "fix-implementer"
- prompt: "Fix: [issue title]. File: [path:line]. Problem: [description]. Expected fix: [solution from plan]."
```

Launch all independent fix agents in a single response. Wait for all to complete before proceeding.

### Sequential execution (same file)
For fixes touching the same file, implement them sequentially using the same `fix-implementer` agent.

### Scope check (reset unrelated changes)
Pre-commit hooks and linters may auto-format beyond the fix scope. Before proceeding:
1. Run `git diff --name-only` to list all modified files
2. Compare against the Phase 3 fix plan — only those files should be modified
3. For any file NOT in the fix plan: `git checkout -- <file>` to discard, log "Reset [count] unrelated files modified by auto-formatters"
4. Run `git diff --stat` to confirm only fix-related files remain

## Phase 5: Run tests (detail)

1. Check for test commands: `package.json` `scripts.test`, `Makefile` targets, `pytest.ini`/`pyproject.toml`, `Cargo.toml`, `go.mod`
2. Run the full test suite
3. If tests pass → Phase 5b
4. If tests fail:
   - Analyze and fix
   - Re-run (attempt 2)
   - Fix and re-run (attempt 3)
   - Still failing after attempt 3: STOP and report

## Phase 5b: Coverage gate (detail)

1. **Detect GHA coverage config**: search `.github/workflows/*.yml` for `orgoro/coverage`, `CodeCoverageReport`, `cobertura-action`, `codecov`
2. **If no coverage config**: skip; add "Coverage: SKIPPED (no CI config)" to report
3. **If found**:
   - Extract thresholds; normalize to 0–100 percentages
   - Base branch: `gh pr view $ARGUMENTS --json baseRefName -q '.baseRefName'`
   - Categorize files:
     - New: `git diff --name-only --diff-filter=A <base>...HEAD`
     - Modified: `git diff --name-only --diff-filter=M <base>...HEAD`
   - Run test suite with coverage; parse per-file coverage
   - Check each file against its category threshold
   - All pass → Phase 6
   - Below threshold: write tests targeting uncovered lines, re-run (up to 2 additional cycles); if still failing after 2 cycles, STOP and report current % vs required %

## Phase 6: Commit and push

```
fix: resolve PR #{PR_NUMBER} review feedback

Fixes applied:
- [Brief description of each fix]

Dismissed as false positives:
- [Count] comments dismissed

Reviewed-by: Claude Code
```

Then `git push`.

## Phase 7: Resolve GitHub threads

For each VALID BUG that was fixed:
```bash
${CLAUDE_PLUGIN_ROOT}/scripts/pr-resolve-comment.sh OWNER REPO PR_NUMBER REF_ID resolve
```

## Phase 8: Report format

```
## Pipeline Results - PR #[number]

### Fixed ([count])
- [ref_id] [file:line] - [brief description of fix]

### Dismissed ([count])
- [ref_id] [file:line] - [reason]

### Threads Resolved ([count])

### Tests: PASS/FAIL

### Coverage: PASS/FAIL/SKIPPED
- [If applicable: files below threshold with current % vs required %]

### Commits: [commit hash] pushed to [branch]
```

## Future direction: agent-teams

Phases 1 (parallel verifiers) and 4 (parallel fix-implementers) are natural fits for agent-teams (peer-to-peer messaging, shared task list). The current implementation uses subagent fan-out, which is the right choice today (agent-teams remain experimental and disabled by default per Claude Code docs). When agent-teams move out of experimental status, consider:

- Replacing the parallel verifier fan-out with an agent-team where verifiers can cross-check each other on overlapping concerns (e.g., a security verifier and a tech-debt verifier looking at the same change)
- Replacing the parallel fix-implementer fan-out with an agent-team where implementers can coordinate on shared dependencies discovered mid-fix
