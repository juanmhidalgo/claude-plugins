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

### `/onboard:architecture [ascii|html] [output-path]`

Generate a high-level architecture overview with component diagram, data flows, and external dependencies. Output is an ASCII map in the terminal (default) or a standalone HTML page with a rendered diagram, written to a file and opened in the browser. Asks which one when no format is given.

**Example:**
```
/onboard:architecture
/onboard:architecture html
```

## Agents

### `onboard-discoverer`

Dedicated agent spawned by `/onboard:start`. Discovers project structure, tech stack, entry points, and configuration for thorough project onboarding analysis.

### `architecture-mapper`

Dedicated agent spawned by `/onboard:architecture`. Maps project layers, components, boundaries, communication patterns, and external dependencies.

---

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

## Needs

- A codebase to explore
- For `/onboard:architecture html`: a browser, opened with `xdg-open` (Linux) or `open` (macOS), and network access to load the Mermaid script from jsDelivr
- No `gh` or MCP servers
