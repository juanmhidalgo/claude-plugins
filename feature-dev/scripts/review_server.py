#!/usr/bin/env python3
"""Local browser review for a feature-dev SPEC-*.md or PLAN-*.md.

Serves one self-contained page on 127.0.0.1 (random free port), opens the
browser, and waits. On submit it writes the reviewer's feedback to
``.feature-dev/reviews/<slug>-<UTC timestamp>.md``, prints that path and exits 0.
With no request for ``--timeout`` seconds it prints a "no review submitted"
line, writes nothing, and exits 3. An open, visible tab pings the server every
60 s, so reading for longer than the timeout does not end the review.

Python 3 standard library only. Nothing is fetched from or sent to the
network: the page carries no external script, stylesheet or font, and its
Content-Security-Policy only allows it to talk back to this server.

Usage:
    review_server.py serve <artifact> [--root DIR] [--timeout SECONDS] [--no-browser]
    review_server.py snapshot <artifact> [--root DIR]
    review_server.py sha <artifact>
    review_server.py latest <artifact> [--root DIR] [--since EPOCH]
    review_server.py url <artifact> [--root DIR]
    review_server.py settle <artifact> [--root DIR]
    review_server.py artifacts [--root DIR] [--dir ARTIFACTS_DIR] [--kind spec|plan] [--new NAME]
    review_server.py purge [--root DIR] [--dir ARTIFACTS_DIR] [--artifact PATH]... [--slug SLUG]... [--pointer SLUG]... [--dry-run]

``snapshot`` copies the artifact to ``.feature-dev/history/<slug>/<name>.<n>.md``
(n increments) and prints the copy's path. The review page diffs against the
most recent snapshot whose content differs from the artifact.

``latest`` prints the newest review file written for this artifact (modified at
or after ``--since``, in epoch seconds) and exits 1 when there is none. ``url``
prints the running server's URL and exits 1 when no server is running. Both
derive the slug exactly as ``serve`` does, so callers never re-derive it.

``settle`` marks the artifact's latest review as current again (bumps its
mtime to now) after /feature-dev:review's own ``status: approved`` edit, so the
review band does not report that edit as an unreviewed change. Exit 1 when the
artifact has no review.

``artifacts`` lists every SPEC/PLAN the commands can use, one path per line
relative to the root: ``<dir>/specs/SPEC-*.md`` and ``<dir>/plans/PLAN-*.md``
first, then legacy ``SPEC-*.md``/``PLAN-*.md`` at the root. A name found in
both places is listed once, from ``<dir>``. ``<dir>`` is ``--dir`` (the plugin's
``artifacts_dir`` option), ``.feature-dev`` when it is empty or still an
unsubstituted ``${...}`` placeholder. With ``--new NAME`` it prints where a new
artifact of that name is written instead, and lists nothing.

``purge`` is the only deletion path for /feature-dev:cleanup. ``--artifact``
removes a ``SPEC-*.md``/``PLAN-*.md`` at the root or in its ``--dir`` folder; ``--slug`` removes that slug's
history folder and its review files (exact slug, never a prefix); ``--pointer``
removes that slug's server pointer. Every argument is validated before anything
is deleted: one invalid argument deletes nothing and exits 2. Git-tracked files
are skipped and reported. ``--dry-run`` prints the plan without deleting.
Once an artifact is deleted, its entry in the review band's Dismiss file
(``.feature-dev/band-dismissed.json``) goes too, and the file itself when no
entry is left; a symlinked, tracked or unreadable Dismiss file is left alone
and reported.

A running server answers a token-free ``GET /alive`` with 204 without resetting
its idle timer, so a liveness probe never keeps a review open.

Set FEATURE_DEV_REVIEW_NO_BROWSER=1 to never open a browser (tests, SSH).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DEFAULT_TIMEOUT = 4 * 60 * 60
VERDICTS = ("approve", "approve-with-notes", "request-changes")
PAGE_FILE = Path(__file__).with_name("review_page.html")
MAX_BODY = 2 * 1024 * 1024
EXIT_SUBMITTED = 0
EXIT_USAGE = 2
EXIT_NO_REVIEW = 3
ARTIFACT_NAME = re.compile(r"^(SPEC|PLAN)-[A-Za-z0-9._-]+\.md$")
DEFAULT_ARTIFACTS_DIR = ".feature-dev"
KIND_DIRS = {"SPEC": "specs", "PLAN": "plans"}
SAFE_SLUG = re.compile(r"^[A-Za-z0-9._-]+$")
BAND_DISMISSED = "band-dismissed.json"
REVIEW_SUFFIX = r"-\d{8}T\d{6}Z(?:-\d+)?\.md"


# --------------------------------------------------------------------------
# Artifact metadata and history
# --------------------------------------------------------------------------

def read_frontmatter(text: str) -> dict[str, str]:
    """Return the flat ``key: value`` pairs of a leading YAML block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    result: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(r"^([A-Za-z_][\w-]*):\s*(.*?)\s*(?:#.*)?$", line)
        if match:
            result[match.group(1)] = match.group(2).strip().strip("'\"")
    return result


def artifact_kind(path: Path, front: dict[str, str]) -> str:
    kind = front.get("type", "")
    if kind == "specification" or path.name.startswith("SPEC-"):
        return "spec"
    if kind == "implementation-plan" or path.name.startswith("PLAN-"):
        return "plan"
    return "doc"


def artifact_slug(path: Path, front: dict[str, str]) -> str:
    slug = front.get("slug", "")
    if not slug:
        slug = re.sub(r"^(SPEC|PLAN)-", "", path.stem)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", slug).strip("-.")
    return slug or "artifact"


def reviews_dir(root: Path) -> Path:
    return root / ".feature-dev" / "reviews"


def url_file(root: Path, slug: str) -> Path:
    return reviews_dir(root) / f".{slug}.url"


def slug_of(artifact: Path) -> str:
    text = artifact.read_text(encoding="utf-8", errors="replace")
    return artifact_slug(artifact, read_frontmatter(text))


def review_pattern(slug: str) -> re.Pattern:
    """Review files of exactly ``slug`` — ``foo`` never matches ``foo-bar-<ts>.md``."""
    return re.compile(r"^" + re.escape(slug) + REVIEW_SUFFIX + r"$")


def latest_review(artifact: Path, root: Path, since: float = 0.0) -> Path | None:
    """Newest review file for ``artifact`` modified at or after ``since``.

    A SPEC and a PLAN share a slug, so the file's ``artifact:`` frontmatter must
    name this artifact too.
    """
    folder = reviews_dir(root)
    if not folder.is_dir():
        return None
    slug = slug_of(artifact)
    pattern = review_pattern(slug)
    best: tuple[float, str, Path] | None = None
    for entry in folder.iterdir():
        if not pattern.match(entry.name) or not entry.is_file():
            continue
        mtime = entry.stat().st_mtime
        if mtime < since:
            continue
        front = read_frontmatter(entry.read_text(encoding="utf-8", errors="replace"))
        if Path(front.get("artifact", "")).name != artifact.name:
            continue
        if best is None or (mtime, entry.name) > best[:2]:
            best = (mtime, entry.name, entry)
    return best[2] if best else None


def history_dir(root: Path, slug: str) -> Path:
    return root / ".feature-dev" / "history" / slug


def history_versions(root: Path, slug: str, name: str) -> list[tuple[int, Path]]:
    """Snapshots of ``name`` (an artifact stem) sorted by version number."""
    folder = history_dir(root, slug)
    if not folder.is_dir():
        return []
    pattern = re.compile(r"^" + re.escape(name) + r"\.(\d+)\.md$")
    found = []
    for entry in folder.iterdir():
        match = pattern.match(entry.name)
        if match and entry.is_file():
            found.append((int(match.group(1)), entry))
    return sorted(found)


def snapshot(artifact: Path, root: Path) -> Path:
    """Copy ``artifact`` into its history folder as the next version."""
    text = artifact.read_bytes()
    front = read_frontmatter(text.decode("utf-8", errors="replace"))
    slug = artifact_slug(artifact, front)
    versions = history_versions(root, slug, artifact.stem)
    number = versions[-1][0] + 1 if versions else 1
    target = history_dir(root, slug) / f"{artifact.stem}.{number}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(text)
    return target


def previous_version(root: Path, slug: str, name: str, current: str) -> tuple[str, str] | None:
    """Newest snapshot whose content differs from ``current``."""
    for _number, path in reversed(history_versions(root, slug, name)):
        text = path.read_text(encoding="utf-8", errors="replace")
        if text != current:
            return path.name, text
    return None


def line_diff(old: str, new: str) -> list[list[str]]:
    """Line diff as ``[op, text]`` pairs, op one of ' ', '-', '+'."""
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    rows: list[list[str]] = []
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            rows.extend([" ", line] for line in old_lines[i1:i2])
            continue
        rows.extend(["-", line] for line in old_lines[i1:i2])
        rows.extend(["+", line] for line in new_lines[j1:j2])
    return rows


# --------------------------------------------------------------------------
# Artifact locations
# --------------------------------------------------------------------------

def artifacts_dir(raw: str | None) -> str:
    """The configured artifacts folder, relative to the root.

    Empty, or a ``${user_config...}`` placeholder the host left unsubstituted
    because the option was never saved, means the default. An absolute path or
    one with ``..`` is refused: artifacts stay inside the project.
    """
    value = (raw or "").strip()
    if not value or "${" in value:
        return DEFAULT_ARTIFACTS_DIR
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"artifacts dir {value!r} must be a relative path inside the project")
    return str(Path(*path.parts)) if path.parts else DEFAULT_ARTIFACTS_DIR


def kind_dir(root: Path, folder: str, name: str) -> Path:
    """Where an artifact named ``name`` is written: ``<folder>/specs`` or ``<folder>/plans``."""
    match = ARTIFACT_NAME.fullmatch(name)
    if not match:
        raise ValueError(f"{name!r} is not SPEC-<name>.md or PLAN-<name>.md")
    return root / folder / KIND_DIRS[match.group(1)]


def find_artifacts(root: Path, folder: str, kind: str | None = None) -> list[Path]:
    """Every artifact, the configured folder first, then legacy ones at the root.

    A name present in both is returned once, from the configured folder.
    """
    prefixes = [kind.upper()] if kind else list(KIND_DIRS)
    places = [(root / folder / KIND_DIRS[p], p) for p in prefixes] + [(root, p) for p in prefixes]
    seen: set[str] = set()
    found: list[Path] = []
    for place, prefix in places:
        if not place.is_dir():
            continue
        for entry in sorted(place.iterdir()):
            if entry.name in seen or not entry.name.startswith(prefix + "-"):
                continue
            if ARTIFACT_NAME.fullmatch(entry.name) and entry.is_file() and not entry.is_symlink():
                seen.add(entry.name)
                found.append(entry)
    return found


# --------------------------------------------------------------------------
# Feedback file
# --------------------------------------------------------------------------

def _one_line(value: str) -> str:
    return " ".join(str(value).split())


def _quote_block(text: str, indent: str) -> list[str]:
    lines = [line.rstrip() for line in str(text).strip().splitlines()] or [""]
    return [f"{indent}> {line}".rstrip() for line in lines]


def render_feedback(
    *,
    artifact: str,
    verdict: str,
    sha256: str,
    changed_on_disk: bool,
    items: list[dict],
    decisions: list[dict],
    reviewed_at: str,
) -> str:
    out = [
        "---",
        f"artifact: {artifact}",
        f"verdict: {verdict}",
        f"reviewed_sha256: {sha256}",
        f"reviewed_at: {reviewed_at}",
        f"changed_on_disk_since_served: {'true' if changed_on_disk else 'false'}",
        f"items: {len(items)}",
        f"decision_overrides: {len(decisions)}",
        "---",
        "",
        f"# Review of {artifact}",
        "",
        "## Items",
        "",
    ]
    if not items:
        out += ["None.", ""]
    for number, item in enumerate(items, start=1):
        prefix = f"{number}. "
        indent = " " * len(prefix)
        quote = str(item.get("quote", "")).strip()
        heading = _one_line(item.get("heading", "")) or "(document)"
        comment = str(item.get("comment", "")).strip()
        head_lines = _quote_block(quote, indent) if quote else [f"{indent}> (no quote)"]
        head_lines[0] = prefix + head_lines[0][len(indent):]
        out += head_lines
        out.append(f"{indent}§ {heading}")
        out.append("")
        for line in comment.splitlines() or [""]:
            out.append(f"{indent}{line}".rstrip())
        out.append("")
    out += ["## Decision overrides", ""]
    if not decisions:
        out += ["None.", ""]
    for decision in decisions:
        out.append(f"{decision['id']}: change to {_one_line(decision['change_to'])}")
        label = _one_line(decision.get("label", ""))
        if label:
            out.append(f"  (was: {label})")
    out.append("")
    return "\n".join(out)


def validate_submission(payload: object) -> tuple[str, list[dict], list[dict]]:
    if not isinstance(payload, dict):
        raise ValueError("body must be a JSON object")
    verdict = payload.get("verdict")
    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of {', '.join(VERDICTS)}")
    raw_items = payload.get("items") or []
    raw_decisions = payload.get("decisions") or []
    if not isinstance(raw_items, list) or not isinstance(raw_decisions, list):
        raise ValueError("items and decisions must be lists")
    items = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ValueError("each item must be an object")
        comment = str(raw.get("comment", "")).strip()
        if not comment:
            raise ValueError("an item has an empty comment")
        items.append(
            {
                "quote": str(raw.get("quote", ""))[:4000],
                "heading": str(raw.get("heading", ""))[:500],
                "comment": comment[:20000],
            }
        )
    decisions = []
    for raw in raw_decisions:
        if not isinstance(raw, dict):
            raise ValueError("each decision must be an object")
        ident = str(raw.get("id", ""))
        change_to = str(raw.get("change_to", "")).strip()
        if not re.fullmatch(r"D\d{1,3}", ident):
            raise ValueError(f"bad decision id {ident!r}")
        if not change_to:
            raise ValueError(f"{ident}: 'change to' needs text")
        decisions.append({"id": ident, "change_to": change_to[:4000], "label": str(raw.get("label", ""))[:500]})
    if verdict == "request-changes" and not items and not decisions:
        raise ValueError("request-changes needs at least one comment or decision override")
    if verdict == "approve" and (items or decisions):
        raise ValueError("approve carries no comments or overrides: use approve-with-notes or request-changes")
    return verdict, items, decisions


# --------------------------------------------------------------------------
# Server
# --------------------------------------------------------------------------

class ReviewState:
    def __init__(self, artifact: Path, root: Path, timeout: float):
        self.artifact = artifact
        self.root = root
        self.timeout = timeout
        self.raw = artifact.read_bytes()
        self.text = self.raw.decode("utf-8", errors="replace")
        self.sha256 = hashlib.sha256(self.raw).hexdigest()
        self.front = read_frontmatter(self.text)
        self.kind = artifact_kind(artifact, self.front)
        self.slug = artifact_slug(artifact, self.front)
        self.token = secrets.token_urlsafe(24)
        self.last_activity = time.monotonic()
        self.result_path: Path | None = None
        self.timed_out = False
        self.lock = threading.Lock()
        try:
            self.display_path = str(artifact.resolve().relative_to(root.resolve()))
        except ValueError:
            self.display_path = artifact.name

    def touch(self) -> None:
        self.last_activity = time.monotonic()

    def diff_payload(self) -> dict:
        previous = previous_version(self.root, self.slug, self.artifact.stem, self.text)
        if previous is None:
            return {"available": False}
        name, old = previous
        return {"available": True, "previous": name, "rows": line_diff(old, self.text)}

    def page(self, nonce: str) -> bytes:
        data = {
            "artifact": self.display_path,
            "name": self.artifact.name,
            "kind": self.kind,
            "slug": self.slug,
            "sha256": self.sha256,
            "token": self.token,
            "content": self.text,
        }
        encoded = json.dumps(data, ensure_ascii=False)
        # Keep the JSON inert inside <script type="application/json">.
        encoded = encoded.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
        template = PAGE_FILE.read_text(encoding="utf-8")
        html = template.replace("__NONCE__", nonce).replace("__DATA__", encoded)
        return html.encode("utf-8")

    def write_feedback(self, verdict: str, items: list[dict], decisions: list[dict]) -> Path:
        now = _dt.datetime.now(_dt.timezone.utc)
        folder = reviews_dir(self.root)
        folder.mkdir(parents=True, exist_ok=True)
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        target = folder / f"{self.slug}-{stamp}.md"
        counter = 1
        while target.exists():
            counter += 1
            target = folder / f"{self.slug}-{stamp}-{counter}.md"
        try:
            on_disk = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        except OSError:
            on_disk = ""
        body = render_feedback(
            artifact=self.display_path,
            verdict=verdict,
            sha256=self.sha256,
            changed_on_disk=on_disk != self.sha256,
            items=items,
            decisions=decisions,
            reviewed_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        target.write_text(body, encoding="utf-8")
        return target


def make_handler(state: ReviewState, server_ref: dict):
    class Handler(BaseHTTPRequestHandler):
        server_version = "feature-dev-review"
        sys_version = ""

        def log_message(self, fmt, *args):  # keep stdout for the result line
            return

        def _host_ok(self) -> bool:
            port = self.server.server_address[1]
            return self.headers.get("Host", "") in (f"127.0.0.1:{port}", f"localhost:{port}")

        def _send(self, status: int, body: bytes, content_type: str, extra: dict | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, payload: dict) -> None:
            self._send(status, json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self):  # noqa: N802
            if not self._host_ok():
                self._json(HTTPStatus.FORBIDDEN, {"error": "bad host"})
                return
            path = self.path.split("?", 1)[0]
            if path == "/alive":  # liveness probe: answers without extending the idle timer
                self.send_response(HTTPStatus.NO_CONTENT)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return
            state.touch()
            if path == "/":
                nonce = secrets.token_urlsafe(16)
                csp = (
                    "default-src 'none'; "
                    f"script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; "
                    "connect-src 'self'; img-src data:; base-uri 'none'; "
                    "form-action 'none'; frame-ancestors 'none'"
                )
                self._send(HTTPStatus.OK, state.page(nonce), "text/html; charset=utf-8", {"Content-Security-Policy": csp})
            elif path in ("/diff", "/ping"):
                if self.headers.get("X-Review-Token") != state.token:
                    self._json(HTTPStatus.FORBIDDEN, {"error": "bad token"})
                    return
                if path == "/ping":  # the visible tab keeps the idle timer alive
                    self._json(HTTPStatus.OK, {"ok": True})
                else:
                    self._json(HTTPStatus.OK, state.diff_payload())
            else:
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self):  # noqa: N802
            if not self._host_ok() or self.headers.get("X-Review-Token") != state.token:
                self._json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})
                return
            state.touch()
            if self.path != "/submit":
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if length < 0 or length > MAX_BODY:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "body too large"})
                return
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                verdict, items, decisions = validate_submission(payload)
            except (ValueError, UnicodeDecodeError) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            with state.lock:
                if state.result_path is not None:
                    self._json(HTTPStatus.CONFLICT, {"error": "already submitted", "path": str(state.result_path)})
                    return
                state.result_path = state.write_feedback(verdict, items, decisions)
            self._json(HTTPStatus.OK, {"path": str(state.result_path)})
            threading.Thread(target=server_ref["server"].shutdown, daemon=True).start()

    return Handler


def watchdog(state: ReviewState, server: ThreadingHTTPServer, stop: threading.Event) -> None:
    interval = min(1.0, max(state.timeout / 10, 0.05))
    while not stop.wait(interval):
        if state.result_path is None and time.monotonic() - state.last_activity > state.timeout:
            state.timed_out = True
            server.shutdown()
            return


def serve(artifact: Path, root: Path, timeout: float, open_browser: bool) -> int:
    state = ReviewState(artifact, root, timeout)
    server_ref: dict = {}
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state, server_ref))
    server.daemon_threads = True
    server_ref["server"] = server
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    url_path = url_file(root, state.slug)
    url_path.parent.mkdir(parents=True, exist_ok=True)
    url_path.write_text(url + "\n", encoding="utf-8")
    print(f"Review page for {state.display_path}: {url}", flush=True)
    stop = threading.Event()
    threading.Thread(target=watchdog, args=(state, server, stop), daemon=True).start()
    if open_browser:
        threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
    try:
        server.serve_forever(poll_interval=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()
        try:
            url_path.unlink()
        except OSError:
            pass
    if state.result_path is not None:
        print(f"Review written: {state.result_path}", flush=True)
        return EXIT_SUBMITTED
    reason = f"idle for {int(timeout)}s" if state.timed_out else "interrupted"
    print(f"No review submitted ({reason}); nothing was written.", flush=True)
    return EXIT_NO_REVIEW


# --------------------------------------------------------------------------
# Purge (the deletion path of /feature-dev:cleanup)
# --------------------------------------------------------------------------

class PurgeError(ValueError):
    """An argument that makes the whole purge refuse to run."""


def valid_slug(slug: str) -> bool:
    return bool(SAFE_SLUG.fullmatch(slug)) and not slug.startswith(".") and ".." not in slug


def is_tracked(root: Path, rel: str) -> bool:
    """True when git tracks ``rel`` under ``root``. Outside a repo nothing is tracked."""
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


def plan_purge(
    root: Path, artifacts: list[str], slugs: list[str], pointers: list[str], folder: str = DEFAULT_ARTIFACTS_DIR
) -> tuple[list[Path], list[tuple[Path, str]]]:
    """Validate every argument and return ``(delete, skip)``.

    ``delete`` is ordered so a directory follows its contents. Raises
    PurgeError on the first invalid argument, before anything is touched.
    An ``--artifact`` is a path relative to the root whose file name is
    SPEC-/PLAN-*.md, sitting at the root (legacy) or in its kind's folder
    under ``folder``; nothing else is accepted.
    """
    delete: list[Path] = []
    skip: list[tuple[Path, str]] = []
    for given in artifacts:
        name = Path(given).name
        if not ARTIFACT_NAME.fullmatch(name) or Path(given).is_absolute() or ".." in Path(given).parts:
            raise PurgeError(f"--artifact {given!r}: must be SPEC-<name>.md or PLAN-<name>.md, relative to the root")
        path = root / given
        if path.is_symlink() or not path.is_file():
            raise PurgeError(f"--artifact {given!r}: not a regular file under {root}")
        allowed = (root.resolve(), kind_dir(root, folder, name).resolve())
        if path.parent.resolve() not in allowed:
            raise PurgeError(f"--artifact {given!r}: neither at the root nor in {kind_dir(root, folder, name).relative_to(root)}/")
        if is_tracked(root, str(path.relative_to(root))):
            skip.append((path, "tracked by git"))
        else:
            delete.append(path)
    for option, values in (("--slug", slugs), ("--pointer", pointers)):
        for slug in values:
            if not valid_slug(slug):
                raise PurgeError(f"{option} {slug!r}: a slug is [A-Za-z0-9._-]+, with no leading '.' and no '..'")
    base = root / ".feature-dev"
    if (slugs or pointers) and base.is_symlink():
        raise PurgeError(f"{base} is a symlink")
    for folder in (base / "history", base / "reviews"):
        if (slugs or pointers) and folder.is_symlink():
            raise PurgeError(f"{folder} is a symlink")

    def claim(path: Path) -> None:
        if path.is_symlink():
            raise PurgeError(f"{path} is a symlink")
        if not _inside(path, base):
            raise PurgeError(f"{path} resolves outside {base}")
        rel = str(path.relative_to(root))
        if is_tracked(root, rel):
            skip.append((path, "tracked by git"))
        else:
            delete.append(path)

    for slug in slugs:
        folder = history_dir(root, slug)
        found = False
        if folder.is_symlink():
            raise PurgeError(f"{folder} is a symlink")
        if folder.is_dir():
            found = True
            for current, dirs, files in os.walk(folder, topdown=False, followlinks=False):
                here = Path(current)
                for entry in sorted(files) + sorted(d for d in dirs if (here / d).is_symlink()):
                    claim(here / entry)
                if not _inside(here, base):
                    raise PurgeError(f"{here} resolves outside {base}")
                delete.append(here)  # removed only if empty once its files are gone
        pattern = review_pattern(slug)
        reviews = reviews_dir(root)
        if reviews.is_dir():
            for entry in sorted(reviews.iterdir()):
                if pattern.match(entry.name):
                    found = True
                    claim(entry)
        if not found:
            skip.append((folder, f"no review data for slug {slug}"))
    for slug in pointers:
        path = url_file(root, slug)
        if path.is_symlink() or path.exists():
            claim(path)
        else:
            skip.append((path, "no such pointer"))
    return delete, skip


def purge(
    root: Path, artifacts: list[str], slugs: list[str], pointers: list[str], dry_run: bool,
    folder: str = DEFAULT_ARTIFACTS_DIR,
) -> int:
    try:
        delete, skip = plan_purge(root, artifacts, slugs, pointers, folder)
    except PurgeError as exc:
        print(f"error: {exc}; nothing was deleted", file=sys.stderr)
        return EXIT_USAGE
    delete = list(dict.fromkeys(delete))  # a repeated argument names a path once
    skip = list(dict.fromkeys(skip))

    def show(path: Path) -> str:
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            rel = str(path)
        return rel + "/" if path.is_dir() and not path.is_symlink() else rel

    failed = False
    named = {root / given for given in artifacts}
    gone: set[Path] = set()
    for path in delete:
        label = show(path)
        is_dir = path.is_dir() and not path.is_symlink()
        if dry_run:
            print(f"would delete {label}")
            if path in named:
                gone.add(path)
            continue
        try:
            if is_dir:
                if any(path.iterdir()):
                    print(f"skipped {label}: not empty (tracked files kept)")
                    continue
                path.rmdir()
            else:
                path.unlink()
        except OSError as exc:
            print(f"failed {label}: {exc}")
            failed = True
            continue
        print(f"deleted {label}")
        if path in named:
            gone.add(path)
    for path, reason in skip:
        print(f"skipped {show(path)}: {reason}")
    line = forget_dismissed(root, folder, gone, dry_run)
    if line is not None:
        print(line)
        failed = failed or line.startswith("failed ")
    return 1 if failed else 0


def band_dismissed_file(root: Path) -> Path:
    """The review band's persistent Dismiss state: ``{"version": 1, "dismissed": {name: mtimeMs}}``."""
    return root / ".feature-dev" / BAND_DISMISSED


def forget_dismissed(root: Path, folder: str, deleted: set[Path], dry_run: bool) -> str | None:
    """Drop the band's Dismiss entries of the artifacts ``purge`` deleted.

    An entry stays while another artifact of the same name remains (a legacy
    copy at the root, say). The file is removed once no entry is left, and
    replaced atomically (temp file, then rename) otherwise. Returns the line
    to print, or None when there is nothing to do. Never raises: the
    deletions already happened.
    """
    if not deleted:
        return None
    path = band_dismissed_file(root)
    label = str(path.relative_to(root))
    if path.is_symlink():
        return f"skipped {label}: is a symlink"
    if not path.is_file():
        return None
    if not _inside(path, root / ".feature-dev"):
        return f"skipped {label}: resolves outside .feature-dev"
    if is_tracked(root, label):
        return f"skipped {label}: tracked by git"
    try:
        dismissed = json.loads(path.read_text(encoding="utf-8"))["dismissed"]
        if not isinstance(dismissed, dict):
            raise TypeError("'dismissed' is not an object")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return f"skipped {label}: unreadable ({exc})"
    places = [root / folder / d for d in KIND_DIRS.values()] + [root]
    remaining = {
        entry.name
        for place in places if place.is_dir()
        for entry in place.iterdir()
        if ARTIFACT_NAME.fullmatch(entry.name) and entry.is_file() and entry not in deleted
    }
    names = {p.name for p in deleted}
    drop = sorted(n for n in dismissed if n in names and n not in remaining)
    if not drop:
        return None
    kept = {n: v for n, v in dismissed.items() if n not in drop}
    if dry_run:
        return f"would {'update' if kept else 'delete'} {label} (forget {len(drop)} dismissed)"
    try:
        if not kept:
            path.unlink()
            return f"deleted {label}"
        temp = path.with_name(f".{BAND_DISMISSED}.{os.getpid()}.tmp")
        temp.write_text(json.dumps({"version": 1, "dismissed": kept}, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, path)
    except OSError as exc:
        return f"failed {label}: {exc}"
    return f"updated {label} (forgot {len(drop)} dismissed)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    serve_p = sub.add_parser("serve", help="serve the review page and wait for a verdict")
    serve_p.add_argument("artifact")
    serve_p.add_argument("--root", default=".", help="project root (default: cwd)")
    serve_p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="idle seconds before giving up")
    serve_p.add_argument("--no-browser", action="store_true", help="do not open a browser")
    snap_p = sub.add_parser("snapshot", help="copy the artifact into .feature-dev/history/")
    snap_p.add_argument("artifact")
    snap_p.add_argument("--root", default=".", help="project root (default: cwd)")
    sha_p = sub.add_parser("sha", help="print the artifact's sha256 (compare with reviewed_sha256)")
    sha_p.add_argument("artifact")
    latest_p = sub.add_parser("latest", help="print the newest review file for the artifact")
    latest_p.add_argument("artifact")
    latest_p.add_argument("--root", default=".", help="project root (default: cwd)")
    latest_p.add_argument("--since", type=float, default=0.0, help="only files modified at or after this epoch")
    url_p = sub.add_parser("url", help="print the running review server's URL")
    url_p.add_argument("artifact")
    url_p.add_argument("--root", default=".", help="project root (default: cwd)")
    art_p = sub.add_parser("artifacts", help="list SPEC/PLAN artifacts, or where a new one goes")
    art_p.add_argument("--root", default=".", help="project root (default: cwd)")
    art_p.add_argument("--dir", default="", help="the artifacts_dir option (default .feature-dev)")
    art_p.add_argument("--kind", choices=("spec", "plan"), help="only specs or only plans")
    art_p.add_argument("--new", metavar="NAME", help="print where a new artifact NAME is written")
    settle_p = sub.add_parser("settle", help="mark the latest review current after the approve edit")
    settle_p.add_argument("artifact")
    settle_p.add_argument("--root", default=".", help="project root (default: cwd)")
    purge_p = sub.add_parser("purge", help="delete cleanup candidates: artifacts, a slug's review data, pointers")
    purge_p.add_argument("--root", default=".", help="project root (default: cwd)")
    purge_p.add_argument("--artifact", action="append", default=[], help="a SPEC/PLAN path relative to the root")
    purge_p.add_argument("--dir", default="", help="the artifacts_dir option (default .feature-dev)")
    purge_p.add_argument("--slug", action="append", default=[], help="delete the slug's history and review files")
    purge_p.add_argument("--pointer", action="append", default=[], help="delete the slug's .<slug>.url pointer")
    purge_p.add_argument("--dry-run", action="store_true", help="print what would be deleted, delete nothing")
    args = parser.parse_args(argv)

    if args.command in ("purge", "artifacts"):
        try:
            folder = artifacts_dir(args.dir)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_USAGE
        if args.command == "purge":
            return purge(Path(args.root), args.artifact, args.slug, args.pointer, args.dry_run, folder)
        root = Path(args.root)
        if args.new is not None:
            try:
                print((kind_dir(root, folder, args.new) / args.new).relative_to(root))
            except ValueError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return EXIT_USAGE
            return 0
        for path in find_artifacts(root, folder, args.kind):
            print(path.relative_to(root))
        return 0

    artifact = Path(args.artifact)
    root = Path(getattr(args, "root", "."))
    if not artifact.is_file():
        print(f"error: {artifact} is not a file", file=sys.stderr)
        return EXIT_USAGE
    if args.command == "sha":
        print(hashlib.sha256(artifact.read_bytes()).hexdigest())
        return 0
    if args.command == "latest":
        found = latest_review(artifact, root, args.since)
        if found is None:
            return 1
        print(found)
        return 0
    if args.command == "url":
        path = url_file(root, slug_of(artifact))
        if not path.is_file():
            return 1
        print(path.read_text(encoding="utf-8").strip())
        return 0
    if args.command == "settle":
        found = latest_review(artifact, root)
        if found is None:
            return 1
        now = max(time.time(), artifact.stat().st_mtime)
        os.utime(found, (now, now))
        print(found)
        return 0
    if args.command == "snapshot":
        print(snapshot(artifact, root))
        return 0
    no_browser = args.no_browser or os.environ.get("FEATURE_DEV_REVIEW_NO_BROWSER") == "1"
    return serve(artifact, root, args.timeout, open_browser=not no_browser)


if __name__ == "__main__":
    sys.exit(main())
