# The Spec axis

Shared by `/code-review:branch`, `:staged`, `:pr` and `:staged-pipeline`. The
defect review asks *is this code correct?*. The Spec axis asks *is this the change
the spec asked for?*. A change can pass one and fail the other, so the two are
reviewed by different agents and reported in different sections, never merged or
re-ranked against each other.

Adapted from the two-axis review in mattpocock/skills `code-review`. Copyright (c) 2026 Matt Pocock, MIT License.

## When it runs

At effort `medium`, `high` and `max`, and only when a spec is found. At `low` it
is skipped and the report says `Spec: skipped (effort low)`.

## 1. Find the spec mechanically

Run the script; do not choose or summarize the spec yourself. The session that
wrote the code holds its own idea of what was asked, which is exactly the framing
this axis must not inherit.

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/find-spec.sh --base <base> [--spec <arg>]   # :branch
${CLAUDE_PLUGIN_ROOT}/scripts/find-spec.sh --pr <N> [--spec <arg>]        # :pr
${CLAUDE_PLUGIN_ROOT}/scripts/find-spec.sh --staged [--spec <arg>]        # :staged
${CLAUDE_PLUGIN_ROOT}/scripts/find-spec.sh --staged                     # :staged-pipeline (no --spec)
```

`--spec <path|#N>` comes from the command's own `--spec` argument, when given.

Lines starting `unavailable` name a source that could not be checked (usually
`gh` failing). Never pass them to the agent, and never list them as "looked at":
report them as `not checked: <source>`.

If it prints no `spec-file` or `issue` line, do not dispatch. The report says `Spec: skipped (no spec
found; looked at: --spec, closing issues, commit messages, .feature-dev/
branch: frontmatter)`, listing only the sources that apply to this command. Do
not ask the user for one: the review stays a fast gate.

## 2. Dispatch, in parallel with the defect review

In the same message as the defect reviewer(s), launch
`subagent_type="code-review:spec-conformance-reviewer"` with:

```
SCOPE: <same scope line as the defect review>
SPEC_SOURCES:
<the script's spec-file and issue lines, verbatim>
OUTPUT_PATH: <scratchpad dir>/spec-review-<scope>.md
```

Nothing else: no summary of the change, no paraphrase of the spec. Read
`OUTPUT_PATH` first, as with every reviewer; a missing report means the axis did
not run, and the report says so.

## 3. Verify (where the command verifies)

Spec findings go through `code-review:finding-verifier` under the same trigger
as the command's other findings (see `verification.md`), with one extra input
line: `SPEC: <the spec source the finding quotes>`. They are **not**
deduplicated against defect findings: the same `file:line` can be both a bug and
a spec gap, and they are different claims.

`Spec too vague to check` is not a finding and is not verified: it is reported
as the axis result.

## 4. Present

A separate section after the defect findings:

```markdown
### Spec (<count>) — against <sources>
For each: **[missing | partial | wrong | unrequested]** title, the quoted spec
line, `file:line` or where it searched, one line of its counter-case
```

- Labelled `expected` (the issue was only referenced) → listed under the
  section as a count with titles, never as gaps.
- One summary line per axis. Do not pick a single worst issue across both axes.

## Spec findings are questions, never fixes

A spec finding is never turned into a proposed fix, at any verdict:

- `missing` and `partial` are feature work. Building it belongs to the author,
  not to a review step.
- `unrequested` may be wanted. "Fixing" it means deleting it, and a batch
  approval would delete work someone meant to ship.
- `wrong` changes what the code does on the strength of a spec line that may
  itself be out of date.

So in `:staged-pipeline` every spec finding goes to the user as a question, the
way `PLAUSIBLE` does, and `/code-review:fixes-plan` does not turn one into a fix
item.
