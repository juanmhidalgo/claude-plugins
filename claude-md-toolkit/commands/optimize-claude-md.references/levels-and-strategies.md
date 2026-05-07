# `/claude-md-toolkit:optimize-claude-md` — Optimization Levels & Strategies

Loaded by `/claude-md-toolkit:optimize-claude-md`.

## Levels

### Conservative
- ✓ XML structure for existing sections
- ✓ Fix tag consistency
- ✗ No content changes

### Moderate (default)
- ✓ Comprehensive XML structure
- ✓ Consolidate repetitive rules
- ✓ Remove obvious verbosity
- ✓ Suggest externalizing 50+ line examples
- ✓ Improve hierarchy with nesting

### Aggressive
- ✓ Complete restructuring
- ✓ 50%+ token-savings target
- ✓ Externalize all long examples
- ✓ Apply all persuasion principles
- ⚠️ Requires manual review before commit

## XML structure (target shape)

```xml
<project_context>Brief description</project_context>
<key_directories>Directory tree</key_directories>
<standards>Code standards</standards>

<critical_rules>
  <rule id="..." priority="blocking">...</rule>
</critical_rules>

<common_commands>Bash commands</common_commands>
<reference_docs>External links</reference_docs>
```

Use nesting for hierarchy and priority attributes (`blocking`, `critical`, `recommended`, `optional`).

## Conciseness improvements

**Remove verbosity:**
- Explanations of basic concepts → assume Claude's knowledge
- Repetitive rules → consolidate into single tagged sections

**Externalize examples:**
- 50+ line code examples → move to `@docs/patterns/[name].md` (or `references/`)

**Consolidate:**
- Multiple similar sections → single structured section with clear hierarchy

## Content enhancements

- Add persuasion language to critical rules (Authority: "YOU MUST", "No exceptions")
- Add imports for external docs: `@docs/architecture.md`
- Group related content with parent tags

## Workflow steps (detailed)

### Step 1 — Backup (blocking)
```bash
cp [original] [original].backup-[timestamp]
```
Show: "Backup created: [path]"

### Step 2 — Transform
Apply optimizations at the chosen level. Track metrics:
- Original: [X] lines, ~[Y] tokens
- Optimized: [A] lines, ~[B] tokens
- Savings: -[%] lines, -[%] tokens

### Step 3 — Preview
Show optimization summary:
1. Metrics comparison
2. Key changes list
3. Side-by-side examples (2-3 significant sections)
4. Backup location

### Step 4 — Confirm (blocking)
Ask the user:
1. Yes — apply changes and overwrite
2. No — cancel (keep backup)
3. Save as new — create `[path].optimized.md`

Do NOT proceed without explicit confirmation.

### Step 5 — Apply
- If confirmed: write optimized content, show success metrics, suggest `/claude-md-toolkit:analyze-claude-md`.
- If save-as-new: write to `[original].optimized.md`, keep original untouched.
- If cancelled: delete backup, show "Cancelled, no changes made".

### Step 6 — Post-optimization message

```
✓ CLAUDE.md optimized successfully!

**Metrics**:
- Original: [X] lines, ~[Y] tokens
- Optimized: [A] lines, ~[B] tokens
- Savings: -[%] tokens

**Backup**: [path]

**Next Steps**:
1. Review changes
2. Run `/claude-md-toolkit:analyze-claude-md` to verify
3. Test with Claude Code
4. Commit: `git add CLAUDE.md && git commit -m "Optimize CLAUDE.md"`
5. Delete backup if satisfied: `rm [backup-path]`

**To restore**: `cp [backup-path] CLAUDE.md`
```

## Safety checks

### Content preservation (blocking)
Before writing the optimized file:
1. All original information preserved (reorganized, not removed)
2. No loss of project-specific context
3. No removal of critical rules
4. XML tags properly nested and closed
5. Token count is LOWER than original

### Sensitive data (blocking)
If credentials, API keys, or connection strings are found:
- FLAG IMMEDIATELY
- DO NOT include in the optimized version
- Inform the user of the security issue

### Already optimized
If analysis score > 85:
- Inform: "File is already well-optimized (score: [X]/100)"
- Ask if the user wants to proceed anyway

## Error handling

| Case | Action |
|------|--------|
| File not found | List available `CLAUDE.md` files; ask for correct path |
| Backup fails | STOP; don't modify original; inform user |
| Unsafe changes detected | Show warning; require explicit confirmation |
