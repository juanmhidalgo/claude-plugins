# Review Prompt

Prompt for the Phase 6 reviewer. Fill the placeholders with absolute paths and send it as is.

```
Review a change made to close one GitHub issue, before it is committed. You have not seen the
session that wrote it; that is the point. Form your own read of the code.

REPO: {absolute repo root}
BASE: {base sha} — {"the change is uncommitted" | "the change is on branch {branch}"}
DIFF: run `git diff {base}` in REPO (include untracked files the plan creates)
APPROVED PLAN: {scratchpad path} — contains the verified issue ledger, the change, deviations
from the issue's suggested fix, consumers checked, test strategy, and out-of-scope list.

Report, in this order:

1. Defects — correctness bugs in the diff (race conditions, state left behind, wrong
   fallback order, error paths, broken consumers). Each with `path:line` and a concrete
   failure scenario: inputs/state → wrong result.
2. Plan conformance — each numbered item of "Proposed change": done / partly / missing.
   Anything in the diff the plan did not call for, including reformatting and changes to
   shared test helpers. Anything listed under Out of scope that the diff touches.
3. Tests against the work type ({work type}) — does the test the strategy calls for prove
   what it claims: for a bug or performance issue, would it fail on BASE for the reason the
   ledger gives, and pass because of the change rather than because of a mock? For a
   refactor, do characterization tests pin the old behavior? Are the tests in files where a
   maintainer would look for them? Is any planned test missing?
4. Consumers — for each consumer in the plan's "Consumers checked", is it actually
   unaffected? Name any consumer of the changed code the plan's list missed.

Evidence rules: you are read-only and cannot run tests or the app. Label evidence [read]
(cite path:line) or [derived]. Never claim to have run anything; a check worth running is
written as a command marked (not run). Report only what you would defend to the author: no
style nits unless they hide a defect.
```

## Why opus

On a real change (an N+1 removal in a Vue view, 11 files, 326 lines), the same prompt on the
same agent found:

- **opus** — two confirmed findings (an error path where the toast and the sheet contradict
  each other; a regression test filed under an unrelated feature's test file), a change to a
  shared test stub the plan did not call for, and two consumers the plan's list missed.
  16 tool calls.
- **sonnet** — no findings, and stated that nothing in the diff fell outside the plan, which
  was false. 51 tool calls.
