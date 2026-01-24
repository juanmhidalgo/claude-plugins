# CLAUDE.md Optimization Patterns

## Pattern 1: Externalize Examples

❌ **Before** (300+ tokens):
```markdown
## DataTable Pattern
[50+ lines of code example]
```

✅ **After** (50 tokens):
```xml
<common_patterns>
  DataTable with FilterBar: @docs/patterns/datatable.md
</common_patterns>
```

## Pattern 2: Consolidate Rules

❌ **Before** (multiple sections):
```markdown
### Component Rule 1
Before creating...
### Component Rule 2
Before creating...
```

✅ **After** (single tagged section):
```xml
<component_policy priority="blocking">
  Check: 1) Design system 2) Installed 3) External
  Create new = ask first
</component_policy>
```

## Pattern 3: Use Priority Hierarchy

```xml
<rules>
  <critical priority="blocking">
    <!-- Must follow, no exceptions -->
  </critical>

  <recommended>
    <!-- Best practices, context-dependent -->
  </recommended>

  <reference>
    <!-- Nice to know, optional -->
  </reference>
</rules>
```

## Pattern 4: Use File Imports

Instead of inline content, reference external files:

```markdown
## Detailed Documentation

- Architecture decisions: @docs/architecture.md
- API patterns: @docs/api-patterns.md
- Component guidelines: @docs/components.md
```

## Pattern 5: Modular Rules

Move complex rules to `.claude/rules/`:

```
.claude/rules/
├── frontend/
│   ├── react.md
│   └── styling.md
├── backend/
│   ├── api-design.md
│   └── database.md
└── testing.md
```

With path-specific rules:

```markdown
---
paths: src/api/**/*.ts
---

# API Development Rules

- All endpoints require validation
- Use standard error format
```
