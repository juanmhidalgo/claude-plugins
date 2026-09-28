#!/usr/bin/env python3
"""Local browser review for a feature-dev SPEC-*.md or PLAN-*.md.

Serves one self-contained page on 127.0.0.1 (random free port), opens the
browser, and waits. On submit it writes the reviewer's feedback to
``.feature-dev/reviews/<slug>-<UTC timestamp>.md``, prints that path and exits 0.
With no request for ``--timeout`` seconds it prints a "no review submitted"
line, writes nothing, and exits 3.

Python 3 standard library only. Nothing is fetched from or sent to the
network: the page carries no external script, stylesheet or font, and its
Content-Security-Policy only allows it to talk back to this server.

Usage:
    review_server.py serve <artifact> [--root DIR] [--timeout SECONDS] [--no-browser]
    review_server.py snapshot <artifact> [--root DIR]
    review_server.py sha <artifact>

``snapshot`` copies the artifact to ``.feature-dev/history/<slug>/<name>.<n>.md``
(n increments) and prints the copy's path. The review page diffs against the
most recent snapshot whose content differs from the artifact.

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
        folder = self.root / ".feature-dev" / "reviews"
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
            state.touch()
            if not self._host_ok():
                self._json(HTTPStatus.FORBIDDEN, {"error": "bad host"})
                return
            path = self.path.split("?", 1)[0]
            if path == "/":
                nonce = secrets.token_urlsafe(16)
                csp = (
                    "default-src 'none'; "
                    f"script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; "
                    "connect-src 'self'; img-src data:; base-uri 'none'; "
                    "form-action 'none'; frame-ancestors 'none'"
                )
                self._send(HTTPStatus.OK, state.page(nonce), "text/html; charset=utf-8", {"Content-Security-Policy": csp})
            elif path == "/diff":
                if self.headers.get("X-Review-Token") != state.token:
                    self._json(HTTPStatus.FORBIDDEN, {"error": "bad token"})
                    return
                self._json(HTTPStatus.OK, state.diff_payload())
            else:
                self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self):  # noqa: N802
            state.touch()
            if not self._host_ok() or self.headers.get("X-Review-Token") != state.token:
                self._json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})
                return
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
    url_file = root / ".feature-dev" / "reviews" / f".{state.slug}.url"
    url_file.parent.mkdir(parents=True, exist_ok=True)
    url_file.write_text(url + "\n", encoding="utf-8")
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
            url_file.unlink()
        except OSError:
            pass
    if state.result_path is not None:
        print(f"Review written: {state.result_path}", flush=True)
        return EXIT_SUBMITTED
    reason = f"idle for {int(timeout)}s" if state.timed_out else "interrupted"
    print(f"No review submitted ({reason}); nothing was written.", flush=True)
    return EXIT_NO_REVIEW


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
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
    args = parser.parse_args(argv)

    artifact = Path(args.artifact)
    root = Path(getattr(args, "root", "."))
    if not artifact.is_file():
        print(f"error: {artifact} is not a file", file=sys.stderr)
        return EXIT_USAGE
    if args.command == "sha":
        print(hashlib.sha256(artifact.read_bytes()).hexdigest())
        return 0
    if args.command == "snapshot":
        print(snapshot(artifact, root))
        return 0
    no_browser = args.no_browser or os.environ.get("FEATURE_DEV_REVIEW_NO_BROWSER") == "1"
    return serve(artifact, root, args.timeout, open_browser=not no_browser)


if __name__ == "__main__":
    sys.exit(main())
