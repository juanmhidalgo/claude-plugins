# refactor

Structured refactoring workflow tools for Claude Code.

## Installation

```bash
# Add marketplace (if not already added)
/plugin marketplace add juanmhidalgo/claude-plugins

# Install plugin
/plugin install refactor@juanmhidalgo-plugins
```

## Commands

### `/refactor:analyze <file-or-directory>`

Analyze code for refactoring opportunities. Identifies complexity, duplication, extraction candidates, and code smells.

**Example:**
```
/refactor:analyze src/services/user.py
/refactor:analyze src/components/
```

---

### `/refactor:plan [target]`

Create a step-by-step refactoring plan with dependencies, checkpoints, and rollback instructions.

**Example:**
```
/refactor:plan src/services/user.py
/refactor:plan "reduce complexity in auth module"
```

---

### `/refactor:extract <what-to-extract>`

Safely extract code into a new function, class, or module. Guides you through naming, placement, and verification.

**Example:**
```
/refactor:extract "validation logic from UserService.create"
/refactor:extract "duplicate error handling to ErrorHandler class"
```

## Typical Workflow

```
/refactor:analyze file.py   → Identify issues
    ↓
/refactor:plan file.py      → Create ordered plan
    ↓
/refactor:extract [code]    → Execute extractions
    ↓
Run tests                   → Verify changes
    ↓
/commit                     → Commit when green
```

## Requirements

- Claude Code CLI
- A codebase to refactor
- Test suite (recommended for safe refactoring)
