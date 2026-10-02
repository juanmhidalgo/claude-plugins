---
description: Plugin & skill authoring conventions for this marketplace
paths:
  - "**/commands/*.md"
  - "**/agents/*.md"
  - "**/skills/**/SKILL.md"
  - "**/.claude-plugin/plugin.json"
  - "**/hooks/hooks.json"
  - ".claude-plugin/marketplace.json"
---

# Plugin & Skill Creation Guidelines

Lessons learned from Anthropic's official documentation and practical experience.

<sources>
- https://code.claude.com/docs/en/skills (official documentation)
- https://claude.com/blog/building-agents-with-skills-equipping-agents-for-specialized-work
- https://claude.com/blog/building-skills-for-claude-code
</sources>

## Skills and Commands

**Commands have been merged into Skills.** A file at `.claude/commands/review.md` and a skill at `.claude/skills/review/SKILL.md` both create `/review` and work the same way.

**Going forward, prefer skills over commands** because they:
- Support `references/` directory for progressive disclosure
- Can use `context: fork` for isolated execution
- Can specify `agent:` for subagent type

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

Keep skills lean (~100-150 lines). Use three tiers:

1. **Metadata** (~50 tokens): Name + description - always loaded
2. **SKILL.md** (~500 tokens): Core instructions - loaded when needed
3. **Reference files** (2000+ tokens): `references/` directory - loaded on-demand

```
skill-name/
├── SKILL.md           # Lean core instructions (~100 lines)
└── references/
    ├── examples.md    # Detailed examples
    ├── templates.md   # Full templates
    └── patterns.md    # Extended patterns
```

Reference files in SKILL.md:
```markdown
For detailed examples, see [examples.md](references/examples.md).
```

</progressive_disclosure>

## Subagent Execution

<subagent_patterns>

### When to Use `context: fork`

Use `context: fork` when the skill:
- Performs a complete task that should run in isolation
- Doesn't need to interact with the user during execution
- Should not pollute the main conversation context
- Is doing parallel/background work

```yaml
---
name: memory-summarizer
description: Summarize conversation and save to memory file
context: fork
agent: general-purpose
---

Summarize the current conversation and save key insights to .claude/memory.md
```

**Do NOT use `context: fork` when:**
- The skill needs to use AskUserQuestion interactively
- The skill is multi-phase with user decisions between phases
- You need the results immediately in the main context

### Agent Types

When using `context: fork`, specify the agent type:

| Agent | Use For |
|-------|---------|
| `Explore` | Codebase research, finding files, understanding patterns |
| `Plan` | Designing implementation approaches |
| `general-purpose` | Full capabilities, default if not specified |

```yaml
---
name: deep-research
description: Research a topic thoroughly
context: fork
agent: Explore
---

Research $ARGUMENTS thoroughly:
1. Find relevant files using Glob and Grep
2. Read and analyze the code
3. Summarize findings with specific file references
```

</subagent_patterns>

## Invocation Control

<invocation_control>

### Who Can Invoke a Skill

Two frontmatter fields control invocation:

| Field | Effect |
|-------|--------|
| `disable-model-invocation: true` | Only user can invoke (via `/skill-name`) |
| `user-invocable: false` | Only Claude can invoke (background knowledge) |

**Use `disable-model-invocation: true` for:**
- Side effects (deploy, commit, send notifications)
- Destructive actions (dismiss comments, resolve threads)
- Actions you want explicit user control over

```yaml
---
name: deploy
description: Deploy the application to production
disable-model-invocation: true
---
```

**Use `user-invocable: false` for:**
- Background knowledge skills
- Reference material Claude should know but users shouldn't invoke directly

```yaml
---
name: legacy-system-context
description: Context about the legacy system architecture
user-invocable: false
---
```

### Invocation Matrix

| Frontmatter | User can invoke | Claude can invoke |
|-------------|-----------------|-------------------|
| (default) | Yes | Yes |
| `disable-model-invocation: true` | Yes | No |
| `user-invocable: false` | No | Yes |

</invocation_control>

## Required Frontmatter

<frontmatter_reference>

### Complete Frontmatter Reference

```yaml
---
name: skill-name                    # Display name, becomes /skill-name
description: |                      # CRITICAL: when to use, what it does
  Use when [context]. Provides [output].
  Do NOT use for [boundaries].
argument-hint: "[file-path]"        # Shown in autocomplete
allowed-tools:                      # Tools allowed without asking
  - Read
  - Glob
  - Bash(git diff *)
keywords:                           # For search/taxonomy
  - kebab-case-terms
triggers:                           # Natural language activation
  - "review this PR"
  - "check my code"

# Invocation control
disable-model-invocation: true      # Only user can invoke
user-invocable: false               # Only Claude can invoke (pick one)

# Subagent execution
context: fork                       # Run in isolated subagent
agent: Explore                      # Which subagent type

# Model selection
model: haiku                        # haiku, sonnet, opus
effort: low                         # reasoning effort: low, medium, high

# Hooks
hooks:
  - event: Stop
    once: true
    command: |
      echo "Next: /another-command"
---
```

`model:` and `effort:` were parsed but **not applied** in interactive sessions
until 2.1.259 / 2.1.267. A command or agent pinned to `model: opus` on an older
build silently ran on the session's model — re-check any behaviour you tuned
around that. `effort:` is reasoning effort, unrelated to any review-depth level
a prompt defines for itself.

### Available Substitutions

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All arguments passed to the skill |
| `${CLAUDE_SESSION_ID}` | Current session ID |
| `!`command`` | Shell output (preprocessed before Claude sees it) |

</frontmatter_reference>

## Patterns to Use

<patterns>

### Shell Embedding for Context

```markdown
## Context
- **Current branch**: !`git branch --show-current`
- **Recent commits**: !`git log --oneline -5`
- **Staged files**: !`git diff --cached --name-only`
```

### Skill Import via @ Reference

```markdown
<best_practices>
@plugin-name/skills/skill-name/SKILL.md
</best_practices>
```

### Hooks for Next Step Guidance

A `Stop` hook fires when a turn ends, and `once: true` makes that the *first* turn. Use one only for a command that finishes in a single turn. A command that asks the user anything (AskUserQuestion, a confirmation, a round-trip) ends its first turn before its work is done, so the hook prints "done" too early and never fires again. For those, make the command's last step print the next command itself, with the artifact path it already knows. feature-dev removed its Stop hooks in 1.27.0 for this reason.

```yaml
hooks:
  - event: Stop
    once: true
    command: |
      echo "Done. Next steps:"
      echo "  - /command:next-step"
      echo "  - Create a PR with the changes"
```

### Delegating to Subagents

For complex exploration, use Agent tool in skill content:

```markdown
## Phase 1: Explore

Use the Agent tool with `subagent_type: "Explore"` to understand:
1. What existing code relates to this feature?
2. What patterns does the project use?
```

</patterns>

## Common Mistakes to Avoid

<anti_patterns>

| Mistake | Why It's Bad | Fix |
|---------|--------------|-----|
| Generic skill description | Won't trigger correctly | Be specific about when/what |
| Skill has generic knowledge | Wastes context tokens | Only include institutional knowledge |
| Long skill (200+ lines) | Context bloat | Use progressive disclosure |
| No next-step guidance | Poor UX, no next steps | Stop hook for single-turn commands; a final step that prints the next command for interactive ones |
| Missing shell context | Less useful output | Use `!` backticks |
| `context: fork` on interactive skill | Subagent can't ask user questions | Only fork complete tasks |
| No `disable-model-invocation` on destructive | Claude might auto-trigger | Add to deploy, commit, delete actions |

</anti_patterns>

## Evaluating an External Plugin Before Replicating It

Before copying or porting a third-party plugin, read `.claude/docs/evaluating-external-plugins.md`.

## Local Testing

To load plugins from the working tree with `--plugin-dir`, read `.claude/docs/plugin-local-testing.md` first (pointing it at the repo root is a silent no-op).

## Mods

<mods>

A mod is a hooks module: `hooks/hooks.json` lists it under `"modules"` (e.g. `"modules": ["./register.js"]`). Docs: https://code.claude.com/docs/en/plugins/mods/overview

- **In-process and unsandboxed.** The module runs inside Claude Code with the user's permissions: files, processes, network, secrets, every prompt and tool call. Write it as if it were installed on a stranger's machine, because this repo is public.
- **`$.store` is shared by every session on the machine, across all projects.** Store metadata only (counts, timestamps, ids, flags). Never prompt text, file contents, or full paths.
- **Before publishing:** `claude plugin validate --strict <plugin>` (warnings fail) and `claude plugin test <plugin>` (runs `*.test.ts`).
- **Requires Claude Code ≥ 2.1.287.** Hooks run everywhere, but panes and bands don't draw in the VS Code extension or `claude -p`. Anything a mod shows needs a text fallback (a transcript line or a command's text reply).

</mods>

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
- [ ] Invocation control set correctly:
  - [ ] `disable-model-invocation: true` for side effects
  - [ ] `user-invocable: false` for background knowledge
- [ ] `context: fork` only for complete, non-interactive tasks

### Command Review (Legacy)

- [ ] `allowed-tools` includes all needed tools
- [ ] `hooks` provide next step guidance
- [ ] Shell embedding for relevant context
- [ ] `keywords` and `triggers` for discoverability

### Final Steps

- [ ] Exercised from the working tree via `--plugin-dir <plugin>` (see Local Testing)
- [ ] Version bumped in `plugin.json`
- [ ] CHANGELOG.md updated
- [ ] README.md documents commands

</checklist>
