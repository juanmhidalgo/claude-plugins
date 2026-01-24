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

## Typical Workflow

```
/discuss:feature "vague idea"   → Identify problems
    ↓
/discuss:brainstorm             → Generate alternatives
    ↓
/discuss:tradeoffs A vs B       → Compare top options
    ↓
/discuss:challenge              → Stress-test decision
    ↓
/prd:create                     → Formalize as PRD
```

## Requirements

- Claude Code CLI
- A codebase to provide context (optional but recommended)

## License

MIT License - See [LICENSE](../LICENSE) for details.
