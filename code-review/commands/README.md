# Code Review Commands

Slash commands for code review workflows.

## Commands

| Command | Description |
|---------|-------------|
| `/code-review/branch [base]` | Review current branch vs base (default: main) |
| `/code-review/staged` | Review staged changes before commit |
| `/code-review/triage PR#` | Triage AI feedback from PR (Copilot, Gemini) |
| `/code-review/dismiss PR#` | Dismiss false positives on GitHub with justification |
| `/code-review/fixes-plan [name]` | Generate/update tracking document for fixes |
| `/code-review/mark-fixed [#\|all]` | Verify and mark issues as fixed |

## Workflows

### Branch Review (before PR)
```
/code-review/branch         → Identify issues in branch
        ↓
/code-review/fixes-plan X   → Generate REVIEW_FIXES.md
        ↓
    Implement fixes         → Write code to fix issues
        ↓
/code-review/mark-fixed 3   → Verify & mark issue #3 as fixed
        ↓
/code-review/mark-fixed all → Verify all remaining issues
```

### PR Feedback Triage (after PR)
```
/code-review/triage 42      → Filter AI feedback (valid vs false positive)
        ↓
/code-review/dismiss 42     → Dismiss false positives on GitHub
        ↓
/code-review/fixes-plan X   → Add verified issues to tracking doc
        ↓
    Implement fixes         → Write code to fix issues
        ↓
/code-review/mark-fixed all → Verify & update tracking doc
```

### Pre-commit Review
```
/code-review/staged         → Review before committing
```

## Related

- **Agent:** `branch-reviewer` - Performs the actual code review
- **Skill:** `branch-review` - Best practices and checklists
- **Skill:** `review-fixes-plan` - Template for tracking documents
- **Skill:** `receiving-code-review` - How to evaluate external feedback
