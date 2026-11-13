#!/usr/bin/env python3
"""Deterministic checks for a feature-dev SPEC or PLAN. Standard library only.

Usage:
    lint_artifact.py <SPEC-or-PLAN path> [--json]
    lint_artifact.py --hook            # PostToolUse hook: tool call JSON on stdin

Checks only what a script can settle: sections, frontmatter keys, id
uniqueness, AC <-> BR citations, the plan's step contract, AC coverage, and the
paths in the plan's file tables. Judgment (is a criterion observable, is a rule
in domain language, is a Verify really a command, is a code claim true) stays
with spec-plan-validator.

Levels map onto spec-plan-validator's severities: ``error`` is Blocking,
``warn`` is Should Address, ``note`` is Nice to Have. The validator runs this
script and reports its findings instead of re-checking them.

Exit codes (CLI): 0 no errors (warnings and notes may be printed), 1 at least
one error, 2 usage error or unreadable file. ``--json`` prints
``{"findings": [{level, section, message}], "ac_coverage": {covered, total,
uncovered, excluded} | null}``. ``--hook`` always exits 0 and prints the errors
and warnings (not notes) as ``hookSpecificOutput.additionalContext`` JSON, or
nothing when the edited file is not a feature artifact or has none.

The section definitions are in
``skills/spec-driven-development/references/spec-template.md`` (spec) and
``references/plan-generation.md`` (plan).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from features import FEATURE_FILE, Malformed, parse_frontmatter  # noqa: E402

ERROR = "error"  # spec-plan-validator: Blocking
WARN = "warn"  # Should Address
NOTE = "note"  # Nice to Have

MAX_STEPS = 25
BASELINE_RESULTS = ("pass", "expected-red", "pre-existing-fail", "hollow", "not-run")
STEP_KINDS = ("behavior", "characterization")

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")
AC_ITEM = re.compile(r"^\s*[-*]\s+\*\*AC-(\d+)\*\*(.*)$")
BR_ITEM = re.compile(r"^\s*[-*]\s+\*\*BR-(\d+)\*\*")
BR_NONE = re.compile(r"^\s*(?:[-*]\s+)?None\b", re.IGNORECASE)
BULLET = re.compile(r"^\s*[-*]\s+\S")
BR_REF = re.compile(r"\bBR-(\d+)\b")
AC_REF = re.compile(r"\bAC-(\d+)\b")
STEP_HEAD = re.compile(r"^(\d+)\.\s+\*\*(.+?)\*\*")
STEP_FIELD = re.compile(
    r"^\s+[-*]\s+(Kind|Accept|Pins|Covers|Impl|Test|Verify|Depends on|Rationale):\s*(.*)$"
)
WRITTEN_BY = re.compile(r"\(written by step (\d+)\)")
SOURCE_SPEC = re.compile(r"^\s*(?:[-*]\s*)?Source spec:\s*`?([^`\s]+)`?\s*$", re.MULTILINE)
TABLE_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
TABLE_RULE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")

SPEC_KEYS = ("feature", "slug", "date", "branch")
QA_GROUPS = ("Happy path", "Edge cases", "Empty states", "Error states")


class Finding(NamedTuple):
    level: str
    section: str
    message: str

    def line(self) -> str:
        return f"{self.level}: [{self.section}] {self.message}"


class Section(NamedTuple):
    level: int
    title: str
    lines: list[str]


# --- markdown ---------------------------------------------------------------


def sections(text: str) -> list[Section]:
    """Every heading with the lines under it, up to the next heading of any level.

    Headings inside fenced code blocks are ignored.
    """
    result: list[Section] = []
    current: Section | None = None
    in_fence = False
    for raw in text.splitlines():
        if FENCE.match(raw):
            in_fence = not in_fence
        match = None if in_fence else HEADING.match(raw)
        if match:
            current = Section(len(match.group(1)), match.group(2).strip(), [])
            result.append(current)
        elif current is not None:
            current.lines.append(raw)
    return result


def _norm(title: str) -> str:
    title = re.sub(r"[`*_]", "", title)
    title = re.split(r"\s+[—–-]\s+|:", title, maxsplit=1)[0]
    return title.strip().lower()


def find(secs: list[Section], title: str) -> int | None:
    want = title.lower()
    for i, sec in enumerate(secs):
        if _norm(sec.title) == want:
            return i
    return None


def body(secs: list[Section], index: int) -> list[str]:
    """Lines of section ``index`` including its deeper subsections."""
    level = secs[index].level
    lines = list(secs[index].lines)
    for sec in secs[index + 1:]:
        if sec.level <= level:
            break
        lines.append("#" * sec.level + " " + sec.title)
        lines.extend(sec.lines)
    return lines


def _strip_fences(lines: list[str]) -> list[str]:
    out, in_fence = [], False
    for line in lines:
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence and not line.lstrip().startswith("<!--"):
            out.append(line)
    return out


def table_rows(lines: list[str]) -> list[list[str]]:
    """Data rows of the first markdown table in ``lines`` (header and rule skipped)."""
    rows: list[list[str]] = []
    seen_rule = False
    for line in lines:
        if not TABLE_ROW.match(line):
            if seen_rule:
                break
            continue
        if TABLE_RULE.match(line):
            seen_rule = True
            continue
        if seen_rule:
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def _ids(pattern: re.Pattern, text: str) -> list[int]:
    return [int(n) for n in pattern.findall(text)]


def _dupes(numbers: list[int]) -> list[int]:
    seen, dupes = set(), []
    for n in numbers:
        if n in seen and n not in dupes:
            dupes.append(n)
        seen.add(n)
    return dupes


# --- spec -------------------------------------------------------------------


class SpecIds(NamedTuple):
    acs: dict[int, list[int]]  # AC id -> BR ids it cites
    brs: list[int]


def spec_ids(text: str) -> SpecIds:
    secs = sections(text)
    acs: dict[int, list[int]] = {}
    i = find(secs, "Acceptance Criteria")
    if i is not None:
        for line in _strip_fences(body(secs, i)):
            m = AC_ITEM.match(line)
            if m:
                cited = re.match(r"\s*\(([^)]*)\)", m.group(2))
                acs.setdefault(int(m.group(1)), _ids(BR_REF, cited.group(1)) if cited else [])
    brs: list[int] = []
    i = find(secs, "Business Rules")
    if i is not None:
        for line in _strip_fences(body(secs, i)):
            m = BR_ITEM.match(line)
            if m:
                brs.append(int(m.group(1)))
    return SpecIds(acs, brs)


def lint_spec(text: str) -> list[Finding]:
    out: list[Finding] = []
    try:
        front, repos = parse_frontmatter(text)
    except Malformed as exc:
        return [Finding(ERROR, "frontmatter", str(exc))]
    if front.get("type") != "specification":
        out.append(Finding(ERROR, "frontmatter", f"type is {front.get('type')!r}, expected 'specification'"))
    missing = [k for k in SPEC_KEYS if not front.get(k)]
    if missing:
        out.append(Finding(ERROR, "frontmatter", f"missing {', '.join(missing)}"))

    secs = sections(text)
    for title, level in (("Objective", ERROR), ("Acceptance Criteria", ERROR),
                         ("Non-Goals", NOTE), ("QA Checklist", WARN), ("Boundaries", WARN)):
        if find(secs, title) is None:
            out.append(Finding(level, title, "section is missing"))

    # Acceptance Criteria
    ac_numbers: list[int] = []
    cites: dict[int, list[int]] = {}
    i = find(secs, "Acceptance Criteria")
    if i is not None:
        unnumbered = 0
        for line in _strip_fences(body(secs, i)):
            m = AC_ITEM.match(line)
            if m:
                n = int(m.group(1))
                ac_numbers.append(n)
                cited = re.match(r"\s*\(([^)]*)\)", m.group(2))
                cites.setdefault(n, _ids(BR_REF, cited.group(1)) if cited else [])
            elif BULLET.match(line) and not line.startswith((" ", "\t")):
                unnumbered += 1
        if not ac_numbers:
            out.append(Finding(NOTE, "Acceptance Criteria",
                               "no criterion carries an id (`- **AC-1** — ...`); plans and /feature-dev:tdd cite them by id"))
        elif unnumbered:
            out.append(Finding(NOTE, "Acceptance Criteria", f"{unnumbered} top-level item(s) without an `**AC-n**` id"))
        for n in _dupes(ac_numbers):
            out.append(Finding(WARN, "Acceptance Criteria", f"AC-{n} is defined more than once (plans cite it; the citation is ambiguous)"))

    # Business Rules
    i = find(secs, "Business Rules")
    br_numbers: list[int] = []
    if i is None:
        out.append(Finding(NOTE, "Business Rules",
                           "section is missing (specs before feature-dev 3.0.0 lack it); write the rules or `None — <why>`"))
    else:
        lines = _strip_fences(body(secs, i))
        br_numbers = [int(m.group(1)) for m in map(BR_ITEM.match, lines) if m]
        if not br_numbers and not any(BR_NONE.match(line) for line in lines if line.strip()):
            out.append(Finding(WARN, "Business Rules",
                               "no `**BR-n**` rule and no `None — <why>` line"))
        for n in _dupes(br_numbers):
            out.append(Finding(WARN, "Business Rules", f"BR-{n} is defined more than once"))
    defined = set(br_numbers)
    cited_all = {b for refs in cites.values() for b in refs}
    for n in sorted(defined - cited_all):
        out.append(Finding(WARN, "Business Rules",
                           f"BR-{n} is cited by no acceptance criterion (cite it as `**AC-n** (BR-{n}) — ...`)"))
    for ac, refs in sorted(cites.items()):
        for b in refs:
            if b not in defined:
                out.append(Finding(WARN, "Acceptance Criteria", f"AC-{ac} cites BR-{b}, which the spec does not define"))

    # QA Checklist groups
    i = find(secs, "QA Checklist")
    if i is not None:
        sub = set()
        for s in secs[i + 1:]:
            if s.level <= secs[i].level:
                break
            sub.add(_norm(s.title))
        absent = [g for g in QA_GROUPS if g.lower() not in sub]
        if absent:
            out.append(Finding(WARN, "QA Checklist", f"missing group(s): {', '.join(absent)}"))

    if len(repos) >= 2:
        if find(secs, "Cross-Repo Contracts") is None:
            out.append(Finding(ERROR, "Cross-Repo Contracts", f"frontmatter lists {len(repos)} repos but the section is missing"))
        if find(secs, "Decisions Log") is None:
            out.append(Finding(WARN, "Decisions Log", "multi-repo spec without a `## Decisions Log` section"))
    return out


# --- plan -------------------------------------------------------------------


class Step(NamedTuple):
    number: int
    name: str
    fields: dict[str, str]


def plan_steps(lines: list[str]) -> list[Step]:
    steps: list[Step] = []
    for line in _strip_fences(lines):
        head = STEP_HEAD.match(line)
        if head:
            steps.append(Step(int(head.group(1)), head.group(2).strip(), {}))
            continue
        field = STEP_FIELD.match(line)
        if field and steps:
            steps[-1].fields.setdefault(field.group(1), field.group(2).strip())
    return steps


FILE_NAME = re.compile(
    r"^[\w.-]+\.(py|pyi|ts|tsx|js|jsx|mjs|vue|svelte|go|rs|rb|java|kt|sql|sh|md|json|ya?ml|toml|ini|cfg|html|css|scss|txt)$"
)


def _expand_braces(token: str) -> list[str]:
    """``a/{b,c}.py`` -> ``a/b.py``, ``a/c.py`` (nested and repeated groups too)."""
    m = re.search(r"\{([^{}]*)\}", token)
    if not m:
        return [token]
    return [p for alt in m.group(1).split(",")
            for p in _expand_braces(token[:m.start()] + alt + token[m.end():])]


def _split_top(value: str) -> list[str]:
    """Split on commas that are not inside ``{...}``."""
    parts, depth, cur = [], 0, ""
    for ch in value:
        depth += (ch == "{") - (ch == "}")
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts


def cell_paths(value: str) -> list[str]:
    """The file paths in an ``Impl:``/``Test:`` value or a table cell.

    Takes backticked items when there are any, else comma-separated items; keeps
    the first word of each, expands ``{a,b}`` groups, drops a pytest ``::node``
    suffix, and keeps only what looks like a path (has a ``/`` or a file
    extension). ``n/a``, ``(none)`` and prose give an empty list.
    """
    value = WRITTEN_BY.sub("", value).strip()
    if not value or _is_na(value):
        return []
    ticks = re.findall(r"`([^`]+)`", value)
    items = ticks if ticks else _split_top(value)
    paths: list[str] = []
    directory = ""
    for item in items:
        words = item.strip().split()
        if not words:
            continue
        for path in _expand_braces(words[0].split("::")[0]):
            if path.startswith(("(", "[")) or path.lower().startswith("n/a"):
                continue
            if "/" in path:
                directory = path.rsplit("/", 1)[0] + "/" if not path.endswith("/") else path
                paths.append(path)
            elif FILE_NAME.match(path):
                # `a/b/x.py, y.py` — a bare name after a path shares its directory
                paths.append(directory + path)
    return paths


def _in_tables(path: str, table_paths: set[str]) -> bool:
    return path in table_paths or any(t.endswith("/") and path.startswith(t) for t in table_paths)


def _dependency_closure(steps: list["Step"]) -> dict[int, set[int]]:
    direct = {s.number: {int(x) for x in re.findall(r"\d+", s.fields.get("Depends on", ""))} for s in steps}
    closure: dict[int, set[int]] = {}

    def visit(n: int, seen: frozenset) -> set[int]:
        if n in closure:
            return closure[n]
        reach: set[int] = set()
        for d in direct.get(n, ()):
            if d not in seen:
                reach |= {d} | visit(d, seen | {d})
        closure[n] = reach
        return reach

    for n in direct:
        visit(n, frozenset({n}))
    return closure


def _is_na(value: str) -> bool:
    return value.strip().strip("`").lower().startswith("n/a")


def _source_spec(plan_path: Path, text: str, root: Path | None) -> Path | None:
    m = SOURCE_SPEC.search(text)
    if m and root is not None:
        candidate = (root / m.group(1)).resolve()
        if candidate.is_file():
            return candidate
    specs = sorted(plan_path.parent.glob("SPEC-*.md"))
    return specs[0] if specs else None


def _completed(plan_path: Path) -> bool:
    try:
        data = json.loads((plan_path.parent / FEATURE_FILE).read_text())
    except (OSError, ValueError):
        return False
    plan = data.get("plan") if isinstance(data, dict) else None
    return bool(isinstance(plan, dict) and plan.get("completed"))


def lint_plan(text: str, plan_path: Path | None = None, root: Path | None = None) -> list[Finding]:
    out: list[Finding] = []
    try:
        front, _ = parse_frontmatter(text)
    except Malformed as exc:
        return [Finding(ERROR, "frontmatter", str(exc))]
    if front.get("type") != "implementation-plan":
        out.append(Finding(ERROR, "frontmatter", f"type is {front.get('type')!r}, expected 'implementation-plan'"))
    missing = [k for k in SPEC_KEYS if not front.get(k)]
    if missing:
        out.append(Finding(ERROR, "frontmatter", f"missing {', '.join(missing)}"))

    secs = sections(text)
    for title, level in (("Files to Modify", ERROR), ("Implementation Order", ERROR),
                         ("Summary", WARN), ("Exploration Findings", WARN), ("Baseline", WARN),
                         ("Key Decisions", WARN), ("Risks", WARN), ("Estimated Test Cases", WARN),
                         ("Files to Create", NOTE), ("Parallelization Hints", NOTE)):
        if find(secs, title) is None:
            out.append(Finding(level, title, "section is missing"))
    i = find(secs, "Risks")
    if i is not None and not any(line.strip() for line in _strip_fences(body(secs, i))):
        out.append(Finding(WARN, "Risks", "section is empty"))

    # Source spec
    m = SOURCE_SPEC.search(text)
    if m and root is not None and not (root / m.group(1)).is_file():
        out.append(Finding(ERROR, "Source spec", f"`{m.group(1)}` does not exist"))
    elif plan_path is not None and not m and not list(plan_path.parent.glob("SPEC-*.md")):
        out.append(Finding(WARN, "Source spec", "no SPEC in the feature folder and no `Source spec:` line (plan-only feature)"))

    # Baseline values
    gating: dict[int, str] = {}  # step -> the Baseline row that leaves its Verify proving nothing
    i = find(secs, "Baseline")
    if i is not None:
        for row in table_rows(body(secs, i)):
            if len(row) >= 3:
                result = row[2].strip("` ").lower()
                if result and not result.startswith(BASELINE_RESULTS):
                    out.append(Finding(WARN, "Baseline",
                                       f"result {row[2]!r} for {row[0]} is not one of {', '.join(BASELINE_RESULTS)}"))
                detail = row[3].strip().lower() if len(row) > 3 else ""
                blocks = result.startswith("hollow") or (result.startswith("not-run") and detail.startswith("missing"))
                if blocks and "accepted by user" not in detail:
                    for n in _ids(re.compile(r"\b(\d+)\b"), row[1]):
                        gating[n] = f"{row[0]} is {result}" + (f" ({row[3].strip()})" if detail else "")

    # File tables
    table_paths: set[str] = set()
    for title in ("Files to Modify", "Files to Create"):
        i = find(secs, title)
        if i is None:
            continue
        for row in table_rows(body(secs, i)):
            for path in cell_paths(row[0]) if row else []:
                table_paths.add(path)
                if root is None:
                    continue
                parts = Path(path).parts
                if parts[0] == ".." and (len(parts) < 2 or not (root / ".." / parts[1]).is_dir()):
                    out.append(Finding(NOTE, title, f"`{path}` is in a sibling repo that is not here; unchecked"))
                    continue
                exists = (root / path).exists()
                if title == "Files to Modify" and not exists:
                    out.append(Finding(ERROR, title, f"`{path}` does not exist"))
                if title == "Files to Create" and exists and not (plan_path and _completed(plan_path)):
                    out.append(Finding(WARN, title, f"`{path}` already exists"))

    # Steps
    i = find(secs, "Implementation Order")
    steps = plan_steps(body(secs, i)) if i is not None else []
    if i is not None and not steps:
        out.append(Finding(ERROR, "Implementation Order", "no numbered `1. **Step name**` items"))
    if len(steps) > MAX_STEPS:
        out.append(Finding(WARN, "Implementation Order",
                           f"{len(steps)} steps (limit {MAX_STEPS}): fold pin-only steps into `Pins:` and structure-only steps into `Kind: characterization`"))
    for n in _dupes([s.number for s in steps]):
        out.append(Finding(ERROR, "Implementation Order", f"step {n} is numbered more than once"))

    depends = _dependency_closure(steps)
    test_writer: dict[str, int] = {}  # test path -> first step that writes it
    for step in steps:
        where = f"step {step.number}"
        f = step.fields
        for key in ("Accept", "Verify", "Impl", "Test"):
            if not f.get(key):
                out.append(Finding(ERROR, "Implementation Order", f"{where} has no `{key}:`"))
        for key in ("Depends on", "Rationale"):
            if key not in f:
                out.append(Finding(WARN, "Implementation Order", f"{where} has no `{key}:`"))
        kind = f.get("Kind", "").strip("` ").lower()
        if kind and kind not in STEP_KINDS:
            out.append(Finding(WARN, "Implementation Order", f"{where}: Kind {f['Kind']!r} is not behavior or characterization"))
        test = f.get("Test", "")
        written_by = WRITTEN_BY.search(test)
        own_test = bool(test) and not _is_na(test) and not written_by
        if f.get("Pins") and not own_test:
            out.append(Finding(WARN, "Implementation Order",
                               f"{where} has `Pins:` but does not create its own test file (Test is n/a or written by another step)"))
        if kind == "characterization" and not own_test:
            out.append(Finding(WARN, "Implementation Order",
                               f"{where} is `Kind: characterization` but does not create its own test file"))
        for path in cell_paths(test) if own_test else []:
            if path in test_writer:
                out.append(Finding(WARN, "Implementation Order",
                                   f"{where}: Test `{path}` is created by step {test_writer[path]}; mark it `(written by step {test_writer[path]})`"))
            else:
                test_writer[path] = step.number
        if step.number in gating:
            out.append(Finding(WARN, "Implementation Order",
                               f"{where}: its Verify proves nothing on HEAD — Baseline: {gating[step.number]}; fix the environment, replace the Verify, or mark the row `accepted by user`"))
        if written_by:
            dep = int(written_by.group(1))
            if dep not in depends.get(step.number, set()):
                out.append(Finding(WARN, "Implementation Order",
                                   f"{where}: Test is written by step {dep} but step {dep} is not among its dependencies"))
        for key in ("Impl", "Test"):
            for path in cell_paths(f.get(key, "")):
                if table_paths and not _in_tables(path, table_paths):
                    out.append(Finding(WARN, "Implementation Order",
                                       f"{where}: {key} path `{path}` is not in Files to Modify / Files to Create"))

    findings, _ = ac_coverage(text, steps, secs, plan_path, root)
    out.extend(findings)
    return out


class Coverage(NamedTuple):
    covered: int
    total: int
    uncovered: list[str]
    excluded: list[str]


def ac_coverage(text: str, steps: list[Step], secs: list[Section], plan_path: Path | None,
                root: Path | None) -> tuple[list[Finding], Coverage | None]:
    """AC coverage of the plan against its spec; None when the spec numbers no ACs."""
    spec_path = _source_spec(plan_path, text, root) if plan_path else None
    if not spec_path:
        return [], None
    try:
        acs = spec_ids(spec_path.read_text()).acs
    except OSError:
        return [], None
    if not acs:
        return [], None
    out: list[Finding] = []
    risks_i = find(secs, "Risks")
    excluded = set(_ids(AC_REF, "\n".join(body(secs, risks_i)))) & set(acs) if risks_i is not None else set()
    covered: set[int] = set()
    missing_covers = []
    for step in steps:
        refs = _ids(AC_REF, step.fields.get("Covers", ""))
        covered.update(refs)
        for n in refs:
            if n not in acs:
                out.append(Finding(WARN, "Implementation Order",
                                   f"step {step.number} covers AC-{n}, which the spec does not define"))
        test = step.fields.get("Test", "")
        if test and not _is_na(test) and not refs:
            missing_covers.append(step.number)
    if missing_covers:
        out.append(Finding(WARN, "Implementation Order",
                           "behavior step(s) without `Covers:`: " + ", ".join(map(str, missing_covers))))
    uncovered = sorted(set(acs) - covered)
    for n in uncovered:
        if n not in excluded:
            out.append(Finding(WARN, "Implementation Order",
                               f"AC-{n} is covered by no step and not excluded by id in Risks"))
    summary = Coverage(len(set(acs) & covered), len(acs),
                       [f"AC-{n}" for n in uncovered if n not in excluded],
                       [f"AC-{n}" for n in uncovered if n in excluded])
    return out, summary


# --- entry points -----------------------------------------------------------


def store_root(path: Path) -> Path | None:
    """Repo root for ``<root>/.feature-dev/features/<slug>/<file>``, else None."""
    folder = path.parent
    if folder.parent.name == "features" and folder.parent.parent.name == ".feature-dev":
        return folder.parent.parent.parent
    return None


def artifact_kind(path: Path) -> str | None:
    if path.suffix != ".md":
        return None
    if path.name.startswith("SPEC-"):
        return "spec"
    if path.name.startswith("PLAN-"):
        return "plan"
    return None


def lint_path(path: Path) -> list[Finding]:
    kind = artifact_kind(path)
    if kind is None:
        raise ValueError(f"{path.name} is not a SPEC-*.md or PLAN-*.md")
    text = path.read_text()
    if kind == "spec":
        return lint_spec(text)
    return lint_plan(text, path.resolve(), store_root(path.resolve()))


def coverage_of(path: Path) -> Coverage | None:
    """The plan's AC coverage summary (None for a spec, or a spec with no AC ids)."""
    if artifact_kind(path) != "plan":
        return None
    text = path.read_text()
    secs = sections(text)
    i = find(secs, "Implementation Order")
    steps = plan_steps(body(secs, i)) if i is not None else []
    resolved = path.resolve()
    return ac_coverage(text, steps, secs, resolved, store_root(resolved))[1]


def _order(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: 0 if f.level == ERROR else 1)


def hook(stdin: str) -> str:
    """The PostToolUse hook's stdout for one tool call (empty when nothing to say)."""
    try:
        payload = json.loads(stdin)
    except ValueError:
        return ""
    tool_input = payload.get("tool_input") if isinstance(payload, dict) else None
    file_path = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not isinstance(file_path, str):
        return ""
    path = Path(file_path)
    if artifact_kind(path) is None or store_root(path) is None or not path.is_file():
        return ""
    try:
        findings = [f for f in _order(lint_path(path)) if f.level != NOTE]
    except Exception as exc:  # the hook must never break an edit; say why it said nothing
        context = f"[feature-dev lint] could not lint {path.name}: {type(exc).__name__}: {exc}"
    else:
        if not findings:
            return ""
        errors = sum(f.level == ERROR for f in findings)
        context = "\n".join(
            [f"[feature-dev lint] {path.name}: {errors} error(s), {len(findings) - errors} warning(s). "
             "Fix them before showing the artifact to the user; a warning you leave on purpose, say why."]
            + [f.line() for f in findings]
        )
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": context}})


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--hook"]:
        out = hook(sys.stdin.read())
        if out:
            print(out)
        return 0
    as_json = "--json" in args
    args = [a for a in args if a != "--json"]
    if len(args) != 1:
        print("usage: lint_artifact.py <SPEC-or-PLAN path> [--json] | --hook", file=sys.stderr)
        return 2
    path = Path(args[0])
    try:
        findings = _order(lint_path(path))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if as_json:
        coverage = coverage_of(path)
        print(json.dumps({"findings": [f._asdict() for f in findings],
                          "ac_coverage": coverage._asdict() if coverage else None}, indent=2))
    else:
        for f in findings:
            print(f.line())
    return 1 if any(f.level == ERROR for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
