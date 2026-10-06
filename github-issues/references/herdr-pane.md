# Running a command in a Herdr pane

<!-- Canonical copy: shared/herdr-pane/herdr-pane.md. Every plugin's
references/herdr-pane.md is a synced copy — edit the canonical one, then run
shared/sync.sh. -->

A command that supports `--pane` can run itself as a **separate top-level Claude
Code session** in another Herdr pane, instead of a subagent of this session or
inline here. Compared with a subagent, the pane:

- **does not block this session.** You keep working, and this session is
  re-invoked when the pane finishes.
- **can fan out.** It is a top-level session, so its own subagents (verifiers,
  parallel reviewers) dispatch the same way they would anywhere else.
- **stays open for follow-up.** The user can question it in its pane, with its
  context intact (`herdr agent focus <agent>`).

The command that sent you here names its **mode** (collect, worktree or
handoff), the **command string** to send, and **how to present** what comes back.
This file holds everything those commands have in common.

## When

Use the pane when `--no-pane` is not in the arguments **and** either:

- `--pane` is in the arguments, or
- the command names a configured option for it (e.g. `review_in_pane`) and that
  option is `true`. A value that still reads as a `user_config` placeholder
  counts as `false`.

Strip `--pane` / `--no-pane` before reading the command's other arguments.
`--no-pane` always wins. It is what the pane session itself receives, so a
configured default cannot open a pane from inside a pane.

Then:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/herdr-pane.sh check
```

A non-zero exit means this session is not inside Herdr. If `--pane` was
explicit, say so in one line and run the command the normal way. If it came only
from a configured option, fall back silently: the option means "when available".

## The command string

The command string is the **only** thing that crosses into the pane: the slash
command, its arguments with `--pane` removed, and `--no-pane`. Never add a
summary, the intent, excerpts, or who wrote the code. A pane is a fresh context
only as long as nothing from this conversation crosses into it, which is the
same rule as for passing a subagent scope rather than content.

## Modes

Every mode opens the pane with `open`. It prints JSON with `agent` (use it from
then on), `pane_id`, `direction` (sibling panes), and for worktrees
`workspace_id`, `worktree_path`, `worktree_branch` and `base_tree`.

The report path is always `<scratchpad dir>/<command>-<slug>.md`.

### collect: a read-only command, its report comes back here

1. `herdr-pane.sh open <name> <report path>`: opens a sibling pane on this
   checkout.
2. One Bash call with `run_in_background: true`:
   `herdr-pane.sh run <agent> <report path> "<command string>"`
3. Tell the user in one line where the pane is (`direction`) and its `agent`
   name, that any approval or question in it is theirs to answer (Herdr notifies
   them), and that the result will be presented here. **End the turn.** Do not
   poll; the background command re-invokes you.
4. On exit `0`, **read the report file.** It is the primary channel. Then
   present as the command says.

### worktree: a command that edits files runs in its own checkout

A pane that edits the checkout you are working in would race your edits. These
commands get their own Herdr worktree workspace instead. The pane is not a split
of this tab; it is the root pane of a new workspace in the sidebar.

- `open <name> <report path> --worktree <branch>` checks out an existing branch:
  the local one (fast-forwarded to origin when it is behind) or one created from
  `origin/<branch>`. Exit `15` means the branch is already checked out somewhere,
  usually in this checkout. Say so, and offer to run it here without a pane.
- `open <name> <report path> --worktree-staged` creates a worktree at `HEAD` on a
  temporary `pane/…` branch and carries this checkout's **staged** diff into its
  index. Unstaged changes stay here. Exit `16` means nothing is staged.

Then follow steps 2–4 of collect. What comes back, and how the worktree is
cleaned up, is up to the command.

`herdr-pane.sh cleanup <workspace_id> [--force] [--delete-branch <branch>]`
removes the workspace and closes its pane. Run it only when the user says yes,
and use `--force` only once the worktree's changes exist somewhere else.

### handoff: the work moves to the pane, nothing comes back

1. `herdr-pane.sh open <name> -`
2. `herdr-pane.sh send <agent> "<command string>"`. It returns once the agent
   has started.
3. Tell the user the work continues in the pane (`direction`, `agent`) and that
   this session must not edit the same files while it runs. **Stop.** Do not
   continue the work here.

## Exit codes

| Exit | Meaning | What to do |
|------|---------|------------|
| `10` | Not inside Herdr | Run the command the normal way (see When) |
| `11` | No pane or worktree was created | Say so; run the normal way |
| `12` | `claude` did not start | The pane was left open to inspect. Say so; run the normal way |
| `13` | A prompt was not taken, or the agent exited | The command did not complete. Say so; offer to re-run |
| `14` | Settled without writing the report | The result may be on screen in the pane: point the user there. **Never** report it as a clean or empty result |
| `15` | Branch already checked out elsewhere | Offer to run it here without a pane |
| `16` | Nothing staged | Same as the command's own "nothing staged" stop |
| `17` | A git step failed | Quote the message; a workspace named in it was left open |
