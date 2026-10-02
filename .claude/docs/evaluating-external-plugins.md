<!-- Moved out of .claude/rules/plugin-creation.md so it loads only when read. -->

## Evaluating an External Plugin Before Replicating It

<external_plugin_evaluation>

**Read its scripts. Never run them.** Auto mode blocks executing code fetched from
a third-party repo (`[Code from External]`) and it is right to — you are evaluating
an approach, not adopting a binary. Reproduce what the script does with your own
commands instead; that is the same work, minus the trust.

**Verify its assumptions against local ground truth before inheriting them.** The
prose in an external plugin describes what the author believed, not what is true
now. Check each load-bearing assumption against real data on this machine before
any of it reaches your version — a plugin that reads Claude Code session logs, for
example, encodes a path, classifies entry types, and counts turns, and every one of
those is checkable in seconds against `~/.claude/projects/`.

**The value is the domain knowledge, not the file.** What is worth taking is the
schema facts, the flags, the edge cases the author hit. What is not worth taking is
the templates, the depth tiers, and the README — those are the parts that will drift
and that you would then own. Prefer a small script plus a lean skill over a port.

**Installing it is not the same as forking it.** A published marketplace plugin can
be installed and trialled directly. Copy it into this repo only when you intend to
diverge from it, and say in the CHANGELOG what you changed and why.

</external_plugin_evaluation>
