---
disable-model-invocation: true
allowed-tools:
  - Bash(git *)
  - Bash(gh *)
  - Read
  - Write
  - Edit
  - Agent
  - Glob
  - Grep
argument-hint: "<feature description>"
description: |
  Parallel codebase exploration before planning. Spawns multiple agents to
  explore different layers (backend, frontend, tests, git history) simultaneously,
  then synthesizes findings into a structured implementation plan.
  Use when starting a feature that touches multiple parts of the codebase.
  Do NOT use for simple bug fixes or single-file changes.
keywords:
  - exploration
  - planning
  - parallel-agents
  - implementation-plan
  - architecture
triggers:
  - "explore and plan"
  - "plan this feature"
  - "parallel exploration"
  - "implementation plan for"
  - "understand the codebase for"
hooks:
  - event: Stop
    once: true
    command: |
      echo "Exploration complete. Plan saved to PLAN-<feature-slug>.md"
      echo "  - Start a NEW conversation and run /feature-dev:tdd to implement (maximizes context)"
      echo "  - Or run /feature-dev:tdd now if context allows"
---

## Context
- **Repository**: !`git remote get-url origin 2>/dev/null || echo "unknown"`
- **Current branch**: !`git branch --show-current`
- **Feature**: $ARGUMENTS

## Phase 0: Validate

1. Feature description was provided (from $ARGUMENTS). If empty, **STOP** and ask user.
2. Parse the feature into a one-line summary for agent prompts.

## Phase 1: Parallel Exploration

Launch **all four agents in a single response** using the Agent tool. They will run in parallel automatically.

**IMPORTANT: Do NOT use `run_in_background: true`.** Background task outputs can expire before being read, causing data loss. Foreground parallel calls wait for all results.

### Agent 1: Backend/API Layer
Use `subagent_type: "feature-dev:backend-explorer"` with prompt:
```
Explore the backend/API layer for: [feature summary]
```

### Agent 2: Frontend/UI Layer
Use `subagent_type: "feature-dev:frontend-explorer"` with prompt:
```
Explore the frontend/UI layer for: [feature summary]
```

### Agent 3: Test Suite
Use `subagent_type: "feature-dev:test-explorer"` with prompt:
```
Explore the test suite for: [feature summary]
```

### Agent 4: Git History & Open PRs
Use `subagent_type: "feature-dev:history-explorer"` with prompt:
```
Explore git history and open PRs for: [feature summary]
```

## Phase 2: Synthesis

After all agents complete, combine findings into a structured plan following this template:

```markdown
---
type: implementation-plan
feature: [Feature Name]
date: [YYYY-MM-DD]
branch: [current branch]
---

## Implementation Plan: [Feature Name]

### Summary
[One paragraph: what this feature does, which layers it touches]

### Exploration Findings

#### Backend
[Key findings from Agent 1]

#### Frontend
[Key findings from Agent 2]

#### Tests
[Key findings from Agent 3]

#### History & Conflicts
[Key findings from Agent 4 — flag any potential conflicts]

### Files to Modify
| File | Change | Layer |
|------|--------|-------|
| [path] | [what to change] | backend/frontend/test |

### Files to Create
| File | Purpose | Layer |
|------|---------|-------|
| [path] | [what it does] | backend/frontend/test |

### Implementation Order
1. [Step 1 — with rationale]
2. [Step 2 — with dependency notes]
3. ...

### Key Decisions
| Decision | Options | Recommendation | Rationale |
|----------|---------|----------------|-----------|
| [e.g., where to put validation] | [A, B] | [chosen] | [why] |

### Risks
- [Risk 1 — and mitigation]
- [Risk 2 — and mitigation]

### Estimated Test Cases
- [Category]: [count] tests ([brief description])
```

## Phase 3: Save Plan

**YOU MUST save the plan to a file:**

1. Generate a filename from the feature name: `PLAN-<slug>.md` (e.g., `PLAN-scheduled-notifications.md`). The slug should be lowercase, hyphenated, max 4 words.
2. Write the plan to that file in the repository root using the Write tool.
3. If `PLAN-*.md` is not in the project's `.gitignore`, add it so plan files are never committed accidentally.

This file is used by `/feature-dev:tdd` to skip redundant exploration.

## Phase 4: User Review

Present the plan and ask:
1. Does this look correct? Any files or areas I missed?
2. Any decisions you'd like to override?
3. Ready to start implementation? (Suggest `/feature-dev:tdd` for test-driven execution in a **new conversation** to maximize available context)
