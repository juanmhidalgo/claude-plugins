#!/usr/bin/env python3
"""PreToolUse guard for the read-only agents of one plugin. Standard library only.

Canonical copy: shared/agent-bash-guard/ (shared/sync.sh copies it into each
plugin's scripts/). Invoked by agent-bash-guard.sh with the plugin root as the
only argument and the hook's JSON on stdin.

Which calls it looks at: a Bash call made by a subagent (the hook input carries
``agent_type`` = ``<plugin>:<agent>``) of THIS plugin, whose ``tools:`` line
lists Bash only with patterns (``Bash(git diff *)``) and no Write/Edit. The main
session, other plugins' agents, and agents granted plain ``Bash`` are left
alone.

What it decides: a deny-list of commands that change something — writes
outside /tmp, file mutation, git and gh commands that write, scripts and build
tools. Everything else is allowed. A segment that matches one of the agent's
own declared Bash patterns is allowed when it is one plain command: separators,
``$(...)`` and backticks disqualify it, and its redirections and
``--output=`` targets are checked before the match. This is text matching, not a
sandbox: it raises the cost of an accidental write, it does not stop a
determined one. A write whose target it cannot resolve (an unknown variable, a
command substitution) gets its own rule, ``write-unresolved``.

Mode, from AGENT_BASH_GUARD (default ``audit``):
  audit    never blocks; logs every decision
  enforce  denies (permissionDecision: deny, with the reason) and logs
  off      does nothing

Log: one JSON line per decision in
``${CLAUDE_CONFIG_DIR:-~/.claude}/agent-bash-guard/audit.jsonl`` (override with
AGENT_BASH_GUARD_LOG). The command is truncated to 300 characters.

Fails open: any error inside the guard allows the command and logs the error.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import shlex
import sys
import time
from pathlib import Path

MAX_LOGGED = 300
UNRESOLVED = "\0"  # marks a path piece the guard could not expand

FILE_MUTATION = {"rm", "rmdir", "mv", "cp", "touch", "chmod", "chown", "chgrp", "ln", "truncate",
                 "dd", "install", "shred", "unlink", "mkfifo", "rsync", "scp"}
INTERPRETERS = {"python", "python3", "node", "ruby", "perl", "bash", "sh", "zsh", "dash", "deno",
                "bun", "php", "lua"}
SHELLS = {"bash", "sh", "zsh", "dash"}
RUNNERS = {"npm", "npx", "pnpm", "yarn", "uvx", "pip", "pip3", "pipx", "make", "cargo", "mvn",
           "gradle", "pytest", "tox", "nox", "docker", "podman", "kubectl", "helm", "terraform",
           "ansible-playbook", "brew", "apt", "apt-get", "sudo", "go", "rake", "bundle", "composer",
           "manage.py", "django-admin", "alembic", "flask", "claude", "curl", "wget"}
RUN_WRAPPERS = {"uv", "poetry", "pdm", "hatch", "pipenv"}  # `<tool> run <cmd>` runs <cmd>
WRAPPERS = {"timeout", "env", "nice", "nohup", "command", "time", "stdbuf"}
KEYWORDS = {"do", "then", "else", "elif", "if", "while", "until", "!", "{", "(", "}", ")", "done", "fi"}

GIT_WRITE = {"checkout", "switch", "reset", "restore", "clean", "commit", "add", "rm", "mv", "push",
             "pull", "fetch", "rebase", "merge", "cherry-pick", "revert", "am", "apply", "tag",
             "notes", "gc", "prune", "update-ref", "update-index", "init", "clone", "submodule",
             "bisect", "filter-branch", "replace", "maintenance", "sparse-checkout", "lfs"}
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}

GH_WRITE = {
    "pr": {"create", "edit", "merge", "close", "reopen", "comment", "review", "ready", "checkout", "lock", "unlock", "update-branch"},
    "issue": {"create", "edit", "close", "reopen", "comment", "delete", "transfer", "lock", "unlock", "pin", "unpin", "develop"},
    "release": {"create", "delete", "edit", "upload", "delete-asset"},
    "repo": {"create", "delete", "edit", "fork", "clone", "rename", "archive", "unarchive", "sync", "set-default"},
    "label": {"create", "edit", "delete", "clone"},
    "workflow": {"run", "enable", "disable"},
    "run": {"rerun", "cancel", "delete", "download"},
    "secret": {"set", "delete"},
    "variable": {"set", "delete"},
    "gist": {"create", "edit", "delete", "clone"},
    "project": {"create", "edit", "delete", "close", "copy", "item-add", "item-edit", "item-delete",
                "item-archive", "field-create", "field-delete", "link", "unlink"},
    "cache": {"delete"},
}
GH_VALUE_FLAGS = {"-R", "--repo", "-X", "--method", "-H", "--header", "-q", "--jq", "-t", "--template",
                  "-f", "-F", "--field", "--raw-field", "--input", "--hostname"}
GH_API_FIELDS = ("-f", "-F", "--field", "--raw-field", "--input")

HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1([^\n]*)\n.*?\n[ \t]*\2[ \t]*(?=\n|$)", re.DOTALL)
REDIRECT = re.compile(r"^(?:\d*|&)(>>?|>\|)(.*)$")
ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.DOTALL)
VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")


class Context:
    """Shell state carried across the segments of one command: variables and cwd."""

    def __init__(self, cwd: str | None = None, env: dict[str, str] | None = None):
        self.cwd = cwd
        self.env = {"TMPDIR": os.environ.get("TMPDIR", "/tmp"), "HOME": str(Path.home())}
        self.env.update(env or {})

    def expand(self, word: str) -> str:
        def var(m: re.Match) -> str:
            return self.env.get(m.group(1) or m.group(2), UNRESOLVED)
        return VARIABLE.sub(var, word)

    def path(self, word: str) -> str | None:
        """Absolute normalized path for ``word``, or None when it cannot be known."""
        value = self.expand(word)
        if UNRESOLVED in value or "$" in value:
            # an unknown file name in a known directory (`> s_$(basename $p)`)
            head, tail = os.path.split(value)
            if (UNRESOLVED in tail or "$" in tail) and UNRESOLVED not in head and "$" not in head:
                known = self.path(head or ".")
                return os.path.join(known, "_") if known else None
            return None
        if value.startswith("~"):
            value = self.env["HOME"] + value[1:]
        if not value.startswith("/"):
            if self.cwd is None:
                return None
            value = os.path.join(self.cwd, value)
        return os.path.normpath(value)


# --- parsing ------------------------------------------------------------------


def strip_heredocs(command: str) -> str:
    """Drop heredoc bodies; the ``cat > file <<'EOF'`` line keeps its redirection."""
    return HEREDOC.sub(lambda m: m.group(3), command)


def replace_subshells(command: str) -> tuple[str, list[str]]:
    """Command with each ``$(...)``/backtick replaced, and the inner commands.

    ``$(dirname X)`` and ``$(basename X)`` with a literal argument are evaluated,
    so ``mkdir -p $(dirname /tmp/a/b)`` keeps a known target; any other
    substitution becomes the UNRESOLVED marker.
    """
    inner: list[str] = []

    def sub(body: str) -> str:
        inner.append(body)
        words = tokens(body) or []
        if len(words) == 2 and words[0] in ("dirname", "basename") and "$" not in words[1]:
            return os.path.dirname(words[1]) if words[0] == "dirname" else os.path.basename(words[1])
        return UNRESOLVED

    out, i = [], 0
    while i < len(command):
        if command.startswith("$(", i) and not command.startswith("$((", i):
            end = _closing_paren(command, i + 2)
            if end is None:
                out.append(command[i:])
                break
            out.append(sub(command[i + 2:end]))
            i = end + 1
        elif command[i] == "`":
            end = command.find("`", i + 1)
            if end < 0:
                out.append(command[i:])
                break
            out.append(sub(command[i + 1:end]))
            i = end + 1
        elif command[i] == "'":  # single quotes: no substitution inside
            end = command.find("'", i + 1)
            end = len(command) - 1 if end < 0 else end
            out.append(command[i:end + 1])
            i = end + 1
        else:
            out.append(command[i])
            i += 1
    return "".join(out), inner


def _closing_paren(command: str, start: int) -> int | None:
    """Index of the ``)`` closing a ``$(`` whose body starts at ``start``."""
    depth, quote, i = 1, None, start
    while i < len(command):
        ch = command[i]
        if quote:
            if ch == "\\" and quote == '"':
                i += 1
            elif ch == quote:
                quote = None
        elif ch == "\\":
            i += 1
        elif ch in "'\"":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def split_segments(command: str) -> list[str]:
    """Split on unquoted ``&&``, ``||``, ``;``, ``|``, ``&`` and newlines."""
    segments, cur, quote, i = [], [], None, 0
    while i < len(command):
        ch = command[i]
        if quote:
            cur.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < len(command):
                cur.append(command[i + 1])
                i += 1
            elif ch == quote:
                quote = None
        elif ch == "\\" and i + 1 < len(command):
            cur.append(ch + command[i + 1])
            i += 1
        elif ch in "'\"":
            quote = ch
            cur.append(ch)
        elif ch in ";\n" or (ch in "|&" and not _is_redirect_amp(command, i)):
            segments.append("".join(cur))
            cur = []
            if i + 1 < len(command) and command[i + 1] == ch and ch in "|&":
                i += 1
        else:
            cur.append(ch)
        i += 1
    segments.append("".join(cur))
    return [s.strip() for s in segments if s.strip()]


def _is_redirect_amp(command: str, i: int) -> bool:
    """``2>&1``, ``>&2``, ``&>file`` and ``>|`` are redirections, not separators."""
    prev = command[i - 1] if i else ""
    nxt = command[i + 1] if i + 1 < len(command) else ""
    if command[i] == "&":
        return prev in "<>" or nxt == ">"
    return prev == ">"


class Word(str):
    """A shlex word that remembers which of its characters were quoted or escaped."""

    quoted: tuple[bool, ...] = ()


def _quote_masks(segment: str) -> list[tuple[str, tuple[bool, ...]]]:
    """Words of ``segment`` as shlex (posix) splits them, with a per-character
    "came from inside quotes or after a backslash" mask."""
    words, chars, mask, started, quote, i = [], [], [], False, None, 0
    while i < len(segment):
        ch = segment[i]
        if quote == "'":
            if ch == "'":
                quote = None
            else:
                chars.append(ch)
                mask.append(True)
        elif quote == '"':
            if ch == '"':
                quote = None
            elif ch == "\\" and i + 1 < len(segment) and segment[i + 1] in '"\\':
                i += 1
                chars.append(segment[i])
                mask.append(True)
            else:
                chars.append(ch)
                mask.append(True)
        elif ch in " \t\r\n":  # shlex's whitespace, not str.isspace()
            if started:
                words.append(("".join(chars), tuple(mask)))
                chars, mask, started = [], [], False
        elif ch in "'\"":
            quote, started = ch, True
        elif ch == "\\" and i + 1 < len(segment):
            i += 1
            chars.append(segment[i])
            mask.append(True)
            started = True
        else:
            chars.append(ch)
            mask.append(False)
            started = True
        i += 1
    if started:
        words.append(("".join(chars), tuple(mask)))
    return words


def tokens(segment: str) -> list[str] | None:
    try:
        split = shlex.split(segment, comments=False, posix=True)
    except ValueError:
        return None
    masked = _quote_masks(segment)
    if [w for w, _ in masked] != split:
        return split  # scanners disagree: no quote information
    out = []
    for w, mask in masked:
        word = Word(w)
        word.quoted = mask
        out.append(word)
    return out


# --- rules --------------------------------------------------------------------


def _under_tmp(path: str) -> bool:
    return path == "/tmp" or path.startswith("/tmp/")


def _write_rule(ctx: Context, what: str, target: str) -> str | None:
    """None when writing ``target`` is fine (under /tmp), else the rule broken."""
    if target in ("/dev/null", "/dev/stdout", "/dev/stderr") or target.startswith("&"):
        return None
    path = ctx.path(target)
    if path is None:
        return f"write-unresolved: {what} {target.replace(UNRESOLVED, '$(...)')!r}"
    return None if _under_tmp(path) else f"write-outside-tmp: {what} {path!r}"


def _inner_redirect(word: str, quoted: tuple[bool, ...]) -> int:
    """Index of an unquoted ``>`` inside ``word`` that starts a redirection
    after an argument (``HEAD>x``), else 0. A leading fd (``2>``, ``&>``) is
    left to REDIRECT."""
    for j, ch in enumerate(word):
        if ch == ">" and not (j < len(quoted) and quoted[j]):
            head = word[:j]
            if not head or re.fullmatch(r"\d*|&", head):
                return 0
            return j
    return 0


def _redirects(words: list[str]) -> tuple[list[str], list[str]]:
    """(words without redirections, redirection targets that write)."""
    rest, targets, skip = [], [], False
    for i, w in enumerate(words):
        if skip:
            skip = False
            continue
        quoted = getattr(w, "quoted", ())
        cut = _inner_redirect(w, quoted)
        if cut:  # `HEAD>out.patch`: the word before the operator is an argument
            rest.append(w[:cut])
            w, quoted = w[cut:], quoted[cut:]
        m = REDIRECT.match(w)
        if m and any(quoted[: m.end(1)]):
            m = None  # the operator came from inside quotes: an argument, not a redirect
        if m:
            target = m.group(2)
            if not target:
                target = words[i + 1] if i + 1 < len(words) else ""
                skip = True
            targets.append(target)
            continue
        rest.append(w)
    return rest, targets


def _program(words: list[str], ctx: Context) -> tuple[str, list[str], list[str]]:
    """(program basename, its args, the words from the program on), past keywords,
    assignments (recorded in ctx) and wrappers."""
    i = 0
    while i < len(words) and words[i] in KEYWORDS:
        i += 1
    while i < len(words):
        assignment = ASSIGNMENT.match(words[i])
        if not assignment:
            break
        ctx.env[assignment.group(1)] = ctx.expand(assignment.group(2))
        i += 1
    while i < len(words) and os.path.basename(words[i]) in WRAPPERS:
        name = os.path.basename(words[i])
        i += 1
        if name == "timeout":
            while i < len(words) and words[i].startswith("-"):
                i += 1
            i += 1  # the duration
        while i < len(words) and (words[i].startswith("-") or ASSIGNMENT.match(words[i])):
            i += 1
    if i >= len(words):
        return "", [], []
    return os.path.basename(words[i]), words[i + 1:], words[i:]


def _positional(args: list[str]) -> list[str]:
    return [a for a in args if not a.startswith("-")]


def check_segment(words: list[str], ctx: Context) -> str | None:
    """The rule a segment breaks, or None when it is allowed."""
    words, targets = _redirects(words)
    for t in targets:
        broken = _write_rule(ctx, "redirect into", t)
        if broken:
            return broken
    prog, args, argv = _program(words, ctx)
    if not prog:
        return None

    if prog == "cd":
        dest = _positional(args)[:1] or ["~"]
        ctx.cwd = ctx.path(dest[0])
        return None
    if prog in FILE_MUTATION:
        return f"file-mutation: {prog}"
    if prog in ("mkdir", "tee"):
        for a in _positional(args):
            broken = _write_rule(ctx, prog, a)
            if broken:
                return broken
        return None
    if prog in ("sed", "gsed"):
        inplace = any(a == "--in-place" or a.startswith("--in-place=") or
                      (a.startswith("-") and not a.startswith("--") and "i" in a[1:]) for a in args)
        if inplace:
            for f in _positional(args)[1:]:
                broken = _write_rule(ctx, "sed -i", f)
                if broken:
                    return broken
        return None
    if prog == "sort":
        for i, a in enumerate(args):
            if a == "-o" and i + 1 < len(args):
                return _write_rule(ctx, "sort -o", args[i + 1])
            if a.startswith("--output="):
                return _write_rule(ctx, "sort --output", a.split("=", 1)[1])
        return None
    if prog == "find":
        return _find(args, ctx)
    if prog == "xargs":
        i = 0
        while i < len(args) and args[i].startswith("-"):
            i += 2 if args[i] in ("-I", "-n", "-P", "-L", "-s", "-d", "-E", "-a") else 1
        return check_segment(args[i:], ctx) if i < len(args) else None
    if prog in ("awk", "gawk", "mawk"):
        program = " ".join(args)
        if "system(" in program or re.search(r"print[^;{}]*>", program) or "|&" in program:
            return "awk-write: system() or print redirection"
        return None
    if prog == "git":
        return _git(args, ctx)
    if prog == "gh":
        return _gh(args)
    if prog in RUN_WRAPPERS:
        pos = _positional(args)
        if pos[:1] == ["run"]:
            return check_segment(args[args.index("run") + 1:], ctx)
        return f"run-tool: {prog} {' '.join(pos[:1])}".rstrip()
    if prog in INTERPRETERS or re.fullmatch(r"python3?\.\d+", prog):
        return _interpreter(prog, args, ctx)
    if prog in RUNNERS:
        return f"run-tool: {prog}"
    if prog.endswith((".sh", ".py", ".js", ".rb", ".pl")) or argv[0].startswith(("./", "../")):
        return f"run-script: {argv[0]}"
    return None


def _find(args: list[str], ctx: Context) -> str | None:
    for i, a in enumerate(args):
        if a == "-delete" or a.startswith("-fprint") or a == "-fls":
            return f"find-action: {a}"
        if a in ("-exec", "-execdir", "-ok", "-okdir"):
            end = next((j for j in range(i + 1, len(args)) if args[j] in (";", "+")), len(args))
            inner = [w for w in args[i + 1:end] if w != "{}"]
            broken = check_segment(inner, ctx) if inner else None
            if broken:
                return f"find {a}: {broken}"
    return None


def _git(args: list[str], ctx: Context) -> str | None:
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in GIT_OPTS_WITH_VALUE else 1
    if i >= len(args):
        return None
    sub, rest = args[i], args[i + 1:]
    if sub in GIT_WRITE and not (sub == "submodule" and rest[:1] in (["status"], ["summary"])):
        return f"git-write: git {sub}"
    if sub == "stash" and rest[:1] not in (["list"], ["show"]):
        return "git-write: git stash"
    if sub == "branch":
        mutating = {"-d", "-D", "--delete", "-m", "-M", "--move", "-c", "-C", "--copy", "-u",
                    "--set-upstream-to", "--unset-upstream", "-f", "--force", "--edit-description"}
        listing = {"--list", "-l", "-a", "--all", "-r", "--remotes", "--show-current", "--contains",
                   "--no-contains", "--merged", "--no-merged", "--points-at", "-v", "-vv"}
        if any(a in mutating for a in rest) or (_positional(rest) and not any(a in listing for a in rest)):
            return "git-write: git branch (create/delete/move)"
    if sub == "worktree" and rest[:1] != ["list"]:
        return f"git-write: git worktree {' '.join(rest[:1])}".rstrip()
    if sub == "config" and not any(a in ("--get", "--get-all", "--get-regexp", "--list", "-l") for a in rest):
        if len(_positional(rest)) >= 2:
            return "git-write: git config <key> <value>"
    if sub == "remote" and rest[:1] and rest[0] in ("add", "remove", "rm", "rename", "set-url", "set-head", "prune", "update"):
        return f"git-write: git remote {rest[0]}"
    if sub == "reflog" and rest[:1] in (["expire"], ["delete"]):
        return f"git-write: git reflog {rest[0]}"
    for a in rest:
        if a.startswith("--output="):
            return _write_rule(ctx, f"git {sub} --output", a.split("=", 1)[1])
    return None


def _gh(args: list[str]) -> str | None:
    pos, skip = [], False
    for a in args:
        if skip:
            skip = False
        elif a in GH_VALUE_FLAGS:
            skip = True
        elif not a.startswith("-"):
            pos.append(a)
    if not pos:
        return None
    if pos[0] == "api":
        method = _flag_value(args, ("-X", "--method"))
        if method:
            return None if method.upper() == "GET" else f"gh-write: gh api -X {method}"
        if any(a in GH_API_FIELDS or a.startswith(tuple(f + "=" for f in GH_API_FIELDS if f.startswith("--")))
               for a in args):
            return "gh-write: gh api with fields (defaults to POST)"
        return None
    if pos[0] in GH_WRITE and len(pos) > 1 and pos[1] in GH_WRITE[pos[0]]:
        return f"gh-write: gh {pos[0]} {pos[1]}"
    return None


def _flag_value(args: list[str], names: tuple[str, ...]) -> str | None:
    for i, a in enumerate(args):
        for n in names:
            if a == n and i + 1 < len(args):
                return args[i + 1]
            if n.startswith("--") and a.startswith(n + "="):
                return a.split("=", 1)[1]
            if not n.startswith("--") and a.startswith(n) and len(a) > len(n):
                return a[len(n):]
    return None


def _interpreter(prog: str, args: list[str], ctx: Context) -> str | None:
    """Inline code (-c / -e / stdin) is allowed; a script path or -m is not.

    ``bash -c '<cmd>'`` is checked as a command of its own.
    """
    inline_flags = {"-c", "-e", "--eval", "-p", "--print"}
    i = 0
    while i < len(args):
        a = args[i]
        clustered_c = prog.startswith("python") and re.fullmatch(r"-[A-Za-z]*c", a) is not None
        if a in inline_flags or clustered_c:
            if prog in SHELLS and i + 1 < len(args):
                return check_command(args[i + 1], ctx)
            return None
        if a == "-m":
            return f"run-script: {prog} -m {args[i + 1] if i + 1 < len(args) else ''}".rstrip()
        if a == "-":
            return None
        if not a.startswith("-"):
            return f"run-script: {prog} {a}"
        i += 1
    return None  # a bare interpreter reads stdin (a heredoc)


def check_command(command: str, ctx: Context | None = None) -> str | None:
    """The first rule ``command`` breaks, or None. Unparseable segments pass."""
    ctx = ctx or Context()
    command, inner = replace_subshells(strip_heredocs(command))
    for body in inner:
        broken = check_command(body, Context(ctx.cwd, dict(ctx.env)))
        if broken:
            return broken
    for segment in split_segments(command):
        words = tokens(segment)
        if not words:
            continue
        broken = check_segment(words, ctx)
        if broken:
            return broken
    return None


# --- agent declarations -------------------------------------------------------


def plugin_name(root: Path) -> str | None:
    try:
        return json.loads((root / ".claude-plugin" / "plugin.json").read_text()).get("name")
    except (OSError, ValueError):
        return None


def bash_patterns(root: Path, agent: str) -> list[str] | None:
    """The agent's ``Bash(<pattern>)`` entries, or None when it is not a guarded agent.

    Guarded: the agent file exists, its ``tools:`` line has Bash only with
    patterns, and no Write/Edit/NotebookEdit.
    """
    if not re.fullmatch(r"[\w.-]+", agent):
        return None
    try:
        text = (root / "agents" / f"{agent}.md").read_text()
    except OSError:
        return None
    m = re.search(r"^tools:\s*(.+)$", text, re.MULTILINE)
    if not m:
        return None
    tools = m.group(1)
    if re.search(r"\b(Write|Edit|MultiEdit|NotebookEdit)\b", tools):
        return None
    if re.search(r"(^|[,\s])Bash\s*(,|$)", tools) or tools.strip() == "*":
        return None
    return re.findall(r"Bash\(([^)]*)\)", tools) or None


def _plain(text: str) -> bool:
    """True when ``text`` has no active shell metacharacter (separator, redirect,
    backtick, ``$(``, newline) outside single quotes."""
    quote, i = None, 0
    while i < len(text):
        ch = text[i]
        if ch == "\\" and quote != "'" and i + 1 < len(text):
            i += 2
            continue
        if quote == "'":
            if ch == "'":
                quote = None
        elif ch in "`" or (ch == "$" and text[i + 1:i + 2] == "("):
            return False
        elif quote == '"':
            if ch == '"':
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch in ";&|<>\n":
            return False
        i += 1
    return True


def declared(segment: str, patterns: list[str]) -> bool:
    """True when ``segment`` is one plain command matching a declared pattern."""
    segment = segment.strip()
    if not _plain(segment):
        return False
    for p in patterns:
        if fnmatch.fnmatchcase(segment, p) or (p.endswith(" *") and segment == p[:-2]):
            return True
    return False


def check_for_agent(command: str, patterns: list[str], cwd: str | None = None) -> str | None:
    """Like check_command, but a plain segment matching a declared pattern passes.

    Redirections and ``--output=`` targets are checked first, and a segment with
    a separator, ``$(...)`` or a backtick never counts as declared, so a declared
    prefix does not exempt those writes or anything chained after it. Other
    writes a declared program can make through its own flags are not checked.
    """
    ctx = Context(cwd)
    stripped, inner = replace_subshells(strip_heredocs(command))
    for body in inner:
        if not declared(body, patterns):
            broken = check_command(body, Context(ctx.cwd, dict(ctx.env)))
            if broken:
                return broken
    for segment in split_segments(stripped):
        words = tokens(segment)
        if not words:
            continue
        rest, targets = _redirects(words)
        for t in targets:
            broken = _write_rule(ctx, "redirect into", t)
            if broken:
                return broken
        # Match the spelling the agent wrote when nothing was removed, so `~`,
        # `$VAR` and quoted arguments still match their pattern; otherwise the
        # remaining words, joined plainly and shell-quoted.
        forms = ([segment] if not targets else []) + [" ".join(rest), shlex.join(rest)]
        # `--output=<file>` writes without a redirect; check it even when declared.
        outputs = [a.split("=", 1)[1] for a in rest if a.startswith("--output=")]
        for t in outputs:
            broken = _write_rule(ctx, "--output", t)
            if broken:
                return broken
        if any(declared(f, patterns) for f in forms):
            _program(words, ctx)  # still record assignments
            continue
        broken = check_segment(words, ctx)
        if broken:
            return broken
    return None


# --- hook ---------------------------------------------------------------------


def log_path() -> Path:
    override = os.environ.get("AGENT_BASH_GUARD_LOG")
    if override:
        return Path(override)
    base = os.environ.get("CLAUDE_CONFIG_DIR") or str(Path.home() / ".claude")
    return Path(base) / "agent-bash-guard" / "audit.jsonl"


def write_log(record: dict) -> None:
    try:
        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError:
        pass


def hook(stdin: str, root: Path, mode: str) -> str:
    """The hook's stdout for one call (empty unless enforce mode denies)."""
    if mode == "off":
        return ""
    try:
        data = json.loads(stdin)
    except ValueError:
        return ""
    agent_type = data.get("agent_type") if isinstance(data, dict) else None
    if not isinstance(agent_type, str) or data.get("tool_name") != "Bash":
        return ""
    plugin, _, agent = agent_type.partition(":")
    if plugin != plugin_name(root):
        return ""
    patterns = bash_patterns(root, agent)
    if patterns is None:
        return ""
    command = (data.get("tool_input") or {}).get("command") or ""
    record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "mode": mode, "agent_type": agent_type,
              "session_id": data.get("session_id"), "command": command[:MAX_LOGGED]}
    try:
        rule = check_for_agent(command, patterns, data.get("cwd"))
    except Exception as exc:  # fail open
        write_log({**record, "decision": "error", "rule": f"{type(exc).__name__}: {exc}"})
        return ""
    if rule is None:
        write_log({**record, "decision": "allow"})
        return ""
    if mode != "enforce":
        write_log({**record, "decision": "would-deny", "rule": rule})
        return ""
    write_log({**record, "decision": "deny", "rule": rule})
    reason = (f"agent-bash-guard: {agent_type} is a read-only agent and this command changes something "
              f"({rule}). Read with grep/find/cat/sed -n/git diff|show|log instead; write only under /tmp.")
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                              "permissionDecision": "deny",
                                              "permissionDecisionReason": reason}})


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        return 0
    try:
        out = hook(sys.stdin.read(), Path(argv[0]), os.environ.get("AGENT_BASH_GUARD", "audit"))
    except Exception:  # never break a tool call
        return 0
    if out:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
