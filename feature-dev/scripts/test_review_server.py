#!/usr/bin/env python3
"""Tests for review_server.py. Standard library only.

Run from anywhere:  python3 feature-dev/scripts/test_review_server.py
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

SCRIPT = Path(__file__).with_name("review_server.py")
sys.dont_write_bytecode = True  # keep __pycache__ out of the plugin directory
sys.path.insert(0, str(SCRIPT.parent))
import review_server  # noqa: E402

SPEC = """---
type: specification
feature: Example Feature
slug: example-feature
status: draft
---

# Spec: Example Feature

## Acceptance Criteria

- **AC-1** — a draft item never appears in the public list
- **AC-2** — an unknown id returns 404 <script>alert(1)</script>

## Notes

Tom & Jerry say "hi".
"""

PLAN = """---
type: implementation-plan
feature: Example Feature
slug: example-feature
source_spec: SPEC-example-feature.md
---

## Implementation Plan: Example Feature

### Key Decisions
| Decision | Options | Recommendation | Rationale |
|----------|---------|----------------|-----------|
| Where to validate | view, service | service | reused by the job |
| Error code | 404, 410 | 404 | matches the API |
"""


class ServerProcess:
    """Runs ``review_server.py serve`` and reads its URL line."""

    def __init__(self, root: Path, artifact: Path, timeout: float = 30):
        env = dict(os.environ, FEATURE_DEV_REVIEW_NO_BROWSER="1")
        self.proc = subprocess.Popen(
            [sys.executable, str(SCRIPT), "serve", str(artifact), "--root", str(root), "--timeout", str(timeout)],
            cwd=root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        first = self.proc.stdout.readline()
        match = re.search(r"(http://127\.0\.0\.1:\d+/)", first)
        if not match:
            self.proc.kill()
            raise AssertionError(f"no URL in first line: {first!r}; stderr: {self.proc.stderr.read()}")
        self.url = match.group(1)

    def get(self, path: str = "", headers: dict | None = None):
        req = urllib.request.Request(self.url + path.lstrip("/"), headers=headers or {})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.headers, resp.read().decode("utf-8")

    def post(self, payload: dict, token: str):
        req = urllib.request.Request(
            self.url + "submit",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Review-Token": token},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read())

    def token(self) -> str:
        _status, _headers, body = self.get()
        data = re.search(r'<script type="application/json" id="data">(.*?)</script>', body, re.S).group(1)
        return json.loads(data)["token"]

    def finish(self, wait: float = 10) -> tuple[int, str]:
        out, _err = self.proc.communicate(timeout=wait)
        return self.proc.returncode, out

    def kill(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.communicate()


class ReviewServerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.spec = self.root / "SPEC-example-feature.md"
        self.spec.write_text(SPEC, encoding="utf-8")
        self.servers: list[ServerProcess] = []

    def tearDown(self):
        for server in self.servers:
            server.kill()
        self._tmp.cleanup()

    def start(self, artifact: Path, timeout: float = 30) -> ServerProcess:
        server = ServerProcess(self.root, artifact, timeout)
        self.servers.append(server)
        return server

    def reviews(self) -> list[Path]:
        folder = self.root / ".feature-dev" / "reviews"
        return sorted(folder.glob("example-feature-*.md")) if folder.is_dir() else []

    def test_page_serves_artifact_escaped_and_self_contained(self):
        server = self.start(self.spec)
        status, headers, body = server.get()
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertIn("a draft item never appears in the public list", body)
        # The artifact's markup is escaped inside the embedded JSON, never raw.
        self.assertNotIn("<script>alert(1)</script>", body)
        self.assertIn("\\u003cscript\\u003ealert(1)\\u003c/script\\u003e", body)
        self.assertIn("Tom \\u0026 Jerry", body)
        # Nothing on the page points off the machine.
        self.assertIsNone(re.search(r"""(src|href)=["']?(https?:)?//""", body))
        self.assertNotIn("@import", body)

    def test_rejects_foreign_host_and_missing_token(self):
        server = self.start(self.spec)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            server.get(headers={"Host": "evil.example:80"})
        self.assertEqual(ctx.exception.code, 403)
        status, body = server.post({"verdict": "approve"}, token="wrong")
        self.assertEqual(status, 403)
        self.assertEqual(self.reviews(), [])

    def test_submit_writes_feedback_and_exits(self):
        server = self.start(self.spec)
        token = server.token()
        payload = {
            "verdict": "request-changes",
            "items": [
                {
                    "quote": "an unknown id returns 404",
                    "heading": "Acceptance Criteria › AC-2",
                    "comment": "Should be 410 for deleted ids.\nKeep 404 for never-existed.",
                },
                {"quote": "", "heading": "", "comment": "General: add a rate-limit AC."},
            ],
        }
        status, body = server.post(payload, token)
        self.assertEqual(status, 200, body)
        code, out = server.finish()
        self.assertEqual(code, 0)
        written = Path(body["path"])
        self.assertIn(f"Review written: {written}", out)
        self.assertEqual(self.reviews(), [written])
        self.assertRegex(written.name, r"^example-feature-\d{8}T\d{6}Z\.md$")

        text = written.read_text(encoding="utf-8")
        front = review_server.read_frontmatter(text)
        self.assertEqual(front["artifact"], "SPEC-example-feature.md")
        self.assertEqual(front["verdict"], "request-changes")
        self.assertEqual(front["reviewed_sha256"], hashlib.sha256(SPEC.encode("utf-8")).hexdigest())
        self.assertEqual(front["changed_on_disk_since_served"], "false")
        self.assertIn(
            "1. > an unknown id returns 404\n"
            "   § Acceptance Criteria › AC-2\n\n"
            "   Should be 410 for deleted ids.\n"
            "   Keep 404 for never-existed.\n",
            text,
        )
        self.assertIn("2. > (no quote)\n   § (document)\n\n   General: add a rate-limit AC.\n", text)
        self.assertIn("## Decision overrides\n\nNone.", text)
        self.assertFalse((self.root / ".feature-dev" / "reviews" / ".example-feature.url").exists())

    def test_plan_decision_overrides_and_sha_mismatch(self):
        plan = self.root / "PLAN-example-feature.md"
        plan.write_text(PLAN, encoding="utf-8")
        server = self.start(plan)
        token = server.token()
        plan.write_text(PLAN + "\nedited while open\n", encoding="utf-8")
        payload = {
            "verdict": "approve-with-notes",
            "items": [],
            "decisions": [{"id": "D2", "change_to": "410 for\ndeleted ids", "label": "Error code → 404"}],
        }
        status, body = server.post(payload, token)
        self.assertEqual(status, 200, body)
        self.assertEqual(server.finish()[0], 0)
        text = Path(body["path"]).read_text(encoding="utf-8")
        self.assertIn("verdict: approve-with-notes", text)
        self.assertIn("changed_on_disk_since_served: true", text)
        self.assertIn("D2: change to 410 for deleted ids\n  (was: Error code → 404)", text)

    def test_invalid_submissions_keep_server_running(self):
        server = self.start(self.spec)
        token = server.token()
        for payload in (
            {"verdict": "maybe"},
            {"verdict": "request-changes", "items": []},
            {"verdict": "approve", "items": [{"quote": "x", "heading": "y", "comment": "z"}]},
            {"verdict": "approve-with-notes", "decisions": [{"id": "X1", "change_to": "a"}]},
            {"verdict": "approve-with-notes", "items": [{"quote": "x", "comment": "  "}]},
        ):
            status, _body = server.post(payload, token)
            self.assertEqual(status, 400, payload)
        self.assertIsNone(server.proc.poll())
        self.assertEqual(self.reviews(), [])
        status, _body = server.post({"verdict": "approve"}, token)
        self.assertEqual(status, 200)
        self.assertEqual(server.finish()[0], 0)
        self.assertIn("verdict: approve\n", self.reviews()[0].read_text(encoding="utf-8"))

    def test_idle_timeout_exits_without_file(self):
        server = self.start(self.spec, timeout=0.5)
        code, out = server.finish(wait=15)
        self.assertEqual(code, review_server.EXIT_NO_REVIEW)
        self.assertIn("No review submitted", out)
        self.assertEqual(self.reviews(), [])

    def test_snapshot_and_diff_against_previous_version(self):
        for expected in (1, 2):
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "snapshot", str(self.spec), "--root", str(self.root)],
                capture_output=True, text=True, check=True,
            )
            path = Path(result.stdout.strip())
            self.assertEqual(path, self.root / ".feature-dev" / "history" / "example-feature" / f"SPEC-example-feature.{expected}.md")
            self.assertEqual(path.read_text(encoding="utf-8"), SPEC)
        self.spec.write_text(SPEC.replace("AC-2** — an unknown id returns 404", "AC-2** — an unknown id returns 410"), encoding="utf-8")

        server = self.start(self.spec)
        token = server.token()
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            server.get("diff")
        self.assertEqual(ctx.exception.code, 403)
        _status, _headers, body = server.get("diff", headers={"X-Review-Token": token})
        diff = json.loads(body)
        self.assertTrue(diff["available"])
        self.assertEqual(diff["previous"], "SPEC-example-feature.2.md")
        changed = [row for row in diff["rows"] if row[0] != " "]
        self.assertEqual(changed[0][0], "-")
        self.assertIn("returns 404", changed[0][1])
        self.assertEqual(changed[1][0], "+")
        self.assertIn("returns 410", changed[1][1])

    def test_diff_unavailable_without_a_differing_snapshot(self):
        review_server.snapshot(self.spec, self.root)  # identical to the artifact
        server = self.start(self.spec)
        _status, _headers, body = server.get("diff", headers={"X-Review-Token": server.token()})
        self.assertEqual(json.loads(body), {"available": False})

    def test_sha_matches_reviewed_sha256(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "sha", str(self.spec)], capture_output=True, text=True, check=True
        )
        self.assertEqual(result.stdout.strip(), hashlib.sha256(SPEC.encode("utf-8")).hexdigest())

    def abs(self, printed: str) -> Path:
        """A path the CLI printed relative to the project root, made absolute."""
        return (self.root / printed.strip()).resolve()

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *args], cwd=self.root, capture_output=True, text=True
        )

    def test_latest_and_url_track_the_running_review(self):
        self.assertEqual(self.run_cli("latest", str(self.spec)).returncode, 1)
        self.assertEqual(self.run_cli("url", str(self.spec)).returncode, 1)
        server = self.start(self.spec)
        url = self.run_cli("url", str(self.spec))
        self.assertEqual((url.returncode, url.stdout.strip()), (0, server.url.rstrip("/") + "/"))
        status, body = server.post({"verdict": "approve"}, server.token())
        self.assertEqual(status, 200)
        server.finish()
        latest = self.run_cli("latest", str(self.spec), "--since", "0")
        self.assertEqual(latest.returncode, 0)
        self.assertEqual(self.abs(latest.stdout), Path(body["path"]).resolve())
        self.assertEqual(self.run_cli("latest", str(self.spec), "--since", "99999999999").returncode, 1)
        self.assertEqual(self.run_cli("url", str(self.spec)).returncode, 1)
        # A plan with the same slug does not pick up the spec's review.
        plan = self.root / "PLAN-example-feature.md"
        plan.write_text(PLAN, encoding="utf-8")
        self.assertEqual(self.run_cli("latest", str(plan)).returncode, 1)

    def test_slug_is_sanitized_everywhere(self):
        self.assertEqual(review_server.artifact_slug(Path("SPEC-x.md"), {"slug": "../../evil dir/x"}), "evil-dir-x")
        self.assertEqual(review_server.artifact_slug(Path("SPEC-a b.md"), {}), "a-b")
        self.assertEqual(review_server.artifact_slug(Path("SPEC-x.md"), {"slug": "../.."}), "artifact")
        odd = self.root / "SPEC-odd.md"
        odd.write_text(SPEC.replace("slug: example-feature", "slug: ../../Odd Slug!"), encoding="utf-8")
        snap = self.abs(self.run_cli("snapshot", str(odd)).stdout)
        self.assertEqual(snap.parent, (self.root / ".feature-dev" / "history" / "Odd-Slug").resolve())
        server = self.start(odd)
        status, body = server.post({"verdict": "approve"}, server.token())
        self.assertEqual(status, 200)
        server.finish()
        self.assertEqual(Path(body["path"]).parent, self.root / ".feature-dev" / "reviews")
        self.assertTrue(Path(body["path"]).name.startswith("Odd-Slug-"))
        self.assertEqual(self.abs(self.run_cli("latest", str(odd)).stdout), Path(body["path"]).resolve())

    def test_diff_requires_token(self):
        server = self.start(self.spec)
        for headers in ({}, {"X-Review-Token": "wrong"}):
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                server.get("diff", headers=headers)
            self.assertEqual(ctx.exception.code, 403)

    def test_ping_requires_token_and_keeps_server_alive(self):
        server = self.start(self.spec, timeout=1.0)
        token = server.token()
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            server.get("ping")
        self.assertEqual(ctx.exception.code, 403)
        deadline = time.monotonic() + 3.0  # three times the idle timeout
        while time.monotonic() < deadline:
            status, _headers, _body = server.get("ping", headers={"X-Review-Token": token})
            self.assertEqual(status, 200)
            time.sleep(0.3)
        self.assertIsNone(server.proc.poll())
        code, out = server.finish(wait=15)  # pings stopped: the idle timeout ends it
        self.assertEqual(code, review_server.EXIT_NO_REVIEW)
        self.assertIn("No review submitted", out)

    def test_alive_is_token_free_and_does_not_extend_idle_timeout(self):
        server = self.start(self.spec, timeout=1.0)
        status, _headers, body = server.get("alive")
        self.assertEqual((status, body), (204, ""))
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            server.get("alive", headers={"Host": "evil.example:80"})
        self.assertEqual(ctx.exception.code, 403)
        started = time.monotonic()
        while server.proc.poll() is None and time.monotonic() - started < 6.0:
            try:
                server.get("alive")
            except (urllib.error.URLError, ConnectionError):
                break
            time.sleep(0.2)
        code, out = server.finish(wait=15)
        # Probed every 0.2 s against a 1 s idle timeout, and it still timed out.
        self.assertLess(time.monotonic() - started, 4.0)
        self.assertEqual(code, review_server.EXIT_NO_REVIEW)
        self.assertIn("No review submitted", out)

    def test_second_submit_is_a_conflict(self):
        # In-process, with shutdown stubbed, so both requests reach the handler.
        state = review_server.ReviewState(self.spec, self.root, timeout=60)

        class NoShutdown:
            def shutdown(self):
                return None

        server = review_server.ThreadingHTTPServer(
            ("127.0.0.1", 0), review_server.make_handler(state, {"server": NoShutdown()})
        )
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}/submit"

            def post():
                req = urllib.request.Request(
                    url, data=b'{"verdict": "approve"}', method="POST",
                    headers={"Content-Type": "application/json", "X-Review-Token": state.token},
                )
                try:
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        return resp.status, json.loads(resp.read())
                except urllib.error.HTTPError as err:
                    return err.code, json.loads(err.read())

            first_status, first = post()
            second_status, second = post()
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(first_status, 200)
        self.assertEqual(second_status, 409)
        self.assertEqual(second["path"], first["path"])
        self.assertEqual(len(self.reviews()), 1)

    def test_control_ids_cannot_collide_with_document_ids(self):
        template = review_server.PAGE_FILE.read_text(encoding="utf-8")
        markup = template.split("<script nonce", 1)[0]
        control_ids = re.findall(r'\bid="([^"]+)"', markup)
        self.assertIn("submit", control_ids)
        self.assertIn("items", control_ids)
        for prefix in ("h-", "ac-"):
            self.assertEqual([i for i in control_ids if i.startswith(prefix)], [], prefix)
        self.assertIn('var HEADING_ID_PREFIX = "h-", AC_ID_PREFIX = "ac-";', template)
        self.assertIn("base = HEADING_ID_PREFIX + base;", template)
        self.assertIn("function $(id) { return CONTROLS[id] || null; }", template)
        # CONTROLS is captured before the document is rendered.
        self.assertLess(template.index("var CONTROLS = {};"), template.index("  render();"))

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_page_script_parses_and_safe_href_allowlist(self):
        template = review_server.PAGE_FILE.read_text(encoding="utf-8")
        script = template.split('<script nonce="__NONCE__">', 1)[1].split("</script>", 1)[0]
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
            handle.write(script)
        try:
            check = subprocess.run(["node", "--check", handle.name], capture_output=True, text=True)
        finally:
            os.unlink(handle.name)
        self.assertEqual(check.returncode, 0, check.stderr)

        func = re.search(r"  function safeHref\(url\) \{.*?\n  \}", script, re.S).group(0)
        cases = {
            "https://example.com/a": True, "http://x": True, "mailto:a@b.c": True, "#h-summary": True,
            "docs/a.md": True, "./a:b": True, "../x/y.md": True,
            "javascript:alert(1)": False, "JavaScript:alert(1)": False, "\x01javascript:alert(1)": False,
            " javascript:alert(1)": False, "java\tscript:alert(1)": False, "data:text/html,x": False,
            "vbscript:x": False, "a:b/c": False,
        }
        program = func + "\nconst cases = " + json.dumps(cases) + ";\n" + (
            "const bad = Object.entries(cases).filter(([u, ok]) => (safeHref(u) !== null) !== ok);\n"
            "console.log(JSON.stringify(bad));\n"
        )
        result = subprocess.run(["node", "-e", program], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [])

    def test_missing_artifact_is_a_usage_error(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "serve", str(self.root / "SPEC-nope.md"), "--no-browser"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, review_server.EXIT_USAGE)


class PurgeTest(unittest.TestCase):
    TS = "20260101T000000Z"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.history = self.root / ".feature-dev" / "history"
        self.reviews = self.root / ".feature-dev" / "reviews"
        self.reviews.mkdir(parents=True)
        for slug in ("foo", "foo-bar"):
            (self.history / slug).mkdir(parents=True)
            (self.history / slug / f"SPEC-{slug}.1.md").write_text("v1", encoding="utf-8")
            (self.reviews / f"{slug}-{self.TS}.md").write_text("r", encoding="utf-8")
        (self.reviews / f"foo-{self.TS}-2.md").write_text("r", encoding="utf-8")
        (self.reviews / "foo-notes.md").write_text("not a review file", encoding="utf-8")
        (self.reviews / ".foo.url").write_text("http://127.0.0.1:1/\n", encoding="utf-8")
        (self.root / "SPEC-foo.md").write_text(SPEC, encoding="utf-8")
        (self.root / "PLAN-foo.md").write_text(PLAN, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def purge(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "purge", "--root", str(self.root), *args],
            cwd=self.root, capture_output=True, text=True,
        )

    def listing(self) -> list[str]:
        return sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*") if ".git" not in p.parts)

    def test_happy_path_deletes_exactly_the_named_data(self):
        result = self.purge("--artifact", "SPEC-foo.md", "--slug", "foo", "--pointer", "foo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("deleted SPEC-foo.md", result.stdout)
        self.assertIn(f"deleted .feature-dev/reviews/foo-{self.TS}-2.md", result.stdout)
        self.assertIn("deleted .feature-dev/history/foo/", result.stdout)
        self.assertIn("deleted .feature-dev/reviews/.foo.url", result.stdout)
        self.assertFalse((self.root / "SPEC-foo.md").exists())
        self.assertFalse((self.history / "foo").exists())
        self.assertFalse((self.reviews / ".foo.url").exists())
        self.assertFalse((self.reviews / f"foo-{self.TS}.md").exists())
        # PLAN not named, a non-review file, and the longer slug all survive.
        self.assertTrue((self.root / "PLAN-foo.md").exists())
        self.assertTrue((self.reviews / "foo-notes.md").exists())

    def test_slug_never_matches_a_longer_slug_by_prefix(self):
        result = self.purge("--slug", "foo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.reviews / f"foo-bar-{self.TS}.md").exists())
        self.assertTrue((self.history / "foo-bar" / "SPEC-foo-bar.1.md").exists())
        self.assertNotIn("foo-bar", result.stdout)
        self.assertFalse(review_server.review_pattern("foo").match(f"foo-bar-{self.TS}.md"))
        self.assertTrue(review_server.review_pattern("foo-bar").match(f"foo-bar-{self.TS}.md"))

    def test_invalid_arguments_delete_nothing(self):
        before = self.listing()
        for args in (
            ("--slug", ".."), ("--slug", "../foo"), ("--slug", "foo/bar"), ("--slug", ".foo"),
            ("--slug", "foo bar"), ("--slug", "~"), ("--slug", "a..b"), ("--slug", ""),
            ("--pointer", "../x"), ("--pointer", ".foo"),
            ("--artifact", "SPEC-foo.md ~/x"), ("--artifact", "../SPEC-foo.md"), ("--artifact", "sub/SPEC-foo.md"),
            ("--artifact", "SPEC-~.md"), ("--artifact", "README.md"), ("--artifact", "SPEC-missing.md"),
        ):
            # A valid argument alongside the invalid one is not deleted either.
            result = self.purge("--slug", "foo", "--artifact", "PLAN-foo.md", *args)
            self.assertEqual(result.returncode, review_server.EXIT_USAGE, args)
            self.assertIn("nothing was deleted", result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(self.listing(), before, args)

    def test_symlinks_are_refused(self):
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside)
        (outside / "keep.md").write_text("keep", encoding="utf-8")
        (self.root / "SPEC-link.md").symlink_to(outside / "keep.md")
        (self.history / "linked").symlink_to(outside, target_is_directory=True)
        (self.history / "foo" / "escape.md").symlink_to(outside / "keep.md")
        for args in (("--artifact", "SPEC-link.md"), ("--slug", "linked"), ("--slug", "foo")):
            result = self.purge(*args)
            self.assertEqual(result.returncode, review_server.EXIT_USAGE, args)
        self.assertTrue((outside / "keep.md").exists())
        self.assertTrue((self.history / "foo" / "SPEC-foo.1.md").exists())

    def test_dry_run_deletes_nothing(self):
        before = self.listing()
        result = self.purge("--artifact", "SPEC-foo.md", "--slug", "foo", "--pointer", "foo", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("would delete SPEC-foo.md", result.stdout)
        self.assertIn(f"would delete .feature-dev/reviews/foo-{self.TS}.md", result.stdout)
        self.assertNotIn("deleted", result.stdout.replace("would delete", ""))
        self.assertEqual(self.listing(), before)

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_tracked_files_are_skipped_and_reported(self):
        def git(*args):
            subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)

        git("init", "-q")
        git("add", "-f", "SPEC-foo.md", f".feature-dev/reviews/foo-{self.TS}.md")
        result = self.purge("--artifact", "SPEC-foo.md", "--artifact", "PLAN-foo.md", "--slug", "foo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("skipped SPEC-foo.md: tracked by git", result.stdout)
        self.assertIn(f"skipped .feature-dev/reviews/foo-{self.TS}.md: tracked by git", result.stdout)
        self.assertTrue((self.root / "SPEC-foo.md").exists())
        self.assertTrue((self.reviews / f"foo-{self.TS}.md").exists())
        self.assertFalse((self.root / "PLAN-foo.md").exists())
        self.assertFalse((self.reviews / f"foo-{self.TS}-2.md").exists())

    def test_missing_slug_data_is_reported_not_an_error(self):
        result = self.purge("--slug", "nothing-here", "--pointer", "nothing-here")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no review data for slug nothing-here", result.stdout)
        self.assertIn("no such pointer", result.stdout)


if __name__ == "__main__":
    unittest.main()
