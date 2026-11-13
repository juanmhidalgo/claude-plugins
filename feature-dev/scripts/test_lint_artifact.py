#!/usr/bin/env python3
"""Tests for lint_artifact.py. Standard library only.

Run from anywhere:  python3 feature-dev/scripts/test_lint_artifact.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("lint_artifact.py")
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPT.parent))
import lint_artifact as lint  # noqa: E402

SPEC = """---
type: specification
feature: Task due dates
slug: task-due-dates
date: 2026-11-13
branch: master
---

# Task due dates

## Objective
Users see which open tasks are late.

## Non-Goals
- Reminders: out of scope.

## Business Rules
- **BR-1** — A task is overdue when it is open and its due date is before today.
- **BR-2** — A done task is never overdue.

## Acceptance Criteria
- **AC-1** (BR-1, BR-2) — Given an open and a done task due yesterday, when the user lists
  overdue tasks, then only the open one appears.
- **AC-2** — An invalid due date is rejected with a message naming the field.

## QA Checklist
### Happy path
- [ ] overdue list
### Edge cases
- [ ] due today
### Empty states
- [ ] no overdue tasks
### Error states
- [ ] invalid date

## Boundaries
- Never: change `status` values — other apps read them.
"""

PLAN = """---
type: implementation-plan
feature: Task due dates
slug: task-due-dates
date: 2026-11-13
branch: master
---

## Implementation Plan: Task due dates

### Summary
Adds due dates.

### Exploration Findings
#### Backend
`app/tasks.py` holds the model.

### Baseline
| Command | Steps | Result on HEAD | Detail |
|---|---|---|---|
| `pytest tests/test_due.py` | 1, 2 | expected-red | step 1 creates it |

### Files to Modify
| File | Change | Layer |
|------|--------|-------|
| app/tasks.py | add due date | backend |

### Files to Create
| File | Purpose | Layer |
|------|---------|-------|
| tests/test_due.py | tests | test |

### Implementation Order

1. **Store a due date**
   - Accept: an invalid date is rejected
   - Covers: AC-2
   - Impl: app/tasks.py
   - Test: tests/test_due.py
   - Verify: `pytest tests/test_due.py`
   - Depends on: none
   - Rationale: first

2. **List overdue tasks**
   - Accept: only open tasks due before today are listed
   - Covers: AC-1
   - Impl: `app/tasks.py`
   - Test: `tests/test_due.py` (written by step 1)
   - Verify: `pytest tests/test_due.py::test_overdue`
   - Depends on: 1
   - Rationale: needs the field

### Key Decisions
| Decision | Options | Recommendation | Rationale |
|---|---|---|---|
| x | a, b | a | y |

### Risks
- none worth naming

### Parallelization Hints
- none

### Estimated Test Cases
- 4
"""


def messages(findings) -> list[str]:
    return [f.line() for f in findings]


def has(findings, level: str, fragment: str) -> bool:
    return any(f.level == level and fragment in f.message for f in findings)


class SpecTest(unittest.TestCase):
    def test_clean_spec_has_no_findings(self):
        self.assertEqual(messages(lint.lint_spec(SPEC)), [])

    def test_missing_objective_is_an_error(self):
        findings = lint.lint_spec(SPEC.replace("## Objective", "## Problem"))
        self.assertTrue(any(f.level == lint.ERROR and f.section == "Objective" for f in findings))

    def test_bad_frontmatter(self):
        findings = lint.lint_spec(SPEC.replace("type: specification", "type: plan").replace("slug: task-due-dates\n", ""))
        self.assertTrue(has(findings, lint.ERROR, "expected 'specification'"))
        self.assertTrue(has(findings, lint.ERROR, "missing slug"))

    def test_no_frontmatter(self):
        findings = lint.lint_spec("# just a title\n")
        self.assertEqual([f.section for f in findings], ["frontmatter"])

    def test_duplicate_ac_id_is_an_error(self):
        text = SPEC.replace("- **AC-2** —", "- **AC-1** —")
        self.assertTrue(has(lint.lint_spec(text), lint.WARN, "AC-1 is defined more than once"))

    def test_duplicate_br_id_is_an_error(self):
        text = SPEC.replace("- **BR-2** —", "- **BR-1** —")
        self.assertTrue(has(lint.lint_spec(text), lint.WARN, "BR-1 is defined more than once"))

    def test_rule_cited_by_no_criterion(self):
        text = SPEC.replace("(BR-1, BR-2)", "(BR-1)")
        findings = lint.lint_spec(text)
        self.assertTrue(has(findings, lint.WARN, "BR-2 is cited by no acceptance criterion"))
        self.assertFalse(has(findings, lint.WARN, "BR-1 is cited"))

    def test_criterion_cites_undefined_rule(self):
        text = SPEC.replace("(BR-1, BR-2)", "(BR-1, BR-2, BR-9)")
        self.assertTrue(has(lint.lint_spec(text), lint.WARN, "AC-1 cites BR-9"))

    def test_br_mentioned_in_prose_is_not_a_citation(self):
        # only the parenthesis right after the AC id counts
        text = SPEC.replace("(BR-1, BR-2) — Given", "— Given (see BR-1, BR-2)")
        self.assertTrue(has(lint.lint_spec(text), lint.WARN, "BR-1 is cited by no acceptance criterion"))

    def test_rules_section_with_none_line(self):
        text = SPEC.replace(
            "- **BR-1** — A task is overdue when it is open and its due date is before today.\n"
            "- **BR-2** — A done task is never overdue.\n",
            "None — a UI-only change.\n",
        ).replace("(BR-1, BR-2) ", "")
        self.assertEqual(messages(lint.lint_spec(text)), [])

    def test_empty_rules_section(self):
        text = SPEC.replace(
            "- **BR-1** — A task is overdue when it is open and its due date is before today.\n"
            "- **BR-2** — A done task is never overdue.\n", "\n").replace("(BR-1, BR-2) ", "")
        self.assertTrue(has(lint.lint_spec(text), lint.WARN, "no `**BR-n**` rule and no `None"))

    def test_missing_rules_section_is_a_warning(self):
        start = SPEC.index("## Business Rules")
        end = SPEC.index("## Acceptance Criteria")
        text = (SPEC[:start] + SPEC[end:]).replace("(BR-1, BR-2) ", "")
        findings = lint.lint_spec(text)
        self.assertTrue(has(findings, lint.NOTE, "section is missing (specs before feature-dev 3.0.0"))
        self.assertEqual([f.level for f in findings], [lint.NOTE])

    def test_unnumbered_criterion(self):
        text = SPEC.replace("- **AC-2** — An invalid", "- An invalid")
        self.assertTrue(has(lint.lint_spec(text), lint.NOTE, "1 top-level item(s) without an `**AC-n**` id"))

    def test_missing_non_goals_is_a_note(self):
        text = SPEC.replace("## Non-Goals\n- Reminders: out of scope.\n", "")
        self.assertEqual([(f.level, f.section) for f in lint.lint_spec(text)], [(lint.NOTE, "Non-Goals")])

    def test_heading_inside_code_fence_is_ignored(self):
        text = SPEC.replace("## Objective\n", "```\n## Objective\n```\n")
        self.assertTrue(any(f.section == "Objective" for f in lint.lint_spec(text)))

    def test_qa_group_missing(self):
        text = SPEC.replace("### Empty states\n- [ ] no overdue tasks\n", "")
        self.assertTrue(has(lint.lint_spec(text), lint.WARN, "missing group(s): Empty states"))

    def test_multi_repo_needs_contracts(self):
        text = SPEC.replace("branch: master\n", "branch: master\nrepos:\n  - name: api\n    path: .\n  - name: web\n    path: ../web\n")
        findings = lint.lint_spec(text)
        self.assertTrue(any(f.level == lint.ERROR and f.section == "Cross-Repo Contracts" for f in findings))
        self.assertTrue(any(f.level == lint.WARN and f.section == "Decisions Log" for f in findings))


class CellPathsTest(unittest.TestCase):
    def test_forms(self):
        cases = {
            "app/tasks.py": ["app/tasks.py"],
            "`app/tasks.py` (the model)": ["app/tasks.py"],
            "`tests/t.py` (written by step 2)": ["tests/t.py"],
            "`tests/t.py::test_x`": ["tests/t.py"],
            "apps/inbox/{models,admin}.py, apps/inbox/migrations/": [
                "apps/inbox/models.py", "apps/inbox/admin.py", "apps/inbox/migrations/"],
            "api/tests/test_a.py, test_b.py": ["api/tests/test_a.py", "api/tests/test_b.py"],
            "manage.py": ["manage.py"],
            "(none)": [],
            "n/a — docs only": [],
            "`n/a`": [],
            "[path]": [],
            "": [],
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(lint.cell_paths(value), expected)


class PlanCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.folder = self.root / ".feature-dev" / "features" / "task-due-dates"
        self.folder.mkdir(parents=True)
        (self.folder / "SPEC-task-due-dates.md").write_text(SPEC)
        (self.root / "app").mkdir()
        (self.root / "app" / "tasks.py").write_text("")
        self.plan = self.folder / "PLAN-task-due-dates.md"

    def tearDown(self):
        self._tmp.cleanup()

    def lint(self, text: str = PLAN):
        self.plan.write_text(text)
        return lint.lint_path(self.plan)


class PlanTest(PlanCase):
    def test_clean_plan_has_no_findings(self):
        self.assertEqual(messages(self.lint()), [])

    def test_missing_step_field_is_an_error(self):
        findings = self.lint(PLAN.replace("   - Verify: `pytest tests/test_due.py`\n", ""))
        self.assertTrue(has(findings, lint.ERROR, "step 1 has no `Verify:`"))

    def test_missing_depends_on_is_a_warning(self):
        findings = self.lint(PLAN.replace("   - Depends on: none\n", ""))
        self.assertTrue(has(findings, lint.WARN, "step 1 has no `Depends on:`"))

    def test_no_steps(self):
        start = PLAN.index("1. **Store")
        end = PLAN.index("### Key Decisions")
        findings = self.lint(PLAN[:start] + PLAN[end:])
        self.assertTrue(has(findings, lint.ERROR, "no numbered"))

    def test_written_by_needs_dependency(self):
        findings = self.lint(PLAN.replace("   - Depends on: 1\n", "   - Depends on: none\n"))
        self.assertTrue(has(findings, lint.WARN, "Test is written by step 1 but step 1 is not among its dependencies"))

    def test_written_by_transitive_dependency_is_fine(self):
        third = (
            "3. **Mark overdue in the list**\n"
            "   - Accept: overdue items carry a class\n"
            "   - Covers: AC-1\n"
            "   - Impl: app/tasks.py\n"
            "   - Test: tests/test_due.py (written by step 1)\n"
            "   - Verify: `pytest tests/test_due.py`\n"
            "   - Depends on: 2\n"
            "   - Rationale: last\n\n"
        )
        findings = self.lint(PLAN.replace("### Key Decisions", third + "### Key Decisions"))
        self.assertFalse(has(findings, lint.WARN, "not among its dependencies"))

    def test_pins_on_step_that_does_not_write_its_test(self):
        findings = self.lint(PLAN.replace("   - Covers: AC-1\n", "   - Covers: AC-1\n   - Pins: the list stays sorted\n"))
        self.assertTrue(has(findings, lint.WARN, "step 2 has `Pins:`"))

    def test_characterization_on_step_without_own_test(self):
        findings = self.lint(PLAN.replace("   - Covers: AC-1\n", "   - Kind: characterization\n   - Covers: AC-1\n"))
        self.assertTrue(has(findings, lint.WARN, "step 2 is `Kind: characterization`"))

    def test_unknown_kind(self):
        findings = self.lint(PLAN.replace("   - Covers: AC-2\n", "   - Kind: refactor\n   - Covers: AC-2\n"))
        self.assertTrue(has(findings, lint.WARN, "Kind 'refactor'"))

    def test_too_many_steps(self):
        step = (
            "{n}. **Step {n}**\n   - Accept: x\n   - Covers: AC-1\n   - Impl: app/tasks.py\n"
            "   - Test: n/a — config\n   - Verify: `true`\n   - Depends on: none\n   - Rationale: r\n\n"
        )
        extra = "".join(step.format(n=n) for n in range(3, 28))
        findings = self.lint(PLAN.replace("### Key Decisions", extra + "### Key Decisions"))
        self.assertTrue(has(findings, lint.WARN, "27 steps (limit 25)"))

    def test_duplicate_step_number(self):
        findings = self.lint(PLAN.replace("2. **List overdue", "1. **List overdue"))
        self.assertTrue(has(findings, lint.ERROR, "step 1 is numbered more than once"))

    def test_impl_path_outside_tables(self):
        findings = self.lint(PLAN.replace("   - Impl: `app/tasks.py`", "   - Impl: `app/views.py`"))
        self.assertTrue(has(findings, lint.WARN, "Impl path `app/views.py` is not in Files to Modify"))

    def test_files_to_modify_path_missing_is_an_error(self):
        (self.root / "app" / "tasks.py").unlink()
        self.assertTrue(has(self.lint(), lint.ERROR, "`app/tasks.py` does not exist"))

    def test_files_to_create_path_already_exists(self):
        (self.root / "tests").mkdir()
        (self.root / "tests" / "test_due.py").write_text("")
        self.assertTrue(has(self.lint(), lint.WARN, "`tests/test_due.py` already exists"))

    def test_files_to_create_existing_is_fine_once_steps_completed(self):
        (self.root / "tests").mkdir()
        (self.root / "tests" / "test_due.py").write_text("")
        (self.folder / "feature.json").write_text(json.dumps({"plan": {"completed": [1]}}))
        self.assertFalse(has(self.lint(), lint.WARN, "already exists"))

    def test_sibling_repo_path_not_present_is_unchecked(self):
        text = PLAN.replace("| app/tasks.py | add due date | backend |",
                            "| app/tasks.py | add due date | backend |\n| ../web/src/x.ts | show it | frontend |")
        self.assertFalse(has(self.lint(text), lint.ERROR, "../web/src/x.ts"))

    def test_bad_baseline_value(self):
        findings = self.lint(PLAN.replace("| expected-red |", "| flaky |"))
        self.assertTrue(has(findings, lint.WARN, "result 'flaky'"))

    def test_uncovered_ac(self):
        findings = self.lint(PLAN.replace("   - Covers: AC-1\n", ""))
        self.assertTrue(has(findings, lint.WARN, "AC-1 is covered by no step"))
        self.assertTrue(has(findings, lint.WARN, "behavior step(s) without `Covers:`: 2"))

    def test_uncovered_ac_excluded_in_risks(self):
        text = PLAN.replace("   - Covers: AC-1\n", "").replace(
            "- none worth naming", "- AC-1 is left to the next milestone: the list view is not built yet")
        findings = self.lint(text)
        self.assertFalse(has(findings, lint.WARN, "AC-1 is covered by no step"))

    def test_covers_unknown_ac(self):
        findings = self.lint(PLAN.replace("   - Covers: AC-2\n", "   - Covers: AC-2, AC-7\n"))
        self.assertTrue(has(findings, lint.WARN, "step 1 covers AC-7"))

    def test_spec_without_ac_ids_skips_coverage(self):
        (self.folder / "SPEC-task-due-dates.md").write_text(SPEC.replace("**AC-1**", "AC").replace("**AC-2**", "AC"))
        findings = self.lint(PLAN.replace("   - Covers: AC-1\n", ""))
        self.assertFalse(has(findings, lint.WARN, "covered by no step"))


class PlanRowsTest(PlanCase):
    def test_missing_optional_sections_are_notes(self):
        text = PLAN.replace("### Parallelization Hints\n- none\n", "")
        self.assertEqual([(f.level, f.section) for f in self.lint(text)], [(lint.NOTE, "Parallelization Hints")])

    def test_empty_risks(self):
        findings = self.lint(PLAN.replace("- none worth naming\n", ""))
        self.assertTrue(any(f.level == lint.WARN and f.section == "Risks" for f in findings))

    def test_source_spec_that_does_not_exist_is_an_error(self):
        text = PLAN.replace("### Summary", "Source spec: `../api/.feature-dev/features/x/SPEC-x.md`\n\n### Summary")
        self.assertTrue(has(self.lint(text), lint.ERROR, "SPEC-x.md` does not exist"))

    def test_plan_only_feature(self):
        (self.folder / "SPEC-task-due-dates.md").unlink()
        self.assertTrue(has(self.lint(), lint.WARN, "plan-only feature"))

    def test_hollow_baseline_gates_its_steps(self):
        findings = self.lint(PLAN.replace("| expected-red | step 1 creates it |", "| hollow | 0 tests collected |"))
        self.assertTrue(has(findings, lint.WARN, "step 1: its Verify proves nothing on HEAD"))
        self.assertTrue(has(findings, lint.WARN, "step 2: its Verify proves nothing on HEAD"))

    def test_not_run_missing_gates_unless_accepted(self):
        missing = PLAN.replace("| expected-red | step 1 creates it |", "| not-run | missing: no DATABASE_URL |")
        self.assertTrue(has(self.lint(missing), lint.WARN, "proves nothing on HEAD"))
        accepted = PLAN.replace("| expected-red | step 1 creates it |", "| not-run | missing: no DATABASE_URL — accepted by user |")
        self.assertFalse(has(self.lint(accepted), lint.WARN, "proves nothing on HEAD"))
        slow = PLAN.replace("| expected-red | step 1 creates it |", "| not-run | slow: full suite |")
        self.assertFalse(has(self.lint(slow), lint.WARN, "proves nothing on HEAD"))

    def test_shared_test_file_needs_written_by_marker(self):
        findings = self.lint(PLAN.replace("`tests/test_due.py` (written by step 1)", "`tests/test_due.py`"))
        self.assertTrue(has(findings, lint.WARN, "step 2: Test `tests/test_due.py` is created by step 1"))

    def test_sibling_repo_path_is_a_note(self):
        text = PLAN.replace("| app/tasks.py | add due date | backend |",
                            "| app/tasks.py | add due date | backend |\n| ../web/src/x.ts | show it | frontend |")
        self.assertTrue(has(self.lint(text), lint.NOTE, "`../web/src/x.ts` is in a sibling repo"))

    def test_coverage_summary(self):
        self.plan.write_text(PLAN.replace("   - Covers: AC-1\n", "").replace(
            "- none worth naming", "- AC-1 is left out: no list view yet"))
        self.assertEqual(lint.coverage_of(self.plan)._asdict(),
                         {"covered": 1, "total": 2, "uncovered": [], "excluded": ["AC-1"]})
        self.plan.write_text(PLAN)
        self.assertEqual(lint.coverage_of(self.plan)._asdict(),
                         {"covered": 2, "total": 2, "uncovered": [], "excluded": []})
        self.assertIsNone(lint.coverage_of(self.folder / "SPEC-task-due-dates.md"))


class HookTest(PlanCase):
    def run_hook(self, payload) -> str:
        stdin = payload if isinstance(payload, str) else json.dumps(payload)
        proc = subprocess.run([sys.executable, "-B", str(SCRIPT), "--hook"],
                              input=stdin, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout.strip()

    def test_ignores_other_files(self):
        other = self.root / "app" / "tasks.py"
        self.assertEqual(self.run_hook({"tool_input": {"file_path": str(other)}}), "")

    def test_ignores_artifacts_outside_the_store(self):
        stray = self.root / "SPEC-stray.md"
        stray.write_text("no frontmatter")
        self.assertEqual(self.run_hook({"tool_input": {"file_path": str(stray)}}), "")

    def test_ignores_history_snapshots(self):
        history = self.folder / "history"
        history.mkdir()
        snap = history / "SPEC-task-due-dates.1.md"
        snap.write_text("no frontmatter")
        self.assertEqual(self.run_hook({"tool_input": {"file_path": str(snap)}}), "")

    def test_clean_artifact_prints_nothing(self):
        self.plan.write_text(PLAN)
        self.assertEqual(self.run_hook({"tool_input": {"file_path": str(self.plan)}}), "")

    def test_findings_become_additional_context(self):
        self.plan.write_text(PLAN.replace("   - Verify: `pytest tests/test_due.py`\n", ""))
        out = json.loads(self.run_hook({"tool_name": "Edit", "tool_input": {"file_path": str(self.plan)}}))
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("PLAN-task-due-dates.md: 1 error(s)", context)
        self.assertIn("error: [Implementation Order] step 1 has no `Verify:`", context)

    def test_notes_are_left_out(self):
        self.plan.write_text(PLAN.replace("### Parallelization Hints\n- none\n", ""))
        self.assertEqual(self.run_hook({"tool_input": {"file_path": str(self.plan)}}), "")

    def test_malformed_stdin_prints_nothing(self):
        self.assertEqual(self.run_hook("not json"), "")
        self.assertEqual(self.run_hook({"tool_input": "x"}), "")


class CliTest(PlanCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True)

    def test_exit_codes(self):
        self.plan.write_text(PLAN)
        self.assertEqual(self.run_cli(str(self.plan)).returncode, 0)
        self.plan.write_text(PLAN.replace("   - Verify: `pytest tests/test_due.py`\n", ""))
        self.assertEqual(self.run_cli(str(self.plan)).returncode, 1)
        self.assertEqual(self.run_cli(str(self.root / "app" / "tasks.py")).returncode, 2)
        self.assertEqual(self.run_cli().returncode, 2)

    def test_json_output(self):
        self.plan.write_text(PLAN.replace("   - Depends on: none\n", ""))
        proc = self.run_cli(str(self.plan), "--json")
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout)
        self.assertEqual(out["findings"][0]["level"], "warn")
        self.assertEqual(out["ac_coverage"], {"covered": 2, "total": 2, "uncovered": [], "excluded": []})


if __name__ == "__main__":
    unittest.main()
