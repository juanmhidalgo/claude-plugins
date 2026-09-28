#!/usr/bin/env python3
"""Tests for review_server.py. Standard library only.

Run from anywhere:  python3 feature-dev/scripts/test_review_server.py
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
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

    def test_missing_artifact_is_a_usage_error(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "serve", str(self.root / "SPEC-nope.md"), "--no-browser"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, review_server.EXIT_USAGE)


if __name__ == "__main__":
    unittest.main()
