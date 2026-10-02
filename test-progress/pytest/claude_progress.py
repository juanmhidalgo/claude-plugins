"""Publish live pytest progress for the Claude Code test-progress mod.

While a run is in progress, writes one tab-separated line to

    ${TMPDIR:-/tmp}/claude-<uid>/test-progress/<CLAUDE_CODE_SESSION_ID>.progress

    runner <TAB> done <TAB> total <TAB> failed <TAB> started_epoch

and removes the file when the run ends. Outside a Claude Code session
(CLAUDE_CODE_SESSION_ID unset) it does nothing.

Enable it for every project:

    export PYTHONPATH="/path/to/test-progress/pytest${PYTHONPATH:+:$PYTHONPATH}"
    export PYTEST_ADDOPTS="-p claude_progress"

or per project, with the directory on PYTHONPATH, in pytest.ini:

    [pytest]
    addopts = -p claude_progress
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import pytest


def _progress_path() -> Path | None:
    session = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not session or "/" in session or session.startswith("."):
        return None
    uid = os.getuid() if hasattr(os, "getuid") else 0
    root = Path(tempfile.gettempdir()) / f"claude-{uid}" / "test-progress"
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    return root / f"{session}.progress"


class ClaudeProgress:
    """Counts finished tests and rewrites the one-line progress file atomically."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        self.started = int(time.time())
        self.total = 0
        self.done = 0
        self.failed_ids: set[str] = set()

    def write(self) -> None:
        line = f"pytest\t{self.done}\t{self.total}\t{len(self.failed_ids)}\t{self.started}\n"
        try:
            self.tmp.write_text(line)
            os.replace(self.tmp, self.path)
        except OSError:
            pass

    def clear(self) -> None:
        for p in (self.tmp, self.path):
            try:
                p.unlink()
            except OSError:
                pass

    def pytest_collection_finish(self, session) -> None:
        self.total = len(session.items)
        self.write()

    # optionalhook: without pytest-xdist installed pluggy does not know this
    # hook, and registering it unguarded aborts the run.
    @pytest.hookimpl(optionalhook=True)
    def pytest_xdist_node_collection_finished(self, node, ids) -> None:
        # Under xdist the controller learns the count from its workers.
        self.total = len(ids)
        self.write()

    def pytest_runtest_logreport(self, report) -> None:
        # A test counts as failed once, whichever phase failed.
        if report.failed:
            self.failed_ids.add(report.nodeid)
        # One teardown report per test, on the xdist controller too.
        if report.when == "teardown":
            self.done += 1
            self.write()

    def pytest_sessionfinish(self, session, exitstatus) -> None:
        self.clear()

    def pytest_unconfigure(self, config) -> None:
        # Also on a run that aborts before sessionfinish (KeyboardInterrupt).
        self.clear()


def pytest_configure(config) -> None:
    # xdist workers stay quiet: only the controller sees every test once.
    if hasattr(config, "workerinput"):
        return
    path = _progress_path()
    if path is None:
        return
    config.pluginmanager.register(ClaudeProgress(path), "claude_progress_reporter")
