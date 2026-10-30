#!/usr/bin/env bash
# Tests for pr-triage-comments.sh and pr-resolve-comment.sh against a fake `gh`.
#
# The fake answers from fixtures written per case and logs every call, so a
# case can assert both on the output and on what would have reached GitHub.
# Review threads come in two GraphQL pages and REST lists in two pages, to
# prove nothing past the first 100 is lost.
#
# Usage: bash code-review/tests/test-pr-scripts.sh

set -uo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
scripts="$here/../scripts"
pass=0
fail=0

check() {
  local name="$1" cond="$2"
  if eval "$cond"; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
    echo "FAIL: $name  ($cond)"
  fi
}

setup() {
  work=$(mktemp -d)
  mkdir -p "$work/bin"
  cat >"$work/bin/gh" <<'SH'
#!/usr/bin/env bash
# Fake gh: answers from $FAKE/*.json and logs each call to $FAKE/log.
echo "$*" >>"$FAKE/log"
args="$*"
case "$args" in
  *resolveReviewThread*) cat "$FAKE/resolve.out" ;;
  *reviewThreads*after=CUR1*) cat "$FAKE/threads-2.json" ;;
  *reviewThreads*) cat "$FAKE/threads-1.json" ;;
  *"--paginate"*issues/*/comments*) cat "$FAKE/issue-comments.json" ;;
  *"--paginate"*pulls/*/comments*) cat "$FAKE/review-comments.json" ;;
  *"--paginate"*reviews*) cat "$FAKE/reviews.json" ;;
  *"-f body="*) exit "$(cat "$FAKE/post.rc" 2>/dev/null || echo 0)" ;;
  *"api repos/"*"/pulls/"*) echo '{"number":7,"title":"t","author":"owner"}' ;;
  *) echo "fake gh: unexpected: $args" >&2; exit 99 ;;
esac
SH
  chmod +x "$work/bin/gh"
  export FAKE="$work" PATH="$work/bin:$PATH"
  : >"$work/log"
  echo true >"$work/resolve.out"

  # Page 1: thread T1 (comment 101, open, 1 comment). Page 2: thread T2
  # (comment 201 plus reply 202, resolved) and T3 (comment 301, open, 2 comments).
  cat >"$work/threads-1.json" <<'JSON'
{"data":{"repository":{"pullRequest":{"reviewThreads":{
  "pageInfo":{"hasNextPage":true,"endCursor":"CUR1"},
  "nodes":[{"id":"T1","isResolved":false,"isOutdated":false,
            "comments":{"totalCount":1,"nodes":[{"databaseId":101}]}}]}}}}}
JSON
  cat >"$work/threads-2.json" <<'JSON'
{"data":{"repository":{"pullRequest":{"reviewThreads":{
  "pageInfo":{"hasNextPage":false,"endCursor":null},
  "nodes":[{"id":"T2","isResolved":true,"isOutdated":false,
            "comments":{"totalCount":2,"nodes":[{"databaseId":201},{"databaseId":202}]}},
           {"id":"T3","isResolved":false,"isOutdated":true,
            "comments":{"totalCount":2,"nodes":[{"databaseId":301}]}}]}}}}}
JSON
  # Two REST pages, as gh --paginate prints them: two arrays back to back.
  cat >"$work/review-comments.json" <<'JSON'
[{"id":101,"user":{"login":"Copilot","type":"Bot"},"body":"a","path":"x.py","line":1}]
[{"id":201,"user":{"login":"abbott","type":"User"},"body":"b","path":"x.py","line":2},
 {"id":202,"user":{"login":"owner","type":"User"},"body":"c","path":"x.py","line":2},
 {"id":301,"user":{"login":"gemini-code-assist[bot]","type":"Bot"},"body":"d","path":"y.py","line":null,"original_line":9}]
JSON
  echo '[]' >"$work/issue-comments.json"
  echo '[]' >"$work/reviews.json"
}

# --- pr-triage-comments.sh ---------------------------------------------------
setup
out=$("$scripts/pr-triage-comments.sh" o r 7 0 false false)
ids=$(jq -r '[.comments[].ref_id] | join(",")' <<<"$out")
check "paged threads: resolved thread on page 2 and its reply are filtered" \
  '[ "$ids" = "review_comment:101,review_comment:301" ]'
check "thread on page 2 keeps its outdated flag" \
  '[ "$(jq -r ".comments[1].outdated" <<<"$out")" = "true" ]'
check "thread_comments is carried for --seen" \
  '[ "$(jq -r ".comments[1].thread_comments" <<<"$out")" = "2" ]'
check "Copilot (type Bot) is a bot" \
  '[ "$(jq -r ".comments[0].is_bot" <<<"$out")" = "true" ]'
all=$("$scripts/pr-triage-comments.sh" o r 7 0 false true)
check "show_resolved keeps all four comments across both REST pages" \
  '[ "$(jq ".comments | length" <<<"$all")" = "4" ]'
check "a human named abbott is not a bot" \
  '[ "$(jq -r ".comments[] | select(.author == \"abbott\") | .is_bot" <<<"$all")" = "false" ]'

sed -i.bak 's|\*reviewThreads\*) cat "$FAKE/threads-1.json" ;;|*reviewThreads*) exit 1 ;;|' "$work/bin/gh"
"$scripts/pr-triage-comments.sh" o r 7 >/dev/null 2>&1
rc=$?
check "a failed thread read stops instead of treating every thread as open" '[ $rc -eq 3 ]'
rm -rf "$work"

# --- pr-resolve-comment.sh ---------------------------------------------------
setup
out=$("$scripts/pr-resolve-comment.sh" --seen 2 o r 7 review_comment:301 dismiss "YAGNI")
rc=$?
check "dismiss on a page-2 thread with matching --seen succeeds" '[ $rc -eq 0 ]'
check "dismiss reports the thread id" '[ "$(jq -r .thread_id <<<"$out")" = "T3" ]'
check "dismiss posted the reply" 'grep -q "in_reply_to=301" "$FAKE/log"'
rm -rf "$work"

setup
out=$("$scripts/pr-resolve-comment.sh" --seen 1 o r 7 review_comment:301 dismiss "YAGNI")
rc=$?
check "thread that grew since triage is skipped with exit 6" '[ $rc -eq 6 ]'
check "skipped thread reports status changed" '[ "$(jq -r .status <<<"$out")" = "changed" ]'
check "nothing posted to a changed thread" '! grep -q "body=" "$FAKE/log"'
rm -rf "$work"

setup
"$scripts/pr-resolve-comment.sh" o r 7 review_comment:201 dismiss "YAGNI" >/dev/null
rc=$?
check "dismiss on a thread resolved meanwhile is skipped with exit 6" '[ $rc -eq 6 ]'
check "nothing posted to a resolved thread" '! grep -q "body=" "$FAKE/log"'
rm -rf "$work"

setup
echo false >"$work/resolve.out"
err=$("$scripts/pr-resolve-comment.sh" o r 7 review_comment:101 dismiss "YAGNI" 2>&1 >/dev/null)
rc=$?
check "reply posted but resolve failed exits 5" '[ $rc -eq 5 ]'
check "and says replied_not_resolved" '[ "$(jq -r .status <<<"$err")" = "replied_not_resolved" ]'
rm -rf "$work"

setup
echo 1 >"$work/post.rc"
"$scripts/pr-resolve-comment.sh" o r 7 review_comment:101 dismiss "YAGNI" >/dev/null 2>&1
rc=$?
check "a failed reply exits 1 and never resolves" '[ $rc -eq 1 ] && ! grep -q resolveReviewThread "$FAKE/log"'
rm -rf "$work"

setup
out=$("$scripts/pr-resolve-comment.sh" o r 7 review_comment:201 resolve)
rc=$?
check "resolve on an already-resolved thread is a no-op success" \
  '[ $rc -eq 0 ] && [ "$(jq -r .status <<<"$out")" = "already_resolved" ]'
rm -rf "$work"

echo "pass: $pass  fail: $fail"
[ "$fail" -eq 0 ]
