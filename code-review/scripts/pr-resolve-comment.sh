#!/bin/bash
# pr-resolve-comment.sh - Mark comment as resolved/dismissed
# Usage: ./pr-resolve-comment.sh owner repo pr_number ref_id action [reason]
#
# Actions:
#   resolve  - Mark review thread as resolved (review_comment only)
#   dismiss  - Add dismissal reply with reason and resolve thread
#   react    - Add eyes reaction to acknowledge
#
# Example: ./pr-resolve-comment.sh facebook react 123 review_comment:456789 resolve
#          ./pr-resolve-comment.sh facebook react 123 review_comment:456789 dismiss "False positive: handled in middleware"

set -euo pipefail

OWNER="${1:?Usage: $0 owner repo pr_number ref_id action [reason]}"
REPO="${2:?Usage: $0 owner repo pr_number ref_id action [reason]}"
PR_NUMBER="${3:?Usage: $0 owner repo pr_number ref_id action [reason]}"
REF_ID="${4:?Usage: $0 owner repo pr_number ref_id action [reason]}"
ACTION="${5:?Usage: $0 owner repo pr_number ref_id action [reason]}"
REASON="${6:-}"

# Parse ref_id (format: type:id)
COMMENT_TYPE="${REF_ID%%:*}"
COMMENT_ID="${REF_ID#*:}"

if [ "$COMMENT_TYPE" = "$REF_ID" ]; then
  echo '{"status":"error","error":"Invalid ref_id format. Expected type:id"}' >&2
  exit 1
fi

# Function to get thread ID for a review comment using GraphQL
get_thread_id() {
  local comment_id="$1"

  gh api graphql -f query='
    query($owner: String!, $repo: String!, $pr: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $pr) {
          reviewThreads(first: 100) {
            nodes {
              id
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
  ' -f owner="$OWNER" -f repo="$REPO" -F pr="$PR_NUMBER" --jq '
    .data.repository.pullRequest.reviewThreads.nodes[] |
    select(.comments.nodes[0].databaseId == '"$comment_id"') |
    .id
  ' 2>/dev/null | head -1
}

# Function to resolve a thread using GraphQL
resolve_thread() {
  local thread_id="$1"

  gh api graphql -f query='
    mutation($threadId: ID!) {
      resolveReviewThread(input: {threadId: $threadId}) {
        thread {
          isResolved
        }
      }
    }
  ' -f threadId="$thread_id" --jq '.data.resolveReviewThread.thread.isResolved' 2>/dev/null
}

case "$ACTION" in
  resolve)
    if [ "$COMMENT_TYPE" != "review_comment" ]; then
      echo '{"status":"error","error":"Only review_comment type can be resolved"}' >&2
      exit 1
    fi

    THREAD_ID=$(get_thread_id "$COMMENT_ID")
    if [ -z "$THREAD_ID" ]; then
      echo '{"status":"error","ref_id":"'"$REF_ID"'","error":"Could not find thread for comment"}' >&2
      exit 1
    fi

    RESOLVED=$(resolve_thread "$THREAD_ID")
    if [ "$RESOLVED" = "true" ]; then
      echo '{"status":"resolved","ref_id":"'"$REF_ID"'","thread_id":"'"$THREAD_ID"'"}'
    else
      echo '{"status":"error","ref_id":"'"$REF_ID"'","error":"Failed to resolve thread"}' >&2
      exit 1
    fi
    ;;

  dismiss)
    DISMISS_BODY="**Dismissed** - This feedback has been reviewed and dismissed."
    if [ -n "$REASON" ]; then
      DISMISS_BODY="$DISMISS_BODY

**Reason:** $REASON"
    fi

    THREAD_RESOLVED="false"

    if [ "$COMMENT_TYPE" = "review_comment" ]; then
      # Add reply to review comment
      gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" \
        -f body="$DISMISS_BODY" \
        -F in_reply_to="$COMMENT_ID" > /dev/null

      # Also resolve the thread
      THREAD_ID=$(get_thread_id "$COMMENT_ID")
      if [ -n "$THREAD_ID" ]; then
        RESOLVED=$(resolve_thread "$THREAD_ID")
        [ "$RESOLVED" = "true" ] && THREAD_RESOLVED="true"
      fi
    else
      # For issue_comments, add a regular reply
      gh api "repos/$OWNER/$REPO/issues/$PR_NUMBER/comments" \
        -f body="Re: comment #$COMMENT_ID

$DISMISS_BODY" > /dev/null
    fi

    echo '{"status":"dismissed","ref_id":"'"$REF_ID"'","reason":"'"${REASON//\"/\\\"}"'","thread_resolved":'"$THREAD_RESOLVED"'}'
    ;;

  react)
    if [ "$COMMENT_TYPE" = "review_comment" ]; then
      gh api "repos/$OWNER/$REPO/pulls/comments/$COMMENT_ID/reactions" -f content="eyes" > /dev/null
    elif [ "$COMMENT_TYPE" = "issue_comment" ]; then
      gh api "repos/$OWNER/$REPO/issues/comments/$COMMENT_ID/reactions" -f content="eyes" > /dev/null
    else
      echo '{"status":"error","error":"Cannot react to '"$COMMENT_TYPE"' type comments"}' >&2
      exit 1
    fi

    echo '{"status":"reacted","ref_id":"'"$REF_ID"'","reaction":"eyes"}'
    ;;

  *)
    echo '{"status":"error","error":"Unknown action: '"$ACTION"'. Use: resolve, dismiss, or react"}' >&2
    exit 1
    ;;
esac
