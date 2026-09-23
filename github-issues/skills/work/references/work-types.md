# Work Types

Classify from the body, not only the labels: an issue labelled `bug` that says "nothing is
broken today" is tech debt, and an unlabelled one with a stack trace is a bug.

| Type | Signals in the issue | Actionable when | Branch prefix | Test strategy |
|---|---|---|---|---|
| **Bug** | wrong output, crash, 500, 403, stack trace, Sentry link | the failure is reproduced, or the failing path is traced end to end in current code | `fix/` | A test that fails on HEAD for the reason the issue gives, then passes with the fix. Show both runs. |
| **Performance** (N+1, slow query) | measured query counts, timings, "per row" | the cost is re-measured on HEAD, or the missing eager-load/annotation is confirmed in the queryset | `perf/` | An assertion on the measured quantity (e.g. query count at two sizes) that fails before and passes after. |
| **Tech debt** | "latent", "nothing broken today", convention violation, inconsistency between two places | the inconsistency still exists at HEAD | `chore/` | Existing tests green before and after. If the change restores a checkable invariant (a route no longer matches, a constant is used), add a test for it that fails on HEAD. |
| **Refactor** | move, extract, consolidate, fold X into Y, remove duplication | the code to change is where the issue says, and its consumers are enumerated | `refactor/` | Existing tests green before and after. Where coverage of the touched code is thin, add characterization tests **first** and show them passing on HEAD. |
| **Test defect** | a test asserts nothing, commented-out assertion, wrong fixture value | the defect is demonstrated (mutate the code; the test still passes) | `test/` | The fixed test must fail under the same mutation that the broken one survived. |
| **Follow-up** | "left out of scope of #N", "deferred from review" | the parent PR merged and the gap still exists | by the underlying type | by the underlying type |
| **Needs decision** | `needs-decision`, "Options (not choosing one)", "decide whether" | never on its own — the user decides | — | — |
| **Epic / spike / feature** | `[Epic]`, `[Spike]`, `enhancement`, "Phase N" | out of scope for this skill | — | Use `/feature-dev:spec`. |

## Consequences of the type

- **A test that fails before the change exists only when the change alters something
  observable** — a bug's output, a query count, a restored invariant. A pure refactor alters
  nothing observable: don't invent a failing test; prove behavior did not change instead.
- **Tech debt and refactors touch consumers.** Before renaming, removing, or changing a
  type or a response, search every consumer — project-wide, and in sibling repos checked
  out locally (a frontend reading a field, a service calling an endpoint), whether or not
  the issue names them.
- **An issue can hold several types.** An issue listing four independent defects is four
  units of work: confirm with the user which ones this branch covers, unless `--part`
  already says.
- **Priority labels are the author's estimate.** If verification changes the impact (a
  latent bug that turns out to fire, a medium one already mitigated), say so in the ledger.
