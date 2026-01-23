# Plugin & Skill Creation Guidelines

Lessons learned from Anthropic's official documentation and practical experience.

<sources>
- https://claude.com/blog/building-agents-with-skills-equipping-agents-for-specialized-work
- https://claude.com/blog/building-skills-for-claude-code
- https://claude.com/blog/how-to-create-skills-key-steps-limitations-and-examples
</sources>

## Skill Best Practices

<skill_description priority="critical">

### Description is the Most Critical Field

The `description` field determines when Claude activates the skill. Write it from Claude's perspective:

**Good description:**
```yaml
description: |
  Use when generating cross-team API handoff prompts. Provides structured output
  formats for communicating API changes. Do NOT use for general API documentation
  or OpenAPI spec generation.
```

**Bad description:**
```yaml
description: Best practices for documenting API changes
```

**Include in description:**
- When to activate (specific task/context)
- What it provides (concrete outputs)
- What it does NOT do (boundaries)

</skill_description>

<skill_content priority="critical">

### Content: Institutional Knowledge Only

Skills should contain knowledge Claude doesn't have from training:

| Include | Exclude |
|---------|---------|
| Your team's specific output formats | Generic best practices |
| Classification rules and decision trees | Explanations of common concepts |
| Checklists specific to your workflow | Theoretical discussions |
| Schema templates with your conventions | Content Claude already knows |

**Test**: "Would Claude give this advice without the skill?" If yes, remove it.

</skill_content>

<progressive_disclosure>

### Progressive Disclosure Pattern

Keep skills lean (~100 lines). Use three tiers:

1. **Metadata** (~50 tokens): Name + description - always loaded
2. **SKILL.md** (~500 tokens): Core instructions - loaded when needed
3. **Reference files** (2000+ tokens): `references/` directory - loaded on-demand

```
skill-name/
├── SKILL.md           # Lean core instructions
└── references/
    ├── examples.md    # Detailed examples (loaded via @)
    └── templates.md   # Full templates (loaded via @)
```

</progressive_disclosure>

## Command Best Practices

<command_structure>

### Required Frontmatter

```yaml
---
allowed-tools:
  - Read
  - Glob
  - Bash(git diff *)      # Scoped bash commands
argument-hint: "[description]"
description: One-line purpose
keywords:
  - kebab-case-terms
triggers:
  - "natural language phrases"
hooks:
  - event: Stop
    once: true
    command: |
      echo "Next steps:"
      echo "  - Actionable suggestion"
---
```

</command_structure>

<command_patterns>

### Patterns to Use

1. **Shell embedding** for context:
   ```markdown
   ## Context
   - **Current branch**: !`git branch --show-current`
   - **Recent commits**: !`git log --oneline -5`
   ```

2. **Skill import** via `@` reference:
   ```markdown
   <best_practices>
   @plugin-name/skills/skill-name/SKILL.md
   </best_practices>
   ```

3. **Hooks** for next step guidance:
   ```yaml
   hooks:
     - event: Stop
       once: true
       command: |
         echo "Done. Next: /command:next-step"
   ```

4. **Arguments** via `$ARGUMENTS` or `$1`:
   ```markdown
   **Target**: $ARGUMENTS
   ```

</command_patterns>

## Common Mistakes to Avoid

<anti_patterns>

| Mistake | Why It's Bad | Fix |
|---------|--------------|-----|
| Generic skill description | Won't trigger correctly | Be specific about when/what |
| Skill has generic knowledge | Wastes context tokens | Only include institutional knowledge |
| Command doesn't import skill | Skill never loaded | Use `@path/to/SKILL.md` |
| No hooks | Poor UX, no next steps | Add Stop hooks |
| Missing shell context | Less useful output | Use `!` backticks |
| Long skill (200+ lines) | Context bloat | Use progressive disclosure |

</anti_patterns>

## Pre-Commit Checklist

<checklist>

### Before Creating a Plugin

- [ ] Identify repeated task (done 5+ times, will do 10+ more)
- [ ] Define success criteria and output format
- [ ] Verify content is institutional knowledge, not generic

### Skill Review

- [ ] Description states when to use AND when NOT to use
- [ ] Content is ~100 lines or uses progressive disclosure
- [ ] No generic knowledge Claude already has
- [ ] `user-invocable` set correctly (true/false)

### Command Review

- [ ] `allowed-tools` includes all needed tools
- [ ] `hooks` provide next step guidance
- [ ] Shell embedding for relevant context
- [ ] Skill imported via `@` if needed
- [ ] `keywords` and `triggers` for discoverability

### Final Steps

- [ ] Version bumped in `plugin.json`
- [ ] CHANGELOG.md updated
- [ ] README.md documents commands

</checklist>
