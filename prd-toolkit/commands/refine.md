---
allowed-tools:
  - Task
argument-hint: [file-path | github-issue-url | "paste"]
description: Improve existing PRD or convert vague issue to structured PRD
keywords:
  - prd-improvement
  - issue-to-prd
  - requirements-refinement
  - prd-conversion
triggers:
  - "improve this PRD"
  - "convert issue to PRD"
  - "refine requirements"
  - "make this PRD better"
hooks:
  - event: Stop
    once: true
    command: |
      echo "Done. Next steps:"
      echo "  - /prd:analyze to identify remaining gaps"
      echo "  - /prd:validate after implementation to verify criteria"
---

## Input to Refine

$ARGUMENTS

## Instructions

Use the Task tool to invoke the `prd-specialist` agent to refine or convert the input to a proper PRD.

The agent should:

1. **Load the content** from one of these sources:
   - Local file path (e.g., `./docs/prd-auth.md`)
   - GitHub issue URL (e.g., `https://github.com/owner/repo/issues/123`)
   - If argument is "paste" or empty, ask user to paste the content

2. **Detect content type**:
   - **Already a PRD**: Has structured sections (Overview, Goals, Acceptance Criteria, etc.)
   - **Vague issue**: Unstructured text, feature request, or bug description

3. **If already a PRD** - Analyze and improve:
   - Are acceptance criteria observable (not implementation details)?
   - Are user stories from user perspective?
   - Is Out of Scope defined?
   - Are goals measurable?
   - Provide specific feedback and suggested rewrites

4. **If vague issue** - Convert to PRD:
   - Extract the core problem/request
   - Ask 1-2 clarifying questions if needed
   - Generate full PRD structure
   - Preserve original context and intent

5. **Offer to apply changes**:
   - Update the file directly
   - Update the GitHub issue
   - Display the improved/converted version

Keep the collaborative tone - iterate based on user feedback.
