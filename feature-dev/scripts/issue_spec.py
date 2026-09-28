#!/usr/bin/env python3
"""Helpers for turning a feature-dev SPEC-*.md into a GitHub issue body.

Every subcommand's marker section is delimited by
``<!-- feature-dev:spec:start slug=... -->`` / ``<!-- feature-dev:spec:end -->``
comments, so a spec's section can live inside a larger, human-edited issue body
without disturbing the rest of it.

Python 3 standard library only.

Usage:
    issue_spec.py section <artifact>
    issue_spec.py extract <file|-> [--slug --fallback-title TITLE]
    issue_spec.py fingerprint <file|->
    issue_spec.py splice <body-file|-> <section-file>

``section`` reads ``<artifact>`` from disk, strips its frontmatter and
``## Decisions Log``, and prints the result wrapped in start/end markers whose
slug comes from the frontmatter (or, if empty, from a sanitized ``feature``
title, or "spec" as a last resort).

``extract`` reads ``<file>`` (or stdin, with ``-``) and prints its single
marker section, markers included. With ``--slug`` it prints the sanitized slug
from the start marker instead (using ``--fallback-title`` if the marker's slug
sanitizes to nothing).

``fingerprint`` reads ``<file>`` (or stdin), extracts its marker section, and
prints the sha256 hex digest of the section's inner text (markers excluded,
line endings normalized).

``splice`` reads ``<body-file>`` (or stdin, with ``-``) and ``<section-file>``,
and prints ``<body-file>`` with its marker section replaced by
``<section-file>``'s content. When ``<body-file>`` has no start marker, the
section is appended instead (after a blank line, unless the body is empty).

Exit codes: 0 on success. 2 (usage error) when a subcommand's arguments are
wrong, or when a body passed to ``extract``/``fingerprint``/``splice`` has a
malformed marker section — more than one start marker, or a start marker with
no end marker. A missing start marker is not an error for ``splice`` (it
appends instead) but is one for ``extract``/``fingerprint``.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

EXIT_USAGE = 2

SECTION_START = "<!-- feature-dev:spec:start slug={slug} -->"
SECTION_END = "<!-- feature-dev:spec:end -->"

_FRONTMATTER_KEY = re.compile(r"^([A-Za-z_][\w-]*):\s*(.*?)\s*(?:#.*)?$")
# Ends at the next level-2 heading that is not a `## Decision — <slug>` entry
# heading, so a log rebuilt from decision comments is stripped whole.
_DECISIONS_LOG = re.compile(r"(?ms)^## Decisions Log\s*\n.*?(?=^## (?!Decision — )|\Z)")
_SECTION_START_RE = re.compile(r"<!-- feature-dev:spec:start slug=[^ ]* -->")
_SECTION_START_SLUG_RE = re.compile(r"<!-- feature-dev:spec:start slug=([^ ]*) -->")


def _clean_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")


def sanitize_slug(raw: str, fallback_title: str) -> str:
    """Sanitize ``raw`` with review_server.artifact_slug's rule.

    Runs of characters outside ``[A-Za-z0-9._-]`` become a single ``-``, then
    leading/trailing ``-``/``.`` are stripped. If that yields nothing, the same
    rule is applied to ``fallback_title``; if that is also empty, "spec" wins.
    """
    slug = _clean_slug(raw)
    if slug:
        return slug
    slug = _clean_slug(fallback_title)
    if slug:
        return slug
    return "spec"


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return the frontmatter dict and the remaining body of a spec file."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, text
    front: dict[str, str] = {}
    body_start = len(lines)
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body_start = i + 1
            break
        match = _FRONTMATTER_KEY.match(line)
        if match:
            front[match.group(1)] = match.group(2).strip().strip("'\"")
    return front, "".join(lines[body_start:])


def _strip_decisions_log(body: str) -> str:
    """Drop the ``## Decisions Log`` heading through the next ``## `` heading or EOF."""
    return _DECISIONS_LOG.sub("", body)


def _read_source(source: str) -> str:
    """Read ``source`` as a path, or from stdin when it is ``-``."""
    if source == "-":
        return sys.stdin.read()
    return Path(source).read_text(encoding="utf-8")


class SectionError(ValueError):
    """Raised when a body does not have exactly one well-formed marker section.

    ``kind`` distinguishes the malformation so callers can react differently
    (e.g. a future ``splice`` step appends on ``"no_start"`` but refuses on
    ``"duplicate_start"``/``"no_end"``).
    """

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


def _find_section_span(body: str) -> tuple[int, int]:
    """Return the ``(start, end)`` indices of the single marker section in ``body``.

    ``end`` is exclusive and lands right after the end marker. Raises
    SectionError if there is no start marker, more than one, or a start
    marker with no following end marker.
    """
    starts = list(_SECTION_START_RE.finditer(body))
    if not starts:
        raise SectionError("no_start", "no start marker found")
    if len(starts) > 1:
        raise SectionError("duplicate_start", "more than one start marker found")
    start_match = starts[0]
    end_index = body.find(SECTION_END, start_match.end())
    if end_index == -1:
        raise SectionError("no_end", "start marker found but no end marker")
    return start_match.start(), end_index + len(SECTION_END)


def _extract_section(body: str) -> str:
    """Return the single marker section of ``body``, markers included.

    Raises SectionError if there is no start marker, more than one, or a
    start marker with no following end marker.
    """
    start, end = _find_section_span(body)
    return body[start:end]


def cmd_section(args: argparse.Namespace) -> int:
    text = Path(args.artifact).read_text(encoding="utf-8")
    front, body = _split_frontmatter(text)
    body = _strip_decisions_log(body).strip("\n")
    slug = sanitize_slug(front.get("slug", ""), front.get("feature", ""))
    print(SECTION_START.format(slug=slug))
    print(body)
    print(SECTION_END)
    return 0


def _extract_or_report(text: str) -> str | None:
    """Return the marker section of ``text``, or ``None`` after reporting the error.

    Shared by every subcommand that needs an extracted section: on
    SectionError, prints the message to stderr and returns None so the
    caller can exit with EXIT_USAGE.
    """
    try:
        return _extract_section(text)
    except SectionError as exc:
        print(str(exc), file=sys.stderr)
        return None


def cmd_extract(args: argparse.Namespace) -> int:
    body = _read_source(args.artifact)
    section = _extract_or_report(body)
    if section is None:
        return EXIT_USAGE
    if args.slug:
        # _extract_section already guarantees `section` starts with a marker
        # matching this pattern, so the match always succeeds.
        raw_slug = _SECTION_START_SLUG_RE.match(section).group(1)
        print(sanitize_slug(raw_slug, args.fallback_title))
        return 0
    print(section)
    return 0


def _inner_text(section: str) -> str:
    """Return ``section``'s content with the start/end marker lines removed."""
    lines = section.split("\n")
    return "\n".join(lines[1:-1]).strip()


def cmd_fingerprint(args: argparse.Namespace) -> int:
    text = _read_source(args.artifact).replace("\r\n", "\n").replace("\r", "\n")
    section = _extract_or_report(text)
    if section is None:
        return EXIT_USAGE
    digest = hashlib.sha256(_inner_text(section).encode("utf-8")).hexdigest()
    print(digest)
    return 0


def cmd_splice(args: argparse.Namespace) -> int:
    body = _read_source(args.body)
    try:
        start, end = _find_section_span(body)
    except SectionError as exc:
        if exc.kind in ("duplicate_start", "no_end"):
            print(str(exc), file=sys.stderr)
            return EXIT_USAGE
        # kind == "no_start": append the section instead of replacing.
        section_content = _read_source(args.section)
        normalized_body = body.replace("\r\n", "\n").replace("\r", "\n")
        if not normalized_body.strip():
            # Empty (or whitespace-only) body: the issue body is just the section.
            sys.stdout.write(section_content)
        else:
            # Non-empty body: strip its trailing newlines, then one blank
            # line, then the section — regardless of how many trailing
            # newlines the original body had.
            sys.stdout.write(normalized_body.rstrip("\n") + "\n\n" + section_content)
        return 0
    # The span ends right after the end marker's "-->", so the newline that
    # followed it is still in body[end:]. Drop the section's own trailing
    # newlines so republishing never grows the body.
    section_content = _read_source(args.section).rstrip("\n")
    sys.stdout.write(body[:start] + section_content + body[end:])
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)

    section_parser = sub.add_parser("section")
    section_parser.add_argument("artifact")
    section_parser.set_defaults(func=cmd_section)

    extract_parser = sub.add_parser("extract")
    extract_parser.add_argument("artifact")
    extract_parser.add_argument("--slug", action="store_true")
    extract_parser.add_argument("--fallback-title", default="")
    extract_parser.set_defaults(func=cmd_extract)

    fingerprint_parser = sub.add_parser("fingerprint")
    fingerprint_parser.add_argument("artifact")
    fingerprint_parser.set_defaults(func=cmd_fingerprint)

    splice_parser = sub.add_parser("splice")
    splice_parser.add_argument("body")
    splice_parser.add_argument("section")
    splice_parser.set_defaults(func=cmd_splice)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
