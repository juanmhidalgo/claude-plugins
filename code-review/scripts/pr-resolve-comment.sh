#!/bin/bash
# pr-resolve-comment.sh - Mark comment as resolved/dismissed
# Usage: ./pr-resolve-comment.sh [--seen N] owner repo pr_number ref_id action [reason]
#
# Actions:
#   resolve  - Mark review thread as resolved (review_comment only)
#   dismiss  - Add dismissal reply with reason and resolve thread
#   react    - Add eyes reaction to acknowledge
#
# --seen N: the thread's comment count when triage read it (`thread_comments`
# from pr-triage-comments.sh). Triage takes minutes and the PR does not stand
# still: the author, or another session, may answer the same thread meanwhile.
# The thread is read again right before acting, and one that now has a
# different count is skipped (exit 6) instead of answered twice. A dismiss
# also skips a thread that someone resolved meanwhile.
#
# Exit codes: 0 done · 1 error, nothing posted · 5 reply posted but the thread
#             was not resolved · 6 thread changed since triage, nothing posted
#
# Example: ./pr-resolve-comment.sh facebook react 123 review_comment:456789 resolve
#          ./pr-resolve-comment.sh --seen 1 facebook react 123 review_comment:456789 dismiss "False positive: handled in middleware"

set -euo pipefail

SEEN=""
if [ "${1:-}" = "--seen" ]; then
  SEEN="${2:?--seen needs a number}"
  shift 2
fi

OWNER="${1:?Usage: $0 [--seen N] owner repo pr_number ref_id action [reason]}"
REPO="${2:?Usage: $0 [--seen N] owner repo pr_number ref_id action [reason]}"
PR_NUMBER="${3:?Usage: $0 [--seen N] owner repo pr_number ref_id action [reason]}"
REF_ID="${4:?Usage: $0 [--seen N] owner repo pr_number ref_id action [reason]}"
ACTION="${5:?Usage: $0 [--seen N] owner repo pr_number ref_id action [reason]}"
REASON="${6:-}"

# Parse ref_id (format: type:id)
COMMENT_TYPE="${REF_ID%%:*}"
COMMENT_ID="${REF_ID#*:}"

if [ "$COMMENT_TYPE" = "$REF_ID" ]; then
  echo '{"status":"error","error":"Invalid ref_id format. Expected type:id"}' >&2
  exit 1
fi

# Prints a JSON status line; extra key/value pairs are added as strings.
report() {
  local status="$1" stream="$2"
  shift 2
  local out
  out=$(jq -cn --arg status "$status" --arg ref_id "$REF_ID" '{status: $status, ref_id: $ref_id}')
  while [ $# -ge 2 ]; do
    out=$(jq -c --arg k "$1" --arg v "$2" '. + {($k): $v}' <<<"$out")
    shift 2
  done
  if [ "$stream" = "err" ]; then echo "$out" >&2; else echo "$out"; fi
}

# Finds the thread holding a review comment, paging through every thread.
# Prints {id, isResolved, count} as one JSON line, or nothing when not found.
find_thread() {
  local comment_id="$1" page found
  local after=()
  while :; do
    page=$(gh api graphql -f query='
      query($owner: String!, $repo: String!, $pr: Int!, $after: String) {
        repository(owner: $owner, name: $repo) {
          pullRequest(number: $pr) {
            reviewThreads(first: 100, after: $after) {
              pageInfo { hasNextPage endCursor }
              nodes {
                id
                isResolved
                comments(first: 1) {
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
    ' -f owner="$OWNER" -f repo="$REPO" -F pr="$PR_NUMBER" ${after[@]+"${after[@]}"}) || return 1
    found=$(jq -c --argjson cid "$comment_id" '
      [.data.repository.pullRequest.reviewThreads.nodes[] |
        select(.comments.nodes[0].databaseId == $cid) |
        {id, isResolved, count: .comments.totalCount}][0] // empty
    ' <<<"$page")
    if [ -n "$found" ]; then
      echo "$found"
      return 0
    fi
    [ "$(jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage' <<<"$page")" = "true" ] || return 0
    after=(-f after="$(jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.endCursor' <<<"$page")")
  done
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
  ' -f threadId="$thread_id" --jq '.data.resolveReviewThread.thread.isResolved' 2>/dev/null || true
}

# Looks the thread up and stops (exit 6) when it moved since triage read it.
# Sets THREAD_ID and THREAD_RESOLVED.
load_thread() {
  local thread count
  thread=$(find_thread "$COMMENT_ID") || {
    report error err error "Could not read review threads"
    exit 1
  }
  if [ -z "$thread" ]; then
    report error err error "Could not find thread for comment"
    exit 1
  fi
  THREAD_ID=$(jq -r '.id' <<<"$thread")
  THREAD_RESOLVED=$(jq -r '.isResolved' <<<"$thread")
  count=$(jq -r '.count' <<<"$thread")
  if [ -n "$SEEN" ] && [ "$count" != "$SEEN" ]; then
    report changed out thread_id "$THREAD_ID" reason "thread has $count comments, triage saw $SEEN"
    exit 6
  fi
}

case "$ACTION" in
  resolve)
    if [ "$COMMENT_TYPE" != "review_comment" ]; then
      echo '{"status":"error","error":"Only review_comment type can be resolved"}' >&2
      exit 1
    fi

    load_thread
    if [ "$THREAD_RESOLVED" = "true" ]; then
      report already_resolved out thread_id "$THREAD_ID"
      exit 0
    fi

    RESOLVED=$(resolve_thread "$THREAD_ID")
    if [ "$RESOLVED" = "true" ]; then
      report resolved out thread_id "$THREAD_ID"
    else
      report error err thread_id "$THREAD_ID" error "Failed to resolve thread"
      exit 1
    fi
    ;;

  dismiss)
    DISMISS_BODY="**Dismissed** - This feedback has been reviewed and dismissed."
    if [ -n "$REASON" ]; then
      DISMISS_BODY="$DISMISS_BODY

**Reason:** $REASON"
    fi

    if [ "$COMMENT_TYPE" = "review_comment" ]; then
      # Check the thread before posting: a reply cannot be taken back.
      load_thread
      if [ "$THREAD_RESOLVED" = "true" ]; then
        report changed out thread_id "$THREAD_ID" reason "thread was resolved since triage"
        exit 6
      fi

      gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" \
        -f body="$DISMISS_BODY" \
        -F in_reply_to="$COMMENT_ID" > /dev/null || {
        report error err thread_id "$THREAD_ID" error "Failed to post the reply; nothing was posted"
        exit 1
      }

      RESOLVED=$(resolve_thread "$THREAD_ID")
      if [ "$RESOLVED" != "true" ]; then
        report replied_not_resolved err thread_id "$THREAD_ID" reason "$REASON" \
          error "Reply posted, but resolving the thread failed"
        exit 5
      fi
      report dismissed out thread_id "$THREAD_ID" reason "$REASON"
    else
      # For issue_comments, add a regular reply
      gh api "repos/$OWNER/$REPO/issues/$PR_NUMBER/comments" \
        -f body="Re: comment #$COMMENT_ID

$DISMISS_BODY" > /dev/null || {
        report error err error "Failed to post the reply; nothing was posted"
        exit 1
      }
      report dismissed out reason "$REASON"
    fi
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
