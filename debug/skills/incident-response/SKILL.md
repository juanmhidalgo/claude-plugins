---
name: incident-response
description: |
  Use to run an incident response workflow — initial triage, status updates during, blameless postmortem after.
  Do NOT use for ordinary debugging — use debugging-strategies for single-engineer bug-hunting.
keywords:
  - incident
  - postmortem
  - sev
  - production-outage
  - blameless
triggers:
  - "we have an incident"
  - "production is down"
  - "write a postmortem"
  - "run incident response"
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Incident Response

Run an incident through three phases: **new** (triage) → **update** (status broadcast) → **postmortem** (blameless retrospective).

## When to use this vs. debugging-strategies

- **Incident response**: production is degraded, multiple users affected, time-pressured, multi-actor coordination needed.
- **debugging-strategies**: a bug in your local environment or CI, single engineer working through it.

If you started in debugging-strategies and it escalated into a customer-impacting outage, switch here. The mindset shifts from "find the cause" to "stop the bleeding, then find the cause." The actual investigation work still uses **`debug:debugging-strategies`** — this skill is the coordination layer on top.

## Mode 1 — new: Triage

Detect, classify severity, assign roles. The first 5 minutes set the trajectory.

### Severity Classification

| Level | Criteria | Response |
|-------|----------|----------|
| SEV1 | Service down for all users / data loss in progress / security breach | Immediate; all-hands; page incident commander |
| SEV2 | Major feature degraded for many users / persistent errors on critical paths | Within 15 min; assign IC and comms |
| SEV3 | Minor feature issue for some users / non-critical degradation | Within 1 hour; one responder |
| SEV4 | Cosmetic / low-impact / single-user issue | Next business day; ticket |

### Triage Output Template

```markdown
# Incident: <title>
**Severity**: SEV<X>
**Detected**: <timestamp>  **Detected by**: <alert / customer / oncall>
**Affected**: <users / regions / features>

## Initial Hypothesis
<one paragraph — what we currently think is happening, with confidence>

## Roles
- **Incident Commander**: <name>
- **Communications**: <name>
- **Responders**: <names>

## Immediate Actions
- [ ] <stop-the-bleeding step>
- [ ] <containment step>
- [ ] <data-collection step (logs, metrics, repro)>
```

## Mode 2 — update: Status Broadcast

Post regular updates to keep stakeholders informed. Cadence:

- **SEV1**: every 15 minutes minimum
- **SEV2**: every 30 minutes
- **SEV3**: every 1 hour or on status change

### Status Update Template

```markdown
## Incident Update — <title>
**Severity**: SEV<X>  **Status**: Investigating | Identified | Mitigating | Monitoring | Resolved
**Impact**: <one sentence on who/what is affected>
**Last Updated**: <timestamp>

### What we know now
<plain-language summary; no speculation>

### What we've done
- <action 1 with timestamp>
- <action 2 with timestamp>

### What's next
- <next step with ETA>

### Next update
<timestamp>
```

## Mode 3 — postmortem: Blameless Retrospective

After resolution, write a blameless postmortem. Focus on systems and processes, not individuals.

### Postmortem Template

```markdown
# Postmortem: <title>
**Date**: <date>  **Duration**: <X hours>  **Severity**: SEV<X>
**Authors**: <names>  **Status**: Draft | Reviewed | Final

## Summary
<2-3 sentences in plain language — what happened, who was affected, how it ended>

## Impact
- **Users affected**: <count or %>
- **Duration**: <X minutes from first symptom to full resolution>
- **Business impact**: <revenue / SLA / reputation; quantified where possible>

## Timeline
| Time (UTC) | Event |
|------------|-------|
| HH:MM | First symptom — <description> |
| HH:MM | Detected — <by what / whom> |
| HH:MM | Triage — <SEV assigned, IC assigned> |
| HH:MM | Mitigation deployed — <what was done> |
| HH:MM | Service restored — <verification> |

## Root Cause (5 Whys)
1. Why did <symptom>? → <because immediate cause>
2. Why did <immediate cause>? → <because deeper cause>
3. Why did <deeper cause>? → <because still deeper>
4. Why did <still deeper>? → <because closer to root>
5. Why did <root level>? → <root cause — usually a missing process, alert, or capacity decision>

## What Went Well
- <thing that worked — detection, communication, coordination>
- <process that prevented worse outcome>

## What Went Poorly
- <thing that didn't work — slow detection, unclear ownership, missing playbook>
- <pattern that should change>

## Action Items
| Action | Owner | Priority | Due |
|--------|-------|----------|-----|
| <action> | <name> | P0 / P1 / P2 | <date> |

P0 = before next deploy. P1 = within 2 weeks. P2 = next quarter or backlog.

## Lessons Learned
<2-4 bullets — what the team takes away that applies beyond this incident>
```

## Common Postmortem Mistakes

| Mistake | What it looks like | Fix |
|---------|-------------------|-----|
| **Naming the person** | "Bob deployed without testing" | Name the system or role. "Deploy pipeline allowed an untested change." |
| **5 Whys stopping at the first plausible cause** | "Why did the disk fill? → Logs grew too fast. Done." | Keep going. The next four whys usually reveal the systemic cause (rotation policy missing, alerting gap, capacity-planning blind spot). |
| **Action items without owners or dates** | "Investigate retry logic" | Every action item gets a name and a date. Otherwise it lives forever in a backlog and nothing changes. |
| **Symptom-only timeline** | Timeline shows only customer-visible events | Include internal events: when the alert fired, when triage started, when mitigation was attempted. Operational gaps live in the *internal* timeline. |
| **Skipping What Went Well** | "Lessons learned" is all critique | Document what prevented worse outcomes. Reinforces practices that paid off; surfaces them for replication. |
| **Pre-populating the conclusion** | Author writes the root cause before the team reviews the timeline | Build the timeline first, run 5 Whys with the team, then write the cause. Other order contaminates the analysis with a hypothesis. |

## Rationalization Defenses

If you catch yourself thinking any of these, STOP — you are about to write a worse postmortem:

| Excuse | Why It's Wrong |
|--------|----------------|
| "We don't need a postmortem, it was a one-off" | The team learns from postmortems even on one-offs. The bar for skipping is "no operational improvement is possible from this," which is rare. |
| "Naming who did what is necessary for accountability" | Blameless ≠ accountability-free. Name the *role* and the *system*, not the individual. Individual blame produces silence, not learning. |
| "The 5 Whys can stop at 2 if the cause is obvious" | If two whys produce a fix that prevents *recurrence*, fine. If they only fix *this incident*, keep going — recurrence-prevention is the goal. |
| "We'll write the postmortem next week" | Write the timeline within 24h while memory is fresh. The analysis can come later, but raw events evaporate fast. |
| "The customer wasn't really affected, severity was lower than we said" | Recalibrating severity downward after the fact erodes the operational signal. Mark the severity at the time it was assigned; if criteria need to change, change them in the runbook for next time. |
