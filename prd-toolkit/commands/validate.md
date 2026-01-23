---
allowed-tools:
  - Task
argument-hint: [file-path | github-issue-url]
description: Verify implementation matches PRD acceptance criteria
keywords:
  - prd-validation
  - acceptance-criteria
  - implementation-check
  - requirements-verification
triggers:
  - "validate PRD implementation"
  - "check acceptance criteria"
  - "verify requirements met"
  - "does code match PRD"
hooks:
  - event: Stop
    once: true
    command: |
      echo "Validation complete."
      echo "  - Create GitHub issues for missing items if needed"
      echo "  - Update PRD if scope changed"
---

## PRD to Validate

$ARGUMENTS

## Instructions

Use the Task tool to invoke the `prd-validator` agent to check if the implementation fulfills the PRD.

The agent should:

1. **Load the PRD** from file path or GitHub issue URL

2. **Extract checkable items**:
   - Acceptance Criteria
   - QA Checklist items
   - User Stories (verify flows exist)

3. **Explore the codebase** to verify each item:
   - Search for relevant code implementing each criterion
   - Check UI/UX flows if applicable
   - Look for tests covering the scenarios

4. **Generate validation report**:

```markdown
# PRD Validation: [Feature Name]

## Summary
- ✅ Completed: X/Y criteria
- ⚠️ Partial: X/Y criteria
- ❌ Missing: X/Y criteria

## Acceptance Criteria

### ✅ Completed
- [Criterion] → Found in `path/to/file.py:123`

### ⚠️ Partial
- [Criterion] → Implemented but [what's missing]

### ❌ Missing
- [Criterion] → No implementation found

## Recommendations
- [What to implement next]
- [Potential gaps to address]
```

5. **Offer next steps**:
   - Create GitHub issues for missing items
   - Update PRD if scope changed
   - Mark items as done in original PRD
