# feature-dev evals

Eval suite for `claude plugin eval`. Each case is a full `claude` child run
against the plugin, so it costs real tokens and minutes.

## Cases

### `explore-plan-fanout`

Guards the regression fixed in 1.25.0. `/feature-dev:explore-plan` launches one
anonymous `general-purpose` generator, and that generator fans out to the
`feature-dev:*-explorer` agents. When the generator was spawned with a `name`,
it became a teammate and the harness refused every explorer spawn. The
generator then explored alone and still wrote a normal-looking plan. This
happened in 3 real runs before anyone noticed.

The case stages a small fixture project (`explore-plan-fanout/fixture/`: a
Python store, a JS list renderer, a unittest file, 3 commits, and an approved
`SPEC-task-due-dates.md`). It runs `/feature-dev:explore-plan
SPEC-task-due-dates.md` and grades:

| Grader | Type | Checks |
|---|---|---|
| `spawned-{backend,frontend,test,history}-explorer` | `tool_used` | an `Agent` call with that `subagent_type` appears in the trace |
| `no-named-agent-spawn` | `tool_used` (max 0) | no `Agent` call carried a top-level `name` (the root cause) |
| `no-teammate-refusal` | `regex` on trace | no tool result starts with `Teammates cannot spawn other teammates` or `In-process teammates cannot spawn background agents` |
| `plan-written` | `file_exists` | `PLAN-task-due-dates.md` was created |
| `plan-not-degraded` | `regex` on the plan | no `Degraded exploration` line |
| `plan-has-baseline` | `regex` on the plan | a `### Baseline` heading |
| `plan-has-explorer-sections` | `regex` on the plan | `#### Backend` / `Frontend` / `Tests` / `History` subsections |

All graders are deterministic. There is no LLM judge.

The two regression guards (`no-named-agent-spawn` and `no-teammate-refusal`)
were checked against the transcripts of the real failing runs, and both fire
on them. The refusal pattern is anchored to the start of a tool-result string,
because the command body itself quotes the refusal message mid-sentence.

## Running

From the repo root:

```bash
claude plugin eval ./feature-dev --case explore-plan-fanout \
  --ablation none --scaffold --allow-tools Bash Write Edit Agent --no-publish
```

- `--ablation none`: a no-plugin baseline arm makes no sense here, because the
  command and the explorers only exist in the plugin.
- `--scaffold`: required. Without it the case runs in an empty directory and
  fails.
- `--allow-tools Bash Write Edit Agent`: the generator writes the plan and runs
  the Baseline commands, and `history-explorer` runs `git`.
- The first run asks you to trust the plugin directory. Add `--trust-plugin`
  when running unattended.
- No network is needed beyond the model API. The fixture's `origin` remote is
  only a name.

**Cost:** one run is a full explore-plan with 4 or more explorers, the
validator and a Baseline. The first run, on 2026-09-27, took 229 s and cost
$1.46 in 6 top-level turns. It spawned 5 explorers: the 4 always-on ones plus
`schema-explorer`.
`case.yaml` sets `runs: 1`. Raise it with `--runs 3` when you want a flake
rate.

Run it when `commands/explore-plan.md` or any `agents/*-explorer.md` changes.
Do not run it on every edit.

## What the graders can see

`tool_used` and `target: trace` read the child's `stream-json` trace. The trace
holds the top-level session plus **one level** of subagents: the generator's
tool calls, its `Agent` spawns of the explorers, and the explorers' hand-back
results. The fan-out is therefore observed directly and not inferred from the
plan. What happens inside each explorer (depth 2) is not in the trace.

A `tool_used` grader matches the call's *input*, not its result, so on its own
it only means "the call was made". It also means "the call was not refused"
only when `no-teammate-refusal` passes too. In the passing run, every explorer
`Agent` call came back as a non-error hand-back report.

The two regression guards rely on the observed trace shape: tool-result
strings, and the `Agent` input serialized as JSON. If a future Claude Code
changes that serialization, the guards can pass silently. Re-check them
against a trace from a failing run (for example, one with `name` added to the
generator call) whenever the runner is upgraded.
