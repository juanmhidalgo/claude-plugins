# Feasibility — Subagent Output Schemas

Loaded by `/intake:feasibility` Phase 3 (Parallel Research).

All `N + 1` Explore agents must use `model: "sonnet"` (Haiku lacks the analysis depth for accurate codebase pattern recognition).

## Capability subagent prompt

Each capability prompt must include:
1. The capability statement (one line)
2. The original quote from the customer request
3. Specific search terms to investigate (3–8 keywords/identifiers)
4. The output schema below

**Required output:**

```markdown
## Capability <ID>: <statement>

**Status**: EXISTS / PARTIAL / MISSING
**Effort**: trivial / small / medium / large
**Evidence**: <file:line references — at least 2 if Status is EXISTS or PARTIAL>
**Gap**: <what is missing or would need to change; "none" if Status is EXISTS>
**Notes**: <one paragraph max — surprises, hidden bugs, naming caveats>
```

**Effort scale (calibrate carefully):**
- **trivial** — config change, single-line edit, or already done
- **small** — hours; one file or a small group of files, no new infrastructure
- **medium** — days; new endpoint/model/migration, fits existing patterns
- **large** — weeks; new infrastructure, new dependencies, new architectural pattern, or cross-cutting changes

## Alternatives subagent prompt

Different lens than capability agents — looks **horizontally** for existing patterns and operationally-realistic combinations of EXISTS capabilities. NOT bounded to any single capability.

The alternatives prompt must include:
1. The full customer request (so the agent sees the complete ask, not one slice)
2. The list of capability IDs and one-line statements (so the agent avoids duplicating)
3. The two-question lens (workarounds + pragmatic alternatives)
4. The output schema below

**Required output:**

```markdown
## Workarounds available today

For each operationally-realistic combination of EXISTS capabilities + manual or admin steps that meets some subset of the customer's ask without writing new production code:

| ID | Workaround | Combines | Operational burden | What it does NOT solve |
|----|------------|----------|---------------------|------------------------|
| W1 | <one-line title> | <which existing capability IDs and which existing tools/admin pages> | <who runs it, how often, by hand or scripted> | <which capability IDs remain unaddressed> |

## Pragmatic alternatives (clone or extend existing patterns)

For each existing pattern in the codebase that could be cloned/extended/broadened to ship a larger acceptable version of the ask faster than building bespoke from scratch:

| ID | Pattern | Found at | Could address | Effort to broaden |
|----|---------|----------|---------------|-------------------|
| P1 | <one-line title — what the pattern is> | <file:line> | <capability IDs this could partially or fully replace> | trivial / small / medium |
```

If neither lens finds anything operationally realistic or backed by file:line evidence, output exactly:

> "No workarounds or pragmatic alternatives identified. Bespoke build appears necessary."

**Rules for the alternatives agent:**
- Workarounds must be **operationally realistic**. An admin running an export 4× per day is plausible; an admin running it 4× per *minute* is not — don't list it.
- Pragmatic alternatives must be **backed by file:line evidence** of the existing pattern. No speculation about "we probably have something like this."
- Always state the **operational burden** of a workaround. "CS runs it daily" is a real workaround with real cost; the cost is part of the workaround's data.
- Always state **what the workaround does NOT solve**. A workaround that meets 60% of the ask is useful; one that hides the other 40% is dangerous.
- Pragmatic alternatives are usually **trade-offs**, not strict replacements. Note what they sacrifice (less custom, less flexible, etc.) when relevant.
