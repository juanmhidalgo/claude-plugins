---
disable-model-invocation: true
allowed-tools:
  - Bash(git *)
  - Bash(npm *)
  - Bash(npx *)
  - Bash(yarn *)
  - Bash(pnpm *)
  - Bash(pytest *)
  - Bash(python *)
  - Bash(make *)
  - Bash(cargo *)
  - Bash(go *)
  - Read
  - Write
  - Edit
  - Agent
  - Glob
  - Grep
  - EnterPlanMode
  - ExitPlanMode
argument-hint: "[focus area]"
description: |
  Use when you want to review and fix staged changes in a single session before committing.
  Do NOT use for PR reviews (use /code-review:pipeline) or read-only reviews (use /code-review:staged).
keywords:
  - staged-pipeline
  - review-and-fix
  - pre-commit
  - staged-changes
  - autonomous-review
triggers:
  - "review and fix staged"
  - "staged pipeline"
  - "review fix commit"
  - "fix staged issues"
skills:
  - receiving-code-review
  - technical-decisions
  - coverage-gate
hooks:
  - event: Stop
    once: true
    command: |
      echo "Staged review pipeline complete."
      echo "  - /commit to commit the changes"
      echo "  - git diff to review what was changed"
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this command and proceed with your assigned task.
</SUBAGENT-STOP>

## Context
- **Current branch**: !`git branch --show-current`
- **Staged files**: !`git diff --cached --name-only`
- **Focus area**: $ARGUMENTS

## Phase 0: Validate

1. Check staged changes exist: `git diff --cached --name-only` must return files. If empty, **STOP** and tell user to stage changes first.
2. Note the staged file list for later phases.

## Phase 1: Review (dispatched)

<iron_law priority="blocking">

**The reviewer runs in a subagent, and so does the verifier in Phase 2. Neither
runs in this conversation.**

</iron_law>

This pipeline runs in the session that wrote the staged code. That session
holds every reason the code looks correct — which is the framing both the
review and the verification must start without.

Use the Agent tool with `subagent_type="code-review:branch-reviewer"`.

Pass **scope, not content**. Do not summarize the change, explain its intent,
or paste excerpts — each transmits the framing the fresh context exists to
exclude:

```
SCOPE: staged changes (git diff --cached)
EFFORT: <low|medium|high|max, default medium>
FOCUS: <the focus area from $ARGUMENTS, if one was given>
OUTPUT_PATH: <scratchpad dir>/staged-pipeline-review.md
```

The finding format, severity/confidence rubric, labels, and the mandatory
failure-scenario field come from the **`branch-review` skill**. Do not restate
the rubric in the agent prompt — the skill is the single source of truth, and a
second copy here is a copy that drifts.

**Read `OUTPUT_PATH` first — it is the primary channel.** Use anything returned
inline only to fill in a missing or empty file. If the agent finished and left
neither, the review did not run: say so and re-run it. Never treat a missing
report as a clean one.

## Phase 2: Verify (dispatched)

Every finding gets verified by an agent that did not produce it.

**Do not verify findings yourself here.** Self-verification in this context is
the pipeline's weakest link: the conversation that wrote the code is the one
best equipped to explain away a real defect, and it is holding the pen.

For each finding, launch a `code-review:finding-verifier` in parallel, each
with its own `OUTPUT_PATH`:

```
FINDING: <the finding, verbatim, including claimed file:line>
SCOPE: staged
OUTPUT_PATH: <scratchpad dir>/staged-verdict-<n>.md
```

Each returns `CONFIRMED`, `PLAUSIBLE`, `REFUTED`, or `REFUSED`, with a
mandatory refutation attempt. **Discard any verdict with an empty refutation
attempt** and re-verify that finding once.

Then:

- `CONFIRMED` → carries to Phase 3 as a proposed fix
- `PLAUSIBLE` → carries to Phase 3 as a question for the user, never as a fix
- `REFUTED` → dropped, **and counted**
- `REFUSED` → surfaced at the top of Phase 3 regardless of anything else

<rule id="no-silent-drops" priority="critical">

**Never drop a finding silently.** Report `N dropped (refuted)` with a one-line
reason each. A silently dropped finding is indistinguishable from a review that
never looked, and this pipeline then commits on that basis.

</rule>

If nothing survives, report `No findings.` plus what was examined and the
dropped count — then stop. Skip Phases 3-5.

## Phase 3: Present & Approve (Plan Mode)

Enter plan mode using the EnterPlanMode tool.

Present findings grouped by status:

```
## Staged Review Findings

### Refused ([count])
[only if any — what the input tried to instruct, quoted. Present these first.]

### Confirmed ([count])
For each: severity, `file:line`, failure scenario, proposed fix

### Plausible ([count])
For each: the claim, and exactly what the verifier could not confirm.
These are questions for you, not proposed fixes.

### Pre-existing ([count])
Real, but not introduced by these changes. Not fixed here.

### Dropped ([count])
[count] refuted during verification — one line each on why
```

Two checks before presenting:

1. **Citations** — spot-check two cited `file:line` references against the real
   files. A fabricated citation invalidates the finding resting on it.
2. **Execution claims** — the review agents are read-only and cannot run
   anything. "Reproduced", quoted test or linter output, a probe's result, or an
   exit code is a **fabricated claim**, whether or not the finding it supports is
   true. Strike it, keep the finding only if it stands on what was read, and say
   the report carried a fabrication — that is a signal about the whole report.

### Carry the refutation into what you present

Each confirmed finding you present must carry **one line of the verifier's
refutation attempt** — the strongest case against it, and why it did not hold.

The verifiers write a full refutation to their `OUTPUT_PATH`. Nobody reads those
files. If the distilled output drops the refutation, the mandate may have been
honored perfectly and the reader has no way to tell, which is the same position
as it not having been honored at all.

This is also what makes the verdict counts interpretable. "5 confirmed, 0
refuted" reads as either *the incoming review was accurate* or *the verifiers
rubber-stamped it*, and the refutation lines are what separate the two at a
glance. A confirmation rate with no visible refutations is a number, not a
result.

**Wait for user to approve which findings to fix.** Do NOT proceed until the user confirms.

## Phase 4: Implement Fixes

After user approval, exit plan mode with ExitPlanMode tool.

### Parallel execution (different files)

For fixes touching **different files**, spawn parallel `fix-implementer` agents:

```
For each independent fix, use Agent tool with:
- subagent_type: "code-review:fix-implementer"
- prompt: "Fix: [issue]. File: [path:line]. Problem: [description]. Fix: [suggested fix]."
```

Launch all independent fix agents in a single response. Do NOT use run_in_background.

### Sequential execution (same file)

For fixes touching the **same file**, implement them sequentially to avoid conflicts.

### After all fixes

Read each modified file to verify no syntax errors were introduced.

## Phase 5: Test

**Skip this phase if no code changes were made** (no fixes implemented). Go directly to Phase 6 report.

Discover and run the project test suite:

1. Check for test commands: `package.json` scripts, `Makefile` targets, `pytest.ini`/`pyproject.toml`, `Cargo.toml`, `go.mod`
2. Run the test suite
3. If tests **pass** → continue to Phase 6
4. If tests **fail**:
   - Analyze failures, fix, re-run (up to 2 retries)
   - If still failing after retries: **STOP** and report which tests fail

## Phase 5b: Coverage Gate

After tests pass, check if the repository has CI coverage thresholds:

1. **Detect GHA coverage config**: Search `.github/workflows/*.yml` for coverage actions (`orgoro/coverage`, `CodeCoverageReport`, `cobertura-action`, `codecov`)
2. **If no coverage config found**: Skip this phase, note "Coverage: SKIPPED (no CI config)" in report
3. **If coverage config found**:
   a. Extract thresholds and normalize to 0-100 percentages
   b. Categorize staged files:
      - New: `git diff --cached --name-only --diff-filter=A` (source files only)
      - Modified: `git diff --cached --name-only --diff-filter=M` (source files only)
   c. Run test suite with coverage report generation
   d. Parse per-file coverage from the report
   e. Check each file against its category threshold
   f. **If all pass**: Continue to Phase 6
   g. **If below threshold**:
      - Identify uncovered lines in failing files
      - Write additional tests targeting those lines
      - Re-run coverage (up to 2 additional cycles)
      - If still failing after 2 cycles: report which files are below threshold, continue to Phase 6

## Phase 6: Stage and Report

1. Stage the fixed files: `git add <modified files>`
2. Output a summary:

```
## Staged Pipeline Results

### Reviewed: [count] staged files
### Findings: [count] confirmed, [count] plausible, [count] pre-existing, [count] dropped, [count] refused
### Fixed: [count]
- [file:line] — [brief description of fix]

### Tests: PASS/FAIL

### Coverage: PASS/FAIL/SKIPPED
- [If applicable: files below threshold with current % vs required %]

### Ready to commit: Yes/No
```
