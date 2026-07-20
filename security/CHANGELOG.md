# Changelog

## [1.2.0] - 2026-07-20

### Added
- **Counter-case (bias check) in the `security-auditor` agent.** Every finding now requires the strongest argument that it does not hold, written before severity is assigned, with the four common shapes named explicitly: sanitization upstream of the flagged line, unreachable code paths, framework-provided controls, and test fixtures mistaken for secrets. Adds a `**Counter-case:**` line to the finding format.
- **Reachability gate on severity.** CRITICAL and HIGH may not be assigned without having traced the input to its source; if the counter-case rests on a caller, middleware, or config that was not read, the finding caps at MEDIUM and must name what went unchecked.

### Why
Security review has both the highest false-positive rate of any review type and the most expensive false positives — they arrive labeled CRITICAL, so they get acted on before they get verified. The gate is deliberately about *ranking*, not suppression: an unverified counter-case is never grounds to drop a finding, only to rank it honestly. Extends the counter-case pattern from `code-review` 2.20.0.

## [1.1.2] - 2026-05-12

### Changed
- Removed unsupported `permissionMode` frontmatter field from `security-auditor` agent (plugin agents silently ignore `hooks`, `mcpServers`, and `permissionMode`).

## [1.1.1] - 2026-05-06

### Changed
- Trimmed `security-hardening` skill description to fit Claude Code's skill-listing budget.

## [1.1.0] - 2026-04-16

### Changed
- Rewrote skill/command descriptions to contain only triggering conditions and boundaries, removing workflow step summaries that caused the model to shortcut skill bodies

## [1.0.0] - 2026-04-04

### Added

- `audit` command: Comprehensive security audit with OWASP Top 10 checks, dependency scanning, and code pattern analysis
- `checklist` command: Quick security checklist verification by area (auth, input, data, infra, deps)
- `security-auditor` agent: Dedicated security review agent with five-scope analysis and severity classification
- `security-hardening` skill: Three-Tier Boundary System, input validation patterns, anti-rationalization table
- Reference: OWASP prevention patterns with TypeScript and Python code examples
- Reference: Security checklist organized by area (authentication, authorization, input, headers, CORS, data, deps, errors)
