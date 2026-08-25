# discuss

Critical feature discussion and idea refinement tools for Claude Code.

## Installation

```bash
# Add marketplace (if not already added)
/plugin marketplace add juanmhidalgo/claude-plugins

# Install plugin
/plugin install discuss@juanmhidalgo-plugins
```

## Commands

### `/discuss:feature <feature or idea>`

Critical analysis with a skeptical Staff Engineer perspective. Explores codebase first, identifies gaps, risks, and offers alternatives.

**Example:**
```
/discuss:feature add caching layer for API responses
```

---

### `/discuss:brainstorm <problem or feature>`

Generate 4-6 distinct approaches to solve a problem. Covers different tradeoffs: simple vs robust, build vs buy, different architectures.

**Example:**
```
/discuss:brainstorm user authentication system
```

---

### `/discuss:challenge <proposal>`

Argue AGAINST a proposal to stress-test it. Finds weaknesses before you commit. If your idea survives, proceed with confidence.

**Example:**
```
/discuss:challenge migrate to microservices
```

---

### `/discuss:tradeoffs <option1> vs <option2>`

Compare 2-4 specific options with structured pros/cons matrix. Produces decision criteria tailored to your project's context.

**Example:**
```
/discuss:tradeoffs REST vs GraphQL vs gRPC
```

## Skills

### `/discuss:adversarial-doc-review <doc-path> [design|descriptive]`

Adversarial review of a technical document that already exists as a **file** — PRD, ADR, spec, RFC, architecture doc. Dispatches the `doc-adversary` subagent in a **fresh context** and reports only what would cause a bad architecture, design, or implementation decision. Not a proofreader and not a completeness checker.

Also triggers on "poke holes in this doc", "red team this design doc", "sanity check this spec".

**Example:**
```
/discuss:adversarial-doc-review docs/adr/0007-event-bus.md design
```

**Two modes:**

| Mode | For | Materiality judged by |
|------|-----|----------------------|
| `design` | Decisions not yet made or built (PRD, ADR, RFC, spec) | Cost of reversal |
| `descriptive` | Claims to describe a system that exists (architecture, data model, integration docs) | Cost of reversal **+** divergence from the code |

If both apply, `descriptive` runs first — a wrong base state invalidates the design review that follows.

**Before acting on the report:** spot-check two entries in its *Falsification attempts* section. Zero findings with an empty falsification log is a failed review, not a clean bill of health.

**Out of scope:** runbooks and operational procedures (different severity model), READMEs, changelogs, code review, and ideas still in conversation with no file — use `/discuss:challenge` for that last one.

---

## Typical Workflow

```
/discuss:feature "vague idea"       → Identify problems
    ↓
/discuss:brainstorm                 → Generate alternatives
    ↓
/discuss:tradeoffs A vs B           → Compare top options
    ↓
/discuss:challenge                  → Stress-test decision
    ↓
/feature-dev:spec                   → Formalize as structured spec
    ↓
/discuss:adversarial-doc-review     → Red-team the written spec/ADR
    ↓
/feature-dev:explore-plan           → Explore and plan implementation
```

`/discuss:challenge` and `/discuss:adversarial-doc-review` are the same skepticism at
two different stages: the first attacks an idea while it is still in conversation, the
second attacks a document after it is written — and must run in a fresh context, because
a reviewer that already holds the doc's framing cannot form an independent model of the
problem.

Each command suggests the next step via Stop hooks, including cross-plugin suggestions.

## Requirements

- Claude Code CLI
- A codebase to provide context (optional but recommended)

## License

MIT License - See [LICENSE](../LICENSE) for details.
