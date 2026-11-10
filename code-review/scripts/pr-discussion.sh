#!/usr/bin/env bash
# pr-discussion.sh — where a PR has already been discussed, without what was said.
# Step 5b of /code-review:pr: run after the review workflow returns, so comments
# posted while the reviewers worked are included.
#
#   pr-discussion.sh <PR number or URL>
#
# Runs `gh feedback fetch --split --include-resolved` into a temporary directory,
# prints its metadata and deletes the directory. The bodies are written by other
# people and bots, and stay out of the caller's context: the caller matches
# findings to comments by location, never by content.
#
# Prints one JSON line on stdout:
#
#   {"inline":[{"ref_id":"review_comment:1","author":"login","bot":false,
#               "file":"a.py","line":12,"thread_comments":2},...],
#    "general":[{"ref_id":"review:9","type":"review","author":"login","bot":false},...]}
#
# `inline` holds every inline comment with a file and a line, open, outdated or
# resolved. `general` holds PR comments and reviews, plus inline comments whose
# line no longer exists (outdated ones can come back without a line).
#
# Exit codes
#   0   printed
#   4   the gh-feedback extension or jq is not installed
#   7   gh failed (including gh-feedback's exit 3, threads unreadable), or bad usage

set -euo pipefail

die() { local code=$1; shift; printf '%s\n' "$*" >&2; exit "$code"; }

[ $# -eq 1 ] && [ "${1#-}" = "$1" ] || die 7 "usage: pr-discussion.sh <PR number or URL>"
pr=$1

# gh feedback takes a number, not a URL: a URL becomes -R owner/repo plus its number.
repo=()
if [[ $pr =~ ^https?://([^/]+)/([^/]+/[^/]+)/pull/([0-9]+)([/?#].*)?$ ]]; then
  host=${BASH_REMATCH[1]}
  repo=(-R "${BASH_REMATCH[2]}")
  [ "$host" = "github.com" ] || repo=(-R "$host/${BASH_REMATCH[2]}")
  pr=${BASH_REMATCH[3]}
elif ! [[ $pr =~ ^[0-9]+$ ]]; then
  die 7 "usage: pr-discussion.sh <PR number or URL>"
fi

command -v jq >/dev/null 2>&1 || die 4 "jq not found in PATH"
gh feedback --version >/dev/null 2>&1 || die 4 "the gh-feedback extension is not installed (gh extension install juanmhidalgo/gh-feedback)"

dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT

if ! meta=$(gh feedback "${repo[@]}" fetch "$pr" --split "$dir" --include-resolved); then
  die 7 "gh feedback fetch failed for PR $pr"
fi

jq -c '{
  inline: [.comments[] | select(.file != null and .line != null)
           | {ref_id, author, bot: .is_bot, file, line, thread_comments}],
  general: [.comments[] | select(.file == null or .line == null)
            | {ref_id, type, author, bot: .is_bot}]
}' <<<"$meta" || die 7 "unexpected gh feedback output"
