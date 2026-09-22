# Changelog

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
