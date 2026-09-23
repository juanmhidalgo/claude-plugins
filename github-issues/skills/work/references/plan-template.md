# Plan Template

Use this template when presenting the plan in Phase 4.

```
## Plan: {issue title} (#{number})

**Work type:** {bug | performance | tech debt | refactor | test defect | follow-up} — {one line on why}
**Verdict:** {actionable as written | actionable with corrections}

### Verification ledger
[The table from Phase 3. Keep every row, including CONFIRMED ones.]

### Problem (as verified)
[What is actually wrong at HEAD, in your words — not the issue's. Where it differs from
the issue, say how.]

### Proposed change
[Specific changes, file by file]

### Deviations from the issue's suggested fix
| Issue suggested | This plan does | Why |
|---|---|---|
| ... | ... | [ledger row, convention, or caller that forced it] |
[Write "None" if the plan follows the suggestion as written.]

### Files to modify / create
| File | Change |
|------|--------|
| path/to/file.py | Description of change |

### Consumers checked
[Every caller or reader of what changes — including other repos — and whether it is affected.]

### Test strategy
[Per the work type. For a bug: the test that fails on HEAD and why. For a refactor: the
existing tests that cover the change, and characterization tests to add first.]
- [ ] ...

### Out of scope
[What the issue explicitly excluded, and anything found during verification that belongs
in its own issue.]

### Risks
[Rollout effects, behavior changes users will notice, anything irreversible.]
```
