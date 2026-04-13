# github-issues

Fix GitHub Issues directly from Claude Code. Fetches issue details, explores the local codebase, plans the fix, and implements it — with multi-repo handoff support.

## Skills

| Skill | Purpose |
|-------|---------|
| `/github-issues:fix <url>` | Fetch a GitHub Issue, explore the codebase, and fix the bug |

## Usage

```bash
/github-issues:fix https://github.com/org/repo/issues/123
```

## Workflow

1. **Fetch** — Parses the issue URL, retrieves title, body, labels, and comments via `gh`
2. **Branch** — Creates `fix/issue-<number>-<slug>` from the current branch
3. **Explore** — Searches the codebase for files related to the bug
4. **Plan** — Enters plan mode with proposed fix for your approval
5. **Implement** — After approval, implements the fix with regression tests
6. **Multi-repo** — If the fix requires changes in other repos, generates a handoff prompt

## Requirements

- `gh` CLI installed and authenticated
- GitHub token with repo scope
