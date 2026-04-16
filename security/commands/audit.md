---
description: |
  Use when you need to audit the codebase or specific files for security vulnerabilities.
  Do NOT use for general code quality — use /code-review:branch for that.
argument-hint: "[path or scope]"
keywords:
  - security
  - audit
  - vulnerability
  - owasp
triggers:
  - "run security audit"
  - "check for vulnerabilities"
  - "security review"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(npm audit *)
  - Bash(pip audit *)
  - Bash(pipenv check *)
  - Bash(git log *)
  - Bash(git diff *)
  - Bash(curl -sI *)
  - Agent
hooks:
  - event: Stop
    once: true
    command: |
      echo "Security audit complete. Next steps:"
      echo "  - Fix CRITICAL/HIGH findings immediately"
      echo "  - Schedule MEDIUM findings for current sprint"
      echo "  - /security:checklist to verify fixes"
      echo "  - /code-review:branch to review changes before merge"
---

## Context

- **Branch**: !`git branch --show-current`
- **Recent commits**: !`git log --oneline -5`

<best_practices>
@security/skills/security-hardening/SKILL.md
</best_practices>

## Security Audit Workflow

Audit scope: **$ARGUMENTS** (if empty, audit the full codebase).

### Phase 1: Scope & Detect Stack

1. Determine audit scope from the argument (specific path or full repo)
2. Detect the tech stack: language, framework, package manager, database
3. Identify high-risk areas: auth, input handling, API endpoints, file uploads, external integrations

### Phase 2: Dependency Scan

Run the appropriate dependency audit:
- **Node.js**: `npm audit` — check for critical/high CVEs
- **Python**: `pip audit` or `pipenv check`
- **Other**: Check for lockfile-based audit tools

Triage results using the decision tree from the skill reference.

### Phase 3: Code Pattern Scan

Search for common vulnerability patterns:

**Secrets in code:**
- Hardcoded API keys, passwords, tokens, connection strings
- `.env` files committed to git
- Secrets in comments or config files

**Injection vectors:**
- String concatenation in SQL queries (no parameterization)
- `eval()`, `exec()`, `os.system()` with user input
- `innerHTML`, `dangerouslySetInnerHTML` with unsanitized data
- Command injection via shell execution

**Auth gaps:**
- Endpoints missing authentication middleware
- Missing authorization checks (IDOR risks)
- Insecure session configuration

**Data exposure:**
- Sensitive fields in API responses (passwords, tokens, PII)
- Stack traces or internal errors in error responses
- Verbose logging of sensitive data

### Phase 4: Configuration Review

Check security configuration:
- Security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options)
- CORS configuration (wildcard origins?)
- Cookie settings (httpOnly, secure, sameSite)
- Rate limiting on auth endpoints
- `.gitignore` covers secrets (.env, *.pem, *.key)

### Phase 5: Report

Use the security-auditor agent to produce the final report. Generate findings using the severity classification from the agent, organized from CRITICAL to INFO.

Include:
- Summary with finding counts per severity
- Each finding with location, description, impact, and recommendation
- Positive observations (what's done well)
- Proactive recommendations for defense-in-depth
