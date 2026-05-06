---
description: |
  Use to manage an incident through its lifecycle: triage on detection, status updates during, blameless postmortem after.
  Do NOT use for ordinary debugging — use /debug:debug for single-engineer bug-hunting.
argument-hint: "<new | update | postmortem> [description]"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git log:*)
  - Bash(git branch --show-current)
keywords:
  - incident
  - postmortem
  - sev
  - outage
  - blameless
triggers:
  - "we have an incident"
  - "production is down"
  - "write a postmortem"
  - "run incident response"
  - "incident commander"
hooks:
  - event: Stop
    once: true
    command: |
      echo "Incident step complete."
      echo "Next-step suggestions:"
      echo "  - For investigation: /debug:debug to dig into root cause"
      echo "  - For follow-up postmortem: /debug:incident postmortem"
---

<best_practices>
@debug/skills/incident-response/SKILL.md
</best_practices>

# Incident Response

Manage an incident from detection through postmortem.

**Mode**: $ARGUMENTS

## Mode Detection

If `$ARGUMENTS` starts with `new`, `update`, or `postmortem`, use that mode. Otherwise ask the user via AskUserQuestion:

> Which incident phase are you in?
> - **new** — initial detection, need to triage and assign severity/roles
> - **update** — incident is in progress, need a status broadcast
> - **postmortem** — incident is resolved, time for blameless retrospective

Then follow the workflow in the **incident-response** skill above. The skill carries the templates and guardrails — do not duplicate them here.

## Cross-Skill Handoff

For root-cause investigation during the incident, delegate to **`debug:debugging-strategies`** (Stop-the-line rule, triage checklist, error-output safety). This command is the coordination layer; debugging-strategies is the investigation layer.
