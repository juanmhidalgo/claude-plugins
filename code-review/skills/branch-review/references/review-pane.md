# Running the review in a Herdr pane

`/code-review:branch` and `/code-review:staged` can run the whole review in a
**separate top-level Claude Code session** in a sibling Herdr pane, instead of a
subagent of this one. The subagent already gives the reviewer a fresh context;
the pane adds three things:

- **It does not block this session.** The review runs while you keep working,
  and you are re-invoked when it finishes.
- **The review session can fan out.** It is top-level, so its own verifiers
  (`high`/`max`) dispatch the same way they would anywhere else.
- **The reviewer stays open for follow-up.** Ask it why it flagged something,
  in its pane, with its context intact.

## When

Use the pane when **either** holds, and `--no-pane` is not in the arguments:

- `--pane` is in the arguments
- the configured `review_in_pane` option is `true`

Strip `--pane` / `--no-pane` before reading the positional arguments (base,
effort). `--no-pane` always wins: it is what the pane session itself receives, so
a configured `review_in_pane` cannot open a pane from inside a pane.

Then run the check:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/review-pane.sh check
```

Non-zero means this session is not inside Herdr (or the server is unreachable).
If `--pane` was explicit, say so in one line, then run the normal subagent
dispatch. If it came only from the config, fall back silently: the option means
"when available".

## Flow

1. **Report path** — `<scratchpad dir>/<command>-review-<branch>.md`
   (`<command>` is `branch` or `staged`).

2. **Open the pane** (foreground, quick):

   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/review-pane.sh open <branch> <report path>
   ```

   It prints `{"pane_id", "agent", "direction"}`. Use `agent` from here on.

3. **Run the review in the background.** One Bash call with
   `run_in_background: true`:

   ```bash
   ${CLAUDE_PLUGIN_ROOT}/scripts/review-pane.sh run <agent> <report path> "/code-review:<command> <positional args> --no-pane"
   ```

   The command string is the **only** thing the pane receives: the slash command,
   its positional arguments, `--no-pane`. The scope-not-content rule applies
   exactly as it does to the subagent — no summary, no intent, no excerpts. The
   pane is fresh only as long as nothing from this conversation crosses into it.

4. **Tell the user in one line and end the turn**: the review is running in the
   pane to the `<direction>` as agent `<agent>`; approval prompts there are theirs
   to answer (Herdr notifies them); the result will be presented here when it
   lands. Do not poll — the background command re-invokes you when it exits.

## When the background command exits

| Exit | Meaning | What to do |
|------|---------|------------|
| `0` | The report is at the printed path | Read it and present (below) |
| `12` | `claude` did not start in the pane | Say so; the pane was left open to inspect. Offer the subagent dispatch |
| `13` | A prompt was not taken, or the agent exited | Say so; the review did not complete. Offer to re-run |
| `14` | The agent settled without writing the report | The review may have finished in the pane: tell the user to read it there, or pass the file to `/code-review:receive` once written. Never report it as clean |

On exit `0`:

- **Read the report file.** It is the primary channel, exactly as `OUTPUT_PATH`
  is for the subagent.
- **Do not re-verify.** The pane ran this effort level's verification, in a
  fresh context, which is better than this one. Run only the two
  pre-presentation checks of `verification.md` (citations, execution claims) —
  they are cheap, and a report that crossed a session boundary needs them most.
- **Present the distilled findings**, then one line: follow-up questions go to
  the reviewer with `herdr agent focus <agent>`; the pane stays open until the
  user closes it. Never close it yourself.

To have the findings re-verified here instead — for example because the code
changed while the review ran — pass the report path to `/code-review:receive`.
