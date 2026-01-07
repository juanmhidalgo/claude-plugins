# claude-md-toolkit

Analyze and optimize CLAUDE.md files using Anthropic's official best practices for prompt engineering, XML tags, and memory patterns.

## Overview

This plugin provides tools to ensure your CLAUDE.md files follow Anthropic's recommended patterns for:
- **XML tag structure** - Clear separation of instructions, context, examples, and references
- **Token efficiency** - Concise prompts that maximize the 200K context window
- **Memory patterns** - Proper use of imports, modularization, and hierarchy
- **Persuasion principles** - Effective enforcement of critical rules

## Commands

### `/analyze-claude-md [path]`

Comprehensive analysis of a CLAUDE.md file against Anthropic's best practices.

**Usage:**
```bash
/analyze-claude-md                    # Analyzes ./CLAUDE.md or ./.claude/CLAUDE.md
/analyze-claude-md path/to/CLAUDE.md  # Analyzes specific file
```

**Generates:**
- Optimization score (0-100) across 4 dimensions:
  - Structure (XML tags, hierarchy, consistency)
  - Conciseness (token efficiency, verbosity)
  - Content Quality (essential sections, references)
  - Memory Patterns (imports, modularization)
- Detailed recommendations with line numbers
- Token efficiency report with savings estimates
- Before/after examples for key improvements

**Example output:**
```
# CLAUDE.md Analysis Report

Score: 72/100 (Needs improvement)

## Metrics
- Lines: 332
- Estimated Tokens: ~2656
- Target Range: ~1200-2000 (medium project)
- Status: Above target (32% over)

## High Priority Issues
1. Missing XML structure (lines 1-332)
   - Problem: No XML tags to separate sections
   - Impact: Claude may confuse instructions with context
   - Fix: Add <project_context>, <critical_rules>, etc.

2. Verbose explanations (lines 134-173)
   - Problem: 150 tokens explaining basic concepts
   - Fix: Reduce to 50 tokens assuming Claude's knowledge

[... detailed analysis continues ...]
```

### `/optimize-claude-md [path] [--level=conservative|moderate|aggressive]`

Automatically optimize a CLAUDE.md file by applying best practices.

**Usage:**
```bash
/optimize-claude-md                             # Moderate optimization of ./CLAUDE.md
/optimize-claude-md --level=conservative        # Only add XML tags, no content changes
/optimize-claude-md --level=aggressive          # Maximum optimization (50%+ token savings)
/optimize-claude-md path/to/CLAUDE.md          # Optimize specific file
```

**Optimization Levels:**

| Level | Changes | Use When |
|-------|---------|----------|
| `conservative` | Add XML tags only, preserve all content | First time optimizing, want minimal disruption |
| `moderate` *(default)* | XML tags + consolidation + verbosity reduction | Standard optimization, safe balance |
| `aggressive` | Complete restructuring for max efficiency | Expert users, willing to review changes |

**Safety features:**
- Automatic backup created before changes (`.backup-[timestamp]`)
- Preview with side-by-side comparisons
- Content preservation checks
- Sensitive data detection
- Option to save as new file instead of overwriting

**Example output:**
```
# CLAUDE.md Optimization Complete

Level: Moderate
File: ./CLAUDE.md

## Metrics
- Original: 332 lines, ~2656 tokens
- Optimized: 187 lines, ~1496 tokens
- Savings: -44% tokens

## Changes Applied
✓ Added XML tag structure to 7 sections
✓ Consolidated 8 repetitive rules into 1 tagged section
✓ Removed verbose explanations from 3 sections
✓ Externalized 2 long code examples to @docs/patterns/

Backup: ./CLAUDE.md.backup-2026-01-07-143052
```

## Installation

### From Marketplace

```bash
# Add marketplace (one-time)
/plugin marketplace add juanmhidalgo/claude-plugins

# Install plugin
/plugin install claude-md-toolkit@juanmhidalgo-plugins
```

### Manual Installation

```bash
# Clone repository
git clone https://github.com/juanmhidalgo/claude-plugins.git

# Install plugin
cd claude-plugins
/plugin install ./claude-md-toolkit
```

## Skill: claude-md-best-practices

The plugin includes a comprehensive skill documenting all Anthropic best practices:

**Content:**
- XML tag patterns and examples
- CLAUDE.md structure guidelines
- Memory system (hierarchy, imports, `.claude/rules/`)
- Persuasion principles for rule enforcement
- Token efficiency optimization techniques
- Quality checklist and anti-patterns
- References to official Anthropic docs

**Activation:**
The skill is automatically activated when using the commands. You can also reference it directly in your prompts when creating or modifying CLAUDE.md files.

## Best Practices

### When to Analyze

Run `/analyze-claude-md` when:
- Creating a new CLAUDE.md file (after `/init`)
- After significant project changes
- When Claude seems to misunderstand instructions
- Before committing CLAUDE.md changes
- Quarterly review of existing files

### When to Optimize

Run `/optimize-claude-md` when:
- Analysis score < 75
- Token count significantly above target
- No XML structure exists
- Content has grown organically and become verbose
- Migrating from old CLAUDE.md format

### Recommended Workflow

1. **Bootstrap**: Run `/init` to create initial CLAUDE.md
2. **Analyze**: Run `/analyze-claude-md` to get baseline score
3. **Optimize**: Run `/optimize-claude-md --level=moderate`
4. **Verify**: Run `/analyze-claude-md` again to confirm improvement
5. **Review**: Manually check changes in your editor
6. **Test**: Use Claude Code to ensure behavior is correct
7. **Commit**: Add to version control
8. **Maintain**: Re-analyze quarterly or after major changes

## Examples

### Example 1: First-time optimization

```bash
# Analyze current file
> /analyze-claude-md
# Score: 62/100 (Needs improvement)
# No XML structure, verbose, 2800 tokens

# Optimize with moderate level
> /optimize-claude-md --level=moderate
# Preview shows: 62/100 → expected 85-90/100
# Savings: -45% tokens

# Verify improvement
> /analyze-claude-md
# Score: 87/100 (Good)
# 1540 tokens, well-structured
```

### Example 2: Conservative optimization for existing projects

```bash
# Team has established CLAUDE.md with good content
# Want XML structure without changing wording

> /optimize-claude-md --level=conservative
# Only adds XML tags, preserves all content
# Savings: -15% tokens (from improved parsing)
```

### Example 3: Analyzing a subdirectory CLAUDE.md

```bash
# Working in src/api/ with local context
> /analyze-claude-md src/api/.claude/CLAUDE.md
# Analyzes subdirectory-specific guidelines
```

## FAQ

**Q: Will optimization change my project-specific instructions?**
A: No. Optimization preserves all content and meaning, only improving structure and reducing unnecessary verbosity.

**Q: What if I don't like the optimized version?**
A: A backup is automatically created. Restore with: `cp CLAUDE.md.backup-[timestamp] CLAUDE.md`

**Q: Can I undo an optimization?**
A: Yes, backups are timestamped. You can also save as a new file first to compare.

**Q: How often should I optimize?**
A: Quarterly, or when the analysis score drops below 75.

**Q: What's the difference between moderate and aggressive?**
A: Moderate balances safety and improvement (~30-40% savings). Aggressive maximizes token efficiency (50%+ savings) but may need manual review.

**Q: Will this work with `.claude/rules/*.md` files?**
A: Yes! Point the commands at any markdown file with prompts or instructions.

## Technical Details

### Token Estimation

- Uses ~8 tokens per line as estimation baseline
- Actual tokens may vary based on content density
- Savings calculations are conservative estimates

### XML Tag Guidelines

Based on Anthropic's official documentation:
- No canonical "best" tags (use descriptive names)
- Nest tags for hierarchy: `<outer><inner></inner></outer>`
- Reference tags in instructions: "Using the <contract> tags..."
- Combine with other patterns (examples, chain-of-thought)

### Safety Checks

Before writing optimized files:
- ✓ Content preservation verified
- ✓ No loss of project-specific context
- ✓ XML syntax validated
- ✓ Token efficiency confirmed
- ✓ Sensitive data detection

## References

This plugin consolidates best practices from:
- [XML Tags](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/use-xml-tags) - Anthropic's guide to structured prompts
- [CLAUDE.md Guidelines](https://claude.com/blog/using-claude-md-files) - Official blog post on file structure
- [Memory System](https://code.claude.com/docs/en/memory) - Claude Code's memory hierarchy

## Contributing

Found an issue or have a suggestion? Open an issue at:
https://github.com/juanmhidalgo/claude-plugins/issues

## License

MIT License - See LICENSE file for details

## Author

Juan M. Hidalgo

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for version history and updates.
