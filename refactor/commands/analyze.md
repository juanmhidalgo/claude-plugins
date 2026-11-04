---
description: |
  Use before starting a refactor to understand what needs attention in a file or directory.
  Do NOT use to make changes — use /refactor:plan or :extract for that.
argument-hint: "<file-or-directory>"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Workflow
hooks:
  - event: Stop
    once: true
    command: |
      echo ""
      echo "Analysis complete."
      echo "  - /refactor:plan to create a refactoring plan"
      echo "  - /refactor:extract to extract code"
---

# Refactoring Analysis

Analyze code for refactoring opportunities.

**Target**: $ARGUMENTS

## Phase 1: Context Gathering

<exploration>
**Requires the `Workflow` tool.** If `Workflow` is not available, **STOP** and
say so: under `claude -p` or the SDK it needs a `Workflow(refactor:refactor)`
allow rule. There is no in-session fallback: the explorer and the conflict
scout are the fan-out this command exists to keep out of the conversation.

Launch the `refactor:refactor` workflow and wait for its notification. It runs
`refactor-analyzer` and `conflict-scout` in parallel and returns both reports as
structured data:

```
Workflow({ name: "refactor:refactor", args: {
  mode: "analyze", target: "<the target>", targets: ["<the target>"] } })
```

- `target` is the analyze target as given. `targets` is the same path, for the
  scout; no `symbols`, since nothing is named for renaming yet.
- Add `base: "<branch>"` only when the user named a base branch; otherwise the
  scout reads it from `origin/HEAD`.

The analyzer gathers **similar code**, **existing abstractions**, **tests** and
**consumers**. The scout reports which open PRs, branches, and uncommitted work
already touch the target. A file under active concurrent work is a bad
refactoring target this week no matter how bad its metrics are — that is why
the scan runs before the analysis, not after it.

**Read what comes back.** `summary` is first and survives a result cut off at
the end; the full reports are `explore` (the analyzer) and `scout`:

- `summary.explore` is `ran` or `failed`. A failed explorer did not explore:
  say so and offer to re-run before writing the Existing Abstractions section
  from your own reading.
- `summary.verdict` is the scout's `CLEAR | CONTESTED | BLOCKED`, or
  `UNSCANNED` when the scout failed twice or did not run. `summary.gh_available`
  false and every line of `summary.data_gaps` go in the Concurrent Work section
  verbatim: a scan on missing data is never clean.
- `scout.textual` and `scout.semantic` are the overlaps (PR number, author,
  age, size, state); `scout.local` the uncommitted edits, stashes, worktrees and
  branches; `scout.sequencing` the do-now / do-first / defer / coordinate call.
- `explore.uncertain` lists the analyzer's own doubts; carry them into the
  report as doubts, not as findings.
</exploration>

## Phase 2: Read and Analyze Target

Read the target file(s) and calculate:

**Metrics:**
- Total lines, function count, class count
- Longest function (lines)
- Deepest nesting level
- Number of parameters per function

**Issue Detection:**

| Category | What to Look For |
|----------|-----------------|
| **Size** | Files >300 lines, functions >50 lines, classes >200 lines |
| **Duplication** | Repeated code blocks, copy-paste patterns |
| **Complexity** | Deep nesting (>3 levels), many branches, long parameter lists |
| **Coupling** | Too many imports, god objects, feature envy |
| **Naming** | Unclear names, inconsistent conventions |
| **Dead code** | Unused functions, unreachable branches |

## Phase 3: Generate Report

<output_format>
```markdown
# Refactoring Analysis: [target]

## Summary
- **Health**: Good / Needs Attention / Critical
- **Priority issues**: [count]
- **Quick wins**: [count]

## Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Total lines | X | <300 | OK/WARN |
| Longest function | X lines | <50 | OK/WARN |
| Max nesting | X levels | <4 | OK/WARN |
| Functions | X | <15 | OK/WARN |

## Issues Found

### Critical (Refactor Now)
1. **[Issue]** at `file:line`
   - Problem: [description]
   - Impact: [why it matters]
   - Suggested fix: [approach]

### High (Should Refactor)
...

### Medium (Nice to Have)
...

## Extraction Candidates

### Functions to Extract
| Current Location | New Function | Why |
|------------------|--------------|-----|
| `file:line` | `descriptive_name()` | [reason] |

### Classes/Modules to Extract
| Current Location | New Module | Contains |
|------------------|------------|----------|
| `file.py` | `new_module.py` | [what to move] |

## Existing Abstractions to Reuse
- `utils/helpers.py:function_name` - could replace [duplicated code]
- `base/base_class.py` - could inherit for [shared behavior]

## Concurrent Work

From the workflow's `scout` report. If the verdict is `UNSCANNED`, or
`gh_available` is false, say so here instead of reporting a clean scan, and
list `data_gaps`.

| Target | Concurrent work | Effect on this refactor |
|--------|-----------------|-------------------------|
| `file:line` | PR #N "title" (@author, 12d, +340/-120) | conflicts on the same functions — defer |
| `file:line` | uncommitted local edits | commit or stash before starting |

(If nothing is in flight, write exactly: "No open PRs, branches, or local edits touch these files.")

## Estimated Effort and Priority

Score each refactoring on a 1-5 scale:
- **Impact**: How much does this improve readability/extensibility/testability? (1 = barely, 5 = unblocks future work)
- **Risk**: What does leaving it cost? (1 = harmless, 5 = actively causing defects or blocking work). Breakage risk while refactoring is handled by the Coverage gap override below.
- **Effort**: How long will it take? (1 = minutes, 5 = weeks)

**Priority = (Impact + Risk) × (6 − Effort)** — rewards high-value refactorings that are cheap to do.

| Refactoring | Impact | Risk | Effort | Priority |
|-------------|--------|------|--------|----------|
| [Refactoring 1] | 5 | 2 | 1 | 35 |
| [Refactoring 2] | 4 | 3 | 3 | 21 |
| [Refactoring 3] | 5 | 5 | 5 | 10 |

## Recommended Order

Sort by Priority descending, but apply three overrides:
1. **Dependency**: if Refactoring B requires Refactoring A done first, A goes first regardless of priority.
2. **Coverage gap**: if a target has no test coverage, propose adding tests *before* refactoring (counts as a separate, prerequisite refactoring).
3. **Contention**: if a target is contested by an open PR, move it out of the front of the queue — either wait for that PR to merge, or do it first *and immediately* while the PR is still small. Say which, and why.

1. [Highest-priority refactoring] — Priority N, lowest risk, unblocks others
2. [Next refactoring] — Priority N, depends on #1
3. [Third refactoring] — Priority N, highest absolute impact (even if priority is lower due to effort)
```
</output_format>

<critical_rules>
<rule priority="blocking">
Always include file:line references for every issue.
</rule>

<rule priority="blocking">
Compare against similar code in the project - don't apply generic rules blindly.
</rule>

<rule priority="blocking">
Consider test coverage before suggesting changes.
</rule>

<rule priority="blocking">
Never present a conflict-free ordering when the scout's verdict is `UNSCANNED` or `gh_available` is false. Report the gap.
</rule>

<rule priority="recommended">
Suggest reusing existing abstractions over creating new ones.
</rule>
</critical_rules>
