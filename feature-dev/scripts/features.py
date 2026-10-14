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
    features.py link-issue <slug> <owner/repo#N> <fingerprint> [--root DIR]
    features.py list [--json] [--root DIR]
    features.py delete <slug> [--force] [--dry-run] [--root DIR]

``new --kind spec`` creates ``feature.json`` with status ``draft`` and prints
the path of the SPEC the agent should write. It exits 1 when the feature
already exists and 2 on a usage error (bad slug, bad arguments).
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


def link_issue(root: Path, slug: str, ref: str, fingerprint: str) -> Path:
    """Set ``issue`` in any state. Not a transition: status and the markdown files stay as they are."""
    if not ISSUE_REF.fullmatch(ref):
        raise UsageError(f"invalid issue ref: {ref!r} (expected owner/repo#N)")
    folder, data = require_feature(root, slug)
    data["issue"] = {"ref": ref, "fingerprint": fingerprint}
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
    p_list = sub.add_parser("list", help="list features")
    p_list.add_argument("--json", action="store_true")
    p_delete = sub.add_parser("delete", help="delete a feature folder")
    p_delete.add_argument("slug")
    p_delete.add_argument("--force", action="store_true")
    p_delete.add_argument("--dry-run", action="store_true")
    for p in (p_new, p_approve, p_plan, p_step, p_impl, p_link, p_list, p_delete):
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
            link_issue(root, args.slug, args.ref, args.fingerprint)
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
