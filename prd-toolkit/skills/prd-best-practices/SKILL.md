---
name: prd-best-practices
description: Best practices for writing PRDs and product requirements.
keywords:
  - prd-writing
  - product-requirements
  - acceptance-criteria
  - user-stories
triggers:
  - "write better PRDs"
  - "define acceptance criteria"
  - "structure requirements"
  - "product specification best practices"
allowed-tools:
  - Read
agent: prd-toolkit:prd-specialist
context: fork
user-invocable: true
---

# PRD Best Practices

## Core Principles

### Focus on Observable Behavior
- Describe what users see and experience
- Let developers investigate implementation details
- Avoid specifying classes, APIs, or technical architecture

### Keep it concise
- PRDs are for scoping, not full specs
- 1-2 pages max for most features
- If it's longer, break into smaller features

### Make it testable
- Every criterion should be verifiable by observing the product
- Use concrete, measurable outcomes
- Avoid vague terms like "fast", "easy", "better"

## Writing Good Acceptance Criteria

Focus on **what the user experiences**, not how it's built.

**Good (observable behavior):**
- [ ] User can sign in with their Google account
- [ ] Session stays active for 24 hours
- [ ] If login fails, error message shows with retry option
- [ ] Admin can connect multiple workspaces simultaneously

**Bad (implementation details):**
- [ ] Implement OAuth 2.0 with PKCE flow
- [ ] Store JWT tokens in Redis with 24h TTL
- [ ] Use retry logic with exponential backoff
- [ ] Create WorkspaceConnection model with foreign key to User

## Writing User Stories

Use the format: **As a [role], I want [action] so that [benefit]**

**Good:**
- As an admin, I want to connect my Teams workspace so that my team receives notifications
- As a user, I want to reply from Teams so that I can take action without opening another app

**Bad:**
- As a developer, I want to use the Teams API to implement webhooks
- As a system, I want to validate OAuth tokens to authenticate users

## Section Guidelines

### Overview
- 2-3 sentences max
- Answer: What problem? What solution?
- Include the user/business benefit

### Goals
- 2-4 business or user objectives
- Start with action verbs (Enable, Reduce, Improve, Expand)
- Tie to measurable outcomes when possible

### User Stories
- Cover main user roles affected
- Focus on user value, not system behavior
- 2-5 stories typically enough

### Acceptance Criteria
- Observable from user perspective
- Include happy path + key error cases
- Checkboxes for tracking

### Out of Scope
- Explicitly list what's NOT included
- Prevents scope creep
- Sets clear expectations for v1

### QA Checklist
- User scenarios to validate
- Alternative flows and error states
- NOT technical test cases

## Common Mistakes to Avoid

1. **Specifying implementation** - Don't mention databases, APIs, or code patterns
2. **Scope creep** - Use Out of Scope section to set boundaries
3. **Vague criteria** - "Should be fast" → "Responds in under 2 seconds"
4. **System perspective** - Write from user POV, not system POV
5. **Missing error cases** - What happens when things fail?

## Format for Different Destinations

### GitHub Issues
- Checkbox syntax works natively
- Use task lists for sub-items
- Link related issues with `#123`

### ClickUp
- Checkbox syntax: `- [ ]`
- Keep sections with `##` headers
- Add labels/tags in task metadata

### Local Files
- Standard markdown
- Consider adding date and author
- Store in `docs/` directory
