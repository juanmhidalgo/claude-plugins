---
name: upgrade-risk
description: |
  Use before upgrading a Python dependency or the Python runtime itself, to decide whether it
  is safe — "is it safe to bump django to 5.2", "can we move to Python 3.13", "what breaks if
  we upgrade pydantic". Produces a go / no-go / go-with-caveats report grounded in this
  repository's actual usage, with every published breaking change marked as applying here or
  not, each citing file:line.
  Do NOT use to perform the upgrade (this changes no files and installs nothing), to audit the
  codebase for vulnerabilities (use /security:audit), or for non-Python ecosystems.
argument-hint: "<package>[==target] | python X.Y"
keywords:
  - dependency-upgrade
  - python-version
  - breaking-changes
  - risk-assessment
  - changelog
  - transitive-dependencies
triggers:
  - "is it safe to upgrade"
  - "what breaks if we bump"
  - "can we move to Python 3.13"
  - "upgrade risk for this package"
allowed-tools:
  - Read
  - Grep
  - Glob
  - WebFetch
  - WebSearch
  - AskUserQuestion
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
  - Bash(coverage report *)
  - Bash(coverage json *)
  - Bash(git log *)
  - Bash(git diff *)
hooks:
  - event: Stop
    once: true
    command: |
      echo "Upgrade risk report complete. Next steps:"
      echo "  - Close the UNKNOWN items before treating the verdict as final"
      echo "  - /feature-dev:tdd to add coverage for the untested affected paths"
      echo "  - /security:audit if the report surfaced CVEs beyond this package"
---

# Upgrade Risk Report

Answers one question: **what breaks in _this_ repo if we move to the target version.** A
changelog summary anyone could get from the release notes is a failed run.

<no_mutation priority="critical">
This skill installs nothing, upgrades nothing, and writes no file in the repo. Lock files,
`pyproject.toml` and the virtualenv are left exactly as found — every resolver command below
is a dry run. If the only way to answer something is to actually install, that item is
reported as UNKNOWN with the command the user can run, not resolved by installing it.
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
make the whole report worthless.
</evidence_rule>

## Phase 0 — Target, mode, manager

Parse **$ARGUMENTS** into one of two modes:

| Mode | Trigger | Extra reading |
|------|---------|---------------|
| PACKAGE | anything that is not `python X.Y` | — |
| PYTHON | `python 3.13`, `python3.12`, "the Python version" | [python-version.md](references/python-version.md) — read it before Phase 1 |

Then, from [resolvers.md](references/resolvers.md):

1. Detect the package manager from lock files present (uv / poetry / pip-tools / pipenv / pip).
2. Read the **current** version from the **lock file**, not from the constraint in
   `pyproject.toml` — `>=4.2` is a range, not a version. No lock file ⇒ say so and use the
   installed version, flagging that CI may resolve differently.
3. Resolve the target. If `$ARGUMENTS` gave no version, use the latest release and say which.

State current → target explicitly before going on. Everything downstream is wrong if this is.

## Phase 1 — Usage scan

Find where this repo actually touches the package. Not `pyproject.toml` — the code.

Beyond plain `import X` / `from X import`, sweep the places static import scans miss: Django
`settings` (`INSTALLED_APPS`, `MIDDLEWARE`, `AUTH_*`, `*_BACKEND`), entry points and plugin
registries, `importlib`/`__import__` strings, Celery task routes, type-only imports under
`TYPE_CHECKING`, and the package's own CLI in Makefiles / CI workflows / Dockerfiles.

Flag the usages that survive a major bump badly — these drive the verdict:

- **Private API** — `_`-prefixed names, `.internal`, `.compat`, anything not in the public docs.
- **Subclassing / overriding** the library's classes, especially its base or `Meta` classes.
- **Monkeypatching** — assignment onto an imported module's attributes.
- **C-extension or binary interop** — `ctypes`, `cffi`, numpy dtypes, protobuf, compiled deps.
- **Behavior assumptions** — dict/kwargs ordering, exception identity, `__slots__`, pickling
  across versions, float formatting, timezone handling.

Output a table: `file:line` · symbol · category · why it is fragile. This table is the only
thing Phase 2 is allowed to cite.

## Phase 2 — Breaking changes, cross-referenced

Fetch the release notes for every version **between** current and target — not just the target
(sources in [resolvers.md](references/resolvers.md)). Skipping the intermediate majors is the
most common way this report misses the break that actually bites.

For each breaking change, deprecation, and removal: one line, one verdict from the evidence
rule above, citing Phase 1. Drop nothing silently — a changelog entry with no bearing here is
reported as DOES NOT APPLY, so the reader can see it was considered.

## Phase 3 — Transitive impact: resolve, do not reason

Run the manager's dry-run resolution ([resolvers.md](references/resolvers.md)) and report what
it actually says. Inferring peer conflicts by reading `pyproject.toml` is guesswork and gets
this section wrong; if the resolver cannot run here (no lock, offline, private index
unreachable), mark the whole section **UNVERIFIED**, print the command, and let the verdict
absorb the hit.

Name every pin the resolver has to move, and every dependency that has no release supporting
the target.

## Phase 4 — CVEs

`pip-audit` against the current state for what the upgrade fixes; the project's advisories or
the changelog for what the target introduces. Cite ids only from tool output or a fetched
page. If `pip-audit` is not installed, that is UNKNOWN plus the command — not "no CVEs found".

## Phase 5 — Coverage of the affected paths

Map the Phase 1 files to coverage data, in this order:

1. An existing artifact — `coverage.xml`, `.coverage`, `htmlcov/`, `coverage.json`. Report its
   timestamp; stale coverage is evidence with an asterisk, not a fact.
2. No artifact ⇒ **ask** (AskUserQuestion) before running anything. A test run is slow and has
   side effects, and this skill is otherwise read-only.
3. Declined or unavailable ⇒ every affected path is **coverage UNKNOWN**. Never report an
   uninspected path as "untested" — that is the same failure as an unverified APPLIES.

An APPLIES item on a path with no coverage is the single strongest no-go signal in the report.

## Phase 6 — Report

Template, verdict rules and rollback strategies: [report-format.md](references/report-format.md).

The verdict is capped, not chosen freely: **go** is unavailable while any APPLIES item is
uncovered or any section is UNVERIFIED — the honest answer there is go-with-caveats, with the
caveats being exactly those items. Close the report with what was not verified and the command
that would close each one.
