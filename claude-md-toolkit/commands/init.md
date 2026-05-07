---
description: |
  Use when creating a new CLAUDE.md or bootstrapping one for a project that doesn't have one yet.
  Do NOT use to improve an existing CLAUDE.md — use /claude-md-toolkit:optimize-claude-md instead.
argument-hint: "[--standalone]"
keywords:
  - claude-md-init
  - memory-setup
  - project-config
  - claude-configuration
triggers:
  - "create CLAUDE.md"
  - "initialize memory file"
  - "set up CLAUDE.md"
  - "start new CLAUDE.md"
allowed-tools: [Read, Write, Bash, Glob, Grep]
hooks:
  - event: Stop
    once: true
    command: |
      echo "CLAUDE.md initialized."
      echo "  - /claude-md-toolkit:analyze-claude-md to verify quality"
      echo "  - Review and customize for your project"
---

# Initialize CLAUDE.md

Create a best-practices CLAUDE.md file with optimal structure and token efficiency.

<context>
**Skill activated**: `claude-md-best-practices`
**Working directory**: !`pwd`
**Arguments**: `$ARGUMENTS`
</context>

## Modes

This command runs in one of two modes:

1. **Enhance mode** (default): optimize the existing `CLAUDE.md` produced by Claude Code's built-in `/init`.
2. **Standalone mode** (`--standalone`): generate an optimized `CLAUDE.md` from scratch (no `/init` required).

If `$ARGUMENTS` contains `--standalone`, use standalone mode. Otherwise, enhance mode.

---

## Mode 1: Enhance (default)

**Prerequisite**: the user has run Claude Code's built-in `/init` so `CLAUDE.md` exists.

### Step 1: check prerequisites

If `CLAUDE.md` does NOT exist, print this and STOP:

```
❌ CLAUDE.md not found.

Please run Claude Code's built-in /init command first to generate a base CLAUDE.md, then run this command to enhance it with Anthropic's best practices.

Workflow:
1. /init                          # Generate base CLAUDE.md
2. /claude-md-toolkit:init        # Enhance with best practices

Alternatively, generate from scratch:
/claude-md-toolkit:init --standalone
```

### Step 2: analyze existing CLAUDE.md

Read the existing file and determine:
- Current token count
- Current structure (XML tags present?)
- Project context defined?
- Critical rules defined?

### Step 3: enhance with best practices

Apply the same optimization logic as `/optimize-claude-md` at `--level=moderate`:

1. Create backup `CLAUDE.md.backup-[timestamp]`
2. Apply optimizations:
   - Add XML semantic structure (`<project_context>`, `<critical_rules>`, etc.)
   - Apply persuasion principles to critical rules (Authority, Commitment)
   - Add priority attributes (`blocking`, `critical`, `recommended`)
   - Consolidate repetitive content
   - Improve hierarchy/nesting
3. Preview the changes (before/after) to the user
4. Ask for confirmation
5. Apply if confirmed

### Step 4: success message

```
✓ CLAUDE.md enhanced successfully!

**Applied enhancements**:
- ✓ XML semantic structure added
- ✓ Critical rules marked with priority attributes
- ✓ Persuasion principles applied
- ✓ Token-optimized structure

**Metrics**:
- Original: [X] tokens
- Enhanced: [Y] tokens
- Effectiveness: +[Z]% (structure score improved)

**Backup**: CLAUDE.md.backup-[timestamp]

**Next Steps**:
1. Review changes
2. Test with Claude Code
3. Commit: `git add CLAUDE.md && git commit -m "feat: enhance CLAUDE.md with best practices"`
```

---

## Mode 2: Standalone (`--standalone`)

Generate an optimized `CLAUDE.md` from scratch, without requiring `/init`. The workflow detects the project's framework, size, and selects an appropriate template.

For detection commands, template selection logic, the generic-small template body, error handling, and the success message, see `@init.references/standalone-detection-and-templates.md`.

---

<critical_rules>
<rule priority="blocking">
In enhance mode, NEVER generate a file if `CLAUDE.md` doesn't exist. User MUST run `/init` first.
</rule>

<rule priority="blocking">
Always create a timestamped backup before modifying an existing `CLAUDE.md`. No exceptions.
</rule>

<rule priority="blocking">
Generated `CLAUDE.md` must be within the token target range for the project's size.
</rule>

<rule priority="recommended">
Detect framework accurately — use multiple signals (files, dependencies, structure).
</rule>

<rule priority="recommended">
Make the active mode (enhance vs standalone) clear in every user-facing message.
</rule>
</critical_rules>
