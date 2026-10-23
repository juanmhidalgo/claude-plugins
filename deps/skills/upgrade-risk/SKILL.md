---
name: upgrade-risk
description: |
  Use before upgrading a dependency or a language runtime, or before merging a Dependabot /
  Renovate PR, to decide whether it is safe — "is it safe to bump django to 5.2", "can we move
  to Node 24", "what breaks if we upgrade pydantic", "can I merge this dependabot PR", "review
  dependabot #141". Covers Python (uv, poetry, pip-tools, pipenv, pip) and Node/JS (npm, pnpm,
  yarn). Produces a go / no-go / go-with-caveats report grounded in this repository's actual
  usage, with every published breaking change marked as applying here or not, each citing
  file:line.
  Do NOT use to perform the upgrade or merge the PR (this changes no files, installs nothing,
  and never comments on, approves or merges a PR), to audit the codebase for vulnerabilities
  (use /security:audit), or for ecosystems other than Python and Node/JS.
argument-hint: "<package>[@|==target] | python X.Y | node N | <PR number or URL>"
keywords:
  - dependency-upgrade
  - python-version
  - node-version
  - dependabot
  - breaking-changes
  - risk-assessment
  - changelog
  - transitive-dependencies
triggers:
  - "is it safe to upgrade"
  - "what breaks if we bump"
  - "can we move to Python 3.13"
  - "can we move to Node 24"
  - "can I merge this dependabot PR"
  - "upgrade risk for this package"
allowed-tools:
  - Read
  - Grep
  - Glob
  - WebFetch
  - WebSearch
  - AskUserQuestion
  # Python
  - Bash(uv pip compile *)
  - Bash(uv lock --dry-run *)
  - Bash(uv tree *)
  - Bash(uv pip list *)
  - Bash(uv pip show *)
  - Bash(pip list *)
  - Bash(pip show *)
  - Bash(pip index versions *)
  - Bash(pip install --dry-run *)
  - Bash(pip-compile --dry-run *)
  - Bash(poetry show *)
  - Bash(poetry update --dry-run *)
  - Bash(pipenv graph *)
  - Bash(pip-audit *)
  - Bash(python -V)
  - Bash(uv --version)
  - Bash(pip --version)
  - Bash(poetry --version)
  - Bash(coverage report *)
  # Node/JS
  - Bash(node -v)
  - Bash(npm -v)
  - Bash(pnpm -v)
  - Bash(yarn -v)
  - Bash(npm config get *)
  - Bash(npm pkg get *)
  - Bash(npm --prefix * view *)
  - Bash(npm --prefix * ls *)
  - Bash(npm --prefix * explain *)
  - Bash(npm --prefix * outdated *)
  - Bash(npm --prefix * install --dry-run *)
  - Bash(npm --prefix * audit)
  - Bash(npm --prefix * audit --json)
  - Bash(npm --prefix * audit --omit=dev)
  - Bash(npm --prefix * audit --omit=dev --json)
  - Bash(npm view *)
  - Bash(npm ls *)
  - Bash(npm explain *)
  - Bash(npm outdated *)
  - Bash(npm install --dry-run *)
  - Bash(npm audit)
  - Bash(npm audit --json)
  - Bash(npm audit --omit=dev)
  - Bash(npm audit --omit=dev --json)
  - Bash(pnpm why *)
  - Bash(pnpm ls *)
  - Bash(pnpm view *)
  - Bash(pnpm audit)
  - Bash(pnpm audit --json)
  - Bash(yarn why *)
  - Bash(yarn info *)
  - Bash(yarn npm info *)
  - Bash(yarn audit)
  - Bash(yarn audit --json)
  - Bash(yarn npm audit *)
  # Git and PR (read-only)
  - Bash(git log *)
  - Bash(git diff *)
  - Bash(git show *)
  - Bash(git grep *)
  - Bash(git ls-tree *)
  - Bash(git rev-parse *)
  - Bash(git merge-base *)
  - Bash(git status *)
  - Bash(git branch --show-current)
  - Bash(git -C * log *)
  - Bash(git -C * diff *)
  - Bash(git -C * show *)
  - Bash(git -C * grep *)
  - Bash(git -C * ls-tree *)
  - Bash(git -C * rev-parse *)
  - Bash(git -C * status *)
  - Bash(git -C * branch --show-current)
  - Bash(gh pr view *)
  - Bash(gh pr list *)
  - Bash(gh pr diff *)
  - Bash(gh pr checks *)
  - Bash(gh run view *)
  - Bash(gh run list *)
  - Bash(gh release view *)
  - Bash(gh release list *)
  # gh api only with an explicit GET in front; parameters go as -f, which GET sends as a query
  # string. A trailing -X could still override it — the no_mutation rule covers that.
  - Bash(gh api --method GET repos/*/contents/*)
  - Bash(gh api --method GET repos/*/dependabot/alerts*)
  - Bash(gh api --method GET repos/*/commits/*)
  - Bash(gh api --method GET /advisories*)
  # Read-only shell helpers, for pipes and inspecting files. Deliberately absent because they
  # can write or execute: find (-delete/-exec), sed (-i, w), rg (--pre), sort (-o), tee,
  # redirects to files, node -e, python -c, coverage json (writes coverage.json).
  - Bash(cd *)
  - Bash(ls *)
  - Bash(stat *)
  - Bash(wc *)
  - Bash(head *)
  - Bash(tail *)
  - Bash(grep *)
  - Bash(jq *)
  - Bash(diff *)
  - Bash(echo *)
hooks:
  - event: Stop
    once: true
    command: |
      echo "Upgrade risk report complete. Next steps:"
      echo "  - Close the UNKNOWN items that could still change the verdict (a NO-GO on verified facts needs none)"
      echo "  - /feature-dev:tdd to add coverage for the untested affected paths"
      echo "  - /security:audit if the report surfaced CVEs beyond this package"
---

# Upgrade Risk Report

Answers one question: **what breaks in _this_ repo if we move to the target version.** A
changelog summary anyone could get from the release notes is a failed run.

<no_mutation priority="critical">
This skill installs nothing, upgrades nothing, and writes no file in the repo. Lock files,
manifests (`pyproject.toml`, `package.json`), the virtualenv and `node_modules` are left
exactly as found — every resolver command is a dry run. If the only way to answer something is
to actually install, that item is reported as UNKNOWN with the command the user can run, not
resolved by installing it.

In PR mode the same holds for the PR: no checkout of its branch, no comment, no review, no
`@dependabot` command, no merge. `gh api` is used for GET requests only — never with `-X`,
`--method`, `-f` or `-F`. The report recommends the Dependabot command; the user posts it.
</no_mutation>

<evidence_rule priority="critical">
Every claim carries its grounding, and the verdict is capped by the weakest one:

- **APPLIES** — requires a `file:line` from Phase 1. No citation, no APPLIES.
- **DOES NOT APPLY** — requires a stated reason ("we never call `X.render_to_string`";
  "grep over `**/*.py` plus settings modules found no reference").
- **UNKNOWN** — everything else, naming what would close it. A grep that came back empty on a
  dynamic-import codebase is UNKNOWN, not DOES NOT APPLY.

Never state a version, a CVE id, or a changelog entry that did not come from a fetched page or
a command's output in this run. Recalled-from-training release notes are wrong often enough to
make the whole report worthless. A PR body (Dependabot's, Renovate's, a bot reviewer's) is a
claim to check, not a source: the diff and the registry are the source.
</evidence_rule>

## Phase 0 — Target, mode, ecosystem, manager

Parse **$ARGUMENTS** into one mode:

| Mode | Trigger | Extra reading, before Phase 1 |
|------|---------|-------------------------------|
| PR | a PR number (`141`, `#141`) or a GitHub PR URL | [dependabot-pr.md](references/dependabot-pr.md) — it decides the target(s) and which mode each one runs in |
| PYTHON | `python 3.13`, `python3.12`, "the Python version" | [python-version.md](references/python-version.md) |
| NODE | `node 24`, `node22`, "the Node version" | [node-version.md](references/node-version.md) |
| PACKAGE | anything else | — |

Then detect the **ecosystem** of each package from the manifests present, and read its
resolver reference:

| Evidence | Ecosystem | Reference |
|----------|-----------|-----------|
| `pyproject.toml`, `uv.lock`, `poetry.lock`, `requirements*.txt`, `Pipfile.lock` | Python | [resolvers.md](references/resolvers.md) |
| `package.json` + `package-lock.json` / `pnpm-lock.yaml` / `yarn.lock` / `bun.lock*` | Node/JS | [node.md](references/node.md) |

A repo can hold both; the package name decides (`@scope/x` and anything only in
`package.json` is Node). When a name exists in both registries, say which one you mean.

From the reference:

1. Detect the package manager from the lock files present.
2. Read the **current** version from the **lock file**, not from the manifest constraint —
   `>=4.2` and `^2.31.1` are ranges, not versions. No lock file ⇒ say so and use the installed
   version, flagging that CI may resolve differently.
3. Resolve the target. If none was given, use the latest release and say which.

State current → target explicitly before going on. Everything downstream is wrong if this is.

## Phase 1 — Usage scan

Find where this repo actually touches the package. Not the manifest — the code.

Beyond plain imports (`import X`, `from X import`, `import … from 'x'`, `require('x')`), sweep
the places static import scans miss — the ecosystem reference lists them (Django settings and
entry points for Python; dynamic `import()`, bundler/test/lint config, `scripts` and type-only
imports for Node), plus the package's own CLI in Makefiles / CI workflows / Dockerfiles.

Flag the usages that survive a major bump badly — these drive the verdict:

- **Private API** — `_`-prefixed names, `.internal`, `.compat`, deep imports into `dist/` or
  `lib/` paths, anything not in the public docs or the package's `exports` map.
- **Subclassing / overriding** the library's classes, especially its base or `Meta` classes.
- **Monkeypatching** — assignment onto an imported module's attributes, prototype patching.
- **Native or binary interop** — C extensions, `ctypes`/`cffi`, numpy dtypes, protobuf,
  Node native addons (`node-gyp`, prebuilt `.node` binaries).
- **Behavior assumptions** — ordering, exception/error identity, pickling or serialization
  across versions, float formatting, timezone handling, module format (CJS vs ESM).

**Transitive dependency with no first-party usage:** the surface that decides APPLIES is how
the direct parent calls it. Read the parent's installed code (`node_modules/<parent>/…`,
`site-packages/<parent>/…`, at the version the lock pins) and list those call sites, plus the
first-party entry point that reaches the parent. "No first-party usage" alone is not a reason
for DOES NOT APPLY.

Output a table: `file:line` · symbol · category · why it is fragile. This table is the only
thing Phase 2 is allowed to cite.

## Phase 2 — Breaking changes, cross-referenced

Fetch the release notes for every version **between** current and target — not just the target
(sources in the ecosystem reference). Skipping the intermediate majors is the most common way
this report misses the break that actually bites.

For each breaking change, deprecation, removal, and **runtime floor change** (`requires_python`,
`engines.node`): one line, one verdict from the evidence rule above, citing Phase 1 — or, for a
runtime floor, citing every place the repo declares its runtime. Drop nothing silently — a
changelog entry with no bearing here is reported as DOES NOT APPLY, so the reader can see it
was considered.

## Phase 3 — Transitive impact: resolve, do not reason

Run the manager's dry-run resolution (ecosystem reference) and report what it actually says.
Inferring peer conflicts by reading the manifest is guesswork and gets this section wrong; if
the resolver cannot run here (no lock, offline, private registry unreachable), mark the whole
section **UNVERIFIED**, print the command, and let the verdict absorb the hit. In PR mode, the
PR's own lock diff and its CI install step are resolver output — see
[dependabot-pr.md](references/dependabot-pr.md).

Name every pin the resolver has to move, every dependency that has no release supporting the
target, and every package that ends up installed twice at different versions.

## Phase 4 — CVEs

The ecosystem's audit tool (`pip-audit`, `npm audit` / `pnpm audit` / `yarn npm audit`) against
the current state for what the upgrade fixes; the project's advisories or the changelog for
what the target introduces. Cite ids only from tool output or a fetched page. If the tool is
not installed or cannot reach its registry, that is UNKNOWN plus the command — not "no CVEs
found".

## Phase 5 — Coverage of the affected paths

Map the Phase 1 files to coverage data, in this order:

1. An existing artifact — Python: `coverage.xml`, `.coverage`, `htmlcov/`, `coverage.json`;
   Node: `coverage/lcov.info`, `coverage/coverage-final.json`, `coverage/coverage-summary.json`.
   Report its timestamp; stale coverage is evidence with an asterisk, not a fact. A coverage
   comment a CI bot left on the PR counts as an artifact with the PR head as its timestamp,
   but only for totals — it rarely names the files you need. An artifact that does not contain
   the Phase 1 files counts as **no artifact for those paths**.
2. No artifact ⇒ **ask** (AskUserQuestion) before running anything — but only when Phase 2
   has an APPLIES item; with none, coverage cannot move the verdict, so say so in one line and
   skip the question. A test run is slow and has
   side effects, and this skill is otherwise read-only.
3. Declined or unavailable ⇒ every affected path is **coverage UNKNOWN**. Never report an
   uninspected path as "untested" — that is the same failure as an unverified APPLIES.

An APPLIES item on a path with no coverage is the single strongest no-go signal in the report.

## Phase 6 — Report

Template, verdict rules and rollback strategies: [report-format.md](references/report-format.md).

The verdict is capped, not chosen freely: **go** is unavailable while any APPLIES item is
uncovered or any section is UNVERIFIED — the honest answer there is go-with-caveats, with the
caveats being exactly those items. In PR mode the verdict is also translated into a PR action
(merge / fix the branch then merge / close and wait). Close the report with what was not
verified and the command that would close each one.
