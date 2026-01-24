---
description: |
  Deep exploration of a specific topic or area in the codebase.
  Use when you need to understand how something works: auth, API, database, etc.
  Returns file references and explanations of the relevant code.
argument-hint: "<topic to explore>"
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
      echo "Exploration complete."
---

# Codebase Exploration

Deep dive into a specific topic in this codebase.

**Topic**: $ARGUMENTS

## Exploration Strategy

<exploration>
Use the Task tool with `subagent_type: "Explore"` to investigate:

1. **Entry points** - Where does this topic get triggered/used?
2. **Core implementation** - Main files that implement this functionality
3. **Data flow** - How does data move through this feature?
4. **Dependencies** - What does this rely on? What relies on it?
5. **Configuration** - Any settings or env vars related to this?
6. **Tests** - How is this tested? What can tests teach us?

Be thorough - explore related files, not just direct matches.
</exploration>

## Output Format

<output_format>
Structure the findings as:

```markdown
# Exploration: [Topic]

## Summary
[2-3 sentence overview of how this works in the codebase]

## Key Files
| File | Purpose | Key Functions/Classes |
|------|---------|----------------------|
| `path/to/file.py` | Description | `function_name`, `ClassName` |

## How It Works
1. [Step 1 of the flow] - `file:line`
2. [Step 2 of the flow] - `file:line`
3. [Step 3 of the flow] - `file:line`

## Code Examples

### [Example 1: Common usage]
```[language]
// From file:line
[relevant code snippet]
```

## Related Areas
- [Related topic 1] - found in `path/to/files`
- [Related topic 2] - found in `path/to/files`

## Questions to Investigate Further
- [Things that weren't clear or need deeper exploration]
```
</output_format>

<critical_rules>
<rule priority="blocking">
Always include file:line references for every finding.
</rule>

<rule priority="blocking">
Show actual code snippets, not just descriptions.
</rule>

<rule priority="recommended">
If the topic is broad, suggest sub-topics to explore separately.
</rule>
</critical_rules>
