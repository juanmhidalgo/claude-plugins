# Friction → destination

A retrospective finding is worthless until it names a file. This is the routing table.

| Friction observed | Destination | Shape of the change |
|---|---|---|
| Same correction given 2+ times, applies to every project | `~/.claude/CLAUDE.md` | One imperative line under the right heading. Not a paragraph. |
| Same correction, but only true for this repo | the repo's `CLAUDE.md` | A rule inside the existing `<critical_rules>` structure, with `priority`. |
| A fact about the project that was re-derived from scratch | memory file in `~/.claude/projects/<encoded-cwd>/memory/` | One file, one fact, plus the `MEMORY.md` pointer line. |
| `permission-rule` denials on commands that are plainly safe | `.claude/settings.json` → `permissions.allow` | The narrowest matching rule, e.g. `Bash(git diff *)`, never a blanket `Bash(*)`. The native `/fewer-permission-prompts` skill can mine the transcripts for candidates. |
| `user-rejected` denials | usually not a settings change | The model proposed the wrong thing — this is a CLAUDE.md rule or a skill fix, not a permission to grant. Never "fix" a rejection by widening permissions. |
| `automode-blocked` denials | nothing, usually | The classifier blocked a genuinely unusual action. Only worth acting on if it blocked something routine and repeated. |
| A check the user performed manually every time | a hook in `.claude/settings.json` | `PostToolUse` to warn, `PreToolUse` to block. Hooks in this setup are text matching, not sandboxes — say so when proposing one. |
| A plugin command/skill in this repo misfired, halted, or was ignored | that plugin's `commands/` or `skills/` file | Then follow the repo's version rule, below. |
| A slow turn caused by exploring the wrong area first | the skill that drove the exploration | Usually a missing "scope to X, do not explore Y" boundary in its description. |
| Something worked well and is not written down | wherever the analogous rule lives | Same routing as a correction — confirmed approaches are worth recording, not just failures. |

## When the destination is a plugin in this repo

The repo's blocking rule applies — all four steps, in order:

1. Bump the version in that plugin's `.claude-plugin/plugin.json`
2. Semver: patch for fixes, minor for features, major for breaking changes
3. Add the entry to that plugin's `CHANGELOG.md`
4. Mirror the version in `.claude-plugin/marketplace.json`, editing the version line in
   place — re-serializing the JSON reflows every inline `keywords` array and turns a
   3-line change into a 120-line diff

Two `PostToolUse` hooks warn when a bump or a CHANGELOG entry is missing.

## Rules for the changes themselves

- **One destination per finding.** If it could go in three places, it is too vague to act on.
- **Quote the exact text** to add or change. "Improve the description" is not a change.
- **No new plugin per finding.** The bar is a repeated task, done 5+ times, expected 10+ more.
- **Don't propose documentation as the fix for a model behavior** that a boundary in a skill
  description would fix better.
