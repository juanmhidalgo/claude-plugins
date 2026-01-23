---
allowed-tools:
  - Bash(gh *)
  - Bash(git *)
  - Task
  - Read
  - Glob
  - Grep
argument-hint: <PR number or URL>
description: Comprehensive code review for a pull request using multi-agent workflow
keywords:
  - pull-request
  - code-review
  - github-pr
  - multi-agent
  - bug-detection
  - security-review
triggers:
  - "review this PR"
  - "review pull request"
  - "check PR for issues"
  - "code review my changes"
  - "run code review on PR"
hooks:
  - event: Stop
    once: true
    command: |
      echo "📝 Code review complete. Next steps:"
      echo "  • Use /code-review:fixes-plan to create fix tracking"
      echo "  • Use /code-review:implement-fix to apply fixes"
---

## Pull Request Code Review

**Target PR**: $ARGUMENTS
**Repository**: !`git remote get-url origin 2>/dev/null | sed 's/.*github.com[:/]\(.*\)\.git/\1/' | sed 's/.*github.com[:/]\(.*\)/\1/'`
**Current branch**: !`git branch --show-current`

Execute this multi-step code review workflow precisely:

---

### Step 1: Eligibility Check

Use Task tool with `subagent_type="code-review:pr-eligibility-checker"` and `model="haiku"` to check if the PR is eligible for review.

**Stop conditions** (do not proceed if any are true):
- PR is closed or merged
- PR is a draft
- PR author is a bot (dependabot, renovate, github-actions)
- PR is trivial (only docs/config/lockfiles)
- PR already has a Claude Code review comment

If not eligible, inform the user why and stop.

---

### Step 2: CLAUDE.md Discovery

Use Task tool with `subagent_type="code-review:claudemd-discoverer"` and `model="haiku"` to find relevant CLAUDE.md files.

Provide the list of files changed in the PR. Get file paths for any CLAUDE.md found.

---

### Step 3: PR Summary

Use Task tool with `subagent_type="code-review:pr-summarizer"` and `model="haiku"` to get a summary of the PR changes.

Store this summary for context in the parallel reviews.

---

### Step 4: Parallel Code Review (5 Agents)

Launch these 5 agents **in parallel** using multiple Task tool calls in a single message:

1. **CLAUDE.md Compliance** - `subagent_type="code-review:claudemd-compliance-reviewer"` (Sonnet)
   - Provide: PR number, CLAUDE.md files from Step 2, PR summary

2. **Bug Scanner** - `subagent_type="code-review:bug-scanner"` (Sonnet)
   - Provide: PR number

3. **Git History** - `subagent_type="code-review:git-history-reviewer"` (Sonnet)
   - Provide: PR number, files changed

4. **Previous PR Comments** - `subagent_type="code-review:pr-comments-reviewer"` (Sonnet)
   - Provide: PR number, files changed

5. **Code Comments** - `subagent_type="code-review:code-comments-reviewer"` (Sonnet)
   - Provide: PR number, files changed

Collect all issues from all agents.

---

### Step 5: Confidence Scoring

For **each issue** found in Step 4, launch a parallel Haiku agent using Task tool with `subagent_type="code-review:confidence-scorer"` and `model="haiku"`.

Provide each agent:
- PR number
- The specific issue to score
- CLAUDE.md files (if issue is compliance-related)

Use this rubric (give to agents verbatim):
- **0**: False positive, doesn't stand up to scrutiny, or pre-existing
- **25**: Maybe real, couldn't verify, stylistic without CLAUDE.md backing
- **50**: Real but nitpick, rare in practice, not very important
- **75**: Verified real, will be hit in practice, important or in CLAUDE.md
- **100**: Definitely real, will happen frequently, evidence confirms

---

### Step 6: Filter Issues

Remove any issues with confidence score **below 80**.

If no issues remain, proceed to Step 8 with "no issues found".

---

### Step 7: Re-verify Eligibility

Use Task tool with `subagent_type="code-review:pr-eligibility-checker"` and `model="haiku"` to confirm PR is still eligible (not closed/merged while reviewing).

If no longer eligible, inform user and stop.

---

### Step 8: Comment on PR

Use `gh pr comment` to post the review. Follow this format exactly:

**If issues found:**
```markdown
### Code review

Found N issues:

1. <brief description> (CLAUDE.md says "<quote>" | bug due to <reason>)

<link to file with full SHA and line range, e.g., https://github.com/owner/repo/blob/abc123def.../file.py#L10-L15>

2. ...

---
Generated with [Claude Code](https://claude.ai/code)

<sub>If this review was useful, react with :+1:. Otherwise, react with :-1:.</sub>
```

**If no issues:**
```markdown
### Code review

No issues found. Checked for bugs and CLAUDE.md compliance.

---
Generated with [Claude Code](https://claude.ai/code)
```

---

## Link Format Requirements

- Use **full SHA-1 hash** (not short hash, not HEAD)
- Format: `https://github.com/{owner}/{repo}/blob/{full_sha}/{file}#L{start}-L{end}`
- Include 1 line of context before and after (e.g., for line 5, link to L4-L6)
- Get SHA with: `gh pr view <PR> --json headRefOid -q '.headRefOid'`

---

## False Positives to Avoid

Do NOT flag:
- Pre-existing issues (not introduced in this PR)
- Issues a linter/typechecker/compiler would catch
- Pedantic nitpicks a senior engineer wouldn't call out
- General code quality unless explicitly in CLAUDE.md
- Issues with lint ignore comments (intentionally silenced)
- Intentional functionality changes
- Issues on lines NOT modified in the PR

---

## Important Notes

- Do NOT run build/typecheck (CI handles this)
- Use `gh` for all GitHub interactions
- Keep output brief, no emojis
- MUST cite and link each issue
- Create a todo list to track progress through the steps
