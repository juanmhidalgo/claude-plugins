---
description: Optimize a CLAUDE.md file by applying Anthropic's best practices automatically
argument-hint: "[path/to/CLAUDE.md] [--level=conservative|moderate|aggressive]"
keywords:
  - claude-md-optimization
  - token-efficiency
  - prompt-improvement
  - memory-optimization
triggers:
  - "optimize my CLAUDE.md"
  - "improve CLAUDE.md"
  - "make CLAUDE.md better"
  - "reduce CLAUDE.md tokens"
allowed-tools: [Read, Write, Bash]
---

# Optimize CLAUDE.md

Apply Anthropic's best practices to optimize CLAUDE.md structure, conciseness, and token efficiency.

<context>
**Skill activated**: `claude-md-best-practices`
**Working directory**: !`pwd`
**Arguments**: `$ARGUMENTS`
</context>

<task>
Transform CLAUDE.md file following best practices with automatic backup and preview.
</task>

## Parse Arguments

<file_location>
Path: `$1` or auto-detect (./CLAUDE.md → ./.claude/CLAUDE.md)
</file_location>

<optimization_level>
Extract `--level=X` from `$ARGUMENTS`. Default: `moderate`

**Conservative**: Add XML tags only, preserve all content
- ✓ XML structure for existing sections
- ✓ Fix tag consistency
- ✗ No content changes

**Moderate** [DEFAULT]: Balanced optimization
- ✓ Comprehensive XML structure
- ✓ Consolidate repetitive rules
- ✓ Remove obvious verbosity
- ✓ Suggest externalizing 50+ line examples
- ✓ Improve hierarchy with nesting

**Aggressive**: Maximum optimization
- ✓ Complete restructuring
- ✓ 50%+ token savings target
- ✓ Externalize all long examples
- ✓ Apply all persuasion principles
- ⚠️ Requires manual review
</optimization_level>

## Optimization Strategy

<xml_structure>
Add tags for key sections:

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

Use nesting for hierarchy and priority attributes (blocking, recommended, optional).
</xml_structure>

<conciseness_improvements>
**Remove verbosity**:
- Explanations of basic concepts → assume Claude's knowledge
- Repetitive rules → consolidate into single tagged sections

**Externalize examples**:
- 50+ line code examples → `@docs/patterns/[name].md`

**Consolidate**:
- Multiple similar sections → single structured section with clear hierarchy
</conciseness_improvements>

<content_enhancements>
- Add persuasion language to critical rules (Authority: "YOU MUST", "No exceptions")
- Add imports for external docs: `@docs/architecture.md`
- Group related content with parent tags
</content_enhancements>

## Workflow

<step1_backup priority="blocking">
YOU MUST create backup before ANY changes:

```bash
cp [original] [original].backup-[timestamp]
```

Show user: "Backup created: [path]"
</step1_backup>

<step2_transform>
Apply optimizations based on selected level.

Track metrics:
- Original: [X] lines, ~[Y] tokens
- Optimized: [A] lines, ~[B] tokens
- Savings: -[%] lines, -[%] tokens
</step2_transform>

<step3_preview>
Show optimization summary with:
1. Metrics comparison
2. Key changes list
3. Side-by-side examples (2-3 significant sections)
4. Backup location
</step3_preview>

<step4_confirm priority="blocking">
YOU MUST ask user for confirmation:

Options:
1. Yes - Apply changes and overwrite
2. No - Cancel (keep backup)
3. Save as new - Create [path].optimized.md

Do NOT proceed without explicit confirmation.
</step4_confirm>

<step5_apply>
If confirmed:
- Write optimized content
- Show success metrics
- Suggest: `/analyze-claude-md` to verify

If save-as-new:
- Write to `[original].optimized.md`
- Keep original untouched

If cancelled:
- Delete backup
- Show "Cancelled, no changes made"
</step5_apply>

<step6_post_optimization>
After success:

```
✓ CLAUDE.md optimized successfully!

**Metrics**:
- Original: [X] lines, ~[Y] tokens
- Optimized: [A] lines, ~[B] tokens
- Savings: -[%] tokens

**Backup**: [path]

**Next Steps**:
1. Review changes in your editor
2. Run `/analyze-claude-md` to verify
3. Test with Claude Code
4. Commit: `git add CLAUDE.md && git commit -m "Optimize CLAUDE.md"`
5. Delete backup if satisfied: `rm [backup-path]`

**To restore**: `cp [backup-path] CLAUDE.md`
```
</step6_post_optimization>

## Safety Checks

<content_preservation priority="blocking">
BEFORE writing optimized file:
1. All original information preserved (reorganized, not removed)
2. No loss of project-specific context
3. No removal of critical rules
4. XML tags properly nested and closed
5. Token count is LOWER than original
</content_preservation>

<sensitive_data_check priority="blocking">
If credentials, API keys, or connection strings found:
- FLAG IMMEDIATELY
- DO NOT include in optimized version
- Inform user of security issue
</sensitive_data_check>

<already_optimized_check>
If analysis score > 85:
- Inform: "File is already well-optimized (score: [X]/100)"
- Ask if user wants to proceed anyway
</already_optimized_check>

## Error Handling

<error_cases>
**File not found**: List available CLAUDE.md files, ask for correct path

**Backup fails**: STOP immediately, don't modify original, inform user

**Unsafe changes detected**: Show warning, ask for explicit confirmation
</error_cases>

## Critical Rules

<rule priority="blocking">
NEVER write to original file without creating backup first. No exceptions.
</rule>

<rule priority="blocking">
NEVER proceed with optimization without user confirmation after preview.
</rule>

<rule priority="blocking">
If sensitive data found, FLAG it and DO NOT include in optimized version.
</rule>

<rule priority="recommended">
Show side-by-side before/after for 2-3 key sections in preview.
</rule>

<rule priority="recommended">
Token savings must be realistic - if optimized has MORE tokens, something is wrong.
</rule>
