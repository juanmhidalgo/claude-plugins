# Report format, verdict rules, rollback strategies

## Template

```markdown
# Upgrade risk: <pkg> <current> → <target>
<!-- or: Python <current> → <target> -->

**Verdict: GO | NO-GO | GO WITH CAVEATS**
<one sentence: the single fact that drove it>

Manager: <uv|poetry|pip-tools|pipenv|pip> · Current from: <uv.lock | installed locally | unpinned>

## 1. What this repo touches

| Location | Symbol | Category | Fragile because |
|----------|--------|----------|-----------------|
| `app/services/mail.py:42` | `X._render` | private API | not in the public docs; renamed in 5.0 |

<or: "No first-party usage found — <pkg> is a transitive dependency of <parent>." Then the
report is about the resolver and the CVEs, and it says so instead of padding this section.>

## 2. Breaking changes, cross-referenced

| Release | Change | Applies here? | Evidence |
|---------|--------|---------------|----------|
| 5.0 | `_render` removed | **APPLIES** | `app/services/mail.py:42` |
| 5.0 | `USE_L10N` removed | DOES NOT APPLY | not set in any settings module |
| 4.2 | tz-aware datetime comparison | **UNKNOWN** | 6 naive `datetime.now()` call sites; needs the DB timezone config, which I did not read |

## 3. Transitive impact

<resolver output, verbatim where it conflicts>
- Forces: `<dep> 2.1 → 3.0`
- No target-compatible release: `<dep>` (latest 1.4 requires `<pkg><5`)
- Silent downgrade: `<dep> 3.2 → 3.1` <- flag separately, resolvers do this quietly

## 4. CVEs

Fixed by the upgrade: <id + severity, from pip-audit / advisory page>
Introduced in the target: <id, or "none published as of <date fetched>">

## 5. Coverage of the affected paths

Source: `coverage.xml`, generated <timestamp>  <!-- or: no coverage data; not run -->

| Path from §1 | Covered | Risk |
|--------------|---------|------|
| `app/services/mail.py:42` | no | **APPLIES + uncovered** |

## 6. Recommendation

<verdict, then:>
Before merging:
- [ ] <specific test to add or run, naming the file>
- [ ] <specific manual check>

Rollback: <strategy, see below>

## Not verified

- <what> — closes with: `<command to run>`
```

## Verdict rules

The verdict is **capped by the evidence**, not chosen on impression:

| Condition | Best available verdict |
|-----------|------------------------|
| An APPLIES item on a path with no coverage | GO WITH CAVEATS |
| Any section UNVERIFIED (resolver could not run, changelog unreachable) | GO WITH CAVEATS |
| An APPLIES item with no migration path in the release notes | NO-GO |
| A dependency with no target-compatible release | NO-GO |
| Target version yanked | NO-GO |
| Everything DOES NOT APPLY, resolver clean, affected paths covered | GO |

"GO WITH CAVEATS" without a numbered, actionable caveat list is just GO wearing a hedge — each
caveat names a file and what to do to it.

## Rollback strategies

Pick one and say why, rather than listing all four:

- **Pin and revert** — the default. The lock file is the rollback; name the exact revert
  command and whether a DB migration ran in between (if it did, pin-and-revert is *not* enough
  and the report must say so).
- **Compatibility shim** — a thin wrapper over the renamed API, merged *before* the bump, so
  the upgrade itself becomes a one-line diff.
- **Feature flag** — only when the library is behind a service boundary the flag can switch.
  Most library upgrades cannot be flagged; do not suggest it reflexively.
- **Canary** — only if the deploy target actually supports partial rollout. Name it.

## Tone

Cite `file:line`. No generic advice that would be identical for any repo — if a paragraph
would survive being pasted into a different project's report unchanged, it does not belong in
this one.
