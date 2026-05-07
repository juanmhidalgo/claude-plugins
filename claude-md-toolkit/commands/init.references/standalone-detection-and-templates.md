# `/claude-md-toolkit:init` — Standalone Mode: Detection & Templates

Loaded by `/claude-md-toolkit:init` when running with `--standalone`.

## Project detection

```bash
# Detect project size
total_loc=$(find . -type f \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.tsx" -o -name "*.go" -o -name "*.rs" \) 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')

# Detect framework/language (in detection priority order)
framework="generic"
[ -f "manage.py" ] && framework="django"
[ -f "pyproject.toml" ] && grep -q "fastapi" pyproject.toml 2>/dev/null && framework="fastapi"
[ -f "package.json" ] && grep -q "react" package.json 2>/dev/null && framework="react"
[ -f "package.json" ] && grep -q "next" package.json 2>/dev/null && framework="nextjs"
[ -f "go.mod" ] && framework="go"
[ -f "Cargo.toml" ] && framework="rust"

# Determine size category
if [ "$total_loc" -lt 10000 ]; then
  size="small"
  token_target="800-1200"
elif [ "$total_loc" -lt 50000 ]; then
  size="medium"
  token_target="1200-2000"
else
  size="large"
  token_target="2000-2500"
fi
```

## Template selection

Templates live in `claude-md-toolkit/templates/`:
- `generic-small.md` — generic project, <10K LOC
- `django-small.md` — Django, <10K LOC
- `fastapi-small.md` — FastAPI, <10K LOC
- `react-small.md` — React, <10K LOC

Template structure (all templates follow this):

```xml
<project_context>
[Framework-specific context]
</project_context>

<architecture>
[Framework-specific architecture patterns]
</architecture>

<critical_rules>
<rule id="..." priority="blocking">
[Framework-specific critical rules]
</rule>
</critical_rules>

<standards>
[Code standards, naming conventions]
</standards>

<common_commands>
[Common development commands]
</common_commands>
```

## Generation steps

1. Check if `CLAUDE.md` already exists.
   - If yes: ask the user to confirm overwrite (create timestamped backup first).
   - If no: proceed.
2. Generate from template, substituting:
   - `{PROJECT_NAME}` — detected/inferred from `package.json`, `pyproject.toml`, or directory name
   - `{FRAMEWORK}` — detected framework
   - `{SIZE}` — small/medium/large
3. Ensure token count is within the size's target range.

## Generic-small template body (fallback)

```markdown
# CLAUDE.md

<project_context>
This is a {FRAMEWORK} project for [describe purpose]. The codebase follows [architectural pattern] principles.
</project_context>

<architecture>

## Project Structure

```
[Auto-detected directory structure]
```

</architecture>

<critical_rules>

<rule id="code-quality" priority="blocking">

## Code Quality Standards

YOU MUST ensure all code changes:
1. Pass existing tests (run test suite before committing)
2. Follow project coding standards
3. Include appropriate error handling

NEVER commit code that breaks existing functionality.

</rule>

</critical_rules>

<standards>

## Development Standards

- **Testing**: Write tests for new features
- **Documentation**: Update README.md for user-facing changes
- **Dependencies**: Document new dependencies and their purpose

</standards>

<common_commands>

## Development Commands

```bash
# [Framework-specific commands will be inserted here]
```

</common_commands>
```

## Error handling

| Case | Action |
|------|--------|
| Enhance mode — `CLAUDE.md` not found | Direct user to run `/init` first; offer `--standalone` as alternative; EXIT without creating files |
| Standalone — `CLAUDE.md` exists | Ask to confirm overwrite; create backup first; EXIT if declined |
| Project analysis fails | Fall back to `generic-small.md`; inform user |
| Backup creation fails | STOP immediately; do NOT modify or create files |

## Success message (standalone)

```
✓ CLAUDE.md generated successfully!

**Generated for**:
- Framework: [detected framework]
- Size: [small/medium/large] (~[X] LOC)
- Token count: ~[Y] tokens (target: [Z])

**Features**:
- ✓ XML semantic structure
- ✓ Framework-specific rules and patterns
- ✓ Priority-based rule system

**Next Steps**:
1. Review and customize CLAUDE.md
2. Add project-specific rules in <critical_rules>
3. Run `/claude-md-toolkit:analyze-claude-md` to verify score
4. Commit
```
