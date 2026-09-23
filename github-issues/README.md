# github-issues

Work GitHub Issues from Claude Code — bugs, tech debt, refactors, and follow-ups left by a
review. Both skills check the issue against the current code first: issues (especially
AI-written ones) describe the code at the time they were written, and their line numbers,
flags, and suggested fixes go stale.

## Skills

| Skill | Purpose |
|-------|---------|
| `/github-issues:verify <#N>... \| --label <label>` | Check issues against HEAD without implementing — triage a backlog, or find out whether an issue is still true |
| `/github-issues:work <#N> [--part N]` | Verify one issue, plan the work, and implement it |
| `/github-issues:fix` | Deprecated alias of `work`, removed in 2.0 |

## Usage

```bash
# Triage the open tech-debt backlog (one read-only agent per issue, in parallel)
/github-issues:verify --label tech-debt --limit 10

# Check specific issues
/github-issues:verify #123 #124

# Work one issue; only items 1 and 3 of an issue that bundles several
/github-issues:work https://github.com/org/repo/issues/123
/github-issues:work #123 --part 1,3
```

Issue numbers without a URL resolve against the current repo.

## The verification ledger

Every claim the work depends on — locations, behavior, "nothing calls X", measurements,
flags, comments, the suggested fix, and how consumers in sibling repos read the thing — is
recorded with a status (CONFIRMED / DRIFTED / REFUTED / ALREADY FIXED / UNVERIFIED) and how
it was checked (`ran` / `read` / `not checked`). The verdict decides what happens next:
actionable issues go to planning; issues that are already fixed, rest on a wrong premise, or
need a decision stop there, with an offer to post the corrections to the issue.

`verify` agents are read-only and can't run anything, so their rows are `read` at most; the
probes they propose can be run afterwards from the main session. `work` starts from a
`verify` ledger produced earlier in the same conversation.

## `work` workflow

1. **Fetch** — issue, comments, and any PR that already references it
2. **Classify** — bug, performance, tech debt, refactor, test defect, follow-up, needs-decision, or epic, from the body as well as the labels
3. **Verify** — build the ledger; stop unless the verdict is actionable
4. **Plan** — plan mode, with the ledger, deviations from the issue's suggested fix, and an explicit out-of-scope list
5. **Branch and implement** — `fix/`, `perf/`, `chore/`, `refactor/`, or `test/` by type; tests by type (a failing-first test for bugs, green-before-and-after for refactors)
6. **Review** — a fresh-context reviewer checks the diff against the approved plan; findings are verified before any fix
7. **Close out** — multi-repo handoff if needed; `Closes` vs `Refs`

Epics, spikes, and new features are out of scope — use `/feature-dev:spec`.

## Requirements

- `gh` CLI installed and authenticated
- GitHub token with repo scope
- For `verify`, a local checkout of the repo the issues belong to; sibling repos checked out next to it are used as consumer evidence
