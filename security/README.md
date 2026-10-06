# security

Security auditing workflow with vulnerability scanning, OWASP Top 10 verification, dependency audit, and hardening recommendations.

## Running in a Herdr pane

`/security:audit [scope] --pane` runs the audit in a separate session in a sibling pane, without blocking this one. The findings come back here.

Inside [Herdr](https://herdr.dev) only; outside it, `--pane` says so and runs normally. Approvals and questions appear in the pane, with a Herdr notification. Flow and exit codes: `references/herdr-pane.md` (a synced copy of `shared/herdr-pane/` in the marketplace repo).

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

## Needs

- A git repository (for code analysis)
- `npm` / `pip` (for dependency auditing)
- No `gh`, MCP servers, or browser
