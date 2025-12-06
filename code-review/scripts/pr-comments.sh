#!/bin/bash
# pr-comments.sh - Fetch all PR feedback (comments, reviews, inline comments)
# Usage: ./pr-comments.sh owner repo pr_number [options]
#
# Options:
#   --minimal         Compact output, no timestamps/urls
#   --max-body N      Truncate bodies to N chars (0=unlimited)
#   --bots-only       Only bot comments
#   --humans-only     Only human comments
#
# Example: ./pr-comments.sh facebook react 123 --minimal --bots-only

set -euo pipefail

# Parse arguments
OWNER=""
REPO=""
PR_NUMBER=""
MINIMAL="false"
MAX_BODY="0"
BOTS_ONLY="false"
HUMANS_ONLY="false"

while [[ $# -gt 0 ]]; do
  case $1 in
    --minimal) MINIMAL="true"; shift ;;
    --max-body) MAX_BODY="$2"; shift 2 ;;
    --bots-only) BOTS_ONLY="true"; shift ;;
    --humans-only) HUMANS_ONLY="true"; shift ;;
    *)
      if [ -z "$OWNER" ]; then OWNER="$1"
      elif [ -z "$REPO" ]; then REPO="$1"
      elif [ -z "$PR_NUMBER" ]; then PR_NUMBER="$1"
      fi
      shift ;;
  esac
done

if [ -z "$OWNER" ] || [ -z "$REPO" ] || [ -z "$PR_NUMBER" ]; then
  echo "Usage: $0 owner repo pr_number [--minimal] [--max-body N] [--bots-only] [--humans-only]" >&2
  exit 1
fi

BOT_PATTERN="bot|copilot|gemini|claude|gpt|dependabot|renovate|greenkeeper|codecov|sonarcloud|github-actions"

# Build jq filter for body truncation
if [ "$MAX_BODY" != "0" ]; then
  BODY_FILTER='if (.body | length) > '"$MAX_BODY"' then (.body[:'"$MAX_BODY"'] + "... [truncated]") else .body end'
else
  BODY_FILTER='.body'
fi

# Fetch PR info
if [ "$MINIMAL" = "true" ]; then
  PR_INFO=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER" --jq '{number, title, state, author: .user.login}')
else
  PR_INFO=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER" --jq '{number, title, state, author: .user.login, url: .html_url, created_at, updated_at}')
fi

# Build comment jq template based on minimal flag
if [ "$MINIMAL" = "true" ]; then
  ISSUE_JQ='[.[] | {
    ref_id: ("issue_comment:" + (.id | tostring)),
    type: "issue_comment",
    author: .user.login,
    is_bot: (.user.login | test("'"$BOT_PATTERN"'"; "i")),
    body: ('"$BODY_FILTER"')
  }]'

  REVIEW_JQ='[.[] | {
    ref_id: ("review_comment:" + (.id | tostring)),
    type: "review_comment",
    author: .user.login,
    is_bot: (.user.login | test("'"$BOT_PATTERN"'"; "i")),
    body: ('"$BODY_FILTER"'),
    file: .path,
    line: (.line // .original_line)
  }]'

  REVIEWS_JQ='[.[] | select(.body != "" or .state == "APPROVED" or .state == "CHANGES_REQUESTED") | {
    ref_id: ("review:" + (.id | tostring)),
    type: "review",
    author: .user.login,
    is_bot: (.user.login | test("'"$BOT_PATTERN"'"; "i")),
    body: ('"$BODY_FILTER"'),
    state: .state
  }]'
else
  ISSUE_JQ='[.[] | {
    ref_id: ("issue_comment:" + (.id | tostring)),
    id: (.id | tostring),
    type: "issue_comment",
    author: .user.login,
    is_bot: (.user.login | test("'"$BOT_PATTERN"'"; "i")),
    body: ('"$BODY_FILTER"'),
    created_at,
    updated_at,
    url: .html_url
  }]'

  REVIEW_JQ='[.[] | {
    ref_id: ("review_comment:" + (.id | tostring)),
    id: (.id | tostring),
    type: "review_comment",
    author: .user.login,
    is_bot: (.user.login | test("'"$BOT_PATTERN"'"; "i")),
    body: ('"$BODY_FILTER"'),
    file: .path,
    line: (.line // .original_line),
    diff_hunk,
    in_reply_to_id,
    created_at,
    updated_at,
    url: .html_url
  }]'

  REVIEWS_JQ='[.[] | select(.body != "" or .state == "APPROVED" or .state == "CHANGES_REQUESTED") | {
    ref_id: ("review:" + (.id | tostring)),
    id: (.id | tostring),
    type: "review",
    author: .user.login,
    is_bot: (.user.login | test("'"$BOT_PATTERN"'"; "i")),
    body: ('"$BODY_FILTER"'),
    state: .state,
    created_at,
    url: .html_url
  }]'
fi

# Fetch all comments
ISSUE_COMMENTS=$(gh api "repos/$OWNER/$REPO/issues/$PR_NUMBER/comments" --jq "$ISSUE_JQ")
REVIEW_COMMENTS=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" --jq "$REVIEW_JQ")
REVIEWS=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews" --jq "$REVIEWS_JQ")

# Build filter for bots/humans
if [ "$BOTS_ONLY" = "true" ]; then
  USER_FILTER='[.[] | select(.is_bot == true)]'
elif [ "$HUMANS_ONLY" = "true" ]; then
  USER_FILTER='[.[] | select(.is_bot == false)]'
else
  USER_FILTER='.'
fi

# Combine and output
jq -n --argjson pr "$PR_INFO" \
      --argjson issue "$ISSUE_COMMENTS" \
      --argjson review "$REVIEW_COMMENTS" \
      --argjson reviews "$REVIEWS" '
{
  pr: $pr,
  comments: (($issue + $review + $reviews) | '"$USER_FILTER"')
} | {
  pr: .pr,
  stats: {
    total_comments: (.comments | length),
    issue_comments: ([.comments[] | select(.type == "issue_comment")] | length),
    review_comments: ([.comments[] | select(.type == "review_comment")] | length),
    reviews: ([.comments[] | select(.type == "review")] | length),
    bot_comments: ([.comments[] | select(.is_bot)] | length),
    human_comments: ([.comments[] | select(.is_bot | not)] | length),
    approved_reviews: ([.comments[] | select(.state == "APPROVED")] | length),
    changes_requested: ([.comments[] | select(.state == "CHANGES_REQUESTED")] | length)
  },
  comments: .comments
}' $([ "$MINIMAL" = "true" ] && echo "-c" || echo "")
