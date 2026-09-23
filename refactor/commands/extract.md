---
description: |
  Use when you know what to extract and want a safe extraction with proper naming and placement.
  Do NOT use while still discovering what to refactor — use /refactor:analyze first.
argument-hint: "<what-to-extract>"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Agent
  - Edit
  - Write
  - Bash(git *)
  - Bash(gh pr list *)
  - Bash(gh pr diff *)
  - AskUserQuestion
hooks:
  - event: Stop
    once: true
    command: |
      echo ""
      echo "Extraction complete."
      echo "  - Run tests to verify"
      echo "  - /code-review:staged to review your changes"
      echo "  - /commit when ready"
---

# Code Extraction

Safely extract code into a reusable unit.

**What to extract**: $ARGUMENTS

## Phase 1: Understand the Context

<exploration>
Use the Agent tool with `subagent_type: "Explore"` to find:

1. The code to extract (if not specified precisely)
2. Where similar extractions live in this project
3. Naming conventions for functions/classes/modules
4. Test files that need updating
</exploration>

## Phase 1.5: Conflict Check

<conflict_check>
Extraction rewrites existing lines, so any open PR touching the same file will conflict. One call, before you clarify anything:

```bash
gh pr list --state open --limit 40 --json number,title,author,isDraft,updatedAt,files \
  --jq '.[] | select(.files[].path | test("<source-file>|<destination-file>")) | {number, title, author: .author.login, isDraft, updatedAt}'
git status --porcelain -- <source-file> <destination-file>
```

Act on the result:

| Result | Action |
|--------|--------|
| No open PR, clean status | Proceed to Phase 2 |
| Uncommitted local edits | Tell the user; offer to commit or stash first |
| An open PR touches the file | **Stop and surface it** — PR number, title, author, age. Use AskUserQuestion: extract now and accept the conflict, extract a different piece, or wait for the PR to merge. Do not decide this silently |
| A PR calls the symbol you are moving but does not touch these files | Surface it too — the move merges clean and breaks that PR at runtime. Keep the old name as a shim, or wait |
| `gh` missing or unauthenticated | Say so and continue on the local check alone — do not report the file as clear |

</conflict_check>

## Phase 2: Clarify Extraction

<clarification>
Use AskUserQuestion to confirm:

| Question | Impact if wrong | Default |
|----------|-----------------|---------|
| Extract as function, class, or module? | Structure mismatch | Function if <50 lines |
| Placement - same file or new file? | Import complexity | Same file if related |
| Name for the extracted code? | Discoverability | [Suggest based on content] |
</clarification>

## Phase 3: Perform Extraction

<extraction_steps>
Extract with explicit inputs, outputs and side effects; update the call site,
imports and every consumer; add a unit test for the extracted unit. Follow the
project's docstring convention.
</extraction_steps>

## Phase 4: Verify

<verification>
After extraction:

```bash
# Run tests
npm test  # or pytest, etc.

# Check for lint issues
npm run lint  # or equivalent

# Review the diff
git diff
```

If tests fail, investigate before committing.
</verification>

<output_format>
```markdown
## Extraction Summary

**Extracted**: `function_name` from `original_file.py:45-78`
**Placed in**: `new_location.py` (or same file)
**Parameters**: `param1: Type, param2: Type`
**Returns**: `ReturnType`

### Before
```python
# original_file.py:45
[original code snippet]
```

### After
```python
# new_location.py (new)
def function_name(param1: Type, param2: Type) -> ReturnType:
    """Brief description."""
    [extracted code]

# original_file.py:45 (updated)
result = function_name(arg1, arg2)
```

### Tests Added
- `test_function_name_basic` - tests normal case
- `test_function_name_edge` - tests edge case

### Next Steps
- [ ] Run full test suite
- [ ] Review diff before committing
- [ ] Update any documentation
```
</output_format>

<critical_rules>
<rule priority="blocking">
Never extract without understanding what consumes the code.
</rule>

<rule priority="blocking">
Never edit a file that an open PR is also editing without telling the user first. The extraction is cheap to redo; someone else's branch is not.
</rule>

<rule priority="blocking">
Always show before/after code for verification.
</rule>

<rule priority="blocking">
Run tests after extraction before considering it done.
</rule>

<rule priority="recommended">
Follow existing project conventions for naming and placement.
</rule>
</critical_rules>
