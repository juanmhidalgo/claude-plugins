#!/bin/bash
# pr-review-summary.sh - Quick overview of PR review status
# Usage: ./pr-review-summary.sh owner repo pr_number [--markdown]
#
# Example: ./pr-review-summary.sh facebook react 123
#          ./pr-review-summary.sh facebook react 123 --markdown

set -euo pipefail

OWNER="${1:?Usage: $0 owner repo pr_number [--markdown]}"
REPO="${2:?Usage: $0 owner repo pr_number [--markdown]}"
PR_NUMBER="${3:?Usage: $0 owner repo pr_number [--markdown]}"
FORMAT="${4:-json}"

BOT_PATTERN="bot|copilot|gemini|claude|gpt|dependabot|renovate|greenkeeper|codecov|sonarcloud|github-actions"

# Fetch reviews
REVIEWS=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews" --jq '
  group_by(.state) |
  map({key: .[0].state, value: length}) |
  from_entries |
  {
    approved: (.APPROVED // 0),
    changes_requested: (.CHANGES_REQUESTED // 0),
    commented: (.COMMENTED // 0)
  }
')

# Get blocking reviewers
BLOCKING=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews" --jq '
  [.[] | select(.state == "CHANGES_REQUESTED") | .user.login] | unique
')

# Count comments
ISSUE_COUNT=$(gh api "repos/$OWNER/$REPO/issues/$PR_NUMBER/comments" --jq 'length')
REVIEW_COUNT=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" --jq 'length')

# Count bots vs humans in comments
BOT_HUMAN=$(gh api "repos/$OWNER/$REPO/issues/$PR_NUMBER/comments" --jq '
  [.[] | .user.login | test("'"$BOT_PATTERN"'"; "i")] |
  {bots: [.[] | select(. == true)] | length, humans: [.[] | select(. == false)] | length}
')
BOT_HUMAN2=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" --jq '
  [.[] | .user.login | test("'"$BOT_PATTERN"'"; "i")] |
  {bots: [.[] | select(. == true)] | length, humans: [.[] | select(. == false)] | length}
')

if [ "$FORMAT" = "--markdown" ]; then
  # Output as markdown
  APPROVED=$(echo "$REVIEWS" | jq -r '.approved')
  CHANGES=$(echo "$REVIEWS" | jq -r '.changes_requested')
  COMMENTED=$(echo "$REVIEWS" | jq -r '.commented')
  BLOCKERS=$(echo "$BLOCKING" | jq -r 'if length > 0 then map("@" + .) | join(", ") else "None" end')

  BOT_COUNT=$(echo "$BOT_HUMAN $BOT_HUMAN2" | jq -s '.[0].bots + .[1].bots')
  HUMAN_COUNT=$(echo "$BOT_HUMAN $BOT_HUMAN2" | jq -s '.[0].humans + .[1].humans')
  TOTAL=$((ISSUE_COUNT + REVIEW_COUNT))

  cat << EOF
# PR Review Summary

## Review Status
- Approved: $APPROVED
- Changes Requested: $CHANGES
- Commented: $COMMENTED

## Blocking Reviewers
$BLOCKERS

## Comment Statistics
- Total Comments: $TOTAL
- Issue Comments: $ISSUE_COUNT
- Review Comments: $REVIEW_COUNT
- Bot Comments: $BOT_COUNT
- Human Comments: $HUMAN_COUNT
EOF

else
  # Output as JSON
  jq -n \
    --argjson reviews "$REVIEWS" \
    --argjson blocking "$BLOCKING" \
    --argjson issue_count "$ISSUE_COUNT" \
    --argjson review_count "$REVIEW_COUNT" \
    --argjson bh1 "$BOT_HUMAN" \
    --argjson bh2 "$BOT_HUMAN2" '
  {
    review_status: ($reviews + {
      blocking_reviewers: $blocking,
      is_blocked: ($blocking | length > 0)
    }),
    comment_counts: {
      total: ($issue_count + $review_count),
      issue_comments: $issue_count,
      review_comments: $review_count,
      bot_comments: ($bh1.bots + $bh2.bots),
      human_comments: ($bh1.humans + $bh2.humans)
    }
  }'
fi
