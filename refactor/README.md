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

## Agents

### `refactor-analyzer`

Dedicated agent spawned by `/refactor:analyze`. Explores the codebase for similar code patterns, existing abstractions, test coverage, and consumers/callers to provide context-aware refactoring analysis.

### `refactor-planner`

Dedicated agent spawned by `/refactor:plan`. Maps test coverage, dependency graphs, past refactoring patterns, and risk areas to produce safe, ordered refactoring plans.

### `conflict-scout`

Spawned by `/refactor:analyze` and `/refactor:plan`. Checks open PRs, other branches, stashes, worktrees, and uncommitted edits against the files the refactor will touch, and reports two kinds of overlap:

- **Textual** — a PR edits a target file. A refactor rewrites existing lines, so this is a near-certain conflict, not a heads-up.
- **Semantic** — a PR *calls* a symbol you are renaming without touching your files. It merges clean and breaks afterwards; git never sees it.

Output is a CLEAR / CONTESTED / BLOCKED verdict plus a sequencing recommendation: do now, do first while the other PR is still small, defer until it merges, or coordinate with its author. Requires `gh`; when it is missing the scan says so rather than reporting a clean result.

`/refactor:extract` does the same check inline with a single `gh pr list` call on the source and destination files, and stops to ask before editing a file an open PR is already changing.

---

## Typical Workflow

```
/refactor:analyze file.py   → Identify issues + scan for concurrent work
    ↓
/refactor:plan file.py      → Create ordered plan (contested files deferred or fast-tracked)
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
- `gh`, authenticated, for the open-PR conflict scan (optional — without it the scan falls back to local git state and says so)
