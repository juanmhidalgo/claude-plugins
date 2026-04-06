# security

Security auditing workflow with vulnerability scanning, OWASP Top 10 verification, dependency audit, and hardening recommendations.

## Installation

```bash
/plugin install security@juanmhidalgo-plugins
```

## Commands

| Command | Description |
|---------|-------------|
| `/security:audit [path]` | Run comprehensive security audit with dependency scanning and code pattern analysis |
| `/security:checklist [area]` | Quick security checklist verification (areas: auth, input, data, infra, deps) |

## Agents

| Agent | Focus |
|-------|-------|
| `security-auditor` | Five-scope security review: input handling, auth, data protection, infrastructure, third-party integrations |

## Skills

| Skill | Purpose |
|-------|---------|
| `security-hardening` | Three-Tier Boundary System, OWASP prevention, input validation patterns |

## The Three-Tier Boundary System

Every security decision falls into one of three tiers:

- **Always Do** — Validate input, parameterize queries, hash passwords, set security headers, audit deps
- **Ask First** — New auth flows, sensitive data storage, CORS changes, file upload handlers
- **Never Do** — Commit secrets, log sensitive data, trust client-side validation, expose stack traces

## Requirements

- Git repository (for code analysis)
- `npm` / `pip` (for dependency auditing)
