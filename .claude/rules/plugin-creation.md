---
description: Plugin & skill authoring conventions for this marketplace
paths:
  - "**/commands/*.md"
  - "**/agents/*.md"
  - "**/skills/**/SKILL.md"
  - "**/.claude-plugin/plugin.json"
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
| No hooks | Poor UX, no next steps | Add Stop hooks |
| Missing shell context | Less useful output | Use `!` backticks |
| `context: fork` on interactive skill | Subagent can't ask user questions | Only fork complete tasks |
| No `disable-model-invocation` on destructive | Claude might auto-trigger | Add to deploy, commit, delete actions |

</anti_patterns>

## Evaluating an External Plugin Before Replicating It

<external_plugin_evaluation>

**Read its scripts. Never run them.** Auto mode blocks executing code fetched from
a third-party repo (`[Code from External]`) and it is right to — you are evaluating
an approach, not adopting a binary. Reproduce what the script does with your own
commands instead; that is the same work, minus the trust.

**Verify its assumptions against local ground truth before inheriting them.** The
prose in an external plugin describes what the author believed, not what is true
now. Check each load-bearing assumption against real data on this machine before
any of it reaches your version — a plugin that reads Claude Code session logs, for
example, encodes a path, classifies entry types, and counts turns, and every one of
those is checkable in seconds against `~/.claude/projects/`.

**The value is the domain knowledge, not the file.** What is worth taking is the
schema facts, the flags, the edge cases the author hit. What is not worth taking is
the templates, the depth tiers, and the README — those are the parts that will drift
and that you would then own. Prefer a small script plus a lean skill over a port.

**Installing it is not the same as forking it.** A published marketplace plugin can
be installed and trialled directly. Copy it into this repo only when you intend to
diverge from it, and say in the CHANGELOG what you changed and why.

</external_plugin_evaluation>

## Local Testing

<local_testing>

Load plugins straight from the working tree with `--plugin-dir`, instead of
installing from the marketplace. Requires Claude Code 2.1.265+.

**Never point `--plugin-dir` at the repo root.** A folder fans out into one
plugin per child *only when the folder itself has no `.claude-plugin/`*. This
repo's root has `.claude-plugin/marketplace.json`, so `--plugin-dir .` loads the
whole repo as a **single** plugin with 0 commands, 0 skills, 0 agents — and
still reports `Status: loaded`. The no-op is silent.

Load the plugins under test by relative path:

```bash
claude --plugin-dir code-review --plugin-dir discuss
```

Or every plugin in the repo (zsh and bash):

```bash
flags=(); for d in */.claude-plugin/plugin.json; do flags+=(--plugin-dir "${d%%/*}"); done
claude "${flags[@]}"
```

Confirm what actually loaded before trusting a test run — session-only plugins
appear under `Session-only plugins` as `<name>@inline`:

```bash
claude "${flags[@]}" plugin list
claude --plugin-dir code-review plugin details code-review   # inventory + token cost
```

The installed copy of the same plugin stays enabled alongside the inline one, so
a name can be live two or three times over (user scope, project scope, inline).
When a command's behaviour is ambiguous, `plugin disable <name>@<marketplace>`
the installed copy for the duration of the test.

</local_testing>

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
