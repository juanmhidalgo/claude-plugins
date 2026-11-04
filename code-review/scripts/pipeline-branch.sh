#!/usr/bin/env bash
# pipeline-branch.sh — put this checkout on a PR's head for /code-review:pipeline,
# and bring it back when the pipeline ends.
#
#   pipeline-branch.sh enter <PR>   check the preconditions, check the PR branch out
#   pipeline-branch.sh leave        return to the branch `enter` left, if the tree is clean
#   pipeline-branch.sh status       print the saved state, if any
#
# `enter` runs Phase 0 of the pipeline as one deterministic step: the gh-feedback
# extension is installed, the tree is clean, the PR is open and not a draft, and
# HEAD is the PR's head. When the checkout is on another branch it runs
# `gh pr checkout` and remembers where it was; when the branch is behind the PR
# head it fast-forwards. It never discards commits: a HEAD with commits the PR
# lacks is exit 6, because a push would carry them along with the fixes.
#
# State lives in <git-dir>/code-review-pipeline-branch.state, so a worktree keeps
# its own. Every command prints one JSON line on stdout; messages go to stderr.
#
# Exit codes
#   0   ok
#   2   working tree not clean
#   3   PR is not open, or is a draft
#   4   gh-feedback extension missing
#   5   `gh pr checkout` failed (its message is on stderr)
#   6   HEAD has commits the PR head lacks (diverged or ahead)
#   7   git or gh failed
#   20  leave: tree not clean, the checkout stays on the PR branch, state kept

set -euo pipefail

json_str() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }
die() { local code=$1; shift; printf '%s\n' "$*" >&2; exit "$code"; }

git_dir=$(git rev-parse --git-dir 2>/dev/null) || die 7 "not a git repository"
state_file="$git_dir/code-review-pipeline-branch.state"

read_state() {
  s_pr=""; s_original=""; s_detached=""; s_switched=""; s_head_ref=""; s_head_oid=""
  [ -f "$state_file" ] || return 1
  local k v
  while IFS='=' read -r k v; do
    case "$k" in
      pr) s_pr=$v ;; original) s_original=$v ;; detached) s_detached=$v ;;
      switched) s_switched=$v ;; head_ref) s_head_ref=$v ;; head_oid) s_head_oid=$v ;;
    esac
  done < "$state_file"
  return 0
}

write_state() {
  printf 'pr=%s\noriginal=%s\ndetached=%s\nswitched=%s\nhead_ref=%s\nhead_oid=%s\n' \
    "$1" "$2" "$3" "$4" "$5" "$6" > "$state_file"
}

print_state() {
  printf '{"pr":%s,"original":"%s","detached":%s,"switched":%s,"head_ref":"%s","head_oid":"%s","state":"%s"}\n' \
    "$s_pr" "$(json_str "$s_original")" "$s_detached" "$s_switched" "$(json_str "$s_head_ref")" "$s_head_oid" "$(json_str "$state_file")"
}

dirty_files() { git status --porcelain; }

cmd_enter() {
  local pr=${1:-}
  [[ "$pr" =~ ^[0-9]+$ ]] || die 7 "usage: pipeline-branch.sh enter <PR number>"

  gh feedback --version >/dev/null 2>&1 \
    || die 4 "the gh-feedback extension is not installed: gh extension install juanmhidalgo/gh-feedback"

  local dirty
  dirty=$(dirty_files)
  [ -z "$dirty" ] || die 2 "working tree not clean:"$'\n'"$dirty"

  local view state draft head_ref head_oid
  view=$(gh pr view "$pr" --json state,isDraft,headRefName,headRefOid \
    -q '[.state, (.isDraft|tostring), .headRefName, .headRefOid] | join("\t")') \
    || die 7 "gh pr view $pr failed"
  IFS=$'\t' read -r state draft head_ref head_oid <<< "$view"
  [ "$state" = "OPEN" ] || die 3 "PR #$pr is $state, not OPEN"
  [ "$draft" = "false" ] || die 3 "PR #$pr is a draft"

  # Where to return to. A previous `enter` for this PR that never left keeps its
  # original: the PR branch itself is never the place to return to.
  local original detached=false current switched=false
  current=$(git branch --show-current)
  if read_state && [ "$s_pr" = "$pr" ] && [ "$s_switched" = "true" ] && [ "$current" = "$s_head_ref" ]; then
    original=$s_original; detached=$s_detached; switched=true
  elif [ -n "$current" ]; then
    original=$current
  else
    original=$(git rev-parse HEAD); detached=true
  fi

  if [ "$current" != "$head_ref" ]; then
    gh pr checkout "$pr" >&2 || die 5 "gh pr checkout $pr failed"
    switched=true
    current=$(git branch --show-current)
    [ "$current" = "$head_ref" ] || die 5 "gh pr checkout left the checkout on '$current', not '$head_ref'"
  fi

  # HEAD must be the PR head: fast-forward when behind, stop when ahead.
  local now fast_forwarded=false
  now=$(git rev-parse HEAD)
  if [ "$now" != "$head_oid" ]; then
    git cat-file -e "$head_oid^{commit}" 2>/dev/null \
      || git fetch --quiet origin "refs/pull/$pr/head" >&2 \
      || die 7 "could not fetch refs/pull/$pr/head from origin"
    if git merge-base --is-ancestor "$now" "$head_oid"; then
      git merge --ff-only --quiet "$head_oid" >&2 || die 7 "fast-forward to $head_oid failed"
      fast_forwarded=true
    else
      if [ "$switched" = true ] && [ "$current" != "$original" ]; then
        if [ "$detached" = true ]; then git switch --quiet --detach "$original" >&2; else git switch --quiet "$original" >&2; fi
      fi
      die 6 "HEAD ($now) has commits PR #$pr's head ($head_oid) lacks: a push would carry them along with the fixes"
    fi
  fi

  write_state "$pr" "$original" "$detached" "$switched" "$head_ref" "$head_oid"
  read_state
  printf '{"pr":%s,"original":"%s","detached":%s,"switched":%s,"fast_forwarded":%s,"head_ref":"%s","head_oid":"%s","state":"%s"}\n' \
    "$pr" "$(json_str "$original")" "$detached" "$switched" "$fast_forwarded" "$(json_str "$head_ref")" "$head_oid" "$(json_str "$state_file")"
}

cmd_leave() {
  if ! read_state; then
    printf '{"left":false,"reason":"no state"}\n'
    return 0
  fi
  local dirty
  dirty=$(dirty_files)
  if [ -n "$dirty" ]; then
    printf '{"left":false,"reason":"tree not clean","branch":"%s","original":"%s"}\n' \
      "$(json_str "$(git branch --show-current)")" "$(json_str "$s_original")"
    die 20 "working tree not clean: the checkout stays on $(git branch --show-current)"$'\n'"$dirty"
  fi
  local switched_back=false
  if [ "$s_switched" = "true" ]; then
    if [ "$s_detached" = "true" ]; then
      git switch --quiet --detach "$s_original" >&2 || die 7 "git switch --detach $s_original failed"
    else
      git switch --quiet "$s_original" >&2 || die 7 "git switch $s_original failed"
    fi
    switched_back=true
  fi
  rm -f "$state_file"
  printf '{"left":true,"switched_back":%s,"branch":"%s"}\n' "$switched_back" "$(json_str "$s_original")"
}

cmd_status() {
  if read_state; then print_state; else printf '{"state":null}\n'; fi
}

case "${1:-}" in
  enter) shift; cmd_enter "$@" ;;
  leave) cmd_leave ;;
  status) cmd_status ;;
  *) die 7 "usage: pipeline-branch.sh enter <PR> | leave | status" ;;
esac
