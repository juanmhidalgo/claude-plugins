#!/usr/bin/env bash
# ship-preflight.sh — Phase 1 of /ship as one deterministic step.
#
#   ship-preflight.sh [--yes]
#
# Reads the repository state the ship skill used to work out by hand (branch,
# default branch, remote, upstream, dirty counts, existing PR, gh, gh-feedback,
# PR templates), prints it as one JSON line on stdout, and stops with a distinct
# exit code for each condition under which /ship does not go on. Messages go to
# stderr. It never changes anything: no fetch, no checkout, no staging.
#
# `--yes` is the skill's headless flag. It changes two decisions here: the
# default branch is a stop instead of a question, and a clean tree with commits
# ahead of the default branch is "push" work instead of "nothing to ship".
#
# JSON fields
#   branch                current branch
#   default_branch        from gh, else origin/HEAD, else a local or remote
#                         main/master, else "main" (see default_branch_source)
#   default_branch_source "gh" | "origin-head" | "local" | "guess"
#   on_default_branch     true when branch == default_branch
#   remote                the upstream's remote, else origin, else the first one
#   upstream              "<remote>/<branch>" or null
#   ahead, behind         commits vs the upstream as git knows it (0 when none)
#   ahead_of_base         commits in <default_branch>..HEAD (0 when the default
#                         branch is not known locally)
#   staged, unstaged, untracked   counts from git status --porcelain
#   mode                  "commit" (something to stage or commit) or "push"
#                         (clean tree, commits ahead of the base, --yes only)
#   gh                    "ok" | "missing" | "unauthenticated"
#   gh_feedback           true when the gh-feedback extension answers
#   pr                    {"number","url","isDraft"} of the open PR for this
#                         branch, or null (also null when gh is not "ok")
#   pr_templates          PR template paths the repo has, sorted by path
#
# Exit codes
#   0   ready: the skill goes on with Phase 2 (mode "commit") or Phase 4 (mode "push")
#   2   nothing to ship: clean tree and nothing staged (with --yes: and no
#       commits ahead of the default branch either)
#   3   on the default branch with --yes: /ship never branches or pushes there on its own
#   4   detached HEAD: nothing to push
#   5   no remote configured: nothing to push to
#   7   git failed (not a repository, or a command this script needs)

set -euo pipefail

json_str() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }
die() { local code=$1; shift; printf '%s\n' "$*" >&2; exit "$code"; }

yes=false
for arg in "$@"; do
  case "$arg" in
    --yes) yes=true ;;
    *) die 7 "usage: ship-preflight.sh [--yes]" ;;
  esac
done

git rev-parse --git-dir >/dev/null 2>&1 || die 7 "not a git repository"
top=$(git rev-parse --show-toplevel) || die 7 "git rev-parse --show-toplevel failed"

branch=$(git branch --show-current)
[ -n "$branch" ] || die 4 "detached HEAD ($(git rev-parse --short HEAD)): check out a branch to ship"

# --- remote and upstream ---------------------------------------------------
upstream=$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)
remote=""
if [ -n "$upstream" ]; then
  remote=${upstream%%/*}
elif git remote | grep -qx origin; then
  remote=origin
else
  remote=$(git remote | head -n 1)
fi
[ -n "$remote" ] || die 5 "no remote configured: add one before shipping (git remote add origin <url>)"

ahead=0; behind=0
if [ -n "$upstream" ]; then
  read -r ahead behind < <(git rev-list --left-right --count "HEAD...$upstream" 2>/dev/null || echo "0 0")
fi

# --- gh and the default branch -------------------------------------------
gh_state=missing
if command -v gh >/dev/null 2>&1; then
  if gh auth status >/dev/null 2>&1; then gh_state=ok; else gh_state=unauthenticated; fi
fi

default_branch=""; default_source=""
if [ "$gh_state" = ok ]; then
  default_branch=$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name 2>/dev/null || true)
  [ -n "$default_branch" ] && default_source=gh
fi
if [ -z "$default_branch" ]; then
  head_ref=$(git symbolic-ref --quiet --short "refs/remotes/$remote/HEAD" 2>/dev/null || true)
  if [ -n "$head_ref" ]; then default_branch=${head_ref#"$remote/"}; default_source=origin-head; fi
fi
if [ -z "$default_branch" ]; then
  for candidate in main master; do
    if git show-ref --verify --quiet "refs/heads/$candidate" \
      || git show-ref --verify --quiet "refs/remotes/$remote/$candidate"; then
      default_branch=$candidate; default_source=local; break
    fi
  done
fi
if [ -z "$default_branch" ]; then default_branch=main; default_source=guess; fi

on_default=false
[ "$branch" = "$default_branch" ] && on_default=true

ahead_of_base=0
if [ "$on_default" = false ]; then
  base_ref=""
  if git show-ref --verify --quiet "refs/heads/$default_branch"; then base_ref=$default_branch
  elif git show-ref --verify --quiet "refs/remotes/$remote/$default_branch"; then base_ref="$remote/$default_branch"
  fi
  [ -n "$base_ref" ] && ahead_of_base=$(git rev-list --count "$base_ref..HEAD" 2>/dev/null || echo 0)
fi

# --- working tree -----------------------------------------------------------
staged=0; unstaged=0; untracked=0
while IFS= read -r line; do
  [ -n "$line" ] || continue
  x=${line:0:1}; y=${line:1:1}
  if [ "$x" = '?' ]; then untracked=$((untracked+1)); continue; fi
  [ "$x" != ' ' ] && staged=$((staged+1))
  [ "$y" != ' ' ] && unstaged=$((unstaged+1))
done < <(git status --porcelain)

# --- gh-feedback, the open PR, the templates ------------------------------
gh_feedback=false
[ "$gh_state" != missing ] && gh feedback --version >/dev/null 2>&1 && gh_feedback=true

pr_json=null
if [ "$gh_state" = ok ]; then
  pr_line=$(gh pr list --head "$branch" --state open --limit 1 --json number,url,isDraft \
    -q '.[0] | select(. != null) | [(.number|tostring), .url, (.isDraft|tostring)] | join("\t")' 2>/dev/null || true)
  if [ -n "$pr_line" ]; then
    IFS=$'\t' read -r pr_number pr_url pr_draft <<< "$pr_line"
    pr_json=$(printf '{"number":%s,"url":"%s","isDraft":%s}' "$pr_number" "$(json_str "$pr_url")" "$pr_draft")
  fi
fi

templates=""
for candidate in \
  .github/pull_request_template.md .github/PULL_REQUEST_TEMPLATE.md \
  docs/pull_request_template.md pull_request_template.md; do
  [ -f "$top/$candidate" ] && templates+="$candidate"$'\n'
done
if [ -d "$top/.github/PULL_REQUEST_TEMPLATE" ]; then
  while IFS= read -r f; do templates+=".github/PULL_REQUEST_TEMPLATE/${f}"$'\n'; done \
    < <(cd "$top/.github/PULL_REQUEST_TEMPLATE" && find . -maxdepth 1 -type f -printf '%P\n' | LC_ALL=C sort)
fi
templates_json="["
first=true
while IFS= read -r t; do
  [ -n "$t" ] || continue
  $first || templates_json+=","
  first=false
  templates_json+="\"$(json_str "$t")\""
done <<< "$templates"
templates_json+="]"

# --- decide -----------------------------------------------------------------
mode=commit
if [ $((staged + unstaged + untracked)) -eq 0 ]; then
  if [ "$yes" = true ] && [ "$ahead_of_base" -gt 0 ]; then
    mode=push
  else
    stop_code=2
  fi
fi
if [ -z "${stop_code:-}" ] && [ "$on_default" = true ] && [ "$yes" = true ]; then
  stop_code=3
fi

upstream_json=null
[ -n "$upstream" ] && upstream_json="\"$(json_str "$upstream")\""

printf '{"branch":"%s","default_branch":"%s","default_branch_source":"%s","on_default_branch":%s,"remote":"%s","upstream":%s,"ahead":%s,"behind":%s,"ahead_of_base":%s,"staged":%s,"unstaged":%s,"untracked":%s,"mode":"%s","gh":"%s","gh_feedback":%s,"pr":%s,"pr_templates":%s}\n' \
  "$(json_str "$branch")" "$(json_str "$default_branch")" "$default_source" "$on_default" \
  "$(json_str "$remote")" "$upstream_json" "$ahead" "$behind" "$ahead_of_base" \
  "$staged" "$unstaged" "$untracked" "$mode" "$gh_state" "$gh_feedback" "$pr_json" "$templates_json"

case "${stop_code:-0}" in
  2) if [ "$yes" = true ]; then
       die 2 "nothing to ship: the tree is clean and $branch has no commits ahead of $default_branch"
     else
       die 2 "nothing to ship: the tree is clean and nothing is staged${upstream:+ (ahead of $upstream: $ahead)}"
     fi ;;
  3) die 3 "on the default branch ($default_branch) with --yes: /ship never branches or pushes there on its own" ;;
esac
exit 0
