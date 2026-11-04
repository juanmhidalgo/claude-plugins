#!/usr/bin/env python3
"""Per-feature state store for feature-dev: one ``feature.json`` per feature.

Each feature lives in ``.feature-dev/features/<slug>/``; ``feature.json`` there
is written only by this script, atomically (temp file in the same folder, then
rename). Python 3 standard library only.

Usage:
    features.py new <slug> --kind spec [--root DIR]
    features.py new <slug> --kind plan [--spec <spec-slug>] [--root DIR]
    features.py approve <slug> [--root DIR]
    features.py plan <slug> --steps N [--from-spec] [--replace] [--root DIR]
    features.py step <slug> done <n> [--root DIR]
    features.py step <slug> halt <n> --reason TEXT [--root DIR]
    features.py step <slug> resume [--root DIR]
    features.py step <slug> reopen <n> [--root DIR]
    features.py implemented <slug> [--root DIR]
    features.py link-issue <slug> <owner/repo#N> <fingerprint> [--kind spec|plan] [--root DIR]
    features.py list [--json] [--root DIR]
    features.py delete <slug> [--force] [--dry-run] [--root DIR]
    features.py resolve spec|plan [<argument>] [--branch NAME] [--skip-implemented] [--newest] [--root DIR]

``new --kind spec`` creates ``feature.json`` with status ``draft`` and prints
the path of the SPEC the agent should write. It exits 1 when the feature
already exists and 2 on a usage error (bad slug, bad arguments).

``resolve`` is the preflight of the commands that take a SPEC or PLAN: it turns
a raw argument (a path, an issue reference, a feature slug or title, or
nothing) into one JSON line describing the artifact, and exits 0 (resolved),
2 (not found; ``reason`` says what was searched), 3 (ambiguous; ``candidates``
lists them) or 4 (the artifact or its ``feature.json`` is malformed). See
``resolve_artifact``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Callable, NamedTuple
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2
# ``resolve`` only; 2 doubles as "not found" there (its stdout is JSON either way).
EXIT_NOT_FOUND = 2
EXIT_AMBIGUOUS = 3
EXIT_MALFORMED = 4

FEATURES_DIR = Path(".feature-dev") / "features"
FEATURE_FILE = "feature.json"
SAFE_SLUG = re.compile(r"^[A-Za-z0-9._-]+$")
ISSUE_REF = re.compile(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+#[1-9][0-9]*")


class Refused(Exception):
    """The requested change is not allowed from the current state."""


class UsageError(Exception):
    """The arguments are invalid."""


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_slug(slug: str) -> str:
    if not (SAFE_SLUG.fullmatch(slug) and not slug.startswith(".") and ".." not in slug):
        raise UsageError(f"invalid slug: {slug!r}")
    return slug


def feature_dir(root: Path, slug: str) -> Path:
    return root / FEATURES_DIR / slug


def write_feature(folder: Path, data: dict) -> None:
    """Atomically write ``feature.json`` into ``folder`` (temp file + os.replace)."""
    temp = folder / f".{FEATURE_FILE}.{os.getpid()}.tmp"
    try:
        temp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, folder / FEATURE_FILE)
    except OSError:
        temp.unlink(missing_ok=True)
        raise


def create_feature(root: Path, slug: str, status: str, plan: dict | None) -> Path:
    folder = feature_dir(root, check_slug(slug))
    if folder.exists():
        raise Refused(f"feature already exists: {slug}")
    folder.mkdir(parents=True)
    write_feature(folder, {
        "version": 1, "slug": slug, "status": status,
        "spec": None, "plan": plan, "issue": None, "updated_at": now_utc(),
    })
    return folder


def new_feature(root: Path, slug: str, kind: str, spec: str | None = None) -> str:
    if kind == "spec":
        create_feature(root, slug, "draft", None)
        return (FEATURES_DIR / slug / f"SPEC-{slug}.md").as_posix()
    if spec is not None:
        # Plan for an existing spec: it lives in the spec's folder, whose feature.json is not touched.
        check_slug(slug)
        if not feature_dir(root, check_slug(spec)).is_dir():
            raise Refused(f"spec feature not found: {spec}")
        return (FEATURES_DIR / spec / f"PLAN-{slug}.md").as_posix()
    create_feature(root, slug, "planned", {"steps": 0, "completed": [], "halted_at": None, "halt_reason": None})
    return (FEATURES_DIR / slug / f"PLAN-{slug}.md").as_posix()


class Transition(NamedTuple):
    froms: tuple[str, ...]
    event: str
    to: str
    guard: Callable[[Path, dict, dict], None]
    effect: Callable[[dict, dict], None]


def _has_md(folder: Path, prefix: str) -> bool:
    return any(folder.glob(f"{prefix}-*.md"))


def _guard_spec_exists(folder: Path, data: dict, opts: dict) -> None:
    if not _has_md(folder, "SPEC"):
        raise Refused("no SPEC-*.md in the feature folder")


def _check_steps(opts: dict) -> None:
    if opts["steps"] is None or opts["steps"] <= 0:
        raise Refused("--steps must be greater than 0")


def _guard_plan(folder: Path, data: dict, opts: dict) -> None:
    _check_steps(opts)
    if not _has_md(folder, "PLAN"):
        raise Refused("no PLAN-*.md in the feature folder")


def _guard_plan_or_from_spec(folder: Path, data: dict, opts: dict) -> None:
    if opts.get("from_spec"):
        _check_steps(opts)
    else:
        _guard_plan(folder, data, opts)


def _guard_next_step(folder: Path, data: dict, opts: dict) -> None:
    plan = data["plan"]
    if opts["n"] != len(plan["completed"]) + 1 or opts["n"] > plan["steps"]:
        raise Refused("n must be the next step after those completed, within the plan's steps")


def _guard_all_completed(folder: Path, data: dict, opts: dict) -> None:
    if len(data["plan"]["completed"]) != data["plan"]["steps"]:
        raise Refused("not every step is completed")


def _effect_step_done(data: dict, opts: dict) -> None:
    data["plan"]["completed"].append(opts["n"])


def _guard_reopen(folder: Path, data: dict, opts: dict) -> None:
    if opts["n"] not in data["plan"]["completed"]:
        raise Refused("n must be a completed step")


def _effect_step_reopen(data: dict, opts: dict) -> None:
    plan = data["plan"]
    plan["completed"] = [k for k in plan["completed"] if k < opts["n"]]
    plan["halted_at"] = None
    plan["halt_reason"] = None


def _effect_step_halt(data: dict, opts: dict) -> None:
    data["plan"]["halted_at"] = opts["n"]
    data["plan"]["halt_reason"] = opts["reason"]


def _effect_step_resume(data: dict, opts: dict) -> None:
    data["plan"]["halted_at"] = None
    data["plan"]["halt_reason"] = None


def _effect_none(data: dict, opts: dict) -> None:
    pass


def _effect_approve(data: dict, opts: dict) -> None:
    data["spec"] = {**(data.get("spec") or {}), "approved_at": now_utc()}


def _effect_plan(data: dict, opts: dict) -> None:
    data["plan"] = {"steps": opts["steps"], "completed": [], "halted_at": None, "halt_reason": None}


TRANSITIONS: tuple[Transition, ...] = (
    Transition(("draft", "approved"), "approve", "approved", _guard_spec_exists, _effect_approve),
    Transition(("approved",), "plan", "planned", _guard_plan_or_from_spec, _effect_plan),
    Transition(("planned", "running", "halted"), "plan --replace", "planned", _guard_plan, _effect_plan),
    Transition(("planned", "running"), "step done", "running", _guard_next_step, _effect_step_done),
    Transition(("planned", "running"), "step halt", "halted", _guard_next_step, _effect_step_halt),
    Transition(("halted",), "step resume", "running", lambda *_: None, _effect_step_resume),
    Transition(("running", "halted"), "step reopen", "running", _guard_reopen, _effect_step_reopen),
    Transition(("running",), "implemented", "implemented", _guard_all_completed, _effect_none),
)


KNOWN_STATUSES = frozenset({"draft", "approved", "planned", "running", "halted", "implemented"})
ARTIFACT_KINDS = (("spec", "SPEC"), ("plan", "PLAN"))


class Invalid(NamedTuple):
    """A feature folder whose ``feature.json`` cannot be used; ``reason`` is a short human string."""
    reason: str


def load_feature(folder: Path) -> dict | Invalid:
    """Read ``feature.json`` from an existing folder, or say why it is unusable."""
    path = folder / FEATURE_FILE
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Invalid(f"{FEATURE_FILE} missing")
    except (OSError, UnicodeDecodeError) as exc:
        return Invalid(f"{FEATURE_FILE} is unreadable: {exc}")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return Invalid(f"{FEATURE_FILE} is not valid JSON: {exc}")
    if not isinstance(data, dict):
        return Invalid(f"{FEATURE_FILE} is not a JSON object")
    if data.get("version") != 1:
        return Invalid(f"unsupported version: {data.get('version')!r}")
    if "status" not in data:
        return Invalid("missing status")
    if data["status"] not in KNOWN_STATUSES:
        return Invalid(f"unknown status: {data['status']}")
    if data.get("plan") is not None and not isinstance(data["plan"], dict):
        return Invalid("plan is not an object")
    return data


def require_feature(root: Path, slug: str) -> tuple[Path, dict]:
    folder = feature_dir(root, check_slug(slug))
    if not folder.is_dir():
        raise Refused(f"feature not found: {slug}")
    data = load_feature(folder)
    if isinstance(data, Invalid):
        raise Refused(f"invalid feature {slug}: {data.reason}")
    return folder, data


def apply(root: Path, slug: str, event: str, **opts) -> Path:
    """Apply ``event`` to a feature: the single path every transition goes through."""
    folder, data = require_feature(root, slug)
    state = data["status"]
    row = next((t for t in TRANSITIONS if t.event == event and state in t.froms), None)
    valid = ", ".join(sorted({t.event for t in TRANSITIONS if state in t.froms})) or "none"
    if row is None:
        raise Refused(f"cannot {event} from {state}; valid from {state}: {valid}")
    try:
        row.guard(folder, data, opts)
    except Refused as exc:
        raise Refused(f"cannot {event} from {state}: {exc}; valid from {state}: {valid}") from None
    row.effect(data, opts)
    data["status"] = row.to
    data["updated_at"] = now_utc()
    write_feature(folder, data)
    return folder


def link_issue(root: Path, slug: str, ref: str, fingerprint: str, kind: str = "spec") -> Path:
    """Set ``issue`` in any state. Not a transition: status and the markdown files stay as they are.

    ``kind`` says which section's fingerprint is recorded: ``spec`` writes
    ``issue.fingerprint``, ``plan`` writes ``issue.plan_fingerprint``. The other
    kind's fingerprint survives when ``ref`` is the one already linked, and is
    dropped when the link moves to another issue (it described that issue).
    """
    if not ISSUE_REF.fullmatch(ref):
        raise UsageError(f"invalid issue ref: {ref!r} (expected owner/repo#N)")
    if kind not in ("spec", "plan"):
        raise UsageError(f"invalid kind: {kind!r} (expected spec or plan)")
    folder, data = require_feature(root, slug)
    previous = data.get("issue") if isinstance(data.get("issue"), dict) else {}
    issue: dict = {"ref": ref}
    if previous.get("ref") == ref:
        for key in ("fingerprint", "plan_fingerprint"):
            if key in previous:
                issue[key] = previous[key]
    issue["fingerprint" if kind == "spec" else "plan_fingerprint"] = fingerprint
    data["issue"] = issue
    data["updated_at"] = now_utc()
    write_feature(folder, data)
    return folder


def _review_artifact(review: Path) -> str | None:
    """Basename of the ``artifact:`` path in a review file's frontmatter, if any."""
    try:
        lines = review.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, _, value = line.partition(":")
        if key.strip() == "artifact":
            value = value.strip().strip("\"'")
            return value.replace("\\", "/").rsplit("/", 1)[-1] or None
    return None


def _newest_review_mtimes(folder: Path) -> dict[str, float]:
    newest: dict[str, float] = {}
    for review in (folder / "reviews").glob("*.md"):
        name = _review_artifact(review)
        if name is None:
            continue
        try:
            mtime = review.stat().st_mtime
        except OSError:
            continue
        newest[name] = max(newest.get(name, mtime), mtime)
    return newest


def _artifacts(root: Path, folder: Path) -> list[dict]:
    reviews = _newest_review_mtimes(folder)
    found = []
    for kind, prefix in ARTIFACT_KINDS:
        for path in sorted(folder.glob(f"{prefix}-*.md")):
            if not path.is_file():
                continue
            reviewed = reviews.get(path.name)
            found.append({
                "kind": kind,
                "path": path.relative_to(root).as_posix(),
                "needs_review": reviewed is None or path.stat().st_mtime > reviewed,
            })
    return found


def list_features(root: Path) -> list[dict]:
    base = root / FEATURES_DIR
    if not base.is_dir():
        return []
    items = []
    for folder in sorted(p for p in base.iterdir() if p.is_dir()):
        data = load_feature(folder)
        item: dict = {"slug": folder.name}
        if isinstance(data, Invalid):
            item.update(status="invalid", reason=data.reason, plan=None, issue=None)
        else:
            issue = data.get("issue")
            item.update(
                status=data["status"], plan=data.get("plan"),
                issue=issue.get("ref") if isinstance(issue, dict) else None,
            )
        item["artifacts"] = _artifacts(root, folder)
        items.append(item)
    return items


def is_tracked(root: Path, rel: str) -> bool:
    """True when git tracks ``rel`` (or anything under it) in ``root``. Outside a repo nothing is tracked."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", rel],
            capture_output=True, text=True,
        )
    except OSError:
        return False
    return result.returncode == 0


def _inside(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
    except ValueError:
        return False
    return True


def plan_delete(root: Path, slug: str, force: bool) -> list[Path]:
    """Validate everything and return the paths to remove, each directory after its contents.

    Raises Refused before anything is touched. Symlinks inside the folder are
    listed as entries of their own and never followed.
    """
    folder = feature_dir(root, check_slug(slug))
    base = root / FEATURES_DIR
    for link in (folder, base, base.parent):
        if link.is_symlink():
            raise Refused(f"{link} is a symlink")
    if not folder.is_dir():
        raise Refused(f"feature not found: {slug}")
    if not _inside(folder, base) or folder.resolve().parent != base.resolve():
        raise Refused(f"{folder} resolves outside {base}")
    data = load_feature(folder)
    state = "invalid" if isinstance(data, Invalid) else data["status"]
    if state != "implemented" and not force:
        raise Refused(f"cannot delete {slug}: state is {state}, not implemented; use --force to delete it anyway")
    if is_tracked(root, folder.relative_to(root).as_posix()):
        raise Refused(f"cannot delete {slug}: it holds files tracked by git")
    found: list[Path] = []
    for current, dirs, files in os.walk(folder, topdown=False, followlinks=False):
        here = Path(current)
        found.extend(here / name for name in sorted(files))
        found.extend(here / name for name in sorted(dirs) if (here / name).is_symlink())
        found.append(here)
    return found


def delete_feature(root: Path, slug: str, force: bool, dry_run: bool) -> list[Path]:
    paths = plan_delete(root, slug, force)
    if not dry_run:
        for path in paths:
            if path.is_dir() and not path.is_symlink():
                path.rmdir()
            else:
                path.unlink()
    return paths


# ---------------------------------------------------------------------------
# resolve: the preflight of /explore-plan, /spec-review and /plan-review
# ---------------------------------------------------------------------------

ARTIFACT_TYPES = {"spec": "specification", "plan": "implementation-plan"}
ISSUE_ARG = re.compile(
    r"^(?:#?(?P<bare>[1-9][0-9]*)"
    r"|(?P<repo>[A-Za-z0-9._-]+/[A-Za-z0-9._-]+)#(?P<num>[1-9][0-9]*)"
    r"|https?://github\.com/(?P<url_repo>[A-Za-z0-9._-]+/[A-Za-z0-9._-]+)/issues/(?P<url_num>[1-9][0-9]*)/?)$"
)
FRONTMATTER_LINE = re.compile(r"^([A-Za-z_][\w-]*):\s*(.*?)\s*$")
REPO_NAME_LINE = re.compile(r"^\s+-\s*name:\s*(.+?)\s*$")
SOURCE_SPEC_LINE = re.compile(r"^\s*(?:[-*]\s*)?Source spec:\s*`?([^`\s]+)`?\s*$", re.MULTILINE)


class Malformed(Exception):
    """The artifact exists but cannot be read the way the commands need it."""


class NotFound(Exception):
    """Nothing resolved; ``reason`` is a short code the commands branch on."""

    def __init__(self, reason: str, message: str, **extra):
        super().__init__(message)
        self.reason = reason
        self.extra = extra


class Ambiguous(Exception):
    """Several artifacts match; ``candidates`` are newest first."""

    def __init__(self, message: str, candidates: list[dict]):
        super().__init__(message)
        self.candidates = candidates


def parse_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    """Return the flat ``key: value`` frontmatter and the names under ``repos:``.

    Raises Malformed when the file does not start with ``---`` or the block is
    never closed. Quotes around a value are stripped; nested keys other than
    the ``repos`` entries' ``name`` are ignored.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise Malformed("no frontmatter block (the file must start with ---)")
    front: dict[str, str] = {}
    repos: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            return front, repos
        match = FRONTMATTER_LINE.match(line)
        if match:
            front[match.group(1)] = match.group(2).strip().strip("'\"")
            continue
        repo = REPO_NAME_LINE.match(line)
        if repo:
            repos.append(repo.group(1).strip("'\""))
    raise Malformed("frontmatter block is not closed (no second ---)")


def parse_issue_argument(argument: str) -> tuple[str | None, int] | None:
    """``#N``, ``N``, ``owner/repo#N`` or an issue URL -> (owner/repo or None, N)."""
    match = ISSUE_ARG.match(argument.strip())
    if not match:
        return None
    if match.group("bare"):
        return None, int(match.group("bare"))
    if match.group("repo"):
        return match.group("repo"), int(match.group("num"))
    return match.group("url_repo"), int(match.group("url_num"))


def _artifact_kind(path: Path) -> str | None:
    for kind, prefix in ARTIFACT_KINDS:
        if path.name.startswith(f"{prefix}-") and path.suffix == ".md":
            return kind
    return None


def _kind_files(folder: Path, kind: str) -> list[Path]:
    prefix = dict(ARTIFACT_KINDS)[kind]
    return sorted(p for p in folder.glob(f"{prefix}-*.md") if p.is_file())


def _store_root_of(path: Path) -> Path | None:
    """The repo root whose ``.feature-dev/features/<slug>/`` holds ``path``, or None."""
    folder = path.parent
    if folder.parent.name == "features" and folder.parent.parent.name == ".feature-dev":
        return folder.parent.parent.parent
    return None


def _display_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _current_branch(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "branch", "--show-current"],
            capture_output=True, text=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _candidate(root: Path, path: Path) -> dict:
    """A short description for the ambiguity list; never raises on a bad file."""
    folder = path.parent
    data = load_feature(folder)
    item = {
        "path": _display_path(root, path),
        "slug": folder.name,
        "feature": None,
        "branch": None,
        "status": "invalid" if isinstance(data, Invalid) else data["status"],
        "mtime": 0.0,
    }
    try:
        item["mtime"] = path.stat().st_mtime
        front, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        item["feature"] = front.get("feature") or None
        item["branch"] = front.get("branch") or None
    except (OSError, UnicodeDecodeError, Malformed):
        pass
    return item


def describe_artifact(root: Path, path: Path, kind: str, matched: str) -> dict:
    """Everything the commands read about one artifact. Raises Malformed."""
    store_root = _store_root_of(path)
    if store_root is None:
        raise Malformed(f"{path.as_posix()} is not inside a .feature-dev/features/<slug>/ folder")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Malformed(f"cannot read {path.as_posix()}: {exc}") from None
    front, repos = parse_frontmatter(text)
    expected = ARTIFACT_TYPES[kind]
    if front.get("type") != expected:
        raise Malformed(f"frontmatter type is {front.get('type')!r}, expected {expected!r}")
    if not front.get("feature"):
        raise Malformed("frontmatter has no feature: title")
    folder = path.parent
    data = load_feature(folder)
    if isinstance(data, Invalid):
        raise Malformed(f"{folder.name}: {data.reason}")
    other = "plan" if kind == "spec" else "spec"
    siblings = _kind_files(folder, other)
    issue = data.get("issue")
    source_spec = SOURCE_SPEC_LINE.search(text) if kind == "plan" else None
    return {
        "kind": kind,
        "path": _display_path(root, path),
        "slug": folder.name,
        "feature": front["feature"],
        "type": front["type"],
        "date": front.get("date") or None,
        "branch": front.get("branch") or None,
        "repos": repos,
        "status": data["status"],
        "plan": data.get("plan"),
        "issue": issue.get("ref") if isinstance(issue, dict) else None,
        "spec_path": _display_path(root, siblings[0]) if kind == "plan" and siblings else (
            _display_path(root, path) if kind == "spec" else None),
        "plan_path": _display_path(root, siblings[0]) if kind == "spec" and siblings else (
            _display_path(root, path) if kind == "plan" else None),
        "source_spec": source_spec.group(1) if source_spec else None,
        "external": store_root.resolve() != root.resolve(),
        "matched": matched,
        "error": None,
    }


def _pick(root: Path, kind: str, files: list[Path], matched: str, what: str,
          *, branch: str | None = None, newest: bool = False) -> tuple[Path, str]:
    """Narrow ``files`` to one: by itself, by ``branch:``, or by mtime with ``newest``."""
    if not files:
        raise NotFound("no_candidates", f"no {kind} found: {what}", searched=[what])
    if len(files) == 1:
        return files[0], matched
    candidates = sorted((_candidate(root, p) for p in files), key=lambda c: -c["mtime"])
    if branch:
        on_branch = [c for c in candidates if c["branch"] == branch]
        if len(on_branch) == 1:
            return next(p for p in files if _display_path(root, p) == on_branch[0]["path"]), "branch"
    if newest:
        return next(p for p in files if _display_path(root, p) == candidates[0]["path"]), "newest"
    raise Ambiguous(f"{len(files)} {kind}s match: {what}", candidates)


def _resolve_path(root: Path, kind: str, argument: str) -> tuple[Path, str]:
    tries = [Path(argument)] if os.path.isabs(argument) else [root / argument, Path(argument)]
    path = next((p for p in tries if p.is_file()), None)
    if path is None:
        raise NotFound("file", f"file not found: {argument}", searched=[p.as_posix() for p in tries])
    if _store_root_of(path) is None:
        raise NotFound(
            "outside_store",
            f"{argument} is not in a feature folder; artifacts live in .feature-dev/features/<slug>/",
        )
    file_kind = _artifact_kind(path)
    if file_kind is None:
        raise NotFound("outside_store", f"{argument} is not a SPEC-*.md or PLAN-*.md")
    if file_kind == kind:
        return path, "path"
    folder = path.parent
    siblings = _kind_files(folder, kind)
    if not siblings:
        raise NotFound("no_sibling", f"{argument} is a {file_kind}; its folder {folder.as_posix()} has no {kind}",
                       searched=[(folder / f"{dict(ARTIFACT_KINDS)[kind]}-*.md").as_posix()])
    return _pick(root, kind, siblings, "sibling", f"{kind} beside {argument}")


def _resolve_issue(root: Path, kind: str, repo: str | None, number: int) -> tuple[Path, str]:
    ref = f"{repo}#{number}" if repo else f"#{number}"
    files: list[Path] = []
    for item in list_features(root):
        linked = item["issue"]
        if not linked or not linked.endswith(f"#{number}"):
            continue
        if repo and linked != ref:
            continue
        files.extend(_kind_files(root / FEATURES_DIR / item["slug"], kind))
    if not files:
        raise NotFound("issue_unlinked", f"no feature in the store is linked to {ref}",
                       issue={"repo": repo, "number": number}, searched=["feature.json issue.ref"])
    return _pick(root, kind, files, "issue", f"linked to {ref}")


def _resolve_name(root: Path, kind: str, argument: str) -> tuple[Path, str]:
    base = root / FEATURES_DIR
    folder = base / argument
    if SAFE_SLUG.fullmatch(argument) and folder.is_dir():
        files = _kind_files(folder, kind)
        if not files:
            raise NotFound("no_candidates", f"feature {argument} has no {kind}",
                           searched=[(folder / f"{dict(ARTIFACT_KINDS)[kind]}-*.md").as_posix()])
        return _pick(root, kind, files, "slug", f"{kind} of feature {argument}")
    wanted = argument.strip().lower()
    files = [
        p for item in list_features(root)
        for p in _kind_files(base / item["slug"], kind)
        if (_candidate(root, p)["feature"] or "").lower() == wanted
    ]
    if not files:
        raise NotFound("unknown_name", f"no feature slug or title matches {argument!r}",
                       searched=[f"{FEATURES_DIR.as_posix()}/<slug>/", "frontmatter feature:"])
    return _pick(root, kind, files, "feature", f"{kind} titled {argument!r}")


def _looks_like_path(argument: str) -> bool:
    return "/" in argument or "\\" in argument or argument.endswith(".md")


def resolve_artifact(root: Path, kind: str, argument: str | None, *, branch: str | None = None,
                     skip_implemented: bool = False, newest: bool = False) -> tuple[int, dict]:
    """Resolve ``argument`` to one artifact of ``kind``; return (exit code, JSON payload).

    The argument may be: empty (every feature's artifact of that kind is a
    candidate, minus ``implemented`` ones with ``skip_implemented``; several
    are narrowed by the current branch, then by ``newest``), a path (an
    artifact of the other kind resolves to the one beside it), an issue
    reference (the feature linked to it), or a feature slug or title. The
    payload always carries ``kind``, ``argument`` and ``error``; a failure adds
    ``reason`` (exit 2), ``candidates`` (exit 3) or nothing else (exit 4).
    """
    if kind not in ARTIFACT_TYPES:
        raise UsageError(f"invalid kind: {kind!r} (expected spec or plan)")
    argument = (argument or "").strip()
    base = {"kind": kind, "argument": argument or None}
    try:
        if not argument:
            files = [
                root / item["path"]
                for feature in list_features(root)
                if not (skip_implemented and feature["status"] == "implemented")
                for item in feature["artifacts"] if item["kind"] == kind
            ]
            what = f"{FEATURES_DIR.as_posix()}/*/{dict(ARTIFACT_KINDS)[kind]}-*.md"
            if skip_implemented:
                what += " (implemented features skipped)"
            path, matched = _pick(root, kind, files, "only", what,
                                  branch=branch or _current_branch(root), newest=newest)
        elif (issue := parse_issue_argument(argument)) is not None:
            path, matched = _resolve_issue(root, kind, *issue)
        elif _looks_like_path(argument) or (root / argument).is_file():
            path, matched = _resolve_path(root, kind, argument)
        else:
            path, matched = _resolve_name(root, kind, argument)
        return EXIT_OK, {**base, **describe_artifact(root, path, kind, matched)}
    except NotFound as exc:
        return EXIT_NOT_FOUND, {**base, "error": str(exc), "reason": exc.reason, **exc.extra}
    except Ambiguous as exc:
        return EXIT_AMBIGUOUS, {**base, "error": str(exc), "candidates": exc.candidates}
    except Malformed as exc:
        return EXIT_MALFORMED, {**base, "error": str(exc)}


def _list_line(item: dict) -> str:
    parts = [item["slug"], item["status"]]
    plan = item["plan"]
    if plan:
        parts.append(f"{len(plan.get('completed') or [])}/{plan.get('steps')}")
    if item["status"] == "invalid":
        parts.append(item["reason"])
    return "  ".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_new = sub.add_parser("new", help="create a feature")
    p_new.add_argument("slug")
    p_new.add_argument("--kind", choices=["spec", "plan"], required=True)
    p_new.add_argument("--spec")
    p_approve = sub.add_parser("approve", help="approve the SPEC")
    p_approve.add_argument("slug")
    p_plan = sub.add_parser("plan", help="record a PLAN for the feature")
    p_plan.add_argument("slug")
    p_plan.add_argument("--steps", type=int, required=True)
    p_plan.add_argument("--from-spec", action="store_true")
    p_plan.add_argument("--replace", action="store_true")
    p_step = sub.add_parser("step", help="record progress on a step")
    p_step.add_argument("slug")
    p_step.add_argument("action", choices=["done", "halt", "resume", "reopen"])
    p_step.add_argument("n", type=int, nargs="?")
    p_step.add_argument("--reason")
    p_impl = sub.add_parser("implemented", help="mark the feature implemented")
    p_impl.add_argument("slug")
    p_link = sub.add_parser("link-issue", help="record the linked GitHub issue")
    p_link.add_argument("slug")
    p_link.add_argument("ref")
    p_link.add_argument("fingerprint")
    p_link.add_argument("--kind", choices=["spec", "plan"], default="spec")
    p_list = sub.add_parser("list", help="list features")
    p_list.add_argument("--json", action="store_true")
    p_delete = sub.add_parser("delete", help="delete a feature folder")
    p_delete.add_argument("slug")
    p_delete.add_argument("--force", action="store_true")
    p_delete.add_argument("--dry-run", action="store_true")
    p_resolve = sub.add_parser("resolve", help="find one SPEC or PLAN from a raw argument; prints one JSON line")
    p_resolve.add_argument("kind", choices=["spec", "plan"])
    p_resolve.add_argument("argument", nargs="?", default=None)
    p_resolve.add_argument("--branch", help="narrow several candidates to this branch (default: git's current branch)")
    p_resolve.add_argument("--skip-implemented", action="store_true", help="with no argument, ignore implemented features")
    p_resolve.add_argument("--newest", action="store_true", help="when still ambiguous, take the newest file")
    for p in (p_new, p_approve, p_plan, p_step, p_impl, p_link, p_list, p_delete, p_resolve):
        p.add_argument("--root", default=".")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return EXIT_USAGE if exc.code else EXIT_OK
    root = Path(args.root)
    try:
        if args.command == "new":
            print(new_feature(root, args.slug, args.kind, args.spec))
        elif args.command == "approve":
            apply(root, args.slug, "approve")
        elif args.command == "step":
            if args.action != "resume" and args.n is None:
                raise UsageError(f"step {args.action} needs a step number")
            if args.action == "halt" and not args.reason:
                raise UsageError("step halt needs --reason")
            apply(root, args.slug, f"step {args.action}", n=args.n, reason=args.reason)
        elif args.command == "implemented":
            apply(root, args.slug, "implemented")
        elif args.command == "list":
            items = list_features(root)
            if args.json:
                print(json.dumps(items, indent=2))
            else:
                for item in items:
                    print(_list_line(item))
        elif args.command == "delete":
            for path in delete_feature(root, args.slug, args.force, args.dry_run):
                print(path.relative_to(root).as_posix())
        elif args.command == "link-issue":
            link_issue(root, args.slug, args.ref, args.fingerprint, args.kind)
        elif args.command == "resolve":
            code, payload = resolve_artifact(
                root, args.kind, args.argument, branch=args.branch,
                skip_implemented=args.skip_implemented, newest=args.newest,
            )
            print(json.dumps(payload))
            return code
        else:
            apply(root, args.slug, "plan --replace" if args.replace else "plan",
                  steps=args.steps, from_spec=args.from_spec)
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
