---
allowed-tools:
  - Task
argument-hint: [file-path | github-issue-url | text]
description: Identify gaps, edge cases, and ambiguities in requirements before implementation
---

## Input to Analyze

$ARGUMENTS

## Instructions

Use the Task tool to invoke the `prd-specialist` agent to analyze requirements and identify potential gaps.

The agent should:

1. **Load the content** from one of these sources:
   - Local file path (e.g., `./docs/prd-auth.md`)
   - GitHub issue URL (e.g., `https://github.com/owner/repo/issues/123`)
   - Direct text (if argument doesn't match file/URL pattern, treat as pasted content)
   - If empty, ask user to paste the requirements

2. **Analyze for gaps and issues**:

   **Ambiguities** - Unclear or open to interpretation:
   - Vague terms ("fast", "easy", "intuitive", "seamless")
   - Missing definitions ("users" - which users? all? admins?)
   - Implicit assumptions not stated

   **Edge Cases** - Boundary conditions not addressed:
   - Empty/null inputs
   - Maximum/minimum limits
   - Concurrent operations
   - Network failures, timeouts
   - Partial success states
   - Unicode, special characters, long strings

   **Missing Error Scenarios**:
   - What happens when X fails?
   - How to handle invalid input?
   - Rollback behavior on failure?
   - User feedback on errors?

   **Unspecified States**:
   - Loading/processing states
   - Empty states (no data yet)
   - Partial completion
   - Offline behavior

   **Dependencies & Assumptions**:
   - External services assumed available
   - Data format assumptions
   - Permission/auth requirements
   - Performance expectations

   **Security Considerations**:
   - Input validation requirements
   - Authorization checks
   - Data exposure risks

3. **Present findings as questions**:
   - Format as actionable questions to answer before implementation
   - Prioritize by impact (critical gaps first)
   - Group by category

4. **Suggest additions**:
   - Propose specific acceptance criteria to add
   - Recommend edge cases to document in "Out of Scope" or handle explicitly

Output should be a structured analysis that helps prevent surprises during implementation.
