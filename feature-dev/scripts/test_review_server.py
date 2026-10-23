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
        self.fdir = self.root / ".feature-dev" / "features" / "example-feature"
        self.fdir.mkdir(parents=True)
        self.spec = self.fdir / "SPEC-example-feature.md"
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
        folder = self.fdir / "reviews"
        return sorted(folder.glob("*.md")) if folder.is_dir() else []

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
        self.assertRegex(written.name, r"^\d{8}T\d{6}Z\.md$")

        text = written.read_text(encoding="utf-8")
        front = review_server.read_frontmatter(text)
        # Pin: still the root-relative path (features.py matches on its basename).
        self.assertEqual(front["artifact"], ".feature-dev/features/example-feature/SPEC-example-feature.md")
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
        self.assertIn("## Accepted decisions\n\nNone.", text)
        self.assertEqual(front["decisions_accepted"], "0")
        self.assertFalse((self.fdir / "reviews" / ".url").exists())

    def test_plan_decision_overrides_and_sha_mismatch(self):
        plan = self.fdir / "PLAN-example-feature.md"
        plan.write_text(PLAN, encoding="utf-8")
        server = self.start(plan)
        token = server.token()
        plan.write_text(PLAN + "\nedited while open\n", encoding="utf-8")
        payload = {
            "verdict": "approve-with-notes",
            "items": [],
            "decisions": [{"id": "D2", "change_to": "410 for\ndeleted ids", "label": "Error code → 404"}],
            "accepted": [{"id": "D1", "label": "Storage → Postgres"}],
        }
        status, body = server.post(payload, token)
        self.assertEqual(status, 200, body)
        self.assertEqual(server.finish()[0], 0)
        text = Path(body["path"]).read_text(encoding="utf-8")
        self.assertIn("verdict: approve-with-notes", text)
        self.assertIn("changed_on_disk_since_served: true", text)
        self.assertIn("D2: change to 410 for deleted ids\n  (was: Error code → 404)", text)
        self.assertIn("decisions_accepted: 1\n", text)
        self.assertIn("## Accepted decisions\n\nD1: accepted — Storage → Postgres\n", text)

    def test_approve_records_accepted_decisions(self):
        plan = self.fdir / "PLAN-example-feature.md"
        plan.write_text(PLAN, encoding="utf-8")
        server = self.start(plan)
        payload = {"verdict": "approve", "accepted": [{"id": "D1", "label": "A → B"}, {"id": "D2", "label": "C → D"}]}
        status, body = server.post(payload, server.token())
        self.assertEqual(status, 200, body)
        self.assertEqual(server.finish()[0], 0)
        text = Path(body["path"]).read_text(encoding="utf-8")
        self.assertIn("verdict: approve\n", text)
        self.assertIn("decision_overrides: 0\ndecisions_accepted: 2\n", text)
        self.assertIn("D1: accepted — A → B\nD2: accepted — C → D\n", text)

    def test_invalid_submissions_keep_server_running(self):
        server = self.start(self.spec)
        token = server.token()
        for payload in (
            {"verdict": "maybe"},
            {"verdict": "request-changes", "items": []},
            {"verdict": "approve", "items": [{"quote": "x", "heading": "y", "comment": "z"}]},
            {"verdict": "approve-with-notes", "decisions": [{"id": "X1", "change_to": "a"}]},
            {"verdict": "approve", "accepted": [{"id": "X1"}]},
            {"verdict": "approve", "accepted": "D1"},
            {"verdict": "approve-with-notes", "decisions": [{"id": "D1", "change_to": "a"}], "accepted": [{"id": "D1"}]},
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
            self.assertEqual(path, self.fdir / "history" / f"SPEC-example-feature.{expected}.md")
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
        plan = self.fdir / "PLAN-example-feature.md"
        plan.write_text(PLAN, encoding="utf-8")
        self.assertEqual(self.run_cli("latest", str(plan)).returncode, 1)

    def test_slug_is_sanitized_everywhere(self):
        self.assertEqual(review_server.artifact_slug(Path("SPEC-x.md"), {"slug": "../../evil dir/x"}), "evil-dir-x")
        self.assertEqual(review_server.artifact_slug(Path("SPEC-a b.md"), {}), "a-b")
        self.assertEqual(review_server.artifact_slug(Path("SPEC-x.md"), {"slug": "../.."}), "artifact")
        oddir = self.root / ".feature-dev" / "features" / "Odd-Slug"
        oddir.mkdir(parents=True)
        odd = oddir / "SPEC-odd.md"
        odd.write_text(SPEC.replace("slug: example-feature", "slug: ../../Odd Slug!"), encoding="utf-8")
        snap = self.abs(self.run_cli("snapshot", str(odd)).stdout)
        self.assertEqual(snap.parent, (oddir / "history").resolve())
        server = self.start(odd)
        status, body = server.post({"verdict": "approve"}, server.token())
        self.assertEqual(status, 200)
        server.finish()
        self.assertEqual(Path(body["path"]).parent, oddir / "reviews")
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


class FeatureLayoutTest(unittest.TestCase):
    """AC-14: everything for a feature resolves inside features/<slug>/."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.fdir = self.root / ".feature-dev" / "features" / "my-feat"
        self.fdir.mkdir(parents=True)
        self.spec = self.fdir / "SPEC-my-feat.md"
        self.spec.write_text(SPEC, encoding="utf-8")  # frontmatter slug differs on purpose
        self.servers: list[ServerProcess] = []

    def tearDown(self):
        for server in self.servers:
            server.kill()
        self._tmp.cleanup()

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *args], cwd=self.root, capture_output=True, text=True
        )

    def test_ac14_serve_writes_review_and_pointer_inside_the_feature_folder(self):
        server = ServerProcess(self.root, self.spec, 30)
        self.servers.append(server)
        pointer = self.fdir / "reviews" / ".url"
        self.assertEqual(pointer.read_text(encoding="utf-8").strip(), server.url.rstrip("/") + "/")
        status, body = server.post({"verdict": "approve"}, server.token())
        self.assertEqual(status, 200, body)
        server.finish()
        written = Path(body["path"])
        self.assertEqual(written.parent, self.fdir / "reviews")
        self.assertRegex(written.name, r"^\d{8}T\d{6}Z(-\d+)?\.md$")
        self.assertFalse(pointer.exists())
        self.assertFalse((self.root / ".feature-dev" / "reviews").exists())

    def test_submit_after_the_feature_was_deleted_is_gone_and_recreates_nothing(self):
        server = ServerProcess(self.root, self.spec, 30)
        self.servers.append(server)
        token = server.token()
        shutil.rmtree(self.fdir)
        status, body = server.post({"verdict": "approve"}, token)
        self.assertEqual(status, 410, body)
        self.assertEqual(body["error"], "the feature was deleted; the review was not saved")
        code, _out = server.finish()
        self.assertEqual(code, review_server.EXIT_NO_REVIEW)
        self.assertFalse(self.fdir.exists())

    def test_submit_creates_a_missing_reviews_folder(self):
        server = ServerProcess(self.root, self.spec, 30)
        self.servers.append(server)
        token = server.token()
        shutil.rmtree(self.fdir / "reviews")
        status, body = server.post({"verdict": "approve"}, token)
        self.assertEqual(status, 200, body)
        server.finish()
        self.assertTrue(Path(body["path"]).is_file())

    def test_ac14_snapshot_writes_to_the_feature_history(self):
        result = self.run_cli("snapshot", str(self.spec), "--root", str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()), self.fdir / "history" / "SPEC-my-feat.1.md")
        self.assertFalse((self.root / ".feature-dev" / "history").exists())

    def test_ac14_latest_and_url_read_the_feature_folder(self):
        reviews = self.fdir / "reviews"
        reviews.mkdir()
        review = reviews / "20260101T000000Z.md"
        review.write_text("---\nartifact: SPEC-my-feat.md\n---\n", encoding="utf-8")
        (reviews / ".url").write_text("http://127.0.0.1:1/\n", encoding="utf-8")
        latest = self.run_cli("latest", str(self.spec), "--root", str(self.root))
        self.assertEqual((latest.returncode, Path(latest.stdout.strip())), (0, review))
        url = self.run_cli("url", str(self.spec), "--root", str(self.root))
        self.assertEqual((url.returncode, url.stdout.strip()), (0, "http://127.0.0.1:1/"))

    def test_ac14_the_slug_is_the_folder_name(self):
        self.assertEqual(review_server.slug_of(self.spec), "my-feat")


class LegacyLayoutTest(unittest.TestCase):
    """AC-12: artifacts outside features/<slug>/ are refused before any read or write."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".feature-dev" / "specs").mkdir(parents=True)
        (self.root / ".feature-dev" / "plans").mkdir(parents=True)
        (self.root / ".feature-dev" / "features" / "feat" / "deeper").mkdir(parents=True)
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "SPEC-linked.md").write_text(SPEC, encoding="utf-8")
        link = self.root / ".feature-dev" / "features" / "feat" / "SPEC-linked.md"
        link.symlink_to(elsewhere / "SPEC-linked.md")
        self.legacy = {
            "root": self.root / "SPEC-old.md",
            "specs": self.root / ".feature-dev" / "specs" / "SPEC-old.md",
            "plans": self.root / ".feature-dev" / "plans" / "PLAN-old.md",
            "nested": self.root / ".feature-dev" / "features" / "feat" / "deeper" / "SPEC-old.md",
            "symlink": link,
        }
        for key, path in self.legacy.items():
            if key != "symlink":
                path.write_text(SPEC, encoding="utf-8")
        os.utime(elsewhere / "SPEC-linked.md", (1_000_000_000, 1_000_000_000))
        for key, path in self.legacy.items():
            if key != "symlink":
                os.utime(path, (1_000_000_000, 1_000_000_000))

    def tearDown(self):
        self._tmp.cleanup()

    def listing(self) -> list[str]:
        return sorted(str(p.relative_to(self.root)) for p in (self.root / ".feature-dev").rglob("*"))

    def test_ac12_every_artifact_command_refuses_the_old_layout(self):
        for key, path in self.legacy.items():
            for command in ("serve", "snapshot", "latest", "url"):
                with self.subTest(layout=key, command=command):
                    target = path.resolve()
                    before = (target.read_bytes(), target.stat().st_mtime, self.listing())
                    args = [command, str(path), "--root", str(self.root)]
                    if command == "serve":
                        args += ["--no-browser", "--timeout", "5"]
                    result = subprocess.run(
                        [sys.executable, "-B", str(SCRIPT), *args],
                        cwd=self.root, capture_output=True, text=True, timeout=20,
                    )
                    self.assertEqual(result.returncode, review_server.EXIT_USAGE, result.stderr)
                    self.assertEqual(len(result.stderr.strip().splitlines()), 1, result.stderr)
                    self.assertIn("old layout", result.stderr)
                    self.assertEqual(result.stdout, "")
                    after = (target.read_bytes(), target.stat().st_mtime, self.listing())
                    self.assertEqual(before, after)


class RemovedSubcommandsTest(unittest.TestCase):
    """AC-10: settle and artifacts are gone; purge keeps only --pointer."""

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, timeout=20,
        )

    def test_ac10_settle_is_an_unknown_subcommand(self):
        result = self.run_cli("settle", "SPEC-x.md")
        self.assertEqual(result.returncode, review_server.EXIT_USAGE)
        self.assertIn("invalid choice", result.stderr)

    def test_ac10_artifacts_is_an_unknown_subcommand(self):
        result = self.run_cli("artifacts")
        self.assertEqual(result.returncode, review_server.EXIT_USAGE)
        self.assertIn("invalid choice", result.stderr)

    def test_ac10_purge_no_longer_takes_artifact_slug_or_dir(self):
        for option in ("--artifact", "--slug", "--dir"):
            with self.subTest(option=option):
                result = self.run_cli("purge", option, "x")
                self.assertEqual(result.returncode, review_server.EXIT_USAGE)
                self.assertIn("unrecognized arguments", result.stderr)

    def test_ac10_the_removed_helpers_are_gone(self):
        for name in (
            "artifacts_dir", "kind_dir", "find_artifacts", "KIND_DIRS", "DEFAULT_ARTIFACTS_DIR",
            "BAND_DISMISSED", "band_dismissed_file", "forget_dismissed",
            "legacy_reviews_dir", "legacy_url_file", "legacy_history_dir",
        ):
            self.assertFalse(hasattr(review_server, name), name)


class PurgeTest(unittest.TestCase):
    """Purge keeps only --pointer: a stale features/<slug>/reviews/.url."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.features = self.root / ".feature-dev" / "features"
        for slug in ("foo", "foo-bar"):
            (self.features / slug / "reviews").mkdir(parents=True)
            (self.features / slug / f"SPEC-{slug}.md").write_text(SPEC, encoding="utf-8")
            (self.features / slug / "reviews" / ".url").write_text("http://127.0.0.1:1/\n", encoding="utf-8")
        self.pointer = self.features / "foo" / "reviews" / ".url"

    def tearDown(self):
        self._tmp.cleanup()

    def purge(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "purge", "--root", str(self.root), *args],
            cwd=self.root, capture_output=True, text=True,
        )

    def listing(self) -> list[str]:
        return sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*") if ".git" not in p.parts)

    def test_pointer_deletes_only_that_slugs_url(self):
        result = self.purge("--pointer", "foo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("deleted .feature-dev/features/foo/reviews/.url", result.stdout)
        self.assertFalse(self.pointer.exists())
        self.assertTrue((self.features / "foo" / "SPEC-foo.md").exists())
        self.assertTrue((self.features / "foo-bar" / "reviews" / ".url").exists())

    def test_invalid_pointers_delete_nothing(self):
        before = self.listing()
        for bad in ("..", "../foo", "foo/bar", ".foo", "foo bar", "~", "a..b", ""):
            result = self.purge("--pointer", "foo", "--pointer", bad)
            self.assertEqual(result.returncode, review_server.EXIT_USAGE, bad)
            self.assertIn("nothing was deleted", result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(self.listing(), before, bad)

    def test_symlinked_pointer_is_refused(self):
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside)
        (outside / "keep").write_text("keep", encoding="utf-8")
        link = self.features / "foo-bar" / "reviews" / ".url"
        link.unlink()
        link.symlink_to(outside / "keep")
        result = self.purge("--pointer", "foo-bar")
        self.assertEqual(result.returncode, review_server.EXIT_USAGE)
        self.assertTrue((outside / "keep").exists())

    def test_symlinked_feature_data_is_refused(self):
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside)
        (outside / ".url").write_text("keep", encoding="utf-8")
        shutil.rmtree(self.features / "foo-bar" / "reviews")
        (self.features / "foo-bar" / "reviews").symlink_to(outside, target_is_directory=True)
        result = self.purge("--pointer", "foo-bar")
        self.assertEqual(result.returncode, review_server.EXIT_USAGE)
        self.assertTrue((outside / ".url").exists())

    def test_dry_run_deletes_nothing(self):
        before = self.listing()
        result = self.purge("--pointer", "foo", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("would delete .feature-dev/features/foo/reviews/.url", result.stdout)
        self.assertEqual(self.listing(), before)

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_tracked_pointer_is_skipped_and_reported(self):
        subprocess.run(["git", "-C", str(self.root), "init", "-q"], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(self.root), "add", "-f", ".feature-dev/features/foo/reviews/.url"],
            check=True, capture_output=True,
        )
        result = self.purge("--pointer", "foo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("skipped .feature-dev/features/foo/reviews/.url: tracked by git", result.stdout)
        self.assertTrue(self.pointer.exists())

    def test_missing_pointer_is_reported_not_an_error(self):
        result = self.purge("--pointer", "nothing-here")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no such pointer", result.stdout)

    def test_band_dismissed_json_is_never_read_or_written(self):
        path = self.root / ".feature-dev" / "band-dismissed.json"
        path.write_text("{not json", encoding="utf-8")
        result = self.purge("--pointer", "foo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("band-dismissed", result.stdout + result.stderr)
        self.assertEqual(path.read_text(encoding="utf-8"), "{not json")
        self.assertFalse(path.with_name(".band-dismissed.json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
