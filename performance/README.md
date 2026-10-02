# performance

Performance optimization workflow with measure-first profiling, bottleneck identification, Core Web Vitals targets, and anti-pattern detection.

## Installation

```bash
/plugin install performance@juanmhidalgo-plugins
```

## Commands

| Command | Description |
|---------|-------------|
| `/performance:audit [path]` | Performance audit with anti-pattern scanning and bottleneck identification |
| `/performance:profile <target>` | Focused profiling of a specific function, endpoint, or component |

## Skills

| Skill | Purpose |
|-------|---------|
| `performance-optimization` | Measure-first workflow, Core Web Vitals, symptom decision tree, performance budgets |

## Philosophy

**Never optimize without measurement.** The workflow is always:

1. **Measure** — Establish baseline with real data
2. **Identify** — Find the actual bottleneck (not the assumed one)
3. **Fix** — Address the specific bottleneck
4. **Verify** — Measure again, confirm improvement
5. **Guard** — Add monitoring to prevent regression

## Needs

- A git repository (for change analysis)
- The project's build and profiling tools (npm, pip, etc.)
- No `gh`, MCP servers, or browser
