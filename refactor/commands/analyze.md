---
description: |
  Use before starting a refactor to understand what needs attention in a file or directory.
  Do NOT use to make changes — use /refactor:plan or :extract for that.
argument-hint: "<file-or-directory>"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Agent
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
Use the Agent tool with `subagent_type: "refactor:refactor-analyzer"` to understand:

1. **Similar code** - Other files with similar patterns for comparison
2. **Existing abstractions** - Utilities, helpers, base classes already in the project
3. **Tests** - What test coverage exists for this code?
4. **Consumers** - What depends on this code?
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

## Estimated Effort and Priority

Score each refactoring on a 1-5 scale:
- **Impact**: How much does this improve readability/extensibility/testability? (1 = barely, 5 = unblocks future work)
- **Risk**: What's the risk of breaking something while doing it? (1 = trivial, 5 = touches critical paths without coverage)
- **Effort**: How long will it take? (1 = minutes, 5 = weeks)

**Priority = (Impact + Risk) × (6 − Effort)** — rewards high-value refactorings that are cheap to do.

| Refactoring | Impact | Risk | Effort | Priority |
|-------------|--------|------|--------|----------|
| [Refactoring 1] | 5 | 2 | 1 | 35 |
| [Refactoring 2] | 4 | 3 | 3 | 21 |
| [Refactoring 3] | 5 | 5 | 5 | 10 |

## Recommended Order

Sort by Priority descending, but apply two overrides:
1. **Dependency**: if Refactoring B requires Refactoring A done first, A goes first regardless of priority.
2. **Coverage gap**: if a target has no test coverage, propose adding tests *before* refactoring (counts as a separate, prerequisite refactoring).

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

<rule priority="recommended">
Suggest reusing existing abstractions over creating new ones.
</rule>
</critical_rules>
