---
name: branch-review
description: |
  Use when reviewing branch changes or PRs for merge readiness with severity classification.
  Do NOT use for general code quality advice — use dedicated linters.
keywords:
  - code-review
  - branch-comparison
  - diff-analysis
  - pr-preparation
  - security-checklist
triggers:
  - "review branch changes"
  - "compare branches"
  - "analyze diff"
  - "prepare PR for merge"
  - "check code before merge"
allowed-tools:
  - Bash(git *)
  - Read
  - Grep
agent: code-review:branch-reviewer
user-invocable: true
---

# Branch Review

## Severity Classification

| Level | Block Merge? | Examples |
|-------|--------------|----------|
| CRITICAL | Yes | Security vulnerabilities, data loss risks, breaking changes without migration |
| HIGH | Should fix | Bugs affecting users, performance regressions, missing error handling |
| MEDIUM | Recommend | Code smells, minor perf issues, missing non-critical tests |
| LOW | Optional | Style issues, refactoring opportunities, docs |

## Confidence Classification

Severity answers "should this block merge?". Confidence answers "how strong is the evidence?". They are orthogonal — always pair both on every finding.

| Level | Meaning |
|-------|---------|
| HIGH | Verified by reading the code path. Evidence is direct: cited file:line, observable behavior, or reproducible scenario. |
| MEDIUM | Strong inference from code patterns or framework behavior; would benefit from runtime confirmation before fixing. |
| LOW | Speculation or pattern-based concern; may not apply in this specific context. Worth flagging, not over-weighting. |

A HIGH-severity / LOW-confidence finding ("this *might* be a security bug") needs different handling than HIGH-severity / HIGH-confidence ("this *is* a security bug — block merge"). Calibrate the response to both dimensions.

## Counter-Case (Bias Check)

Every finding requires an explicit argument against itself, written *before* assigning Confidence. State the strongest case that this is a false positive, an intentional design choice, or an edge case that does not apply here.

The counter-case determines the Confidence label — it is not decorative prose:

| What the counter-case looks like | Confidence |
|---|---|
| No plausible counter-case; you read the code path and the defect holds | HIGH |
| A counter-case exists but depends on context you did **not** verify in the code | MEDIUM at most |
| The counter-case is as strong as the finding | LOW — or drop the finding entirely |

Two failure modes to avoid: a token counter-case written to satisfy the format ("this could be intentional" with no mechanism), and a counter-case that survives scrutiny but leaves Confidence at HIGH anyway. If you can articulate a real reason the code is correct, the Confidence label must move.

## Feedback Format

```markdown
**[SEVERITY] · [CONFIDENCE]** Brief title

📍 `path/to/file.py:42`

**Issue:** Clear description of the problem

**Risk:** What could go wrong

**Evidence:** What in the code proves (or suggests) this — required for HIGH; recommended for MEDIUM; explicit "speculation only" if LOW

**Counter-case:** The strongest reason this may be a false positive or a deliberate choice — and what you would need to read to rule it out

**Suggestion:**
```python
# Recommended fix
```
```

## Focus Areas (Non-Obvious)

**Security** - Hardcoded secrets, missing input validation, SQL injection, auth gaps. For deeper threat modeling and OWASP-aligned analysis, delegate to the **`security:security-hardening`** skill rather than expanding this section — that skill is the canonical security reference.

**Bugs** - Race conditions in concurrent code, resource leaks (connections, file handles)

**Performance** - N+1 queries, blocking calls in async contexts, missing pagination. For load profiling and Core Web Vitals analysis, delegate to **`performance:performance-optimization`** rather than diagnosing here.

## Review Anti-Patterns

1. **Nitpicking** - Don't block on minor style issues
2. **Rubber stamping** - Actually read the code
3. **Bike-shedding** - Focus on important issues
4. **No context** - Understand the "why" before criticizing

## Request Changes vs Comment

**Request Changes:** Security issues, bugs affecting users, breaking changes, missing critical tests

**Comment Only:** Suggestions, questions about approach, style preferences, future considerations
