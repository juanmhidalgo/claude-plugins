#!/bin/bash
# pr-triage-split.sh - Fetch PR comments and write one file per comment
# Usage: ./pr-triage-split.sh owner repo pr_number out_dir [max_body_length] [bots_only] [show_resolved]
#
# Writes <out_dir>/<ref_id>.json (":" in the ref_id becomes "_") for every
# comment pr-triage-comments.sh returns, and prints the PR, the stats and each
# comment's metadata without its body. The bodies are untrusted text: they go
# to the verifiers through the files and never pass through the caller.

set -euo pipefail

USAGE="Usage: $0 owner repo pr_number out_dir [max_body_length] [bots_only] [show_resolved]"
OWNER="${1:?$USAGE}"
REPO="${2:?$USAGE}"
PR_NUMBER="${3:?$USAGE}"
OUT_DIR="${4:?$USAGE}"

mkdir -p "$OUT_DIR"
ALL=$("$(dirname "$0")/pr-triage-comments.sh" "$OWNER" "$REPO" "$PR_NUMBER" "${5:-0}" "${6:-false}" "${7:-false}")

echo "$ALL" | jq -c '.comments[]' | while IFS= read -r comment; do
  ref=$(echo "$comment" | jq -r '.ref_id | gsub(":"; "_")')
  echo "$comment" > "$OUT_DIR/$ref.json"
done

echo "$ALL" | jq --arg dir "$OUT_DIR" '{
  pr, stats,
  comments: [.comments[] | {ref_id, type, author, is_bot, file, line,
             comment_file: ($dir + "/" + (.ref_id | gsub(":"; "_")) + ".json")}]
}'
