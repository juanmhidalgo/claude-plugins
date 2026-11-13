#!/usr/bin/env python3
"""Tests for agent_bash_guard.py and agent-bash-guard.sh. Standard library only.

Run from anywhere:  python3 shared/agent-bash-guard/tests/test_agent_bash_guard.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import agent_bash_guard as g  # noqa: E402

REPO = "/home/u/repo"

# Commands read-only agents ran, or would run, that must pass. Several are
# regressions from replaying the guard over real transcripts.
ALLOWED = [
    "grep -rn 'def foo' src | head -20",
    "cd /home/u/repo && git diff master...HEAD --stat | tail -5",
    "git log --oneline -5 -- app/x.py; git show abc123:app/x.py | sed -n 1,40p",
    "git diff",
    "git branch --show-current; git stash list; git status --short",
    "git -C ../other log -3",
    "sed -n '10,20p' app/models.py",
    "cat > /tmp/claude-1000/x/scratchpad/report.md <<'EOF'\n# Report\n> quoted line\nrm -rf /\nEOF",
    "mkdir -p /tmp/claude-1000/x/scratchpad && echo ok > /tmp/claude-1000/x/scratchpad/a.txt",
    "S=/tmp/claude-1000/x/scratchpad; mkdir -p $S; git diff > $S/diff.txt",
    "mkdir -p $(dirname /tmp/claude-1000/x/scratchpad/out/r.md)",
    "cd /tmp/claude-1000/pr26 && for p in a b; do gh api repos/o/r/contents/$p | jq -r .content | base64 -d > s_$(basename $p); done",
    "f=$(python3 -c \"import pre_commit,os;print(os.path.dirname(pre_commit.__file__))\" 2>/dev/null); grep -n x $f/a.py",
    "N=$(uv run python -c \"import ninja,os;print(os.path.dirname(ninja.__file__))\" 2>/dev/null); echo $N",
    "git ls-files | grep -i dockerfile | xargs grep -n '^FROM'",
    "find . -name feature.json -not -path './.git/*' -exec cat {} \\;",
    "for p in a b; do grep -n \"$p\" src/*.py; done",
    "python3 -I - <<'EOF'\nimport json\nopen('/etc/x','w')\nEOF",
    "bash -c 'grep -rn foo . | head'",
    "gh pr view 12 --json title; gh pr diff 12 | head; gh issue view 3 --comments",
    "gh api repos/o/r/pulls/1/comments --paginate",
    "gh api -X GET repos/o/r/issues -f state=open",
    "awk '{print $1}' file.txt | sort | uniq -c",
    "timeout 30 grep -rn x .",
    "echo $((1 + 2))",
    "grep -E 'a|b' x.py 2>&1 | head",
    "ls -la 2>/dev/null >/dev/null",
]

# (command, rule prefix) that must be caught.
DENIED = [
    ("echo x > app/x.py", "write-outside-tmp"),
    ("cd /home/u/repo && echo x >> notes.md", "write-outside-tmp"),
    ("git diff | tee review.txt", "write-outside-tmp"),
    ("mkdir -p build/out", "write-outside-tmp"),
    ("sed -i 's/a/b/' app/x.py", "write-outside-tmp"),
    ("sed -Ei 's/a/b/' app/x.py", "write-outside-tmp"),
    ("sort -o data.txt data.txt", "write-outside-tmp"),
    ("git diff --output=patch.diff", "write-outside-tmp"),
    ("cat x > $UNKNOWN/out.txt", "write-unresolved"),
    ("rm -rf build", "file-mutation"),
    ("mv a b", "file-mutation"),
    ("grep -l x . | xargs rm", "file-mutation"),
    ("find . -name '*.pyc' -delete", "find-action"),
    ("find . -name x -exec rm {} \\;", "find -exec"),
    ("awk '{system(\"rm \" $1)}' list", "awk-write"),
    ("awk '{print > \"out\"}' in", "awk-write"),
    ("git checkout main", "git-write"),
    ("git fetch origin", "git-write"),
    ("git commit -m x", "git-write"),
    ("git push", "git-write"),
    ("git stash", "git-write"),
    ("git stash pop", "git-write"),
    ("git branch -D old", "git-write"),
    ("git branch new-branch", "git-write"),
    ("git config user.name x", "git-write"),
    ("git -C /home/u/repo reset --hard", "git-write"),
    ("gh pr comment 1 --body x", "gh-write"),
    ("gh -R o/r issue close 3", "gh-write"),
    ("gh api -X POST repos/o/r/issues", "gh-write"),
    ("gh api repos/o/r/issues -f title=x", "gh-write"),
    ("python3 scripts/sync_shared.py", "run-script"),
    ("python -m pip install x", "run-script"),
    ("bash deploy.sh", "run-script"),
    ("./manage.py migrate", "run-tool"),
    ("npm install", "run-tool"),
    ("make build", "run-tool"),
    ("uv pip install x", "run-tool"),
    ("uv run python scripts/x.py", "run-script"),
    ("bash -c 'rm -rf build'", "file-mutation"),
    ("echo $(git checkout main)", "git-write"),
    ("curl -X POST https://example.com", "run-tool"),
]


class CommandTest(unittest.TestCase):
    def test_allowed(self):
        for command in ALLOWED:
            with self.subTest(command=command):
                self.assertIsNone(g.check_command(command, g.Context(REPO)))

    def test_denied(self):
        for command, rule in DENIED:
            with self.subTest(command=command):
                broken = g.check_command(command, g.Context(REPO))
                self.assertIsNotNone(broken)
                self.assertTrue((broken or "").startswith(rule), broken)

    def test_relative_write_with_unknown_cwd_is_unresolved(self):
        self.assertTrue((g.check_command("echo x > out.txt", g.Context(None)) or "").startswith("write-unresolved"))

    def test_cd_into_tmp_makes_relative_writes_fine(self):
        self.assertIsNone(g.check_command("cd /tmp/work && echo x > out.txt", g.Context(REPO)))
        self.assertIsNotNone(g.check_command("cd /tmp/work && cd /home/u && echo x > out.txt", g.Context(REPO)))

    def test_dotdot_out_of_tmp(self):
        self.assertTrue((g.check_command("echo x > /tmp/../etc/x", g.Context(REPO)) or "").startswith("write-outside-tmp"))


    def test_quoted_redirect_operator_is_an_argument(self):
        for command in ("grep -n '>' README.md", "echo '>x'", 'printf "%s" ">>"'):
            with self.subTest(command=command):
                self.assertIsNone(g.check_command(command, g.Context(REPO)))
        self.assertTrue((g.check_command("echo hi > out.txt", g.Context(REPO)) or "").startswith("write-outside-tmp"))
        self.assertTrue((g.check_command('echo hi >"/etc/x"', g.Context(REPO)) or "").startswith("write-outside-tmp"))

    def test_redirect_glued_to_an_argument(self):
        for command in ("git diff HEAD>x.patch", "echo hi>>notes.md", "grep x a.py>out"):
            with self.subTest(command=command):
                self.assertTrue((g.check_command(command, g.Context(REPO)) or "").startswith("write-outside-tmp"))
        for command in ("git diff HEAD>/tmp/x.patch", "grep 'a>b' x.py", "grep a x.py 2>/dev/null", "ls 2>&1"):
            with self.subTest(command=command):
                self.assertIsNone(g.check_command(command, g.Context(REPO)))

    def test_quote_scanner_agrees_with_shlex(self):
        corpus = ["grep -n 'a b' \"c d\" e\\ f", "echo a\x0cb", "printf '%s\\n' x", "echo \"a\\\"b\" 'c'\"d\"",
                  "git log --format='%h %s' -- x", "echo a\tb\rc"]
        for command in corpus:
            with self.subTest(command=command):
                self.assertEqual([w for w, _ in g._quote_masks(command)], g.shlex.split(command, posix=True))


class AgentTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".claude-plugin").mkdir()
        (self.root / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": "demo"}))
        (self.root / "agents").mkdir()
        agents = {
            "reader": "Read, Grep, Glob, Bash(git diff *), Bash(python3 -B *lint.py *)",
            "builder": "Read, Write, Edit, Bash",
            "free": "Read, Bash",
            "searcher": "Read, Grep, Glob",
            "writer": "Read, Write, Bash(git diff *)",
        }
        for name, tools in agents.items():
            (self.root / "agents" / f"{name}.md").write_text(f"---\nname: {name}\ntools: {tools}\n---\nbody\n")
        self.log = self.root / "audit.jsonl"
        os.environ["AGENT_BASH_GUARD_LOG"] = str(self.log)

    def tearDown(self):
        os.environ.pop("AGENT_BASH_GUARD_LOG", None)
        self._tmp.cleanup()

    def payload(self, command: str, agent_type: str | None = "demo:reader", tool: str = "Bash") -> str:
        data = {"tool_name": tool, "tool_input": {"command": command}, "session_id": "s", "cwd": REPO}
        if agent_type is not None:
            data["agent_type"] = agent_type
        return json.dumps(data)

    def records(self) -> list[dict]:
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_which_agents_are_guarded(self):
        self.assertEqual(g.bash_patterns(self.root, "reader"), ["git diff *", "python3 -B *lint.py *"])
        for name in ("builder", "free", "searcher", "writer", "missing", "../x"):
            with self.subTest(agent=name):
                self.assertIsNone(g.bash_patterns(self.root, name))

    def test_declared_pattern_passes_even_when_a_rule_would_not(self):
        self.assertIsNone(g.check_for_agent("python3 -B /p/scripts/lint.py SPEC.md --json", ["python3 -B *lint.py *"], REPO))
        self.assertIsNotNone(g.check_for_agent("python3 /p/scripts/other.py", ["python3 -B *lint.py *"], REPO))

    def test_declared_prefix_does_not_exempt_chained_or_redirected_commands(self):
        pats = ["git diff *"]
        for cmd in ("git diff > x.patch", "git diff && rm -rf b", "git diff $(git stash)", "git diff\nrm x",
                    "git diff | tee review.txt"):
            with self.subTest(cmd=cmd):
                self.assertIsNotNone(g.check_for_agent(cmd, pats, REPO))
        self.assertIsNone(g.check_for_agent("git diff master...HEAD", pats, REPO))
        self.assertIsNone(g.check_for_agent("git diff 2>&1", pats, REPO))
        self.assertIsNone(g.check_for_agent("python3 -B /p/scripts/lint_artifact.py SPEC.md --json",
                                            ["python3 -B *lint_artifact.py *"], REPO))
        self.assertIsNotNone(g.check_for_agent("git diff master...HEAD>review.patch", pats, REPO))
        self.assertIsNotNone(g.check_for_agent("git diff --output=review.patch", pats, REPO))
        self.assertIsNone(g.check_for_agent("git diff --output=/tmp/x/review.patch", pats, REPO))

    def test_declared_pattern_matches_the_written_spelling(self):
        lint = ["python3 -B *lint_artifact.py *"]
        for cmd in ("python3 -B ~/p/scripts/lint_artifact.py SPEC.md --json",
                    "python3 -B $ROOT/scripts/lint_artifact.py SPEC.md --json",
                    "python3 -B /p/scripts/lint_artifact.py SPEC.md --json 2>&1"):
            with self.subTest(cmd=cmd):
                self.assertIsNone(g.check_for_agent(cmd, lint, REPO))
        self.assertIsNone(g.check_for_agent("git log --format='%h' x", ["git log --format='%h' *"], REPO))

    def test_main_session_and_other_plugins_are_ignored(self):
        self.assertEqual(g.hook(self.payload("rm -rf x", None), self.root, "enforce"), "")
        self.assertEqual(g.hook(self.payload("rm -rf x", "other:reader"), self.root, "enforce"), "")
        self.assertEqual(g.hook(self.payload("rm -rf x", "demo:free"), self.root, "enforce"), "")
        self.assertEqual(g.hook(self.payload("rm -rf x", tool="Read"), self.root, "enforce"), "")
        self.assertEqual(self.records(), [])

    def test_audit_never_blocks_and_logs(self):
        self.assertEqual(g.hook(self.payload("rm -rf x"), self.root, "audit"), "")
        self.assertEqual(g.hook(self.payload("git diff"), self.root, "audit"), "")
        decisions = [(r["decision"], r.get("rule", "")[:13]) for r in self.records()]
        self.assertEqual(decisions, [("would-deny", "file-mutation"), ("allow", "")])
        self.assertEqual(self.records()[0]["agent_type"], "demo:reader")

    def test_enforce_denies_with_reason(self):
        out = json.loads(g.hook(self.payload("git checkout main"), self.root, "enforce"))
        spec = out["hookSpecificOutput"]
        self.assertEqual(spec["permissionDecision"], "deny")
        self.assertIn("git-write: git checkout", spec["permissionDecisionReason"])
        self.assertEqual(self.records()[0]["decision"], "deny")

    def test_off_does_nothing(self):
        self.assertEqual(g.hook(self.payload("rm -rf x"), self.root, "off"), "")
        self.assertEqual(self.records(), [])

    def test_malformed_input(self):
        self.assertEqual(g.hook("not json", self.root, "enforce"), "")
        self.assertEqual(g.hook(json.dumps({"agent_type": "demo:reader", "tool_name": "Bash", "tool_input": None}),
                                self.root, "enforce"), "")

    def test_long_command_is_truncated_in_the_log(self):
        g.hook(self.payload("grep x " + "a" * 1000), self.root, "audit")
        self.assertEqual(len(self.records()[0]["command"]), g.MAX_LOGGED)

    def run_wrapper(self, stdin: str, mode: str) -> subprocess.CompletedProcess:
        env = {**os.environ, "AGENT_BASH_GUARD": mode}
        return subprocess.run(["bash", str(HERE / "agent-bash-guard.sh"), str(self.root)],
                              input=stdin, capture_output=True, text=True, env=env)

    def test_wrapper(self):
        main = self.run_wrapper(self.payload("rm -rf x", None), "enforce")
        self.assertEqual((main.returncode, main.stdout), (0, ""))
        denied = self.run_wrapper(self.payload("rm -rf x"), "enforce")
        self.assertEqual(denied.returncode, 0)
        self.assertEqual(json.loads(denied.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        audited = self.run_wrapper(self.payload("rm -rf x"), "audit")
        self.assertEqual((audited.returncode, audited.stdout), (0, ""))
        off = self.run_wrapper(self.payload("rm -rf x"), "off")
        self.assertEqual((off.returncode, off.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
