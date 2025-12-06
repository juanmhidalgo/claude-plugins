#!/bin/bash
# pr-triage-comments.sh - Token-optimized PR comments for AI review triage
# Usage: ./pr-triage-comments.sh owner repo pr_number [max_body_length] [include_humans]
#
# Example: ./pr-triage-comments.sh facebook react 123
#          ./pr-triage-comments.sh facebook react 123 1500 true

set -euo pipefail

OWNER="${1:?Usage: $0 owner repo pr_number [max_body_length] [include_humans]}"
REPO="${2:?Usage: $0 owner repo pr_number [max_body_length] [include_humans]}"
PR_NUMBER="${3:?Usage: $0 owner repo pr_number [max_body_length] [include_humans]}"
MAX_BODY="${4:-1500}"
INCLUDE_HUMANS="${5:-false}"

# Bot patterns for filtering
BOT_PATTERN="bot|copilot|gemini|claude|gpt|dependabot|renovate|greenkeeper|codecov|sonarcloud|github-actions"

# Fetch PR info
PR_INFO=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER" --jq '{number, title, author: .user.login}')

# Fetch and process issue comments (general comments)
ISSUE_COMMENTS=$(gh api "repos/$OWNER/$REPO/issues/$PR_NUMBER/comments" --jq --arg max "$MAX_BODY" '
  [.[] | {
    ref_id: ("issue_comment:" + (.id | tostring)),
    type: "issue_comment",
    author: .user.login,
    is_bot: (.user.login | test("'"$BOT_PATTERN"'"; "i")),
    body: (if ($max | tonumber) > 0 and (.body | length) > ($max | tonumber)
           then (.body[:($max | tonumber)] + "... [truncated]")
           else .body end)
  }]
')

# Fetch and process review comments (inline comments)
REVIEW_COMMENTS=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" --jq --arg max "$MAX_BODY" '
  [.[] | {
    ref_id: ("review_comment:" + (.id | tostring)),
    type: "review_comment",
    author: .user.login,
    is_bot: (.user.login | test("'"$BOT_PATTERN"'"; "i")),
    body: (if ($max | tonumber) > 0 and (.body | length) > ($max | tonumber)
           then (.body[:($max | tonumber)] + "... [truncated]")
           else .body end),
    file: .path,
    line: (.line // .original_line)
  }]
')

# Fetch and process reviews
REVIEWS=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews" --jq --arg max "$MAX_BODY" '
  [.[] | select(.body != "" or .state == "APPROVED" or .state == "CHANGES_REQUESTED") | {
    ref_id: ("review:" + (.id | tostring)),
    type: "review",
    author: .user.login,
    is_bot: (.user.login | test("'"$BOT_PATTERN"'"; "i")),
    body: (if ($max | tonumber) > 0 and (.body | length) > ($max | tonumber)
           then (.body[:($max | tonumber)] + "... [truncated]")
           else .body end),
    state: .state
  }]
')

# Combine and filter
if [ "$INCLUDE_HUMANS" = "true" ]; then
  FILTER='.'
else
  FILTER='[.[] | select(.is_bot == true)]'
fi

# Merge all comments and compute stats
jq -n --argjson pr "$PR_INFO" \
      --argjson issue "$ISSUE_COMMENTS" \
      --argjson review "$REVIEW_COMMENTS" \
      --argjson reviews "$REVIEWS" \
      --arg filter "$FILTER" '
{
  pr: $pr,
  comments: (($issue + $review + $reviews) | '"$FILTER"')
} | {
  pr: .pr,
  stats: {
    total: (.comments | length),
    bots: ([.comments[] | select(.is_bot)] | length),
    humans: ([.comments[] | select(.is_bot | not)] | length),
    by_type: {
      issue: ([.comments[] | select(.type == "issue_comment")] | length),
      inline: ([.comments[] | select(.type == "review_comment")] | length),
      review: ([.comments[] | select(.type == "review")] | length)
    }
  },
  comments: .comments
}'
