# XML Patterns for CLAUDE.md

## Why XML Tags?

- **Clarity**: Separate instructions, examples, context, references
- **Accuracy**: Reduce misinterpretation by 40-60%
- **Parseability**: Claude processes structured content better
- **Flexibility**: Modify sections without rewriting

## Essential Structure

```xml
<project_context>
  Brief description (2-3 sentences)
</project_context>

<key_directories>
  src/
  ├── components/  # UI components
  └── services/    # Business logic
</key_directories>

<standards>
  - Type hints required
  - Test coverage: 80%+
  - Line length: 100
</standards>

<critical_rules>
  <rule id="testing" priority="blocking">
    All features require tests before merge
  </rule>
</critical_rules>

<reference_docs>
  Architecture: @docs/architecture.md
  API patterns: @docs/api-patterns.md
</reference_docs>
```

## Tag Best Practices

1. **Consistent naming**: Use same tags throughout, reference explicitly
2. **Nest for hierarchy**: `<outer><inner></inner></outer>`
3. **Priority attributes**: `priority="blocking|recommended|optional"`
4. **Combine with patterns**: Examples, chain-of-thought, imports

## Nested Hierarchy Example

```xml
<critical_rules>
  <component_policy priority="blocking">
    <check_order>
      1. Design system
      2. Installed components
      3. External docs
    </check_order>

    Create new = ask user first
  </component_policy>
</critical_rules>
```

## Rule Priority Template

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
