---
description: |
  Analyze a file or directory for refactoring opportunities.
  Identifies complexity, duplication, extraction candidates, and code smells.
  Use before refactoring to understand what needs attention.
argument-hint: "<file-or-directory>"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Task
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
Use the Task tool with `subagent_type: "Explore"` to understand:

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

## Estimated Effort
| Refactoring | Effort | Risk | Impact |
|-------------|--------|------|--------|
| [Refactoring 1] | Low | Low | High |
| [Refactoring 2] | Medium | Medium | Medium |

## Recommended Order
1. [First refactoring] - lowest risk, unblocks others
2. [Second refactoring] - depends on #1
3. [Third refactoring] - highest impact
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
