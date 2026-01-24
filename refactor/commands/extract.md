---
description: |
  Extract code into a new function, class, or module.
  Guides you through the extraction with proper naming and placement.
  Use when you know what to extract but want help doing it safely.
argument-hint: "<what-to-extract>"
allowed-tools:
  - Read
  - Glob
  - Grep
  - Task
  - Edit
  - Write
  - Bash(git *)
  - AskUserQuestion
hooks:
  - event: Stop
    once: true
    command: |
      echo ""
      echo "Extraction complete."
      echo "  - Run tests to verify"
      echo "  - /commit when ready"
---

# Code Extraction

Safely extract code into a reusable unit.

**What to extract**: $ARGUMENTS

## Phase 1: Understand the Context

<exploration>
Use the Task tool with `subagent_type: "Explore"` to find:

1. The code to extract (if not specified precisely)
2. Where similar extractions live in this project
3. Naming conventions for functions/classes/modules
4. Test files that need updating
</exploration>

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
Follow this checklist:

1. **Identify boundaries**
   - Find exact start/end lines
   - Identify inputs (parameters needed)
   - Identify outputs (return values)
   - Identify side effects (mutations, I/O)

2. **Create the new unit**
   - Define signature with clear parameter names
   - Add docstring explaining purpose
   - Move the code
   - Add return statement if needed

3. **Update the original location**
   - Replace extracted code with a call
   - Pass required arguments
   - Handle return value

4. **Fix imports**
   - Add imports in the new location
   - Add exports if in new file
   - Update imports in consumers

5. **Update tests**
   - Add unit test for extracted function
   - Verify existing tests still pass
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
Always show before/after code for verification.
</rule>

<rule priority="blocking">
Run tests after extraction before considering it done.
</rule>

<rule priority="recommended">
Follow existing project conventions for naming and placement.
</rule>
</critical_rules>
