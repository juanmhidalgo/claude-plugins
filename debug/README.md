# debug

Systematic debugging workflow with structured triage, root cause analysis, regression guards, and error pattern recognition.

## Installation

```bash
/plugin install debug@juanmhidalgo-plugins
```

## Commands

| Command | Description |
|---------|-------------|
| `/debug:debug <error>` | Systematic 6-step debugging: reproduce, localize, reduce, root cause, guard, verify |
| `/debug:triage <error>` | Quick error classification with targeted investigation steps |

## Skills

| Skill | Purpose |
|-------|---------|
| `debugging-strategies` | Stop-the-Line Rule, triage checklist, error output safety, anti-rationalizations |

## The Stop-the-Line Rule

When anything unexpected happens:

1. **STOP** — Don't add features or push past failures
2. **PRESERVE** — Save error output, logs, reproduction steps
3. **DIAGNOSE** — Follow the structured triage checklist
4. **FIX** — Address the root cause, not the symptom
5. **GUARD** — Write a regression test
6. **RESUME** — Only after all verification passes

## Requirements

- Git repository (for bisect and history analysis)
- Test runner (npm test, pytest, etc.)
