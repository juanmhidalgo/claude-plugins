# deps

Dependency, runtime and Dependabot PR upgrade risk assessment for Python and Node/JS
projects. Answers "what breaks in *this* repo if we move to the target version" — or "can this
bot PR be merged" — not "what does the changelog say".

## Installation

```bash
/plugin install deps@juanmhidalgo-plugins
```

## Skills

| Skill | Description |
|-------|-------------|
| `/deps:upgrade-risk <pkg>[==target]` | Risk report for a Python dependency upgrade |
| `/deps:upgrade-risk <pkg>[@target]` | Risk report for a Node/JS dependency upgrade (npm, pnpm, yarn) |
| `/deps:upgrade-risk python X.Y` | Risk report for a Python runtime upgrade |
| `/deps:upgrade-risk node N` | Risk report for a Node.js runtime upgrade |
| `/deps:upgrade-risk <PR number or URL>` | Merge verdict for a Dependabot / Renovate PR |

## What it does

1. **Usage scan** — where the repo actually touches the package, including the places static
   import scans miss (settings modules, entry points, `importlib` strings, dynamic `import()`,
   bundler/test/lint config, CI and Dockerfiles),
   flagging private API, monkeypatching, subclassing, C-extension interop, and behaviour
   assumptions.
2. **Breaking changes, cross-referenced** — every release between current and target, each
   entry marked APPLIES (with `file:line`), DOES NOT APPLY (with a reason), or UNKNOWN.
3. **Transitive impact** — the manager's own dry-run resolution and reverse dependency tree,
   including silent downgrades. Never inferred from `pyproject.toml`.
4. **CVEs** — `pip-audit` / `npm audit` plus the project's advisories; ids only from output seen in the run.
5. **Coverage** — affected paths mapped to real coverage data, with *unmeasured* kept distinct
   from *uncovered*.
6. **PR checks** (PR mode) — packages taken from the diff, not the PR body; lockstep families
   checked for members the group left behind; the PR's CI install step read as resolver output;
   runtime floors (`engines.node`, `requires_python`) raised in a minor compared against every
   runtime declaration; security PRs checked against the open alerts they claim to close.
7. **Verdict** — go / no-go / go-with-caveats, capped by the weakest evidence, with a rollback
   strategy and a closing list of what was not verified.

## Guarantees

- **Nothing is installed or written.** Lock files, manifests, the virtualenv and `node_modules`
  are left as found; `allowed-tools` admits only dry-run and read commands.
- **The PR is not touched.** No checkout, comment, review, `@dependabot` command or merge; the
  report names the command and the user posts it.
- **The test suite is not run without asking.** No coverage artifact means the skill asks, and
  a decline means paths are reported as unmeasured.
- **No recalled release notes.** Versions, CVE ids and changelog entries come from a fetched
  page or a command's output in that run, or they are reported as UNKNOWN.

## Needs

- A Python project (uv, poetry, pip-tools, pipenv, or plain pip) or a Node/JS project (npm,
  pnpm, or yarn)
- Network access for registry metadata and changelogs
- `gh`, authenticated, for PR mode (Dependabot alerts need read access to security alerts;
  without it that section is reported UNKNOWN)
- Optional: `pip-audit` for the Python CVE section, a coverage artifact for the coverage section
- No MCP servers or browser

## Related

- `/security:audit` — vulnerabilities in the codebase, not upgrade breakage
- `/feature-dev:tdd` — add the coverage the report says is missing
