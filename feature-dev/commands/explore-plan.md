---
disable-model-invocation: true
allowed-tools:
  - Read
  - Agent
  - Glob
argument-hint: "[feature description — optional; auto-discovers SPEC-*.md if omitted]"
description: |
  Use when starting a feature that touches multiple parts of the codebase and you need a
  structured implementation plan before coding.
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

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this command and proceed with your assigned task.
</SUBAGENT-STOP>

## Context
- **Repository**: !`git remote get-url origin`
- **Current branch**: !`git branch --show-current`
- **Feature**: $ARGUMENTS

## Phase 0: Resolve Feature and Validate

1. **Resolve the feature:**
   - **If `$ARGUMENTS` is provided** → use it as the feature description. Record `source_spec: null`.
   - **If `$ARGUMENTS` is empty** → auto-discover spec files. Use Glob with pattern `SPEC-*.md` in the repo root, then read each file's frontmatter and **filter out any spec with `status: implemented`** (those features are already shipped). From the remaining candidates:
     - **0 specs** → **STOP** and ask the user for a feature description.
     - **1 spec** → use it. Read its frontmatter, use `feature:` as the feature description, record the spec path as `source_spec`. Inform the user: "Auto-selected spec: `SPEC-<slug>.md` (feature: <name>, status: <status>)". If `status: draft`, also warn: "This spec is still in draft — the user may not have approved it yet. Proceed anyway?" and wait for confirmation.
     - **2+ specs** → use AskUserQuestion to let the user pick (label = `feature:` value, description = `<filename> — status: <status>`). Use the chosen spec's `feature:` as the feature description and record its path as `source_spec`.
2. Parse the feature into a one-line summary for agent prompts.
3. Generate a plan filename: `PLAN-<slug>.md` (slug = lowercase, hyphenated, max 4 words from the feature name. E.g., `PLAN-scheduled-notifications.md`). If `source_spec` is set, reuse its `slug:` value for consistency.

## Phase 1: Explore and Generate Plan (Forked)

Launch a **single Agent** with `subagent_type: "general-purpose"` to do all exploration and plan generation in an isolated context.

**CRITICAL: The agent MUST write the plan file to disk.** The agent's context is discarded after it completes — only the file persists.

Agent prompt — include all of this:

```
You are generating an implementation plan for: [feature summary]

Repository: [repo URL]
Branch: [current branch]
Plan file: [PLAN-<slug>.md filename from Phase 0]
Source spec: [source_spec path from Phase 0, or "none"]

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
slug: [feature-slug]
date: [YYYY-MM-DD]
branch: [current branch]
source_spec: [source_spec path, or null if none]
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
