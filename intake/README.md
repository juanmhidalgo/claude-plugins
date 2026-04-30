# intake

Translate unstructured customer/CSM/Sales/Support requests into engineering feasibility reports against the current codebase.

The `intake` plugin sits **before** discussion and specification: it answers "is this possible, how hard is it, and where in the code?" before anyone debates scope or commits to a SPEC.

## Workflow Position

```
Customer message  →  /intake:feasibility  →  /discuss:feature  →  /feature-dev:spec  →  /feature-dev:tdd
   (prose ask)         (capability map)        (debate scope)       (commit to spec)        (build)
```

Each plugin owns one stage. `intake` produces a verifiable feasibility report. The handoff to `/discuss:feature` or `/feature-dev:spec` happens after a human picks which capabilities to pursue.

## Installation

```bash
# Add marketplace (if not already added)
/plugin marketplace add juanmhidalgo/claude-plugins

# Install plugin
/plugin install intake@juanmhidalgo-plugins
```

## Commands

### `/intake:feasibility <paste request OR path to file>`

Decompose a customer request into atomic capabilities, research each in parallel against the current codebase, and produce a feasibility report.

**Output (printed inline in chat by default):**
- Capability map table (Status × Effort × Key Finding)
- Per-capability evidence with `file:line` references
- Top 3 risks for the overall request
- Phased recommendation (Phase 1 / 2 / 3 by effort and priority)
- Open questions back to the customer (when applicable)
- After printing, the command asks whether to save it to `INTAKE-feasibility-<slug>.md` — opt-in only

**Examples:**

```
/intake:feasibility A customer wants to extract their interview data multiple times a day, joined with custom audience fields, delivered via SFTP since email is blocked by their IT policy
```

```
/intake:feasibility ./tickets/customer-request-1234.txt
```

**What it produces (table excerpt):**

| ID | Capability | Status | Effort | Key Finding |
|----|------------|--------|--------|-------------|
| A | Custom field support on uploads | PARTIAL | small | `JSONField` exists at `apps/candidates/models.py:44` but importer drops unknown columns at `bulk_import.py:264` |
| B | Scheduled report generation | MISSING | large | `django-celery-beat` not installed; no `ScheduledReport` model |

**What it does NOT do:**
- Write code or implementation
- Create a SPEC, PLAN, or PRD file
- Decide which capabilities should be built — that's a human call after reading the report

## When to Use This Plugin

**Use when:**
- A CSM, Sales, Support, or Partnership team forwards an unstructured customer request
- The request bundles many asks together that need to be separated and individually assessed
- You need a defensible answer ("yes, partial, no") backed by code evidence — not intuition

**Do NOT use when:**
- The ask is already scoped to a single, well-defined feature → use `/feature-dev:spec` directly
- The ask is a bug report → use `/debug:debug`
- The request needs design debate, not feasibility research → use `/discuss:feature` or `/discuss:brainstorm`

## Why This Exists

The most expensive feasibility mistake is the silent "yes." A capability that *appears* to exist — a JSON column, a config flag, a half-wired endpoint — but is silently broken in production. Engineers know to look for these; CSMs and Sales generally don't.

This plugin enforces the discipline that protects everyone: **every Status verdict must be backed by `file:line` evidence**, and the report flags silent-bug risks loudly so they don't end up as customer-facing promises.

## Disclaimer

This is a community project and is **not affiliated with, endorsed, or supported by Anthropic**.
