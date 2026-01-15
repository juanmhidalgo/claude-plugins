---
description: Analyze a CLAUDE.md file against Anthropic's best practices and generate optimization recommendations
argument-hint: "[path/to/CLAUDE.md]"
keywords:
  - claude-md-analysis
  - best-practices-audit
  - prompt-optimization
  - memory-file
triggers:
  - "analyze my CLAUDE.md"
  - "check CLAUDE.md quality"
  - "audit memory file"
  - "review CLAUDE.md"
allowed-tools: [Read, Glob, Bash]
---

# Analyze CLAUDE.md

Analyze a CLAUDE.md file against Anthropic's official best practices.

<context>
**Skill activated**: `claude-md-best-practices`
**Working directory**: !`pwd`
**Target file**: `$1` or auto-detect (./CLAUDE.md → ./.claude/CLAUDE.md)
</context>

<task>
Generate comprehensive optimization report with score (0-100) and actionable recommendations.
</task>

## Analysis Criteria

<structure_analysis weight="25">
  - XML tags present and consistent
  - Clear hierarchy (nesting, priority attributes)
  - Sections properly labeled (context, instructions, examples, references)
</structure_analysis>

<conciseness_analysis weight="25">
  - Token count vs. target range for project size
  - No verbose explanations of basic concepts
  - No long embedded code examples (50+ lines)
  - No repetitive content
</conciseness_analysis>

<content_quality_analysis weight="25">
  - Essential sections present (context, directories, standards, commands)
  - External references for complex content
  - Persuasion principles for critical rules (Authority, Commitment, Social Proof)
  - NO sensitive data (credentials, keys, connection strings)
  - Actionable workflows defined
</content_quality_analysis>

<memory_patterns_analysis weight="25">
  - Uses imports (@path) for external content
  - Modularization with `.claude/rules/*.md`
  - Path-specific rules use YAML frontmatter
</memory_patterns_analysis>

## Token Targets by Project Size

<token_targets>
- Small (< 10K LOC): 800-1200 tokens
- Medium (10-50K LOC): 1200-2000 tokens
- Large (> 50K LOC): 2000-2500 tokens
</token_targets>

## Scoring

<score_ranges>
- 90-100: Excellent (minor tweaks only)
- 75-89: Good (some optimization opportunities)
- 60-74: Needs improvement
- 0-59: Poor (major restructuring required)
</score_ranges>

## Output Format

<output_structure>
# CLAUDE.md Analysis Report

**File**: [path]
**Date**: [current date]
**Score**: [X]/100 ([Rating])

---

## Metrics

- **Lines**: [count]
- **Estimated Tokens**: [count * 8]
- **Target Range**: [range for project size]
- **Status**: [within/above/below target]

---

## Analysis Summary

<dimension name="Structure" score="X/25">
[Brief summary with specific issues]
</dimension>

<dimension name="Conciseness" score="X/25">
[Brief summary with specific issues]
</dimension>

<dimension name="Content Quality" score="X/25">
[Brief summary with specific issues]
</dimension>

<dimension name="Memory Patterns" score="X/25">
[Brief summary with specific issues]
</dimension>

---

## Issues by Priority

<high_priority>
Issues blocking effective Claude Code usage:
1. [Issue with line numbers] - Impact: [description] - Fix: [specific action]
</high_priority>

<medium_priority>
Significant improvement opportunities:
1. [Issue] - Savings: [X tokens] - Fix: [action]
</medium_priority>

<low_priority>
Nice-to-have enhancements:
1. [Issue] - Fix: [action]
</low_priority>

---

## Token Efficiency Report

**Current**: [X] tokens
**Target**: [Y] tokens
**Potential savings**: -[Z]% tokens

<optimization_opportunities>
1. XML structuring: -[X]% tokens
2. Externalizing examples: -[Y]% tokens
3. Consolidating rules: -[Z]% tokens
</optimization_opportunities>

---

## Next Steps

<recommended_actions>
1. Run `/optimize-claude-md [path] [--level=moderate]` to apply optimizations
2. Manual review: [specific areas requiring attention]
3. Consider modularizing: [topics for .claude/rules/]
</recommended_actions>
</output_structure>

## Critical Rules

<rule priority="blocking">
YOU MUST flag sensitive data (API keys, credentials, connection strings) as HIGH PRIORITY immediately.
</rule>

<rule priority="blocking">
Provide specific line numbers for ALL issues. Vague feedback is useless.
</rule>

<rule priority="recommended">
Show concrete before/after examples for top 3 improvements.
</rule>

<rule priority="recommended">
Estimate token counts realistically (avg 8 tokens/line, adjust for code blocks).
</rule>
