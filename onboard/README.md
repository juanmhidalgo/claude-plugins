# onboard

Codebase exploration and onboarding tools for Claude Code.

## Installation

```bash
# Add marketplace (if not already added)
/plugin marketplace add juanmhidalgo/claude-plugins

# Install plugin
/plugin install onboard@juanmhidalgo-plugins
```

## Commands

### `/onboard:start [focus-area]`

Generate a comprehensive onboarding guide for the project. Covers architecture, key files, patterns, and gotchas.

**Example:**
```
/onboard:start
/onboard:start backend
```

---

### `/onboard:explore <topic>`

Deep exploration of a specific topic in the codebase. Returns file references, code examples, and flow explanations.

**Example:**
```
/onboard:explore authentication
/onboard:explore database queries
/onboard:explore error handling
```

---

### `/onboard:architecture`

Generate a high-level architecture overview with component diagram, data flows, and external dependencies.

**Example:**
```
/onboard:architecture
```

## Typical Workflow

```
/onboard:start              → Get the big picture
    ↓
/onboard:architecture       → Understand components
    ↓
/onboard:explore auth       → Dive into specific areas
    ↓
/onboard:explore api        → Continue exploring
```

## Requirements

- Claude Code CLI
- A codebase to explore
