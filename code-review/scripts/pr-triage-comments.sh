#!/bin/bash
# pr-triage-comments.sh - Token-optimized PR comments for AI review triage
# Usage: ./pr-triage-comments.sh owner repo pr_number [options]
#
# Options:
#   max_body_length   Truncate comment bodies (default: 1500, 0=unlimited)
#   include_humans    Include human comments (default: false, bots only)
#   show_resolved     Include resolved threads (default: false)
#
# Example: ./pr-triage-comments.sh facebook react 123
#          ./pr-triage-comments.sh facebook react 123 1500 true false
#          ./pr-triage-comments.sh facebook react 123 0 true true

set -euo pipefail

OWNER="${1:?Usage: $0 owner repo pr_number [max_body_length] [include_humans] [show_resolved]}"
REPO="${2:?Usage: $0 owner repo pr_number [max_body_length] [include_humans] [show_resolved]}"
PR_NUMBER="${3:?Usage: $0 owner repo pr_number [max_body_length] [include_humans] [show_resolved]}"
MAX_BODY="${4:-1500}"
INCLUDE_HUMANS="${5:-false}"
SHOW_RESOLVED="${6:-false}"

# Bot patterns for filtering
BOT_PATTERN="bot|copilot|gemini|claude|gpt|dependabot|renovate|greenkeeper|codecov|sonarcloud|github-actions"

# GraphQL query to get review thread resolution status
GRAPHQL_QUERY='
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100) {
        nodes {
          isResolved
          isOutdated
          comments(first: 1) {
            nodes {
              databaseId
            }
          }
        }
      }
    }
  }
}
'

# Fetch resolution status via GraphQL (maps comment databaseId -> {resolved, outdated})
RESOLUTION_MAP=$(gh api graphql \
  -f query="$GRAPHQL_QUERY" \
  -F owner="$OWNER" \
  -F repo="$REPO" \
  -F pr="$PR_NUMBER" \
  --jq '
    [.data.repository.pullRequest.reviewThreads.nodes[] |
      select(.comments.nodes | length > 0) |
      {
        id: (.comments.nodes[0].databaseId | tostring),
        resolved: .isResolved,
        outdated: .isOutdated
      }
    ] | map({(.id): {resolved, outdated}}) | add // {}
  ' 2>/dev/null || echo '{}')

# Fetch PR info
PR_INFO=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER" --jq '{number, title, author: .user.login}')

# Fetch and process issue comments (general comments)
ISSUE_COMMENTS=$(gh api "repos/$OWNER/$REPO/issues/$PR_NUMBER/comments" | jq --arg max "$MAX_BODY" '
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

# Fetch and process review comments (inline comments) - include id for resolution lookup
REVIEW_COMMENTS_RAW=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" | jq --arg max "$MAX_BODY" '
  [.[] | {
    ref_id: ("review_comment:" + (.id | tostring)),
    comment_id: (.id | tostring),
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

# Enrich review comments with resolution status from GraphQL
REVIEW_COMMENTS=$(echo "$REVIEW_COMMENTS_RAW" | jq --argjson res "$RESOLUTION_MAP" '
  [.[] | . + {
    resolved: ($res[.comment_id].resolved // false),
    outdated: ($res[.comment_id].outdated // false)
  } | del(.comment_id)]
')

# Fetch and process reviews
REVIEWS=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews" | jq --arg max "$MAX_BODY" '
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

# Build filters based on options
BOT_FILTER='.'
RESOLVED_FILTER='.'

if [ "$INCLUDE_HUMANS" != "true" ]; then
  BOT_FILTER='[.[] | select(.is_bot == true)]'
fi

if [ "$SHOW_RESOLVED" != "true" ]; then
  RESOLVED_FILTER='[.[] | select(.resolved != true)]'
fi

# Merge all comments and compute stats
jq -n --argjson pr "$PR_INFO" \
      --argjson issue "$ISSUE_COMMENTS" \
      --argjson review "$REVIEW_COMMENTS" \
      --argjson reviews "$REVIEWS" '
{
  pr: $pr,
  all_comments: ($issue + $review + $reviews)
} | {
  pr: .pr,
  # Apply bot filter first
  comments: (.all_comments | '"$BOT_FILTER"')
} | {
  pr: .pr,
  # Count before resolution filter for stats
  total_before_filter: (.comments | length),
  resolved_count: ([.comments[] | select(.resolved == true)] | length),
  outdated_count: ([.comments[] | select(.outdated == true)] | length),
  # Apply resolution filter
  comments: (.comments | '"$RESOLVED_FILTER"')
} | {
  pr: .pr,
  stats: {
    total: (.comments | length),
    filtered_out: {
      resolved: .resolved_count,
      outdated: .outdated_count
    },
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
