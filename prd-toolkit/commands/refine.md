---
allowed-tools: Task
argument-hint: [file-path | github-issue-url | "paste"]
description: Improve an existing PRD with feedback and suggestions
---

## PRD to Refine

$ARGUMENTS

## Instructions

Use the Task tool to invoke the `prd-specialist` agent to refine an existing PRD.

The agent should:

1. **Load the PRD** from one of these sources:
   - Local file path (e.g., `./docs/prd-auth.md`)
   - GitHub issue URL (e.g., `https://github.com/owner/repo/issues/123`)
   - If argument is "paste" or empty, ask user to paste the PRD content

2. **Analyze against best practices**:
   - Are acceptance criteria observable (not implementation details)?
   - Are user stories from user perspective?
   - Is Out of Scope defined?
   - Are goals measurable?
   - Is the overview clear on problem + solution?

3. **Provide specific feedback**:
   - What's good (keep it brief)
   - What needs improvement (be specific)
   - Suggested rewrites for weak sections

4. **Offer to apply changes**:
   - Update the file directly
   - Update the GitHub issue
   - Display the improved version

Keep the collaborative tone - refine iteratively based on user feedback.
