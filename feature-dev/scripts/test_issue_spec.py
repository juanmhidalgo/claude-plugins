#!/usr/bin/env python3
"""Tests for issue_spec.py. Standard library only.

Run from anywhere:  python3 feature-dev/scripts/test_issue_spec.py
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("issue_spec.py")
sys.dont_write_bytecode = True  # keep __pycache__ out of the plugin directory
sys.path.insert(0, str(SCRIPT.parent))
import issue_spec  # noqa: E402
import review_server  # noqa: E402


def run_cli(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), *args],
        input=stdin,
        capture_output=True,
        text=True,
    )


class SanitizeSlugTest(unittest.TestCase):
    """AC-11: sanitize_slug mirrors review_server.artifact_slug's rule."""

    def test_sanitize_slug_strips_path_traversal(self):
        self.assertEqual(issue_spec.sanitize_slug("../x", "fallback"), "x")

    def test_sanitize_slug_strips_leading_dot(self):
        self.assertEqual(issue_spec.sanitize_slug(".hidden", "fallback"), "hidden")

    def test_sanitize_slug_replaces_slash_with_dash(self):
        self.assertEqual(issue_spec.sanitize_slug("a/b", "fallback"), "a-b")

    def test_sanitize_slug_drops_non_ascii(self):
        self.assertEqual(issue_spec.sanitize_slug("café", "fallback"), "caf")

    def test_sanitize_slug_falls_back_to_title_when_raw_is_empty(self):
        self.assertEqual(issue_spec.sanitize_slug("", "My Feature"), "My-Feature")

    def test_sanitize_slug_falls_back_to_title_when_raw_sanitizes_to_empty(self):
        self.assertEqual(issue_spec.sanitize_slug("../..", "My Feature"), "My-Feature")

    def test_sanitize_slug_falls_back_to_spec_when_both_empty(self):
        self.assertEqual(issue_spec.sanitize_slug("../..", "///"), "spec")

    def test_sanitize_slug_matches_artifact_slug_for_every_non_empty_case(self):
        cases = ["../x", ".hidden", "a/b", "café", "plain-slug", "My Feature"]
        for raw in cases:
            with self.subTest(raw=raw):
                sanitized = issue_spec.sanitize_slug(raw, "unused-fallback")
                self.assertTrue(sanitized)  # these all sanitize to something non-empty
                self.assertEqual(
                    sanitized,
                    review_server.artifact_slug(Path("SPEC-x.md"), {"slug": raw}),
                )


SPEC_WITH_MIDDLE_DECISIONS_LOG = """---
type: specification
feature: Sample Feature
slug: sample-feature
status: approved
---

# Sample Feature

## Objective

Do the thing.

## Decisions Log

- **2026-01-01** — decided something.

## Acceptance Criteria

- AC-1 — thing happens.
"""

EXPECTED_BODY_WITHOUT_DECISIONS_LOG = (
    "# Sample Feature\n"
    "\n"
    "## Objective\n"
    "\n"
    "Do the thing.\n"
    "\n"
    "## Acceptance Criteria\n"
    "\n"
    "- AC-1 — thing happens."
)


class SectionCommandTest(unittest.TestCase):
    """AC-3: `section` prints the marker-wrapped spec body."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def _write_spec(self, name: str, text: str) -> Path:
        path = Path(self.tmpdir.name) / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_section_strips_frontmatter_and_middle_decisions_log(self):
        spec = self._write_spec("SPEC-sample.md", SPEC_WITH_MIDDLE_DECISIONS_LOG)
        result = run_cli("section", str(spec))
        self.assertEqual(result.returncode, 0)
        expected = (
            "<!-- feature-dev:spec:start slug=sample-feature -->\n"
            f"{EXPECTED_BODY_WITHOUT_DECISIONS_LOG}\n"
            "<!-- feature-dev:spec:end -->\n"
        )
        self.assertEqual(result.stdout, expected)

    def test_section_strips_decisions_log_with_nested_decision_headings(self):
        """A log rebuilt with `## Decision — <slug>` headings is stripped whole."""
        spec = (
            "---\nslug: s\n---\n"
            "# Title\n\nBody.\n\n"
            "## Decisions Log\n\n"
            "## Decision — s\n\n- **[repo: r · step 1]** one\n\n"
            "## Decision — s\n\n- **[repo: r · step 2]** two\n\n"
            "## After\n\nTail.\n"
        )
        spec_file = self._write_spec("SPEC-s.md", spec)
        result = run_cli("section", str(spec_file))
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("Decision", result.stdout)
        self.assertIn("## After", result.stdout)
        self.assertIn("Tail.", result.stdout)

    def test_section_falls_back_to_feature_when_slug_missing(self):
        text = SPEC_WITH_MIDDLE_DECISIONS_LOG.replace("slug: sample-feature\n", "")
        spec = self._write_spec("SPEC-sample.md", text)
        result = run_cli("section", str(spec))
        self.assertEqual(result.returncode, 0)
        self.assertIn("slug=Sample-Feature", result.stdout.splitlines()[0])


ISSUE_BODY_WITH_SECTION = (
    "Intro paragraph before the marker.\n"
    "\n"
    "<!-- feature-dev:spec:start slug=sample-feature -->\n"
    "# Sample Feature\n"
    "\n"
    "Section body line.\n"
    "<!-- feature-dev:spec:end -->\n"
    "\n"
    "Trailing footer after the marker.\n"
)

EXPECTED_EXTRACTED_SECTION = (
    "<!-- feature-dev:spec:start slug=sample-feature -->\n"
    "# Sample Feature\n"
    "\n"
    "Section body line.\n"
    "<!-- feature-dev:spec:end -->"
)


class ExtractCommandTest(unittest.TestCase):
    """AC-18: `extract` prints the single marker section, markers included."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def _write_body(self, name: str, text: str) -> Path:
        path = Path(self.tmpdir.name) / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_extract_prints_section_with_text_before_and_after(self):
        body_file = self._write_body("issue-body.md", ISSUE_BODY_WITH_SECTION)
        result = run_cli("extract", str(body_file))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, EXPECTED_EXTRACTED_SECTION + "\n")

    def test_extract_prints_section_from_stdin(self):
        result = run_cli("extract", "-", stdin=ISSUE_BODY_WITH_SECTION)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, EXPECTED_EXTRACTED_SECTION + "\n")

    def test_extract_refuses_body_with_no_start_marker(self):
        body_file = self._write_body("issue-body.md", "No markers here at all.\n")
        result = run_cli("extract", str(body_file))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.strip())

    def test_extract_refuses_body_with_duplicate_start_marker(self):
        body = (
            "<!-- feature-dev:spec:start slug=a -->\n"
            "First.\n"
            "<!-- feature-dev:spec:end -->\n"
            "<!-- feature-dev:spec:start slug=b -->\n"
            "Second.\n"
            "<!-- feature-dev:spec:end -->\n"
        )
        body_file = self._write_body("issue-body.md", body)
        result = run_cli("extract", str(body_file))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.strip())

    def test_extract_refuses_body_with_unterminated_start_marker(self):
        body = "<!-- feature-dev:spec:start slug=sample -->\nNo end marker follows.\n"
        body_file = self._write_body("issue-body.md", body)
        result = run_cli("extract", str(body_file))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.strip())


class ExtractSlugOptionTest(unittest.TestCase):
    """AC-11, AC-8: `extract --slug` prints only the sanitized marker slug."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def _write_body(self, name: str, text: str) -> Path:
        path = Path(self.tmpdir.name) / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_extract_slug_sanitizes_path_traversal(self):
        body = (
            "<!-- feature-dev:spec:start slug=../../etc -->\n"
            "Body.\n"
            "<!-- feature-dev:spec:end -->\n"
        )
        body_file = self._write_body("issue-body.md", body)
        result = run_cli(
            "extract", "--slug", "--fallback-title", "Something", str(body_file)
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "etc\n")

    def test_extract_slug_falls_back_to_title_when_value_is_empty(self):
        body = (
            "<!-- feature-dev:spec:start slug= -->\n"
            "Body.\n"
            "<!-- feature-dev:spec:end -->\n"
        )
        body_file = self._write_body("issue-body.md", body)
        result = run_cli(
            "extract", "--slug", "--fallback-title", "My Feature", str(body_file)
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "My-Feature\n")

    def test_extract_slug_malformed_body_exits_2_with_empty_stdout(self):
        body_file = self._write_body("issue-body.md", "No markers here at all.\n")
        result = run_cli("extract", "--slug", "--fallback-title", "x", str(body_file))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.strip())


class FingerprintCommandTest(unittest.TestCase):
    """AC-18, AC-4, AC-5, AC-9: `fingerprint` hashes the section's inner text."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def _write_body(self, name: str, text: str) -> Path:
        path = Path(self.tmpdir.name) / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_fingerprint_prints_sha256_of_inner_text(self):
        body_file = self._write_body("issue-body.md", ISSUE_BODY_WITH_SECTION)
        result = run_cli("fingerprint", str(body_file))
        self.assertEqual(result.returncode, 0)
        expected_inner = "# Sample Feature\n\nSection body line."
        expected_digest = hashlib.sha256(expected_inner.encode("utf-8")).hexdigest()
        self.assertEqual(result.stdout, expected_digest + "\n")

    def test_fingerprint_same_digest_for_crlf_and_lf_input(self):
        lf_file = self._write_body("issue-body-lf.md", ISSUE_BODY_WITH_SECTION)
        crlf_body = ISSUE_BODY_WITH_SECTION.replace("\n", "\r\n")
        crlf_file = self._write_body("issue-body-crlf.md", crlf_body)
        lf_result = run_cli("fingerprint", str(lf_file))
        crlf_result = run_cli("fingerprint", str(crlf_file))
        self.assertEqual(lf_result.stdout, crlf_result.stdout)

    def test_fingerprint_differs_on_one_character_change_in_inner_text(self):
        original_file = self._write_body("issue-body.md", ISSUE_BODY_WITH_SECTION)
        changed_body = ISSUE_BODY_WITH_SECTION.replace(
            "Section body line.", "Section body Line."
        )
        changed_file = self._write_body("issue-body-changed.md", changed_body)
        original_result = run_cli("fingerprint", str(original_file))
        changed_result = run_cli("fingerprint", str(changed_file))
        self.assertNotEqual(original_result.stdout, changed_result.stdout)

    def test_fingerprint_same_digest_for_full_body_and_section_output(self):
        full_body_file = self._write_body("issue-body.md", ISSUE_BODY_WITH_SECTION)
        section_only_file = self._write_body(
            "section-only.md", EXPECTED_EXTRACTED_SECTION
        )
        full_result = run_cli("fingerprint", str(full_body_file))
        section_result = run_cli("fingerprint", str(section_only_file))
        self.assertEqual(full_result.stdout, section_result.stdout)

    def test_fingerprint_malformed_input_exits_2_with_empty_stdout(self):
        body_file = self._write_body("issue-body.md", "No markers here at all.\n")
        result = run_cli("fingerprint", str(body_file))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.strip())


class SpliceCommandTest(unittest.TestCase):
    """AC-18: `splice` refuses a body with a malformed marker section."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def _write_body(self, name: str, text: str) -> Path:
        path = Path(self.tmpdir.name) / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_splice_refuses_duplicate_start_marker(self):
        body = (
            "<!-- feature-dev:spec:start slug=a -->\n"
            "First.\n"
            "<!-- feature-dev:spec:end -->\n"
            "<!-- feature-dev:spec:start slug=b -->\n"
            "Second.\n"
            "<!-- feature-dev:spec:end -->\n"
        )
        body_file = self._write_body("issue-body.md", body)
        section_file = self._write_body("section.md", EXPECTED_EXTRACTED_SECTION)
        result = run_cli("splice", str(body_file), str(section_file))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("more than one start marker", result.stderr)

    def test_splice_refuses_unterminated_start_marker(self):
        body = "<!-- feature-dev:spec:start slug=sample -->\nNo end marker follows.\n"
        body_file = self._write_body("issue-body.md", body)
        section_file = self._write_body("section.md", EXPECTED_EXTRACTED_SECTION)
        result = run_cli("splice", str(body_file), str(section_file))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("no end marker", result.stderr)

    def test_splice_replaces_section_and_preserves_surrounding_bytes(self):
        """AC-2: bytes before the start marker and after the end marker survive untouched."""
        original = ISSUE_BODY_WITH_SECTION
        start_marker = "<!-- feature-dev:spec:start slug=sample-feature -->"
        end_marker = "<!-- feature-dev:spec:end -->"
        prefix = original[: original.index(start_marker)]
        suffix = original[original.index(end_marker) + len(end_marker) :]
        new_section = (
            "<!-- feature-dev:spec:start slug=other-feature -->\n"
            "# Other Feature\n"
            "\n"
            "Different body line.\n"
            "<!-- feature-dev:spec:end -->\n"
        )
        body_file = self._write_body("issue-body.md", original)
        section_file = self._write_body("section.md", new_section)
        result = run_cli("splice", str(body_file), str(section_file))
        self.assertEqual(result.returncode, 0)
        # The span ends right after "-->", so the section's own trailing
        # newline is dropped and the suffix keeps the original bytes.
        self.assertEqual(result.stdout, prefix + new_section.rstrip("\n") + suffix)

    def test_splice_replaces_is_idempotent(self):
        """Republishing the same section leaves the body byte-identical."""
        body_file = self._write_body("issue-body.md", ISSUE_BODY_WITH_SECTION)
        # Real `section` output ends with a newline.
        section_file = self._write_body("section.md", EXPECTED_EXTRACTED_SECTION + "\n")
        first = run_cli("splice", str(body_file), str(section_file))
        self.assertEqual(first.returncode, 0)
        second_body = self._write_body("issue-body-2.md", first.stdout)
        second = run_cli("splice", str(second_body), str(section_file))
        self.assertEqual(second.returncode, 0)
        self.assertEqual(second.stdout, first.stdout)

    def test_splice_replaces_preserves_bytes_after_end_marker(self):
        """A blank line then a footer after the end marker is kept exactly."""
        body = (
            "intro\n\n"
            "<!-- feature-dev:spec:start slug=x -->\nold\n<!-- feature-dev:spec:end -->"
            "\n\nfooter\n"
        )
        section = "<!-- feature-dev:spec:start slug=x -->\nnew\n<!-- feature-dev:spec:end -->\n"
        body_file = self._write_body("issue-body.md", body)
        section_file = self._write_body("section.md", section)
        result = run_cli("splice", str(body_file), str(section_file))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            result.stdout,
            "intro\n\n"
            "<!-- feature-dev:spec:start slug=x -->\nnew\n<!-- feature-dev:spec:end -->"
            "\n\nfooter\n",
        )

    def test_splice_appends_section_after_normalized_body_with_blank_line(self):
        """AC-1, AC-2: no start marker -> LF-normalized body + blank line + section."""
        body = "No markers here at all.\n"
        section = EXPECTED_EXTRACTED_SECTION + "\n"
        body_file = self._write_body("issue-body.md", body)
        section_file = self._write_body("section.md", section)
        result = run_cli("splice", str(body_file), str(section_file))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "No markers here at all.\n\n" + section)

    def test_splice_appends_normalizes_crlf_body_to_lf(self):
        """AC-1: CRLF line endings in the body are normalized to LF before appending."""
        body = "No markers here at all.\r\n"
        section = EXPECTED_EXTRACTED_SECTION + "\n"
        body_file = self._write_body("issue-body.md", body)
        section_file = self._write_body("section.md", section)
        result = run_cli("splice", str(body_file), str(section_file))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "No markers here at all.\n\n" + section)

    def test_splice_appends_only_section_for_empty_body(self):
        """AC-1: an empty body produces an issue body that is just the section."""
        section = EXPECTED_EXTRACTED_SECTION + "\n"
        body_file = self._write_body("issue-body.md", "")
        section_file = self._write_body("section.md", section)
        result = run_cli("splice", str(body_file), str(section_file))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, section)

    def test_splice_appends_only_section_for_whitespace_only_body(self):
        """AC-1: a whitespace-only body counts as empty; output is just the section."""
        section = EXPECTED_EXTRACTED_SECTION + "\n"
        body_file = self._write_body("issue-body.md", "   \n\n  \n")
        section_file = self._write_body("section.md", section)
        result = run_cli("splice", str(body_file), str(section_file))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, section)

    def test_splice_replaces_round_trip_preserves_fingerprint(self):
        """AC-2, AC-18: splice(section-output) -> extract -> fingerprint == fingerprint(section-output)."""
        spec = self._write_body("SPEC-sample.md", SPEC_WITH_MIDDLE_DECISIONS_LOG)
        section_result = run_cli("section", str(spec))
        section_file = self._write_body("section.md", section_result.stdout)

        body_file = self._write_body("issue-body.md", ISSUE_BODY_WITH_SECTION)
        splice_result = run_cli("splice", str(body_file), str(section_file))
        self.assertEqual(splice_result.returncode, 0)

        spliced_file = self._write_body("spliced-body.md", splice_result.stdout)
        extract_result = run_cli("extract", str(spliced_file))
        extracted_file = self._write_body("extracted.md", extract_result.stdout)

        fingerprint_of_round_trip = run_cli("fingerprint", str(extracted_file))
        fingerprint_of_section = run_cli("fingerprint", str(section_file))
        self.assertEqual(
            fingerprint_of_round_trip.stdout, fingerprint_of_section.stdout
        )


if __name__ == "__main__":
    unittest.main()
