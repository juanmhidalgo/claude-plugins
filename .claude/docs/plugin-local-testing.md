<!-- Moved out of .claude/rules/plugin-creation.md so it loads only when read. -->

## Local Testing

<local_testing>

Load plugins straight from the working tree with `--plugin-dir`, instead of
installing from the marketplace. Requires Claude Code 2.1.265+.

**Never point `--plugin-dir` at the repo root.** A folder fans out into one
plugin per child *only when the folder itself has no `.claude-plugin/`*. This
repo's root has `.claude-plugin/marketplace.json`, so `--plugin-dir .` loads the
whole repo as a **single** plugin with 0 commands, 0 skills, 0 agents — and
still reports `Status: loaded`. The no-op is silent.

Load the plugins under test by relative path:

```bash
claude --plugin-dir code-review --plugin-dir discuss
```

Or every plugin in the repo (zsh and bash):

```bash
flags=(); for d in */.claude-plugin/plugin.json; do flags+=(--plugin-dir "${d%%/*}"); done
claude "${flags[@]}"
```

Confirm what actually loaded before trusting a test run — session-only plugins
appear under `Session-only plugins` as `<name>@inline`:

```bash
claude "${flags[@]}" plugin list
claude --plugin-dir code-review plugin details code-review   # inventory + token cost
```

The installed copy of the same plugin stays enabled alongside the inline one, so
a name can be live two or three times over (user scope, project scope, inline).
When a command's behaviour is ambiguous, `plugin disable <name>@<marketplace>`
the installed copy for the duration of the test.

</local_testing>
