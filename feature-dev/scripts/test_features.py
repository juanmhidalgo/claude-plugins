#!/usr/bin/env python3
"""Tests for features.py. Standard library only.

Run from anywhere:  python3 feature-dev/scripts/test_features.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).with_name("features.py")
sys.dont_write_bytecode = True  # keep __pycache__ out of the plugin directory
sys.path.insert(0, str(SCRIPT.parent))
import features  # noqa: E402


class CliCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *args, "--root", str(self.root)],
            capture_output=True, text=True,
        )

    def listing(self) -> list[str]:
        return sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))

    def feature(self, slug: str) -> dict:
        path = self.root / ".feature-dev" / "features" / slug / "feature.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def make(self, slug, status, *, spec_md=True, plan_md=False, plan=None, spec=None) -> Path:
        folder = self.root / ".feature-dev" / "features" / slug
        folder.mkdir(parents=True)
        if spec_md:
            (folder / f"SPEC-{slug}.md").write_text("# spec\n", encoding="utf-8")
        if plan_md:
            (folder / f"PLAN-{slug}.md").write_text("# plan\n", encoding="utf-8")
        data = {"version": 1, "slug": slug, "status": status, "spec": spec, "plan": plan,
                "issue": None, "updated_at": "2026-01-01T00:00:00Z"}
        (folder / "feature.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return folder

    def assert_rejected(self, folder, *args, state, valid):
        before = (folder / "feature.json").read_bytes()
        result = self.run_cli(*args)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual((folder / "feature.json").read_bytes(), before)
        self.assertIn("refused", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn(state, result.stderr)
        for event in valid:
            self.assertIn(event, result.stderr)


class NewSpecTest(CliCase):
    def test_ac1_new_spec_writes_draft_feature_json_and_prints_spec_path(self):
        result = self.run_cli("new", "foo", "--kind", "spec")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), ".feature-dev/features/foo/SPEC-foo.md")
        data = self.feature("foo")
        updated_at = data.pop("updated_at")
        self.assertRegex(updated_at, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(
            data, {"version": 1, "slug": "foo", "status": "draft", "spec": None, "plan": None, "issue": None}
        )

    def test_ac1_second_new_with_same_slug_is_refused_and_changes_nothing(self):
        self.assertEqual(self.run_cli("new", "foo", "--kind", "spec").returncode, 0)
        before = self.listing()
        content = (self.root / ".feature-dev/features/foo/feature.json").read_text(encoding="utf-8")
        result = self.run_cli("new", "foo", "--kind", "spec")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.listing(), before)
        self.assertEqual((self.root / ".feature-dev/features/foo/feature.json").read_text(encoding="utf-8"), content)

    def test_ac1_unsafe_slug_is_a_usage_error_and_writes_nothing(self):
        result = self.run_cli("new", "../evil", "--kind", "spec")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.listing(), [])


class NewPlanTest(CliCase):
    def test_ac2_new_plan_with_spec_prints_path_in_spec_folder_and_leaves_spec_json_untouched(self):
        self.assertEqual(self.run_cli("new", "foo", "--kind", "spec").returncode, 0)
        path = self.root / ".feature-dev/features/foo/feature.json"
        before = path.read_bytes()
        result = self.run_cli("new", "bar", "--kind", "plan", "--spec", "foo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), ".feature-dev/features/foo/PLAN-bar.md")
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((self.root / ".feature-dev/features/bar").exists())

    def test_ac2_new_plan_without_spec_creates_planned_feature_with_unset_steps(self):
        result = self.run_cli("new", "bar", "--kind", "plan")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), ".feature-dev/features/bar/PLAN-bar.md")
        data = self.feature("bar")
        data.pop("updated_at")
        self.assertEqual(data, {
            "version": 1, "slug": "bar", "status": "planned", "spec": None, "issue": None,
            "plan": {"steps": 0, "completed": [], "halted_at": None, "halt_reason": None},
        })

    def test_ac2_new_plan_with_missing_spec_folder_is_refused_and_creates_nothing(self):
        result = self.run_cli("new", "bar", "--kind", "plan", "--spec", "nope")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.listing(), [])

    def test_pin_new_plan_without_spec_refuses_existing_slug(self):
        self.assertEqual(self.run_cli("new", "bar", "--kind", "plan").returncode, 0)
        before = self.listing()
        content = (self.root / ".feature-dev/features/bar/feature.json").read_text(encoding="utf-8")
        result = self.run_cli("new", "bar", "--kind", "plan")
        self.assertEqual(result.returncode, 1)
        self.assertIn("refused", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.listing(), before)
        self.assertEqual((self.root / ".feature-dev/features/bar/feature.json").read_text(encoding="utf-8"), content)


class SpecTransitionsTest(CliCase):
    def test_ac3_approve_from_draft_sets_approved_at(self):
        self.make("foo", "draft")
        result = self.run_cli("approve", "foo")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self.feature("foo")
        self.assertEqual(data["status"], "approved")
        self.assertRegex(data["spec"]["approved_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_ac3_approve_from_approved_refreshes_approved_at(self):
        self.make("foo", "approved", spec={"approved_at": "2020-01-01T00:00:00Z"})
        self.assertEqual(self.run_cli("approve", "foo").returncode, 0)
        data = self.feature("foo")
        self.assertEqual(data["status"], "approved")
        self.assertNotEqual(data["spec"]["approved_at"], "2020-01-01T00:00:00Z")

    def test_ac3_approve_without_spec_file_is_rejected(self):
        folder = self.make("foo", "draft", spec_md=False)
        self.assert_rejected(folder, "approve", "foo", state="draft", valid=["approve"])

    def test_ac3_approve_from_planned_is_rejected(self):
        folder = self.make("foo", "planned", plan={"steps": 2, "completed": [], "halted_at": None, "halt_reason": None})
        self.assert_rejected(folder, "approve", "foo", state="planned", valid=["plan --replace"])

    def test_ac3_plan_from_approved_with_plan_file_sets_planned(self):
        self.make("foo", "approved", plan_md=True, spec={"approved_at": "x"})
        result = self.run_cli("plan", "foo", "--steps", "4")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self.feature("foo")
        self.assertEqual(data["status"], "planned")
        self.assertEqual(data["plan"], {"steps": 4, "completed": [], "halted_at": None, "halt_reason": None})
        self.assertEqual(data["spec"], {"approved_at": "x"})

    def test_ac3_plan_without_plan_file_and_without_from_spec_is_rejected(self):
        folder = self.make("foo", "approved")
        self.assert_rejected(folder, "plan", "foo", "--steps", "4", state="approved", valid=["approve", "plan"])

    def test_ac3_plan_with_zero_steps_is_rejected(self):
        folder = self.make("foo", "approved", plan_md=True)
        self.assert_rejected(folder, "plan", "foo", "--steps", "0", state="approved", valid=["plan"])

    def test_ac3_plan_from_draft_is_rejected(self):
        folder = self.make("foo", "draft", plan_md=True)
        self.assert_rejected(folder, "plan", "foo", "--steps", "3", state="draft", valid=["approve"])

    def test_ac3_plan_from_spec_without_plan_file_sets_planned(self):
        self.make("foo", "approved")
        result = self.run_cli("plan", "foo", "--steps", "6", "--from-spec")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self.feature("foo")
        self.assertEqual(data["status"], "planned")
        self.assertEqual(data["plan"]["steps"], 6)

    def test_ac3_plan_from_spec_from_draft_is_rejected(self):
        folder = self.make("foo", "draft")
        self.assert_rejected(folder, "plan", "foo", "--steps", "6", "--from-spec", state="draft", valid=["approve"])

    def test_ac3_plan_replace_from_each_state_clears_progress(self):
        progress = {"steps": 5, "completed": [1, 2], "halted_at": 3, "halt_reason": "boom"}
        for status in ("planned", "running", "halted"):
            with self.subTest(status=status):
                self.make(status, status, plan_md=True, plan=progress)
                result = self.run_cli("plan", status, "--replace", "--steps", "7")
                self.assertEqual(result.returncode, 0, result.stderr)
                data = self.feature(status)
                self.assertEqual(data["status"], "planned")
                self.assertEqual(data["plan"], {"steps": 7, "completed": [], "halted_at": None, "halt_reason": None})

    def test_ac3_plan_replace_from_approved_or_draft_is_rejected(self):
        for status in ("draft", "approved"):
            with self.subTest(status=status):
                folder = self.make(status, status, plan_md=True)
                self.assert_rejected(folder, "plan", status, "--replace", "--steps", "7", state=status, valid=["approve"])

    def test_ac3_plan_replace_without_plan_file_or_zero_steps_is_rejected(self):
        folder = self.make("nofile", "planned", plan={"steps": 2, "completed": [], "halted_at": None, "halt_reason": None})
        self.assert_rejected(folder, "plan", "nofile", "--replace", "--steps", "3", state="planned", valid=["plan --replace"])
        folder = self.make("zero", "planned", plan_md=True, plan={"steps": 2, "completed": [], "halted_at": None, "halt_reason": None})
        self.assert_rejected(folder, "plan", "zero", "--replace", "--steps", "0", state="planned", valid=["plan --replace"])

    def test_pin_feature_json_unchanged_when_os_replace_raises(self):
        folder = self.make("foo", "draft")
        before = (folder / "feature.json").read_bytes()
        with mock.patch.object(features.os, "replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                features.main(["approve", "foo", "--root", str(self.root)])
        self.assertEqual((folder / "feature.json").read_bytes(), before)
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ["SPEC-foo.md", "feature.json"])

    def test_ac8_transitions_never_touch_markdown_mtimes(self):
        folder = self.make("foo", "draft", plan_md=True)
        mds = sorted(folder.glob("*.md"))
        for md in mds:
            os.utime(md, ns=(1_000_000_000, 1_000_000_000))
        for args in (("approve",), ("approve",), ("plan", "--steps", "3"), ("plan", "--replace", "--steps", "2")):
            self.assertEqual(self.run_cli(args[0], "foo", *args[1:]).returncode, 0)
        self.assertEqual([md.stat().st_mtime_ns for md in mds], [1_000_000_000] * len(mds))


def progress(steps, completed=(), halted_at=None, halt_reason=None):
    return {"steps": steps, "completed": list(completed), "halted_at": halted_at, "halt_reason": halt_reason}


class StepTransitionsTest(CliCase):
    def test_ac4_step_done_from_planned_sets_running_and_appends(self):
        self.make("foo", "planned", plan_md=True, plan=progress(3))
        result = self.run_cli("step", "foo", "done", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self.feature("foo")
        self.assertEqual(data["status"], "running")
        self.assertEqual(data["plan"]["completed"], [1])

    def test_ac4_step_done_from_running_appends_next(self):
        self.make("foo", "running", plan=progress(3, [1]))
        self.assertEqual(self.run_cli("step", "foo", "done", "2").returncode, 0)
        data = self.feature("foo")
        self.assertEqual(data["status"], "running")
        self.assertEqual(data["plan"]["completed"], [1, 2])

    def test_ac4_step_done_rejects_gap_repeat_and_past_steps(self):
        for label, plan, n in (("gap", progress(5, [1]), "3"), ("repeat", progress(5, [1]), "1"),
                               ("past", progress(2, [1, 2]), "3"), ("zero", progress(2), "0")):
            with self.subTest(label=label):
                folder = self.make(label, "running", plan=plan)
                self.assert_rejected(folder, "step", label, "done", n, state="running",
                                     valid=["step done", "step halt", "implemented"])

    def test_ac4_step_done_from_halted_is_rejected(self):
        folder = self.make("foo", "halted", plan=progress(3, [1], 2, "boom"))
        self.assert_rejected(folder, "step", "foo", "done", "2", state="halted",
                             valid=["step resume", "plan --replace"])

    def test_ac4_step_halt_from_running_records_reason(self):
        self.make("foo", "running", plan=progress(3, [1]))
        result = self.run_cli("step", "foo", "halt", "2", "--reason", "tests fail")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self.feature("foo")
        self.assertEqual(data["status"], "halted")
        self.assertEqual(data["plan"]["halted_at"], 2)
        self.assertEqual(data["plan"]["halt_reason"], "tests fail")
        self.assertEqual(data["plan"]["completed"], [1])

    def test_ac4_step_halt_with_wrong_n_is_rejected(self):
        folder = self.make("foo", "running", plan=progress(3, [1]))
        self.assert_rejected(folder, "step", "foo", "halt", "3", "--reason", "x", state="running",
                             valid=["step done", "step halt"])

    def test_step_halt_from_planned_records_halt_at_step_one(self):
        self.make("foo", "planned", plan_md=True, plan=progress(3))
        result = self.run_cli("step", "foo", "halt", "1", "--reason", "x")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self.feature("foo")
        self.assertEqual(data["status"], "halted")
        self.assertEqual(data["plan"]["halted_at"], 1)
        self.assertEqual(data["plan"]["halt_reason"], "x")

    def test_step_reopen_from_running_truncates_completed(self):
        self.make("foo", "running", plan=progress(5, [1, 2, 3]))
        result = self.run_cli("step", "foo", "reopen", "2")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self.feature("foo")
        self.assertEqual(data["status"], "running")
        self.assertEqual(data["plan"], progress(5, [1]))

    def test_step_reopen_from_halted_truncates_and_clears_halt(self):
        self.make("foo", "halted", plan=progress(5, [1, 2, 3], 4, "boom"))
        result = self.run_cli("step", "foo", "reopen", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self.feature("foo")
        self.assertEqual(data["status"], "running")
        self.assertEqual(data["plan"], progress(5, []))

    def test_step_reopen_of_step_not_completed_is_refused(self):
        folder = self.make("foo", "running", plan=progress(5, [1, 2]))
        self.assert_rejected(folder, "step", "foo", "reopen", "3", state="running",
                             valid=["step done", "step halt", "step reopen"])

    def test_step_reopen_from_planned_and_implemented_is_refused(self):
        for status, valid in (("planned", ["step done", "step halt"]), ("implemented", [])):
            with self.subTest(status=status):
                folder = self.make(status, status, plan=progress(2, [1] if status == "implemented" else []))
                self.assert_rejected(folder, "step", status, "reopen", "1", state=status, valid=valid)

    def test_step_reopen_without_n_is_a_usage_error(self):
        self.make("foo", "running", plan=progress(3, [1]))
        self.assertEqual(self.run_cli("step", "foo", "reopen").returncode, 2)

    def test_ac4_step_resume_from_halted_clears_halt(self):
        self.make("foo", "halted", plan=progress(3, [1], 2, "boom"))
        result = self.run_cli("step", "foo", "resume")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self.feature("foo")
        self.assertEqual(data["status"], "running")
        self.assertEqual(data["plan"], progress(3, [1]))

    def test_ac4_step_resume_from_running_is_rejected(self):
        folder = self.make("foo", "running", plan=progress(3, [1]))
        self.assert_rejected(folder, "step", "foo", "resume", state="running", valid=["step done"])

    def test_ac4_implemented_when_all_steps_completed(self):
        self.make("foo", "running", plan=progress(2, [1, 2]))
        result = self.run_cli("implemented", "foo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.feature("foo")["status"], "implemented")

    def test_ac4_implemented_with_steps_remaining_is_rejected(self):
        folder = self.make("foo", "running", plan=progress(3, [1, 2]))
        self.assert_rejected(folder, "implemented", "foo", state="running", valid=["implemented", "step done"])

    def test_ac4_implemented_from_planned_is_rejected(self):
        folder = self.make("foo", "planned", plan_md=True, plan=progress(0))
        self.assert_rejected(folder, "implemented", "foo", state="planned", valid=["plan --replace"])

    def test_ac3_rejections_are_byte_identical_for_gap_repeat_and_past(self):
        self.make("foo", "running", plan=progress(5, [1]))
        errors = {self.run_cli("step", "foo", "done", n).stderr for n in ("3", "1", "6")}
        self.assertEqual(len(errors), 1, errors)
        self.assertTrue(errors.pop().startswith("refused: cannot step done from running"))

    def test_ac8_step_events_never_touch_markdown_mtimes(self):
        folder = self.make("foo", "planned", plan_md=True, plan=progress(2))
        mds = sorted(folder.glob("*.md"))
        for md in mds:
            os.utime(md, ns=(1_000_000_000, 1_000_000_000))
        for args in (("step", "foo", "done", "1"), ("step", "foo", "halt", "2", "--reason", "r"),
                     ("step", "foo", "resume"), ("step", "foo", "done", "2"),
                     ("step", "foo", "reopen", "2"), ("step", "foo", "done", "2"), ("implemented", "foo")):
            self.assertEqual(self.run_cli(*args).returncode, 0, args)
        self.assertEqual(self.feature("foo")["status"], "implemented")
        self.assertEqual([md.stat().st_mtime_ns for md in mds], [1_000_000_000] * len(mds))


class LinkIssueTest(CliCase):
    STATES = {
        "draft": {}, "approved": {}, "planned": {"plan": progress(2)},
        "running": {"plan": progress(2, completed=[1])},
        "halted": {"plan": progress(2, completed=[1], halted_at=2, halt_reason="r")},
        "implemented": {"plan": progress(1, completed=[1])},
    }

    def test_ac13_link_issue_sets_issue_from_every_state_without_changing_status(self):
        for state, extra in self.STATES.items():
            with self.subTest(state=state):
                folder = self.make(state, state, plan_md=True, **extra)
                mds = sorted(folder.glob("*.md"))
                for md in mds:
                    os.utime(md, ns=(1_000_000_000, 1_000_000_000))
                result = self.run_cli("link-issue", state, "owner/repo#123", "abc123")
                self.assertEqual(result.returncode, 0, result.stderr)
                data = self.feature(state)
                self.assertEqual(data["issue"], {"ref": "owner/repo#123", "fingerprint": "abc123"})
                self.assertEqual(data["status"], state)
                self.assertNotEqual(data["updated_at"], "2026-01-01T00:00:00Z")
                self.assertEqual([md.stat().st_mtime_ns for md in mds], [1_000_000_000] * len(mds))

    def test_ac13_malformed_ref_exits_nonzero_and_leaves_feature_json_identical(self):
        folder = self.make("foo", "draft")
        before = (folder / "feature.json").read_bytes()
        for ref in ("owner/repo", "repo#1", "owner/repo#", "owner/repo#x", "#12", "a b/c#1"):
            with self.subTest(ref=ref):
                result = self.run_cli("link-issue", "foo", ref, "fp")
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual((folder / "feature.json").read_bytes(), before)


class InvalidFeatureTest(CliCase):
    COMMANDS = (
        ("approve", "foo"),
        ("plan", "foo", "--steps", "2"),
        ("plan", "foo", "--steps", "2", "--replace"),
        ("step", "foo", "done", "1"),
        ("step", "foo", "halt", "1", "--reason", "r"),
        ("step", "foo", "resume"),
        ("implemented", "foo"),
        ("link-issue", "foo", "owner/repo#1", "fp"),
    )

    def assert_every_command_refused_as_invalid(self, folder, reason):
        before_listing = self.listing()
        before_bytes = {p: p.read_bytes() for p in folder.iterdir()}
        for args in self.COMMANDS:
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("refused", result.stderr)
                self.assertIn("invalid", result.stderr)
                self.assertIn(reason, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(self.listing(), before_listing)
                self.assertEqual({p: p.read_bytes() for p in folder.iterdir()}, before_bytes)

    def test_ac6_missing_feature_json_is_invalid_for_every_command(self):
        folder = self.make("foo", "draft")
        (folder / "feature.json").unlink()
        self.assert_every_command_refused_as_invalid(folder, "feature.json missing")

    def test_ac6_unparseable_feature_json_is_invalid_for_every_command(self):
        folder = self.make("foo", "draft")
        (folder / "feature.json").write_text("{not json", encoding="utf-8")
        self.assert_every_command_refused_as_invalid(folder, "not valid JSON")

    def test_ac6_unsupported_version_is_invalid_for_every_command(self):
        folder = self.make("foo", "draft")
        data = self.feature("foo")
        data["version"] = 2
        (folder / "feature.json").write_text(json.dumps(data), encoding="utf-8")
        self.assert_every_command_refused_as_invalid(folder, "unsupported version: 2")

    def test_ac6_absent_folder_is_not_found_not_invalid(self):
        for args in self.COMMANDS:
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("feature not found", result.stderr)
                self.assertNotIn("invalid", result.stderr)


class ListTest(CliCase):
    def list_json(self) -> list[dict]:
        result = self.run_cli("list", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def review(self, folder: Path, name: str, artifact: str, mtime: int) -> Path:
        reviews = folder / "reviews"
        reviews.mkdir(exist_ok=True)
        path = reviews / name
        path.write_text(f"---\nartifact: .feature-dev/features/{folder.name}/{artifact}\n---\nbody\n", encoding="utf-8")
        os.utime(path, (mtime, mtime))
        return path

    def touch(self, path: Path, mtime: int) -> None:
        os.utime(path, (mtime, mtime))

    def test_ac5_no_features_folder_prints_empty_list_and_exits_0(self):
        result = self.run_cli("list", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [])

    def test_ac5_json_has_one_object_per_feature_sorted_by_slug(self):
        self.make("zed", "running", plan_md=True, plan=progress(3, completed=[1]))
        self.make("alpha", "draft")
        (self.root / ".feature-dev" / "features" / "stray.txt").write_text("x", encoding="utf-8")
        items = self.list_json()
        self.assertEqual([i["slug"] for i in items], ["alpha", "zed"])
        zed = items[1]
        self.assertEqual(zed["status"], "running")
        self.assertEqual(zed["plan"], progress(3, completed=[1]))
        self.assertIsNone(zed["issue"])
        self.assertEqual(
            [(a["kind"], a["path"]) for a in zed["artifacts"]],
            [("spec", ".feature-dev/features/zed/SPEC-zed.md"), ("plan", ".feature-dev/features/zed/PLAN-zed.md")],
        )
        self.assertIsNone(items[0]["plan"])

    def test_ac5_issue_is_the_ref_string(self):
        self.run_cli("new", "foo", "--kind", "spec")
        self.run_cli("link-issue", "foo", "o/r#7", "fp")
        self.assertEqual(self.list_json()[0]["issue"], "o/r#7")

    def test_ac5_artifact_without_review_needs_review(self):
        self.make("foo", "draft")
        self.assertTrue(self.list_json()[0]["artifacts"][0]["needs_review"])

    def test_ac5_needs_review_compares_mtime_with_newest_matching_review(self):
        folder = self.make("foo", "draft", plan_md=True)
        spec, plan = folder / "SPEC-foo.md", folder / "PLAN-foo.md"
        self.touch(spec, 1000)
        self.touch(plan, 3000)
        self.review(folder, "20260101T000000Z.md", "SPEC-foo.md", 500)
        self.review(folder, "20260101T000001Z.md", "SPEC-foo.md", 2000)
        self.review(folder, "20260101T000002Z.md", "PLAN-foo.md", 2500)
        (folder / "reviews" / ".url").write_text("http://x", encoding="utf-8")
        by_kind = {a["kind"]: a["needs_review"] for a in self.list_json()[0]["artifacts"]}
        self.assertEqual(by_kind, {"spec": False, "plan": True})
        self.touch(spec, 2001)
        by_kind = {a["kind"]: a["needs_review"] for a in self.list_json()[0]["artifacts"]}
        self.assertEqual(by_kind["spec"], True)

    def test_ac5_artifact_with_same_mtime_as_review_is_not_newer(self):
        folder = self.make("foo", "draft")
        self.touch(folder / "SPEC-foo.md", 1000)
        self.review(folder, "20260101T000000Z.md", "SPEC-foo.md", 1000)
        self.assertFalse(self.list_json()[0]["artifacts"][0]["needs_review"])

    def test_ac5_review_matches_on_artifact_basename(self):
        folder = self.make("foo", "draft")
        self.touch(folder / "SPEC-foo.md", 1000)
        reviews = folder / "reviews"
        reviews.mkdir()
        (reviews / "20260101T000000Z.md").write_text(
            "---\nartifact: /elsewhere/SPEC-foo.md\n---\n", encoding="utf-8")
        os.utime(reviews / "20260101T000000Z.md", (2000, 2000))
        self.assertFalse(self.list_json()[0]["artifacts"][0]["needs_review"])

    def test_ac5_plain_list_prints_one_line_per_feature(self):
        self.make("alpha", "draft")
        self.make("beta", "planned", plan_md=True, plan=progress(2))
        result = self.run_cli("list")
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("alpha", lines[0])
        self.assertIn("draft", lines[0])
        self.assertIn("beta", lines[1])
        self.assertIn("planned", lines[1])

    def test_ac6_invalid_folders_are_listed_with_reason_and_exit_0(self):
        broken = self.make("broken", "draft")
        (broken / "feature.json").write_text("{not json", encoding="utf-8")
        nofile = self.make("nofile", "draft")
        (nofile / "feature.json").unlink()
        items = {i["slug"]: i for i in self.list_json()}
        for slug in ("broken", "nofile"):
            self.assertEqual(items[slug]["status"], "invalid")
            self.assertIn("reason", items[slug])
            self.assertIsNone(items[slug]["plan"])
            self.assertIsNone(items[slug]["issue"])
            self.assertEqual([a["kind"] for a in items[slug]["artifacts"]], ["spec"])
        self.assertIn("not valid JSON", items["broken"]["reason"])
        self.assertEqual(self.run_cli("list").returncode, 0)

    def test_ac6_version_1_with_bad_shape_is_invalid_not_a_crash(self):
        cases = {
            "nostatus": ({"version": 1, "plan": None}, "missing status"),
            "weird": ({"version": 1, "status": "x", "plan": None}, "unknown status: x"),
            "badplan": ({"version": 1, "status": "draft", "plan": [1]}, "plan is not an object"),
        }
        for slug, (data, _) in cases.items():
            folder = self.make(slug, "draft")
            (folder / "feature.json").write_text(json.dumps(data), encoding="utf-8")
        items = {i["slug"]: i for i in self.list_json()}
        for slug, (_, reason) in cases.items():
            with self.subTest(slug=slug):
                self.assertEqual(items[slug]["status"], "invalid")
                self.assertEqual(items[slug]["reason"], reason)
        result = self.run_cli("approve", "nostatus")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)



class DeleteTest(CliCase):
    def git(self, *args):
        subprocess.run(
            ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
            cwd=self.root, check=True, capture_output=True,
        )

    def test_ac7_delete_implemented_removes_the_folder(self):
        folder = self.make("foo", "implemented", plan_md=True)
        result = self.run_cli("delete", "foo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(folder.exists())
        self.assertTrue((self.root / ".feature-dev" / "features").is_dir())

    def test_ac7_delete_refuses_other_state_naming_it_and_force(self):
        folder = self.make("foo", "running", plan={"steps": 1, "completed": [], "halted_at": None, "halt_reason": None})
        result = self.run_cli("delete", "foo")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("running", result.stderr)
        self.assertIn("--force", result.stderr)
        self.assertTrue(folder.exists())

    def test_ac7_force_removes_any_state_including_invalid(self):
        running = self.make("foo", "draft")
        broken = self.make("bar", "draft")
        (broken / "feature.json").write_text("{nope", encoding="utf-8")
        for slug, folder in (("foo", running), ("bar", broken)):
            result = self.run_cli("delete", slug, "--force")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(folder.exists())

    def test_ac7_plain_delete_refuses_invalid_naming_it(self):
        broken = self.make("bar", "draft")
        (broken / "feature.json").write_text("{nope", encoding="utf-8")
        result = self.run_cli("delete", "bar")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("invalid", result.stderr)
        self.assertTrue(broken.exists())

    def test_ac7_missing_feature_is_refused(self):
        result = self.run_cli("delete", "ghost")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("feature not found", result.stderr)

    def test_ac7_dry_run_lists_every_path_and_removes_nothing(self):
        folder = self.make("foo", "implemented", plan_md=True)
        (folder / "reviews").mkdir()
        (folder / "reviews" / "r.md").write_text("x", encoding="utf-8")
        before = self.listing()
        result = self.run_cli("delete", "foo", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.listing(), before)
        for name in ("feature.json", "SPEC-foo.md", "PLAN-foo.md", "reviews/r.md", "reviews", "foo"):
            self.assertIn(name, result.stdout)

    def test_ac7_tracked_file_refuses_even_with_force(self):
        self.git("init", "-q")
        folder = self.make("foo", "implemented")
        self.git("add", ".feature-dev/features/foo/SPEC-foo.md")
        self.git("commit", "-q", "-m", "x")
        for extra in ((), ("--force",)):
            result = self.run_cli("delete", "foo", *extra)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("tracked", result.stderr)
            self.assertTrue((folder / "SPEC-foo.md").exists())

    def test_ac7_untracked_folder_in_a_git_repo_is_removed(self):
        self.git("init", "-q")
        folder = self.make("foo", "implemented")
        result = self.run_cli("delete", "foo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(folder.exists())

    def test_ac7_symlinked_folder_is_refused(self):
        target = self.root / "elsewhere"
        target.mkdir()
        (target / "keep.txt").write_text("x", encoding="utf-8")
        base = self.root / ".feature-dev" / "features"
        base.mkdir(parents=True)
        (base / "foo").symlink_to(target, target_is_directory=True)
        result = self.run_cli("delete", "foo", "--force")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("symlink", result.stderr)
        self.assertTrue((target / "keep.txt").exists())

    def test_ac7_features_dir_symlinked_outside_is_refused(self):
        outside = self.root / "outside"
        (outside / "foo").mkdir(parents=True)
        (outside / "foo" / "keep.txt").write_text("x", encoding="utf-8")
        (self.root / ".feature-dev").mkdir()
        (self.root / ".feature-dev" / "features").symlink_to(outside, target_is_directory=True)
        result = self.run_cli("delete", "foo", "--force")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue((outside / "foo" / "keep.txt").exists())

    def test_ac7_inner_symlink_is_removed_not_followed(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "keep.txt").write_text("x", encoding="utf-8")
        folder = self.make("foo", "implemented")
        (folder / "link").symlink_to(outside, target_is_directory=True)
        result = self.run_cli("delete", "foo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(folder.exists())
        self.assertTrue((outside / "keep.txt").exists())

    def test_ac7_unsafe_slug_is_a_usage_error(self):
        self.assertEqual(self.run_cli("delete", "../x").returncode, 2)


PLUGIN_DIR = SCRIPT.parent.parent
COMMANDS_DIR = PLUGIN_DIR / "commands"
ISSUE_STORE = PLUGIN_DIR / "skills" / "spec-driven-development" / "references" / "issue-store.md"
FEATURES_TOOL = "Bash(${CLAUDE_PLUGIN_ROOT}/scripts/features.py *)"

STATE_KEYS = (
    "status", "run_status", "completed_steps", "halted_at", "halt_reason",
    "source_spec", "issue_fingerprint", "issue",
)
_KEYS = "|".join(STATE_KEYS)
# A frontmatter template line: the key opens a line (optionally commented out).
_TEMPLATE_KEY = re.compile(rf"^\s*(?:#\s*)?(?:{_KEYS}):", re.M)
# An "Edit ... to" sentence: an instruction verb, then the key written with its colon
# (`status:`) on the same line. Prose that only names a key (feature.json's `status`)
# carries no colon and does not match.
_EDIT_KEY = re.compile(
    rf"\b(?:edit|update|set|flip|change|write|record|add|put|mark|keep|confirm)\b"
    rf"[^\n]*?(?<![\w.])(?:{_KEYS}):",
    re.I,
)
_REFUSAL_DIR = ".feature-dev/features/"


def removed_key_instructions(text: str) -> list[str]:
    """Lines that tell the reader to write one of the removed frontmatter keys."""
    found = []
    for line in text.splitlines():
        if _TEMPLATE_KEY.match(line) or _EDIT_KEY.search(line):
            found.append(line.strip())
    return found


def branch_after(text: str, pattern: str) -> str:
    """The bullet whose first line matches `pattern`, with its nested lines."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(pattern, line):
            indent = len(line) - len(line.lstrip())
            out = [line]
            for nxt in lines[i + 1:]:
                if nxt.strip() and len(nxt) - len(nxt.lstrip()) <= indent:
                    break
                out.append(nxt)
            return "\n".join(out)
    return ""


class CommandTextTest(unittest.TestCase):
    """The command files drive features.py instead of hand-editing state."""

    def command(self, name: str) -> str:
        return (COMMANDS_DIR / name).read_text(encoding="utf-8")

    def assertNoRemovedKeys(self, text: str):
        self.assertEqual(removed_key_instructions(text), [])

    def assertNoOldLayout(self, text: str):
        self.assertNotIn("artifacts_dir", text)
        self.assertNotIn("review_server.py artifacts", text)
        self.assertIsNone(re.search(r"\.feature-dev/(specs|plans)", text))

    def assertAllowsFeatures(self, text: str):
        self.assertIn(FEATURES_TOOL, text)

    def test_detector_flags_instructions_not_prose(self):
        self.assertTrue(removed_key_instructions("   status: draft  # x"))
        self.assertTrue(removed_key_instructions("Update `status:` to `approved`."))
        self.assertTrue(removed_key_instructions("Edit the PLAN frontmatter to set `run_status: running`."))
        self.assertFalse(removed_key_instructions("Read feature.json's `status` and `plan.halted_at`."))
        self.assertFalse(removed_key_instructions("Skip specs whose status is `implemented`."))

    def test_spec_md(self):
        text = self.command("spec.md")
        self.assertIn("features.py new", text)
        self.assertIn("features.py approve", text)
        self.assertAllowsFeatures(text)
        self.assertNoRemovedKeys(text)
        self.assertNoOldLayout(text)

    def test_explore_plan_md(self):
        text = self.command("explore-plan.md")
        self.assertIn("features.py new", text)
        self.assertIn("features.py plan", text)
        self.assertIn("--steps", text)
        self.assertIn("--replace", text)
        self.assertIn("list --json", text)
        self.assertAllowsFeatures(text)
        self.assertNoRemovedKeys(text)
        self.assertNoOldLayout(text)
        draft = branch_after(text, r"`draft`")
        self.assertIn("AskUserQuestion", draft)
        self.assertIn("features.py approve", draft)
        self.assertIn("/feature-dev:review", draft)
        sibling = branch_after(text, r"(?i)sibling")
        self.assertRegex(sibling, r"new (<\S+> )?--kind plan")
        self.assertRegex(sibling, r"without `--spec`")
        self.assertRegex(sibling, r"(?i)by path")

    def test_review_md(self):
        text = self.command("review.md")
        self.assertIn("features.py approve", text)
        self.assertIn("features.py list --json", text)
        self.assertAllowsFeatures(text)
        self.assertNotIn("settle", text)
        self.assertNoRemovedKeys(text)
        self.assertNoOldLayout(text)

    def test_cleanup_md(self):
        text = self.command("cleanup.md")
        self.assertIn("features.py list --json", text)
        self.assertIn("features.py delete", text)
        self.assertAllowsFeatures(text)
        deletes = [line for line in text.splitlines() if "features.py delete" in line]
        self.assertTrue(any("--dry-run" in line for line in deletes), "no --dry-run delete")
        self.assertRegex(text, r"features\.py delete[^\n]*--dry-run")
        self.assertIsNone(re.search(r"purge[^\n]*--artifact", text))
        self.assertNotIn("--slug", text)
        self.assertNoOldLayout(text)

    def test_tdd_md(self):
        text = self.command("tdd.md")
        self.assertIn("features.py list --json", text)
        self.assertRegex(text, r"features\.py step \S+ done")
        self.assertRegex(text, r"features\.py step \S+ halt \S+ --reason")
        self.assertRegex(text, r"features\.py step \S+ resume")
        self.assertRegex(text, r"features\.py step \S+ reopen")
        self.assertIn("features.py implemented", text)
        self.assertRegex(text, r"features\.py plan \S+ --steps [^\n]*--from-spec")
        self.assertAllowsFeatures(text)
        draft = branch_after(text, r"`draft`")
        self.assertIn("AskUserQuestion", draft)
        self.assertIn("features.py approve", draft)
        for key in ("completed_steps", "run_status", "halted_at", "halt_reason"):
            self.assertIsNone(re.search(rf"(?<![\w.]){key}:", text), key)
        self.assertNoRemovedKeys(text)
        self.assertIsNone(re.search(r"(?i)delete the PLAN", text))
        self.assertNoOldLayout(text)

    def test_issue_store_md(self):
        text = ISSUE_STORE.read_text(encoding="utf-8")
        self.assertRegex(text, r"features\.py link-issue \S+ <owner/repo#N> <fingerprint>")
        self.assertRegex(text, r"new (<\S+> )?--kind spec")
        self.assertIn("approve", text)
        self.assertIn("list --json", text)
        self.assertIn("issue.ref", text)
        self.assertNoRemovedKeys(text)
        self.assertNoOldLayout(text)

    def test_commands_refuse_old_layout(self):
        for name in ("spec.md", "spec-review.md", "plan-review.md",
                     "review.md", "tdd.md", "explore-plan.md"):
            text = self.command(name)
            refusals = [line for line in text.splitlines()
                        if _REFUSAL_DIR in line and re.search(r"(?i)refus", line)]
            self.assertTrue(refusals, f"{name}: no old-layout refusal line")
        for name in ("spec-review.md", "plan-review.md"):
            text = self.command(name)
            self.assertIn("list --json", text, name)
            self.assertNotIn("artifacts_dir", text, name)
            self.assertNotIn("source_spec", text, name)


if __name__ == "__main__":
    unittest.main()
