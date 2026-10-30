#!/bin/bash
# pr-triage-comments.sh - Token-optimized PR comments for AI review triage
# Usage: ./pr-triage-comments.sh owner repo pr_number [options]
#
# Options:
#   max_body_length   Truncate comment bodies (default: 1500, 0=unlimited)
#   bots_only         Only show bot comments (default: false, shows all)
#   show_resolved     Include resolved threads (default: false)
#
# Example: ./pr-triage-comments.sh facebook react 123
#          ./pr-triage-comments.sh facebook react 123 1500 true false
#          ./pr-triage-comments.sh facebook react 123 0 false true

set -euo pipefail

OWNER="${1:?Usage: $0 owner repo pr_number [max_body_length] [bots_only] [show_resolved]}"
REPO="${2:?Usage: $0 owner repo pr_number [max_body_length] [bots_only] [show_resolved]}"
PR_NUMBER="${3:?Usage: $0 owner repo pr_number [max_body_length] [bots_only] [show_resolved]}"
MAX_BODY="${4:-1500}"
BOTS_ONLY="${5:-false}"
SHOW_RESOLVED="${6:-false}"

# A comment is a bot's when GitHub says so (`user.type == "Bot"`: Copilot, every
# `<app>[bot]`) or its login is a known bot account. Matching a bare "bot"
# substring would also take humans such as "abbott" or "robotlover".
BOT_PATTERN='\[bot\]$|^(copilot|gemini-code-assist|coderabbitai|claude|chatgpt-codex-connector|sourcery-ai|dependabot|renovate|greenkeeper|codecov|sonarcloud|github-actions)$'

# GraphQL query for review thread resolution, paged: a PR past 100 threads (or a
# thread past 100 comments) would otherwise lose its resolution status silently.
GRAPHQL_QUERY='
query($owner: String!, $repo: String!, $pr: Int!, $after: String) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          isOutdated
          comments(first: 100) {
            totalCount
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

# Maps every comment databaseId in a thread (the first one and its replies) to
# the thread's {thread_id, resolved, outdated, thread_comments}. thread_comments
# is what triage saw: pr-resolve-comment.sh --seen compares it right before
# replying, so a thread that moved meanwhile is not answered twice.
RESOLUTION_MAP='{}'
AFTER=()
while :; do
  PAGE=$(gh api graphql \
    -f query="$GRAPHQL_QUERY" \
    -F owner="$OWNER" \
    -F repo="$REPO" \
    -F pr="$PR_NUMBER" \
    ${AFTER[@]+"${AFTER[@]}"}) || {
    echo '{"status":"error","error":"Could not read review threads (GraphQL)"}' >&2
    exit 3
  }
  RESOLUTION_MAP=$(jq -n --argjson acc "$RESOLUTION_MAP" --argjson page "$PAGE" '
    $acc + ([$page.data.repository.pullRequest.reviewThreads.nodes[] |
      . as $t | $t.comments.nodes[] |
      {(.databaseId | tostring): {
        thread_id: $t.id,
        resolved: $t.isResolved,
        outdated: $t.isOutdated,
        thread_comments: $t.comments.totalCount
      }}
    ] | add // {})
  ')
  [ "$(echo "$PAGE" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage')" = "true" ] || break
  AFTER=(-f after="$(echo "$PAGE" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.endCursor')")
done

# REST lists, every page: --paginate prints one array per page, jq -s joins them.
rest_list() {
  gh api --paginate "$1" | jq -s 'add // []'
}

# Fetch PR info
PR_INFO=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER" --jq '{number, title, author: .user.login}')

# Fetch and process issue comments (general comments)
ISSUE_COMMENTS=$(rest_list "repos/$OWNER/$REPO/issues/$PR_NUMBER/comments?per_page=100" | jq --arg max "$MAX_BODY" --arg bots "$BOT_PATTERN" '
  [.[] | {
    ref_id: ("issue_comment:" + (.id | tostring)),
    type: "issue_comment",
    author: .user.login,
    is_bot: (.user.type == "Bot" or (.user.login | test($bots; "i"))),
    body: (if ($max | tonumber) > 0 and (.body | length) > ($max | tonumber)
           then (.body[:($max | tonumber)] + "... [truncated]")
           else .body end)
  }]
')

# Fetch and process review comments (inline comments) - include id for resolution lookup
REVIEW_COMMENTS_RAW=$(rest_list "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments?per_page=100" | jq --arg max "$MAX_BODY" --arg bots "$BOT_PATTERN" '
  [.[] | {
    ref_id: ("review_comment:" + (.id | tostring)),
    comment_id: (.id | tostring),
    type: "review_comment",
    author: .user.login,
    is_bot: (.user.type == "Bot" or (.user.login | test($bots; "i"))),
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
    outdated: ($res[.comment_id].outdated // false),
    thread_id: ($res[.comment_id].thread_id // null),
    thread_comments: ($res[.comment_id].thread_comments // null)
  } | del(.comment_id)]
')

# Fetch and process reviews
REVIEWS=$(rest_list "repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews?per_page=100" | jq --arg max "$MAX_BODY" --arg bots "$BOT_PATTERN" '
  [.[] | select(.body != "" or .state == "APPROVED" or .state == "CHANGES_REQUESTED") | {
    ref_id: ("review:" + (.id | tostring)),
    type: "review",
    author: .user.login,
    is_bot: (.user.type == "Bot" or (.user.login | test($bots; "i"))),
    body: (if ($max | tonumber) > 0 and (.body | length) > ($max | tonumber)
           then (.body[:($max | tonumber)] + "... [truncated]")
           else .body end),
    state: .state
  }]
')

# Build filters based on options
BOT_FILTER='.'
RESOLVED_FILTER='.'

if [ "$BOTS_ONLY" = "true" ]; then
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
