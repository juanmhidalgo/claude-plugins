# factory

The stage commands the **factory daemon** runs headless, one per tick, inside
a sandbox: `/factory:spec`, `/factory:plan`, `/factory:implement`,
`/factory:harden`, `/factory:ship`. Each one reads everything from a GitHub
issue and the factory branch, composes the existing plugins (`feature-dev`,
`code-review`, `ship`, `github-issues`), and writes everything back to GitHub
before it ends. None of them can ask: the daemon runs them with
`--permission-prompts none`, so every interactive gate of the composed
commands is a documented default or a `question` outcome on the issue.

The daemon itself (the state machine, the sandboxes, the caps, the
notifications) lives in the `factory` repository; this plugin is only the
five commands it types.

## Commands

| Command | Starts from | Ends with |
|---|---|---|
| `/factory:spec #N` | `status:needs-spec` | the spec section in the body; `needs-plan` (`factory:auto`) or `spec-review` (a gate lane) |
| `/factory:plan #N` | `status:needs-plan` | the plan section in the body; `ready` or `plan-review` (`factory:plan-gate`) |
| `/factory:implement #N` | `status:ready`, or `in-progress` with no done marker | one commit and one push per plan step on `factory/<N>-<slug>`, a progress comment each; `in-progress` |
| `/factory:harden #N` | last done marker `implement` | the review loop with every confirmed finding fixed, one `fix:` commit per round (two at most); `in-progress` |
| `/factory:ship #N` | last done marker `harden` | `/ship --yes --skip-copilot-review`: the PR against the default branch; `in-review` |

The factory never requests a Copilot review (`ship` passes
`--skip-copilot-review`): the PR review is the human gate.

Every command starts with [`references/factory-contract.md`](references/factory-contract.md):
where the inputs come from (`FACTORY_*` variables from the daemon, or `#N`
alone when testing by hand), the issue body format (feature-dev's issue-store
sections for the spec and the plan), the marker rule for comments, the three
outcomes and the label flips per lane, the question protocol, and the hard
rules (never the default branch, never force, never close the issue, never
stage secrets, never ask).

## Outcomes

A stage ends in exactly one of three outcomes, written to the issue by
`scripts/factory-outcome.sh`, which is the only place a marker is typed:

| Outcome | Comment starts with | `status:*` |
|---|---|---|
| done | `<!-- factory:done stage=… sha=… run=… -->` then the stage report | the next status for the lane |
| question | `<!-- factory:question id=… stage=… from=… run=… -->` then up to four numbered questions with 2–4 options each, one `(Recommended)` | `waiting-human`; a human comment after it is the answer, and the daemon re-runs the stage |
| parked | `<!-- factory:parked stage=… reason=… run=… -->` then what happened and a `How to recover:` block | `needs-human` |

A comment without a `<!-- factory:… -->` marker is a human's, whichever login
wrote it. The flip refuses when the status moved meanwhile (a human relabelled
the issue): the stage then parks with `reason=status-moved` and the human's
label wins.

## Testing a stage by hand

```bash
claude -p "/factory:spec #12" --permission-prompts none --output-format json \
  --plugin-dir factory --plugin-dir feature-dev --plugin-dir code-review \
  --plugin-dir ship --plugin-dir github-issues
```

Without the `FACTORY_*` variables the command derives the repository from
`gh repo view`, the branch `factory/<N>-<slug>` from the issue title, and a
`manual-<timestamp>` run id. It still never asks. The acceptance criteria the
stages are reviewed against are in the `factory` repository's
`docs/SPEC-factory-plugin.md` (§7).

The scripts are tested offline, with a stubbed `gh`:

```bash
bash factory/scripts/test_factory_scripts.sh
```

## Needs

- The whole `claude-plugins` checkout as the plugins mount: feature-dev's
  scripts are reached at `${CLAUDE_PLUGIN_ROOT}/../feature-dev/scripts/`.
- `gh` authenticated, `jq`, `git`, and the plugins in `dependencies`
  (`feature-dev` ≥ 2.8.0 for the plan section and the step loop, `ship` ≥
  2.1.0 for `--yes`, `code-review` ≥ 3.13.0 for the review workflow,
  `github-issues` for the issue verifier).
- Workflows enabled (`Workflow(feature-dev:plan-fanout)` and
  `Workflow(code-review:review)`); without them `plan` falls back to the
  Agent fan-out and `harden` parks.

## Installation

```
/plugin install factory@juanmhidalgo-plugins
```
