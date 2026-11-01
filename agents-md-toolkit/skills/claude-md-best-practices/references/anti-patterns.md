# CLAUDE.md Anti-Patterns

## Common Issues

| Issue | Why Bad | Fix |
|-------|---------|-----|
| No XML tags | Claude confuses context/instructions | Add structure |
| Verbose explanations | Wastes tokens on known concepts | Assume intelligence |
| Long examples inline | Better spent on actual work | Use @references |
| Flat structure | Hard to parse priority | Nest tags + attributes |
| Sensitive data | Security risk | Never commit secrets |
| Theoretical content | Doesn't solve real problems | Document friction points |
| Stale content | Misleads with outdated info | Review quarterly |

## Detection Checklist

Before committing CLAUDE.md changes:

- [ ] **Concise**: Each paragraph justifies token cost
- [ ] **Structured**: XML tags separate sections
- [ ] **Hierarchical**: Priority clear via nesting/attributes
- [ ] **Referenced**: Long examples in external files
- [ ] **Actionable**: Workflows and commands, not theory
- [ ] **Secure**: No credentials or sensitive data
- [ ] **Current**: Reflects actual practices
- [ ] **Tested**: Validated with `/analyze-claude-md`

## Red Flags

- File > 400 lines
- Multiple 50+ line code examples
- Repeated explanations of the same concept
- Explanations of well-known concepts (REST, async/await, etc.)
- Copy-pasted README content
