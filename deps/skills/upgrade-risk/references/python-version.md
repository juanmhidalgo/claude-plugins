# PYTHON mode: upgrading the runtime

The skeleton is the same, but three things change: the "package" is the stdlib, the blocking
risk is usually **wheel availability** rather than your own code, and the version is declared
in a dozen places that drift apart.

<verify_against_whats_new priority="critical">
Do not report removals or semantic changes from memory. Fetch
`https://docs.python.org/3/whatsnew/3.X.html` for **every** version in the range and use its
"Removed" and "Deprecated" sections as the source. The lists below are grep targets to *start*
from, not the answer — they go stale, and a confidently wrong removal list discredits the
whole report.
</verify_against_whats_new>

## 1. Where the version is declared

Every one of these is a place the upgrade can be half-applied. Grep them all and report the
ones that disagree — a mismatch here is a finding on its own, independent of the verdict.

| File | Key |
|------|-----|
| `pyproject.toml` | `requires-python`, `[tool.mypy] python_version`, `[tool.ruff] target-version`, `[tool.black] target-version` |
| `.python-version` | pyenv / uv |
| `uv.lock` | `requires-python` |
| `setup.cfg` / `setup.py` | `python_requires`, classifiers |
| `tox.ini` / `noxfile.py` | `envlist` |
| `Dockerfile`, `docker-compose.yml` | `FROM python:X.Y`, build args |
| `.github/workflows/*.yml` | `python-version`, matrix entries |
| runtime config | `runtime.txt`, `.tool-versions`, Nix, Lambda runtime, buildpack |

## 2. Dependency compatibility — the usual blocker

Resolve against the target interpreter; the resolver answers this faster than reading metadata:

```bash
uv lock --python 3.13 --dry-run
uv pip compile pyproject.toml --python-version 3.13
pip-compile --pip-args '--python-version 3.13' requirements.in
```

A dependency fails the target in one of two ways, and they need different treatment:

- **`requires_python` excludes it** — the resolver says so outright. Report the dependency, its
  latest release that does support the target, and what that bump drags in.
- **No wheel for the new ABI tag** — resolution succeeds, then the install compiles from source
  on the deploy host and fails there, or silently costs minutes of build time. Resolution does
  *not* catch this. For each dependency carrying a C extension, fetch
  `https://pypi.org/pypi/<pkg>/json` and look in `urls[].filename` for the target's tag
  (`cp313`, plus `manylinux`/`musllinux` matching the deploy image). A `-none-any.whl` is pure
  Python and safe.

Prioritise: database drivers, crypto, numeric/scientific, protobuf/grpc, image and PDF
libraries, anything vendoring a C library. Pure-Python dependencies rarely block a runtime bump.

Also check the **tooling** pinned in CI, not just the runtime dependencies — mypy, ruff, black
and pytest plugins each carry their own target-version support, and CI turning red on the
linter is still the upgrade being blocked.

## 3. Stdlib removals to grep for

Start here, then confirm each hit against the "What's New" page for the exact version:

- **3.12**: `distutils` (PEP 632), `imp`, `asynchat`, `asyncore`, `smtpd`, `unittest`
  `makeSuite`/`getTestCaseNames` helpers.
- **3.13**: the PEP 594 "dead batteries" — `cgi`, `cgitb`, `crypt`, `imghdr`, `mailcap`,
  `msilib`, `nis`, `nntplib`, `ossaudiodev`, `pipes`, `sndhdr`, `spwd`, `sunau`, `telnetlib`,
  `uu`, `xdrlib`.

`distutils` is the one that bites hardest, because it is usually imported by a *dependency's*
`setup.py`, not by first-party code — grep the lock's source distributions, not only `src/`.

## 4. Semantic changes to scan for

Grep-able, and each has burned a real codebase:

- `datetime.utcnow()` / `utcfromtimestamp()` — deprecated in 3.12, noisy or removed later.
- Frame-locals semantics (PEP 667, 3.13) — anything mutating `locals()`, and debugger/tracing
  or template hacks that rely on the old behaviour.
- f-string parsing (PEP 701, 3.12) — relaxes rules rather than breaking, but breaks *parsers*
  and codegen that assumed the old grammar.
- `typing` re-exports and aliases removed across 3.12/3.13 — a `mypy` run on the target catches
  these cheaply, and is worth suggesting as a caveat item.
- C-API changes — only relevant if the repo itself ships an extension module; if it does, that
  is a build-and-test item, not a grep item, and the report should say so.

## 5. Deployment reality

A runtime upgrade is only safe if the place it runs has that runtime. Name it explicitly:
the base image tag, the buildpack, the managed runtime's supported list, and whether the
target is in security-fix-only status or not yet at its first patch release. `3.X.0` in
production is its own risk line.

## 6. Verdict

Same capping rules as [report-format.md](report-format.md), plus: a dependency with no
target-ABI wheel and no pure-Python fallback is NO-GO until either a wheel ships or the deploy
image gains a build toolchain — and "add a build toolchain" is a change to the deploy, so it
belongs in the report as its own risk, not as a footnote.
