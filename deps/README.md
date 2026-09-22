# deps

Dependency and runtime upgrade risk assessment for Python projects. Answers "what breaks in
*this* repo if we move to the target version", not "what does the changelog say".

## Installation

```bash
/plugin install deps@juanmhidalgo-plugins
```

## Skills

| Skill | Description |
|-------|-------------|
| `/deps:upgrade-risk <pkg>[==target]` | Risk report for a dependency upgrade |
| `/deps:upgrade-risk python X.Y` | Risk report for a Python runtime upgrade |

## What it does

1. **Usage scan** — where the repo actually touches the package, including the places static
   import scans miss (settings modules, entry points, `importlib` strings, CI and Dockerfiles),
   flagging private API, monkeypatching, subclassing, C-extension interop, and behaviour
   assumptions.
2. **Breaking changes, cross-referenced** — every release between current and target, each
   entry marked APPLIES (with `file:line`), DOES NOT APPLY (with a reason), or UNKNOWN.
3. **Transitive impact** — the manager's own dry-run resolution and reverse dependency tree,
   including silent downgrades. Never inferred from `pyproject.toml`.
4. **CVEs** — `pip-audit` plus the project's advisories; ids only from output seen in the run.
5. **Coverage** — affected paths mapped to real coverage data, with *unmeasured* kept distinct
   from *uncovered*.
6. **Verdict** — go / no-go / go-with-caveats, capped by the weakest evidence, with a rollback
   strategy and a closing list of what was not verified.

## Guarantees

- **Nothing is installed or written.** Lock files, `pyproject.toml` and the virtualenv are left
  as found; `allowed-tools` admits only dry-run and read commands.
- **The test suite is not run without asking.** No coverage artifact means the skill asks, and
  a decline means paths are reported as unmeasured.
- **No recalled release notes.** Versions, CVE ids and changelog entries come from a fetched
  page or a command's output in that run, or they are reported as UNKNOWN.

## Requirements

- A Python project (uv, poetry, pip-tools, pipenv, or plain pip)
- Network access for PyPI metadata and changelogs
- Optional: `pip-audit` for the CVE section, a coverage artifact for the coverage section

## Related

- `/security:audit` — vulnerabilities in the codebase, not upgrade breakage
- `/feature-dev:tdd` — add the coverage the report says is missing
