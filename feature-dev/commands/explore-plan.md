---
disable-model-invocation: true
allowed-tools:
  - Read
  - Agent
  - Glob
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
      echo "Exploration complete."
      echo "  - Review the plan above, then run /feature-dev:tdd to implement"
      echo "  - Or start a NEW conversation and run /feature-dev:tdd (maximizes context)"
---

## Context
- **Repository**: !`git remote get-url origin 2>/dev/null || echo "unknown"`
- **Current branch**: !`git branch --show-current`
- **Feature**: $ARGUMENTS

## Phase 0: Validate

1. Feature description was provided (from $ARGUMENTS). If empty, **STOP** and ask user.
2. Parse the feature into a one-line summary for agent prompts.
3. Generate a plan filename: `PLAN-<slug>.md` (slug = lowercase, hyphenated, max 4 words from the feature name. E.g., `PLAN-scheduled-notifications.md`).

## Phase 1: Explore and Generate Plan (Forked)

Launch a **single Agent** with `subagent_type: "general-purpose"` to do all exploration and plan generation in an isolated context.

**CRITICAL: The agent MUST write the plan file to disk.** The agent's context is discarded after it completes — only the file persists.

Agent prompt — include all of this:

```
You are generating an implementation plan for: [feature summary]

Repository: [repo URL]
Branch: [current branch]
Plan file: [PLAN-<slug>.md filename from Phase 0]

## Step 1: Parallel Exploration

Launch all four agents in a single response. Do NOT use run_in_background.

Agent 1 — subagent_type: "feature-dev:backend-explorer"
Prompt: "Explore the backend/API layer for: [feature summary]"

Agent 2 — subagent_type: "feature-dev:frontend-explorer"
Prompt: "Explore the frontend/UI layer for: [feature summary]"

Agent 3 — subagent_type: "feature-dev:test-explorer"
Prompt: "Explore the test suite for: [feature summary]"

Agent 4 — subagent_type: "feature-dev:history-explorer"
Prompt: "Explore git history and open PRs for: [feature summary]"

## Step 2: Synthesize and Write Plan

After all agents complete, synthesize findings into a plan and write it to [PLAN-<slug>.md] using the Write tool.

The plan MUST follow this template:

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

## Step 3: Update .gitignore

If PLAN-*.md is not in the project's .gitignore, add it.
```

## Phase 2: Present Plan for Review

After the agent completes:

1. Read the `PLAN-<slug>.md` file from disk
2. Present the full plan to the user
3. Ask:
   - Does this look correct? Any files or areas I missed?
   - Any decisions you'd like to override?
   - Ready to implement? (Suggest `/feature-dev:tdd` to start)
