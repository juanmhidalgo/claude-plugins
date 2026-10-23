# Changelog

## [0.2.0] - 2026-10-23

### Added
- **Node/JS ecosystem** (`references/node.md`): npm, pnpm and yarn (classic and berry) detection,
  every locked copy of a package rather than one version, `npm view` metadata (`engines`,
  exact vs range `peerDependencies`, ESM-only and `exports` changes, deprecation), the config
  files and `overrides`/patches a plain import grep misses, `npm install --dry-run` resolution,
  and the audit commands. Write-capable look-alikes (`npm audit fix`, `--package-lock-only`,
  `pnpm audit --fix`) are named as forbidden and kept out of `allowed-tools`.
- **NODE mode** (`node N`, `references/node-version.md`): runtime declaration sites that drift
  apart (`engines`, `.nvmrc`, `setup-node`, `FROM node`, hosting config, `@types/node`),
  dependency engine floors, native addons and per-ABI prebuilds vs Node-API, deprecations and
  OpenSSL/global changes to grep for, and LTS/odd-major deployment status.
- **PR mode** (`<PR number or URL>`, `references/dependabot-pr.md`) for Dependabot and Renovate
  PRs: packages read from the diff instead of the PR body; version vs security update and
  direct vs transitive classification; the repo's `dependabot.yml` rules run as checks; lockstep
  family completeness (a grouped PR can leave a member behind when it has no release at the
  target, and exact peers then fail the install); the PR's CI install step read as resolver
  output; runtime floors raised in a minor compared against every runtime declaration;
  security PRs checked against open alerts for every locked copy; bot-reviewer claims verified.
  The capped verdict is translated into a PR action (merge, rebase, fix the branch, close and
  wait).
- PR mode checks found by a test run on a real grouped bump: the local tree is compared with
  the PR's base commit (Phase 1 reads the base via `git grep`/`git show` when they differ, and
  tree-reading commands are marked not representative); open PRs that supersede the bot PR are
  searched; a member left behind is checked for upstream deprecation (a deprecated member
  never catches up, so "close and wait" becomes "close; remove the member"); a bot review is
  matched to the head commit before its claims are used; a failed CI install leaves every
  "CI would catch it" item UNKNOWN; alerts carry their vulnerable range.
- Verdict caps for PR mode: incomplete lockstep family, failing CI install, and an unmet raised
  runtime floor are each NO-GO.

### Changed
- `upgrade-risk` is no longer Python-only; Phases 0–5 are ecosystem-neutral and defer to the
  matching resolver reference.
- `allowed-tools` gains read-only Node commands and read-only `gh` (`pr view/diff/checks`,
  `run view`, `api` on contents and Dependabot alerts); the no-mutation rule now covers the PR
  and forbids `gh api` with a method or fields.
- README **Needs** now lists `gh` for PR mode.
- `allowed-tools` also admits read-only helpers a real run needed (`ls`, `stat`, `head`,
  `tail`, `grep`, `rg`, `jq`, `sed -n`, `wc`, `diff`, `cd`), `git -C` / `npm --prefix` forms for
  a repo outside the cwd, version probes, `npm config get` / `npm pkg get`, and
  `gh run list` / `gh release view|list`. Look-alikes that can write (`find`, plain `sed`,
  `sort`, `tee`, `node -e`, `python -c`) stay out, listed in a comment.
- A second test run, on a transitive security bump, tightened PR mode: staleness is defined
  (base lock changed since `baseRefOid`) with the command that measures it, and a stale-but-green
  PR needs a clean dry run on the current base lock or a rebase; a local tree whose lock equals
  the current base branch's lock is used as merge-result evidence instead of being discarded;
  alerts are reported only for the packages the PR moves.
- Transitive dependencies: Phase 1 reads how the direct parent calls the package in its
  installed code, so DOES NOT APPLY rests on the real call sites, not on "no first-party usage".
- Node changelog fallback to per-commit diffs when a project publishes no releases, and a
  `gh api /advisories?affects=` query for advisories in the target version.
- `allowed-tools` closed patterns that admitted writes: `gh api` now requires a leading
  `--method GET` (parameters as `-f`, sent as a query string); audit forms are exact (no
  trailing `*` that admitted `audit fix` / `--fix`); `sed`, `rg` (`--pre` executes) and
  `coverage json` (writes `coverage.json`, present since 0.1.0) were removed. Added
  `git merge-base`.
- GO rule unified between SKILL.md and the report template: coverage gates GO only for APPLIES
  paths. Phase 5 skips the "run the tests?" question when nothing APPLIES.
- Phase 5: a coverage artifact that lacks the affected files counts as no artifact for them.
- The Stop hook no longer asks to close UNKNOWNs that cannot change a verdict.

### Why
Two bot PRs showed what the Python-only skill could not judge: a grouped SDK bump whose family
had one member with no release at the target — the exact peer made `npm ci` fail with
`ERESOLVE`, and the minor also raised the Node floor — and a transitive lock-only security
bump where the question is whether it closes the open alerts, not what the changelog says.

## [0.1.1] - 2026-10-02

### Changed
- README gains a **Needs** section listing prerequisites (`gh`, MCP servers, browser, external CLIs), replacing the old Requirements list.

## [0.1.0] - 2026-09-22

### Added
- **`/deps:upgrade-risk` skill.** Assesses whether upgrading a Python dependency — or the
  Python runtime itself — is safe in *this* repository, and returns a capped
  go / no-go / go-with-caveats verdict. Two modes: PACKAGE (`<pkg>[==target]`) and PYTHON
  (`python X.Y`), branching at Phase 0.
- **Evidence rule with three verdicts per breaking change.** Every changelog entry is marked
  APPLIES (requires a `file:line` from the usage scan), DOES NOT APPLY (requires a stated
  reason), or UNKNOWN (names what would close it). An empty grep on a dynamic-import codebase
  is UNKNOWN, not DOES NOT APPLY.
- **No-mutation guard.** The skill installs nothing and writes no file in the repo; every
  resolver command is a dry run, and `allowed-tools` admits only dry-run and read forms
  (no bare `pip install`, `uv lock`, or `poetry update`).
- **Resolver-verified transitive impact** (`references/resolvers.md`): manager detection from
  lock files cross-checked against CI, current version read from the lock rather than the
  `pyproject.toml` constraint, per-manager dry-run and reverse-tree commands, PyPI JSON for
  release metadata and wheel tags, and changelog sources ranked by trust.
- **Coverage gate** that distinguishes *uncovered* from *unmeasured*: an existing coverage
  artifact is used with its timestamp, running the suite requires asking first, and paths with
  no data are reported UNKNOWN rather than untested.
- **Python-runtime branch** (`references/python-version.md`): the declaration sites that drift
  apart, `requires_python` exclusion vs. missing-ABI-wheel (resolution catches the first, not
  the second), stdlib removal grep targets, semantic changes, and deployment runtime
  availability.
- **Report template and verdict capping** (`references/report-format.md`): GO is unavailable
  while any APPLIES item is uncovered or any section is UNVERIFIED, every report ends with a
  "Not verified" section carrying the command that closes each gap, and rollback strategy is a
  single justified pick rather than a list.

### Why
An upgrade report that summarises the changelog is worthless — that is available from the
release notes in less time than the run takes. The value is entirely in the cross-reference
against real usage, and that cross-reference is only trustworthy if unverified items are
visibly unverified. Hence the three-way marking, the resolver-over-reasoning rule in Phase 3,
and the coverage distinction: each closes a path by which the report could sound confident
about something it never checked.
