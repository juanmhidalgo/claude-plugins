#!/bin/bash
# pr-watch.sh - Wait for a PR's CI checks and (optionally) Copilot's review, then report
# Usage: ./pr-watch.sh pr_number [--copilot] [--timeout SECONDS] [--interval SECONDS]
#
# Options:
#   --copilot         Also wait for a Copilot review on the PR's current head commit
#   --timeout N       Give up after N seconds (default 1800)
#   --interval N      Poll every N seconds (default 30)
#   --no-checks-grace N  Seconds without any check before CI counts as "none" (default 180)
#
# Prints one line per event while waiting, then a final block:
#   CI: pass | fail | none | pending
#   FAILED: <check name> <link>          (one per failed or cancelled check)
#   COPILOT: <N> inline comments | not-waited | pending
#   COPILOT_REVIEW: <review url>         (when Copilot reviewed)
#
# Exit codes: 0 finished, 1 usage or gh error, 3 timed out (final block still printed)
#
# Example: ./pr-watch.sh 42 --copilot --timeout 2400

set -euo pipefail

PR_NUMBER=""
WAIT_COPILOT="false"
TIMEOUT="1800"
INTERVAL="30"
NO_CHECKS_GRACE="180"

while [[ $# -gt 0 ]]; do
  case $1 in
    --copilot) WAIT_COPILOT="true"; shift ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    --interval) INTERVAL="$2"; shift 2 ;;
    --no-checks-grace) NO_CHECKS_GRACE="$2"; shift 2 ;;
    *)
      if [ -z "$PR_NUMBER" ]; then PR_NUMBER="$1"; fi
      shift ;;
  esac
done

if [ -z "$PR_NUMBER" ]; then
  echo "Usage: $0 pr_number [--copilot] [--timeout N] [--interval N] [--no-checks-grace N]" >&2
  exit 1
fi

REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner) || { echo "gh: cannot resolve repository" >&2; exit 1; }
HEAD_SHA=$(gh pr view "$PR_NUMBER" --json headRefOid -q .headRefOid) || { echo "gh: cannot read PR #$PR_NUMBER" >&2; exit 1; }

echo "Watching $REPO#$PR_NUMBER at ${HEAD_SHA:0:7} (copilot: $WAIT_COPILOT, timeout: ${TIMEOUT}s)"

START=$(date +%s)
CI_STATE="pending"
COPILOT_STATE="pending"
[ "$WAIT_COPILOT" = "true" ] || COPILOT_STATE="not-waited"
COPILOT_COMMENTS=""
COPILOT_URL=""
CHECKS_JSON="[]"
PREV_DONE=""

while true; do
  NOW=$(date +%s)
  ELAPSED=$((NOW - START))

  if [ "$CI_STATE" = "pending" ]; then
    # `gh pr checks` exits 8 while checks are pending and errors when none exist yet
    CHECKS_JSON=$(gh pr checks "$PR_NUMBER" --json name,bucket,link 2>/dev/null) || true
    [ -n "$CHECKS_JSON" ] || CHECKS_JSON="[]"

    DONE=$(jq -r '.[] | select(.bucket != "pending") | "CI \(.name): \(.bucket)"' <<<"$CHECKS_JSON" | sort)
    comm -13 <(echo "$PREV_DONE") <(echo "$DONE") | sed '/^$/d'
    PREV_DONE=$DONE

    TOTAL=$(jq 'length' <<<"$CHECKS_JSON")
    if [ "$TOTAL" -eq 0 ]; then
      [ "$ELAPSED" -lt "$NO_CHECKS_GRACE" ] || CI_STATE="none"
    elif jq -e 'all(.bucket != "pending")' <<<"$CHECKS_JSON" >/dev/null; then
      if jq -e 'any(.bucket == "fail" or .bucket == "cancel")' <<<"$CHECKS_JSON" >/dev/null; then
        CI_STATE="fail"
      else
        CI_STATE="pass"
      fi
      echo "CI finished: $CI_STATE"
    fi
  fi

  if [ "$COPILOT_STATE" = "pending" ]; then
    # Only a review of the current head counts: an older one predates this push
    REVIEW=$(gh api "repos/$REPO/pulls/$PR_NUMBER/reviews" --paginate \
      --jq "[.[] | select((.user.login | test(\"copilot\"; \"i\")) and .commit_id == \"$HEAD_SHA\")] | last // empty | \"\(.id) \(.html_url)\"" 2>/dev/null) || true
    if [ -n "$REVIEW" ]; then
      REVIEW_ID=${REVIEW%% *}
      COPILOT_URL=${REVIEW#* }
      COPILOT_COMMENTS=$(gh api "repos/$REPO/pulls/$PR_NUMBER/reviews/$REVIEW_ID/comments" --paginate --jq 'length' 2>/dev/null | awk '{s+=$1} END {print s+0}')
      COPILOT_STATE="reviewed"
      echo "Copilot reviewed: $COPILOT_COMMENTS inline comments"
    fi
  fi

  if [ "$CI_STATE" != "pending" ] && [ "$COPILOT_STATE" != "pending" ]; then
    TIMED_OUT="false"
    break
  fi
  if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
    TIMED_OUT="true"
    break
  fi
  sleep "$INTERVAL"
done

echo "---"
echo "CI: $CI_STATE"
jq -r '.[] | select(.bucket == "fail" or .bucket == "cancel") | "FAILED: \(.name) \(.link)"' <<<"$CHECKS_JSON"
if [ "$COPILOT_STATE" = "reviewed" ]; then
  echo "COPILOT: $COPILOT_COMMENTS inline comments"
  echo "COPILOT_REVIEW: $COPILOT_URL"
else
  echo "COPILOT: $COPILOT_STATE"
fi

[ "$TIMED_OUT" = "false" ] || exit 3
