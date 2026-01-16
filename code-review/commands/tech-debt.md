---
allowed-tools:
  - Bash(git *)
  - Task
  - Read
argument-hint: [base-branch]
description: Analyze branch changes for technical debt before merging
keywords:
  - tech-debt
  - technical-debt
  - code-quality
  - maintainability
  - refactoring
triggers:
  - "check for tech debt"
  - "analyze technical debt"
  - "review code quality"
  - "check maintainability"
hooks:
  - event: Stop
    once: true
    command: |
      echo "Technical debt analysis complete."
      echo "  • Address critical items before merge"
      echo "  • Track others in backlog for future refactoring"
---

## Context
- **Current branch**: !`git branch --show-current`
- **Specified base**: $1
- **Default base**: main (or master if main doesn't exist)

## Branch Configuration
If `$1` is provided, use it as the base branch. Otherwise, use `main` or `master` as the default.

## Instructions

Use Task tool with subagent_type="code-review:tech-debt-reviewer" to analyze technical debt in the branch changes.

**Analysis focus:**

1. **Complexity**
   - Functions longer than 30 lines
   - Deep nesting (>3 levels)
   - High cyclomatic complexity
   - God classes/functions doing too much

2. **Duplication**
   - Copy-pasted code blocks
   - Similar logic that could be abstracted
   - Repeated patterns across files

3. **Debt Markers**
   - New TODO/FIXME/HACK/XXX comments
   - Temporary workarounds
   - "Will fix later" patterns

4. **Test Coverage**
   - New code without corresponding tests
   - Complex logic paths untested
   - Missing edge case coverage

5. **Code Smells**
   - Magic numbers/strings
   - Poor naming (single letters, abbreviations)
   - Long parameter lists
   - Feature envy (excessive use of other class's data)

6. **Maintainability**
   - Missing or outdated documentation for public APIs
   - Implicit dependencies
   - Tight coupling between modules

**Output format:**

Organize findings by impact:

- **HIGH**: Will cause maintenance problems soon
- **MEDIUM**: Should be addressed but not blocking
- **LOW**: Nice to fix when time permits

For each item include:
- File and line number
- What the debt is
- Why it matters
- Suggested improvement

**Important:** Only flag issues in the changed code, not pre-existing debt.
