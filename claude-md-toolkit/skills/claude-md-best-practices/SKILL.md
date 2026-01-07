---
name: claude-md-best-practices
description: Anthropic's official best practices for CLAUDE.md files, including XML tag usage, memory patterns, and prompt engineering for optimal Claude Code performance
---

# CLAUDE.md Best Practices

Consolidated guide from Anthropic's official documentation for creating effective CLAUDE.md files.

## Core Principles

<context_window_management>
**The 200K context window is shared between:**
- System prompt
- Conversation history
- All CLAUDE.md files (project + user + enterprise)
- Commands, skills, hooks
- User's actual request

**Golden rule**: Only add what Claude doesn't already know.

Test each section: "Does Claude need this?" "Does this justify its token cost?"
</context_window_management>

<conciseness_imperative>
**Target sizes:**
- Small projects (< 10K LOC): 100-150 lines, ~800-1200 tokens
- Medium projects (10-50K LOC): 150-250 lines, ~1200-2000 tokens
- Large projects (> 50K LOC): 200-300 lines, ~2000-2500 tokens

**Red flags**: > 400 lines, multiple 50+ line examples, repeated explanations
</conciseness_imperative>

## XML Tags for Structure

<why_xml>
- **Clarity**: Separate instructions, examples, context, references
- **Accuracy**: Reduce misinterpretation by 40-60%
- **Parseability**: Claude processes structured content better
- **Flexibility**: Modify sections without rewriting
</why_xml>

<xml_patterns>
**Essential structure:**

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

**Tag best practices:**
1. **Consistent naming**: Use same tags throughout, reference explicitly
2. **Nest for hierarchy**: `<outer><inner></inner></outer>`
3. **Priority attributes**: `priority="blocking|recommended|optional"`
4. **Combine with patterns**: Examples, chain-of-thought, imports

**Example - Nested hierarchy:**

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
</xml_patterns>

## Memory System

<memory_hierarchy>
**Precedence order (higher overrides lower):**

1. **Enterprise**: `/etc/claude-code/CLAUDE.md` (org-wide, managed by IT)
2. **Project**: `./CLAUDE.md` (team, version controlled)
3. **Project Rules**: `./.claude/rules/*.md` (modular topics)
4. **User**: `~/.claude/CLAUDE.md` (personal, all projects)
5. **Local**: `./CLAUDE.local.md` (personal, this project, gitignored)
</memory_hierarchy>

<file_imports>
**Syntax**: `@path/to/file`

```markdown
See @README for overview
Git workflow: @docs/git-workflow.md
Personal: @~/.claude/my-preferences.md
```

**Rules**: Max depth 5 hops, relative/absolute paths work, not evaluated in code blocks
</file_imports>

<modular_rules>
**Organize with `.claude/rules/*.md`:**

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

**Path-specific rules (YAML frontmatter):**

```markdown
---
paths: src/api/**/*.ts
---

# API Development Rules

- All endpoints require validation
- Use standard error format
```

Rules without `paths` apply globally.
</modular_rules>

## Essential CLAUDE.md Content

<include>
**Must have:**
- Project purpose (1-2 sentences)
- Key directory structure (tree format)
- Standards (typing, testing, style)
- Common commands with examples
- Critical rules (blocking requirements)
- Workflows (standard patterns)
- References to detailed docs

**For critical rules, use Authority principle:**
```xml
<mandatory_checklist>
  <requirement priority="blocking">
    YOU MUST check design system before creating components.
    No exceptions.
  </requirement>
</mandatory_checklist>
```
</include>

<exclude>
**Never include:**
- ❌ API keys, credentials, tokens
- ❌ Database connection strings
- ❌ Detailed security vulnerabilities
- ❌ Explanations of concepts Claude knows
- ❌ Long code examples (use @references)
- ❌ Duplicate information from README
- ❌ Theoretical discussions without practical application
</exclude>

## Persuasion Principles

<authority>
**When to use**: Blocking requirements, safety-critical practices

```xml
<rule priority="blocking">
Write code before test? Delete it. Start over. No exceptions.
</rule>
```

Language: "YOU MUST", "NEVER", "No exceptions", imperative framing
</authority>

<commitment>
**When to use**: Multi-step processes, accountability

```xml
<instructions>
Before proceeding, you MUST:
1. Announce which skill you're using
2. Create TodoWrite checklist
3. Mark each step completed
</instructions>
```

Requires: Announcements, explicit choices, tracking
</commitment>

<social_proof>
**When to use**: Establishing norms, warning about failures

```xml
<anti_pattern>
Checklists without TodoWrite = steps get skipped. Every time.
</anti_pattern>
```

Language: "Every time", "Always", "X without Y = failure"
</social_proof>

<scarcity>
**When to use**: Time-sensitive workflows, preventing procrastination

```xml
<workflow>
After implementation: IMMEDIATELY run tests before proceeding.
</workflow>
```

Language: "IMMEDIATELY", "Before proceeding", "First thing"
</scarcity>

## Optimization Patterns

<pattern_1_externalize_examples>
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
</pattern_1_externalize_examples>

<pattern_2_consolidate_rules>
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
</pattern_2_consolidate_rules>

<pattern_3_hierarchy>
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
</pattern_3_hierarchy>

## Common Anti-Patterns

<anti_patterns>
| Issue | Why Bad | Fix |
|-------|---------|-----|
| No XML tags | Claude confuses context/instructions | Add structure |
| Verbose explanations | Wastes tokens on known concepts | Assume intelligence |
| Long examples inline | Better spent on actual work | Use @references |
| Flat structure | Hard to parse priority | Nest tags + attributes |
| Sensitive data | Security risk | Never commit secrets |
| Theoretical content | Doesn't solve real problems | Document friction points |
| Stale content | Misleads with outdated info | Review quarterly |
</anti_patterns>

## Quality Checklist

<pre_commit_checklist>
- [ ] **Concise**: Each paragraph justifies token cost
- [ ] **Structured**: XML tags separate sections
- [ ] **Hierarchical**: Priority clear via nesting/attributes
- [ ] **Referenced**: Long examples in external files
- [ ] **Actionable**: Workflows and commands, not theory
- [ ] **Secure**: No credentials or sensitive data
- [ ] **Current**: Reflects actual practices
- [ ] **Tested**: Validated with `/analyze-claude-md`
</pre_commit_checklist>

## Quick Start

<workflow>
1. **Bootstrap**: `/init` in project root
2. **Structure**: Add XML tags to generated content
3. **Refine**: Remove verbosity, add @references
4. **Modularize**: Move complex rules to `.claude/rules/`
5. **Validate**: Run `/analyze-claude-md`
6. **Iterate**: Update based on friction points
</workflow>

---

**Sources:**
- [XML Tags](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/use-xml-tags)
- [CLAUDE.md Guidelines](https://claude.com/blog/using-claude-md-files)
- [Memory System](https://code.claude.com/docs/en/memory)
