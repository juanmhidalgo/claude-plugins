# Manager detection, dry-run resolution, and changelog sources

<flag_caveat>
The flags below are the ones to reach for, not a guarantee about the version installed here.
If a command errors on an unknown flag, run its `--help` and adapt — do not silently fall back
to a command that *writes* (a plain `uv lock`, `poetry update`, `pip install`). The no-mutation
rule outranks getting the section answered.
</flag_caveat>

## 1. Detect the manager

Check in this order and stop at the first hit — a repo can carry leftovers from a previous
manager, and the *lock file that CI uses* is the one that matters. If two live locks exist,
say so in the report rather than picking one.

| Evidence | Manager | Lock file to read for current versions |
|----------|---------|----------------------------------------|
| `uv.lock` | uv | `uv.lock` |
| `poetry.lock` | poetry | `poetry.lock` |
| `requirements*.txt` + `*.in` | pip-tools | the compiled `requirements*.txt` |
| `Pipfile.lock` | pipenv | `Pipfile.lock` |
| only `requirements*.txt` | pip | the pinned `requirements*.txt`, if pinned at all |
| only `pyproject.toml` / `setup.py` | pip, unlocked | none — flag it |

Cross-check against CI (`.github/workflows/*.yml`, `Dockerfile`, `Makefile`, `tox.ini`): the
manager CI invokes beats the one the repo root suggests.

## 2. Current version

```bash
grep -A2 'name = "<pkg>"' uv.lock          # uv
grep -A2 'name = "<pkg>"' poetry.lock      # poetry
grep -i '^<pkg>==' requirements*.txt       # pip-tools / pip
python -c ...                              # NOT allowed here - not in allowed-tools, and the
                                           # venv may not be the one CI builds
```

`pip show <pkg>` / `uv pip show <pkg>` report what is **installed locally**, which can differ
from what CI resolves. Use them only when there is no lock file, and label the number as
"installed locally" in the report.

## 3. Target version and its metadata

```bash
pip index versions <pkg>                   # available releases
```

The PyPI JSON API answers more in one fetch — WebFetch these:

- `https://pypi.org/pypi/<pkg>/json` — `info.project_urls` (Changelog / Release Notes / Source),
  `info.requires_python`, `info.yanked`, and `urls[].filename` for the wheel tags that were
  published (`cp313`, `manylinux`, `musllinux`, or `-none-any` for pure Python).
- `https://pypi.org/pypi/<pkg>/<version>/json` — the same for one specific release.

A yanked target version is an immediate no-go; say which release replaced it.

## 4. Dry-run resolution

Run the one for the detected manager. Report its output, including the exact conflict text.

```bash
# uv
uv lock --upgrade-package '<pkg>==<target>' --dry-run
uv tree --package <pkg>            # what it pulls in
uv tree --invert --package <pkg>   # who depends on it - these are the constrainers

# poetry
poetry update --dry-run <pkg>
poetry show --tree <pkg>

# pip-tools
pip-compile --upgrade-package '<pkg>==<target>' --dry-run requirements.in

# pipenv
pipenv graph --reverse

# pip (no lock)
pip install --dry-run '<pkg>==<target>'
```

`uv tree --invert` (and `poetry show --tree` / `pipenv graph --reverse`) is the step people
skip: the conflict usually comes from a package that *depends on* the one being upgraded, not
from the upgrade itself.

Read the output for: pins the resolver has to move, packages with no release satisfying the
new constraint, and a resolver that backtracks onto an *older* version of something else —
that last one is a silent downgrade and belongs in the report as its own finding.

## 5. Changelog sources, in order of trust

1. The `Changelog` / `Release Notes` URL from the PyPI JSON — authoritative, maintained.
2. `https://github.com/<org>/<repo>/releases` — fetch the tag range, not just the newest.
3. `CHANGELOG.md` / `docs/releases/` in the source repo, at the target tag.
4. A migration guide, when the project publishes one (Django, SQLAlchemy, Pydantic all do) —
   usually more useful than the changelog, because it is written against real usage.

Fetch **every** release between current and target, majors included. A break introduced in an
intermediate major and merely *mentioned* in the target's notes is the classic miss.

## 6. CVEs

```bash
pip-audit                                  # current state, whole environment
pip-audit -r requirements.txt              # against a requirements file
```

Not installed ⇒ report UNKNOWN with the command. For the target version, use the project's own
security advisories (`https://github.com/<org>/<repo>/security/advisories`) or the GHSA entries
linked from its releases. Cite ids only from output actually seen in this run.
