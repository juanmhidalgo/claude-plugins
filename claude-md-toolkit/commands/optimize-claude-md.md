---
description: |
  Use when you want to apply best-practice improvements to an existing CLAUDE.md file.
  Do NOT use to create one from scratch — use /claude-md-toolkit:init instead.
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
hooks:
  - event: Stop
    once: true
    command: |
      echo "Optimization complete."
      echo "  - /claude-md-toolkit:analyze-claude-md to verify score"
      echo "  - Test with Claude Code before committing"
---

# Optimize CLAUDE.md

Apply Anthropic's best practices to optimize CLAUDE.md structure, conciseness, and token efficiency.

<context>
**Skill activated**: `claude-md-best-practices`
**Working directory**: !`pwd`
**Arguments**: `$ARGUMENTS`
</context>

## Parse arguments

**Path**: `$1`, or auto-detect (`./CLAUDE.md` → `./.claude/CLAUDE.md`).

**Level**: extract `--level=X` from `$ARGUMENTS`. Default: `moderate`. Valid values: `conservative`, `moderate`, `aggressive`.

For each level's full scope (what is/isn't changed), see `@optimize-claude-md.references/levels-and-strategies.md`.

## Workflow

1. **Backup** — `cp [original] [original].backup-[timestamp]`. Show the backup path. Blocking.
2. **Transform** — apply optimizations at the chosen level. Track before/after metrics (lines, tokens).
3. **Preview** — show metrics comparison, key changes list, 2–3 side-by-side examples, backup location.
4. **Confirm** — ask the user: apply / cancel / save-as-new. Do NOT proceed without explicit confirmation. Blocking.
5. **Apply** — write optimized content (or to `[original].optimized.md` if save-as-new), or delete backup if cancelled.
6. **Post-optimization message** — print metrics, next steps, backup-restore command.

For optimization-strategy details (XML structure target, conciseness moves, content enhancements, full success message, error handling), see `@optimize-claude-md.references/levels-and-strategies.md`.

## Safety checks

**Content preservation (blocking)**: before writing, ensure (1) all original info preserved, (2) no loss of project context, (3) no removal of critical rules, (4) XML tags properly closed, (5) token count is LOWER than original.

**Sensitive data (blocking)**: if credentials, API keys, or connection strings are found — FLAG IMMEDIATELY, do NOT include in the optimized version, inform the user.

**Already optimized**: if analysis score > 85, inform the user and ask if they want to proceed anyway.

<critical_rules>
<rule priority="blocking">
NEVER write to the original file without creating a backup first. No exceptions.
</rule>

<rule priority="blocking">
NEVER proceed with optimization without user confirmation after the preview.
</rule>

<rule priority="blocking">
If sensitive data is found, FLAG it and do NOT include it in the optimized version.
</rule>

<rule priority="recommended">
Show side-by-side before/after for 2–3 key sections in the preview.
</rule>

<rule priority="recommended">
Token savings must be realistic — if optimized has MORE tokens than original, something is wrong.
</rule>
</critical_rules>
