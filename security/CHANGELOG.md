# Changelog

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
