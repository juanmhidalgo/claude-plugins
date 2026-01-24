---
name: claude-md-best-practices
description: |
  Use when creating, analyzing, or optimizing CLAUDE.md files for Claude Code projects.
  Provides XML structure patterns, memory hierarchy, and token optimization techniques.
  Do NOT use for general prompt engineering or non-CLAUDE.md configuration files.
keywords:
  - claude-md
  - memory-file
  - xml-tags
  - prompt-engineering
  - context-management
triggers:
  - "write better CLAUDE.md"
  - "CLAUDE.md best practices"
  - "optimize memory file"
  - "structure CLAUDE.md"
---

# CLAUDE.md Best Practices

Consolidated guide from Anthropic's official documentation.

## Core Principles

<context_window_management>
**The 200K context window is shared between:**
- System prompt, conversation history, all CLAUDE.md files
- Commands, skills, hooks, and user's actual request

**Golden rule**: Only add what Claude doesn't already know.
</context_window_management>

<conciseness_imperative>
**Target sizes:**
- Small projects (< 10K LOC): 100-150 lines
- Medium projects (10-50K LOC): 150-250 lines
- Large projects (> 50K LOC): 200-300 lines

**Red flags**: > 400 lines, multiple 50+ line examples, repeated explanations
</conciseness_imperative>

## XML Tags for Structure

XML tags reduce misinterpretation by 40-60% and help Claude process structured content better.

**Essential tags**: `<project_context>`, `<key_directories>`, `<standards>`, `<critical_rules>`, `<reference_docs>`

For detailed XML patterns and examples, see [patterns.md](references/patterns.md).

## Memory System

<memory_hierarchy>
**Precedence order (higher overrides lower):**
1. **Enterprise**: `/etc/claude-code/CLAUDE.md`
2. **Project**: `./CLAUDE.md`
3. **Project Rules**: `./.claude/rules/*.md`
4. **User**: `~/.claude/CLAUDE.md`
5. **Local**: `./CLAUDE.local.md` (gitignored)
</memory_hierarchy>

**File imports**: Use `@path/to/file` syntax. Max depth 5 hops.

**Modular rules**: Use `.claude/rules/*.md` with optional `paths:` frontmatter for path-specific rules.

## Essential Content

<include>
**Must have:**
- Project purpose (1-2 sentences)
- Key directory structure (tree format)
- Standards (typing, testing, style)
- Common commands with examples
- Critical rules (blocking requirements)
- References to detailed docs
</include>

<exclude>
**Never include:**
- API keys, credentials, tokens
- Explanations of concepts Claude knows
- Long code examples (use @references)
- Duplicate information from README
</exclude>

## Persuasion Principles

Use these for critical rules enforcement. See [persuasion.md](references/persuasion.md) for patterns:

- **Authority**: "YOU MUST", "NEVER", "No exceptions"
- **Commitment**: Announcements, explicit choices, tracking
- **Social proof**: "Every time", "X without Y = failure"
- **Scarcity**: "IMMEDIATELY", "Before proceeding"

## Optimization Patterns

See [optimization.md](references/optimization.md) for detailed patterns:

1. **Externalize examples**: Use `@docs/patterns/` instead of inline code
2. **Consolidate rules**: Single tagged section instead of scattered rules
3. **Hierarchy**: Use priority attributes (`blocking|recommended|optional`)

## Common Anti-Patterns

See [anti-patterns.md](references/anti-patterns.md) for the full table.

Key issues: No XML tags, verbose explanations, inline examples, flat structure, sensitive data.

## Quick Start Workflow

1. **Bootstrap**: `/init` in project root
2. **Structure**: Add XML tags to generated content
3. **Refine**: Remove verbosity, add @references
4. **Modularize**: Move complex rules to `.claude/rules/`
5. **Validate**: Run `/analyze-claude-md`

---

**Sources:**
- [XML Tags](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/use-xml-tags)
- [CLAUDE.md Guidelines](https://claude.com/blog/using-claude-md-files)
- [Memory System](https://code.claude.com/docs/en/memory)
