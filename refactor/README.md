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

Explore stage of the `refactor` workflow when `/refactor:analyze` launches it. Explores the codebase for similar code patterns, existing abstractions, test coverage, and consumers/callers, and returns them as structured data for the analysis.

### `refactor-planner`

Explore stage of the `refactor` workflow when `/refactor:plan` launches it. Maps test coverage, dependency graphs, past refactoring patterns, and risk areas, and returns them as structured data for the plan.

### `conflict-scout`

Scout stage of the `refactor` workflow, which `/refactor:analyze` and `/refactor:plan` both launch. Checks open PRs, other branches, stashes, worktrees, and uncommitted edits against the files the refactor will touch, and reports two kinds of overlap:

- **Textual** — a PR edits a target file. A refactor rewrites existing lines, so this is a near-certain conflict, not a heads-up.
- **Semantic** — a PR *calls* a symbol you are renaming without touching your files. It merges clean and breaks afterwards; git never sees it.

Output is a CLEAR / CONTESTED / BLOCKED verdict plus a sequencing recommendation: do now, do first while the other PR is still small, defer until it merges, or coordinate with its author. Requires `gh`; when it is missing the scan returns `gh_available: false` and the commands say so rather than reporting a clean result.

`/refactor:extract` does the same check inline with a single `gh pr list` call on the source and destination files, and stops to ask before editing a file an open PR is already changing.

---

## Workflows

### `refactor`

Runs the explorer (`refactor-analyzer` or `refactor-planner`, by `mode`) and `conflict-scout` in parallel and returns both reports as structured data: a `summary` first (scout verdict, `gh_available`, data gaps, overlap count, stage status), then the full `explore` and `scout` reports. An agent that returns nothing or does not finish is retried once and otherwise reported as `failed`; a scout that did not run gives verdict `UNSCANNED`, never `CLEAR`. Launched by `/refactor:analyze` and `/refactor:plan`, not meant to be run by hand.

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

## Needs

- A codebase to refactor, ideally with a test suite
- `gh`, authenticated, for the open-PR conflict scan (optional: without it the scan falls back to local git state and says so)
- The `Workflow` tool, for `/refactor:analyze` and `/refactor:plan`. Under `claude -p` or the SDK that is a `Workflow(refactor:refactor)` allow rule; neither command has an in-session fallback
- No MCP servers or browser
