# PR mode: Dependabot and Renovate pull requests

A bot PR asks "can this be merged", which is the upgrade-risk question plus three
the bot does not answer: **did it bump everything that has to move together**, **does the
branch actually install**, and **does it close what it claims to close**. The bot's PR body
is a claim to check — it is generated from release notes and says nothing about this repo.

Read-only, as everywhere in this skill: no checkout, no comment, no review, no
`@dependabot` command, no merge. The report names the command; the user posts it.

## 1. Read the PR

Run from the repo, or add `--repo <owner>/<repo>` to every `gh pr` / `gh run` command.

```bash
gh pr view <N> --json title,author,headRefName,headRefOid,baseRefName,baseRefOid,labels,body,files,mergeable,state
gh pr diff <N>                      # the manifest and lock diff — the real list of changes
gh pr checks <N>                    # CI state per job
gh pr view <N> --json comments,reviews   # bot reviewers, coverage comments, prior @dependabot commands
```

Take the package list **from the diff**, not the title or the body:

- Manifest diff (`package.json`, `pyproject.toml`) ⇒ the **direct** bumps, with the old and new
  constraint.
- Lock diff only ⇒ a **transitive** bump. Read every entry the lock diff moves: a "bump X
  1.2.3 → 1.2.4" PR routinely moves other packages too, and those are part of the change.
- A file at the PR head, when you need it whole:
  `gh api --method GET repos/<owner>/<repo>/contents/<path> -f ref=<headRefOid> -H 'Accept: application/vnd.github.raw'`

**The local working tree is probably not the PR's base.** Compare `git rev-parse HEAD` with
`baseRefOid`. When they differ (another branch checked out, base moved, uncommitted work),
first check whether the local lock equals the **current** base branch's lock
(`git diff --stat origin/<baseRefName> -- <lock> <manifest>` empty, and `git status` clean on
them). If it does, tree commands describe the **merge result**, which is better evidence for
staleness than the PR's old base — use them and say so. Otherwise every tree-reading step
describes the wrong code: run Phase 1 with `git grep <pattern> "<baseRefOid>"`
and `git show "<baseRefOid>:<path>"` instead of Grep/Read, and mark `npm ls`, `npm audit`,
`npm install --dry-run` (and their Python equivalents) as **not representative** of the PR —
they read the tree. If the base commit is not present locally, say so; fetching is the user's
call. Quote refs in `git show "<ref>:<path>"`: zsh parses an unquoted `$ref:t…` as a modifier.

**Look for a PR that supersedes this one** before judging it in isolation — a human often
opens the real fix when a bot PR cannot work:

```bash
gh pr list --state open --search "<N> in:body"
gh pr list --state open --search "<package or family name>"
```

A superseding PR changes the action (close as superseded) but is not assessed by this run;
cite its claims as claims and recommend running this skill on it.

## 2. Classify

| Question | How to tell | Why it matters |
|----------|-------------|----------------|
| Version update or security update? | Security PRs are opened even when the repo's config only allows direct deps or ignores majors; check `gh api repos/<owner>/<repo>/dependabot/alerts` for an open alert on that package | A security update is judged against the alert it closes, not against "do we want this version" |
| Direct or transitive? | Manifest diff present or not | Transitive with no first-party usage ⇒ Phase 1 is short and says so; Phases 3 and 4 carry the report |
| Grouped? | Title "bump the `<group>` group", or several packages in one manifest diff | Run §3 |
| Semver jump | from → to of each package | Patch-only on a transitive dep is the smallest report the skill produces; it is still not "auto-merge" until §4 and §5 pass |

Then read the repo's `.github/dependabot.yml` (or `renovate.json`): groups, `ignore` rules,
`allow` filters, and above all the **comments** — a team that got burned writes the rule down
there ("these packages must move in lockstep", "check X before merging"). A rule stated in that
file is a check this report runs.

## 3. Group completeness — the bot does not guarantee it

A group pattern bundles the members that *have* a new release. A family whose packages
peer-depend on each other at **exact** versions only installs when every member moves, and
families often publish asymmetrically — one member skips a release. The grouped PR then bumps
seven of eight and leaves the eighth pinning the old exact peer.

For each package family touched (same scope prefix, or listed together in a group):

1. List every member in the manifest, not just the ones in the diff.
2. For each member left behind: does the target version exist?
   `npm view <member> versions --json` / `pip index versions <member>`. If not, that is the
   finding: the family **cannot** reach the target yet. Then check whether it ever will:
   `npm view <member> deprecated`, the PyPI classifiers / yanked state, and the family's
   release notes for "stop publishing" / "deprecated". A deprecated member never catches up —
   the fix is a code change that removes it and its usages, not waiting.
3. Read the peers of the bumped members: `npm view <pkg>@<target> peerDependencies`. An exact
   peer (`"2.1.0"`, not `^`) on a member that stayed behind is a guaranteed install failure
   under npm's strict peers, or a silently nested second copy under a manager that tolerates it
   (two copies of an SDK split its types and its singletons).
4. A repo script that checks parity (`check:*`, `scripts/*parity*`) is the team's own oracle —
   cite it, and read whether CI ran it.

## 4. Does the branch install? — CI as resolver output

You cannot run the resolver on the PR branch without checking it out, which this skill does not
do. The PR's CI already ran it: the install step (`npm ci`, `uv sync --locked`, …) is the dry
run, performed on the exact lock in the PR.

```bash
gh pr checks <N>                         # find the failing job and its run id in the link
gh run view <run-id> --log-failed        # read the install step first, then the rest
```

- Install step failed ⇒ quote the resolver's error verbatim (`ERESOLVE`, peer conflict,
  `EBADENGINE`, no matching distribution). That is Phase 3's answer, and it outranks any
  changelog reading.
- Install passed, tests failed ⇒ the bump is resolvable but breaks behaviour; Phase 2 should
  find the cause, and a failing test is an APPLIES with its own `file:line`.
- All green ⇒ evidence for resolvability and for the covered paths only; it says nothing about
  paths CI does not exercise, and nothing about a runtime floor CI happens to satisfy.
- Checks never ran, or skipped ⇒ Phase 3 is UNVERIFIED for the PR head; say so.
- A failed install means every later CI step (build, typecheck, parity scripts, tests) never
  ran. Items you would have left to "CI will catch it" stay **UNKNOWN** — they are not covered
  by CI, and a superseding PR's CI is where they close.

**Staleness.** The PR is *stale* when the base branch's lock or manifest changed after
`baseRefOid`:

```bash
git log --oneline <baseRefOid>..origin/<baseRefName> -- <lock> <manifest>
```

Empty ⇒ not stale; the PR's CI result stands for the merge. Non-empty ⇒ the PR's CI resolved
against an old lock, so its green install does not prove the merge resolves. Close that gap
with a dry run on the current base lock (allowed when the local tree matches it, above) — clean
⇒ merge is fine without a rebase; not runnable ⇒ recommend `@dependabot rebase` and treat
Phase 3 as UNVERIFIED for the merge result until CI re-runs. `mergeable: MERGEABLE` only means
no textual conflict.

## 5. Runtime floor changes hidden in a minor

Bot PRs label by semver of the package, but a **minor** release that raises
`engines.node` or `requires_python` is a breaking change for the repo running the old runtime.
Read the target's floor (`npm view <pkg>@<target> engines`, PyPI `requires_python`) and compare
it against every place the repo declares its runtime ([node-version.md](node-version.md) §1,
[python-version.md](python-version.md) §1). A floor that CI satisfies but the deploy target,
the Dockerfile or the local `.nvmrc` does not is an APPLIES on that file. No declared runtime
anywhere except CI is itself a finding: the floor is unenforced.

## 6. Security PRs — does it close the alert?

```bash
gh api --method GET repos/<owner>/<repo>/dependabot/alerts -f state=open \
  --jq '.[] | {number, package: .dependency.package.name, scope: .dependency.scope,
              relationship: .dependency.relationship, ghsa: .security_advisory.ghsa_id,
              severity: .security_advisory.severity,
              range: .security_vulnerability.vulnerable_version_range,
              patched: .security_vulnerability.first_patched_version.identifier}'
```

Report only alerts on packages the PR moves; other open alerts are out of scope, one line at
most. For each open alert on a package the PR moves: is the new locked version ≥ the first patched
version, **for every copy** of the package in the lock? A transitive package locked at two
paths is often bumped at one. List the alerts the PR closes and the ones it leaves open. No
access to the alerts API (403) ⇒ UNKNOWN, with the command, not "fixes the CVE because the
title says so".

## 7. Bot reviewers

A Copilot or other AI review on the PR is a set of unverified claims, like the PR body. First
compare the review's commit (`gh pr view <N> --json reviews --jq '.reviews[] | {author: .author.login, commit: .commit.oid}'`)
with `headRefOid`: Dependabot rebases and recreates, so a review often describes an older
target version. Then check each claim against the current diff and the registry; a confirmed one is
cited as confirmed by you, with your evidence.

## 8. Then run the normal phases

Each bumped package goes through Phases 1–5 in its own mode (PACKAGE for each dependency;
NODE or PYTHON if the PR bumps the runtime image or `setup-node`). Scale to the change: a
transitive patch with no first-party usage gets one Phase 1 line and a full Phase 3/4, not a
padded table. A grouped bump gets one Phase 2 table with a column per package or one table per
package — never "release notes summarised by Dependabot".

## PR verdict

Translate the capped verdict into what to do with the PR:

| Situation | PR action |
|-----------|-----------|
| GO, CI green, alert(s) closed where relevant | **Merge** |
| GO WITH CAVEATS | **Merge after** the numbered caveats; each names a file |
| Branch fails only because it is stale | **`@dependabot rebase`**, then re-run this |
| Group incomplete but the missing member's target exists | **Fix the branch**: one commit bumping the member left behind — note Dependabot stops rebasing a branch someone else pushed to |
| Group incomplete and the missing member's target does not exist | **Close and wait** (or `@dependabot ignore` that version), naming the release to watch for |
| Group incomplete because the missing member is deprecated / no longer published | **Close**; the fix is a separate PR that removes the member and its usages, then bumps the rest |
| Another open PR already does the bump properly | **Close as superseded**, citing it; assess that PR with its own run |
| A dependency with no target-compatible release, or an APPLIES with no migration path | **Close**, and say what would reopen it |
| Security PR that leaves an alert open | Merge if it closes part of it, and list what stays open — a partial fix is not "resolves the alert" |

The Dependabot commands (`rebase`, `recreate`, `ignore this major/minor version`,
`ignore this dependency`) go into the report as text for the user to post.

## Rationalization defenses

| Rationalization | Why it's wrong |
|-----------------|----------------|
| "CI is green and it's a patch, merge it" | Green CI proves the covered paths install and pass; it says nothing about a runtime floor CI satisfies and prod does not, or a second copy of the package still locked at the vulnerable version. |
| "It's grouped, so the whole family moved" | A group bundles what has a release; a member with no release at the target is silently left behind, and exact peers make that an install failure. |
| "The PR body lists the breaking changes" | It lists the package's changes, not this repo's exposure — the cross-reference is the report. |
| "The bot reviewer flagged X, so X is a problem" | Unverified until checked against the diff; bot reviews are claims like the PR body. |
| "The repo is checked out, so I'll grep it" | Check that HEAD is the PR's base first; a different branch makes Phase 1 scan code the PR never touches. |
| "Close and wait for the missing member's release" | Check it is not deprecated first — a wait on an abandoned package never ends. |
| "I'll just check out the branch and run `npm ci`" | That mutates the working tree and `node_modules`; the PR's CI install already ran on that exact lock. |
