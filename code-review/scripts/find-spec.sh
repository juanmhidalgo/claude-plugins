#!/bin/bash
# find-spec.sh - Locate the spec a change was built from, for the Spec axis of a review
#
# Usage:
#   find-spec.sh --base <base-branch> [--spec <path|#N>]
#   find-spec.sh --pr <number> [--spec <path|#N>]
#   find-spec.sh --staged [--spec <path|#N>]
#
# Prints one source per line, most explicit first, deduplicated:
#   spec-file <path>      a file passed with --spec, or a SPEC-*/PLAN-* whose
#                         `branch:` frontmatter matches the branch under review
#   issue <N> closes      an issue the change claims to close
#   issue <N> refs        an issue the change only references (partial work expected)
#   unavailable <source>  a source that could not be checked (gh failed); the
#                         report must not claim it was looked at
#
# Prints nothing when no spec is found. Exits 0 except on bad usage (2): an
# absent spec is a normal outcome, not an error.
#
# Sources, in order:
#   1. --spec <path|#N>
#   2. --pr: the PR's closing issue references (gh)
#   3. --base: "Closes/Fixes/Resolves #N" (closes) and "Refs #N" (refs) in base..HEAD
#   4. SPEC-*.md / PLAN-*.md under .feature-dev/ whose `branch:` equals the branch.
#      Matches both the per-feature layout (.feature-dev/features/<slug>/) and the
#      older .feature-dev/specs|plans/ one. .feature-dev/ is usually gitignored,
#      so this reads the filesystem, not git. In a linked worktree it also looks
#      in the main checkout, where .feature-dev/ usually lives.

set -u

mode=""
target=""
spec_arg=""

usage() {
  sed -n '2,8p' "$0" >&2
  exit 2
}

need_value() {
  if [ $# -lt 2 ] || [ -z "$2" ]; then
    echo "find-spec: $1 needs a value" >&2
    usage
  fi
}

while [ $# -gt 0 ]; do
  case "$1" in
    --base) need_value "$@"; mode="base"; target="$2"; shift 2 ;;
    --pr) need_value "$@"; mode="pr"; target="$2"; shift 2 ;;
    --staged) mode="staged"; shift ;;
    --spec) need_value "$@"; spec_arg="$2"; shift 2 ;;
    *) usage ;;
  esac
done

[ -n "$mode" ] || usage
if [ "$mode" != "staged" ] && [ -z "$target" ]; then usage; fi

root=$(git rev-parse --show-toplevel 2>/dev/null) || root="."

out=()
add() {
  local line="$1" seen
  for seen in "${out[@]+"${out[@]}"}"; do
    # An issue already listed as "closes" is not repeated as "refs".
    [ "$seen" = "$line" ] && return
    [ "${line% refs}" != "$line" ] && [ "$seen" = "${line% refs} closes" ] && return
  done
  out+=("$line")
}

# 1. Explicit argument
if [ -n "$spec_arg" ]; then
  if [ -f "$spec_arg" ]; then
    add "spec-file $spec_arg"
  elif [[ "$spec_arg" =~ ^#?([0-9]+)$ ]]; then
    add "issue ${BASH_REMATCH[1]} closes"
  else
    echo "find-spec: --spec '$spec_arg' is neither a file nor an issue number" >&2
  fi
fi

# "Closes #1, #2" closes both; "Refs #3" is partial work. Only the trailer-style
# keywords GitHub itself recognizes, plus "Refs"/"Part of": prose like "see #4"
# is not a spec.
commit_keywords() {
  local msgs n
  msgs=$(git log "$1" --format=%B 2>/dev/null) || return 0
  while read -r n; do
    [ -n "$n" ] && add "issue $n closes"
  done < <(printf '%s\n' "$msgs" \
             | grep -oiE '(^|[^[:alnum:]])(close[sd]?|fix(e[sd])?|resolve[sd]?):? +#[0-9]+( *, *#[0-9]+)*' \
             | grep -oE '#[0-9]+' | tr -d '#')
  while read -r n; do
    [ -n "$n" ] && add "issue $n refs"
  done < <(printf '%s\n' "$msgs" \
             | grep -oiE '(^|[^[:alnum:]])(refs?|part of):? +#[0-9]+( *, *#[0-9]+)*' \
             | grep -oE '#[0-9]+' | tr -d '#')
}

branch=""
case "$mode" in
  pr)
    # 2. Closing issue references of the PR, then its commits' keywords
    #    (GitHub fills closingIssuesReferences only for PRs into the default branch)
    if pr_lines=$(gh pr view "$target" --json closingIssuesReferences,headRefName,baseRefName \
         -q '"head \(.headRefName)", "base \(.baseRefName)", (.closingIssuesReferences[].number | "issue \(.)")' 2>/dev/null); then
      pr_base=""
      while read -r kind value; do
        case "$kind" in
          head) branch="$value" ;;
          base) pr_base="$value" ;;
          issue) add "issue $value closes" ;;
        esac
      done <<< "$pr_lines"
      if [ -n "$branch" ] && git rev-parse -q --verify "origin/$branch" >/dev/null \
         && git rev-parse -q --verify "origin/$pr_base" >/dev/null; then
        commit_keywords "origin/$pr_base..origin/$branch"
      fi
    else
      add "unavailable pr-closing-issues"
    fi
    ;;
  base)
    # 3. Issue keywords in the branch's commit messages
    commit_keywords "$target..HEAD"
    branch=$(git branch --show-current 2>/dev/null)
    ;;
  staged)
    branch=$(git branch --show-current 2>/dev/null)
    ;;
esac

# 4. feature-dev artifacts whose branch: frontmatter matches, compared as an
#    exact string (branch names can hold regex metacharacters). Searched in this
#    checkout and, from a linked worktree, in the main one.
roots=("$root")
common=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || common=""
main_root="${common%/.git}"
if [ -n "$common" ] && [ "$main_root" != "$common" ] && [ "$main_root" != "$root" ]; then
  roots+=("$main_root")
fi
if [ -n "$branch" ]; then
  for r in "${roots[@]}"; do
    [ -d "$r/.feature-dev" ] || continue
    while read -r f; do
      if awk -v want="$branch" '
           { sub(/\r$/, "") }
           NR == 1 { if ($0 != "---") exit; next }
           $0 == "---" { exit }
           /^branch:/ {
             v = $0; sub(/^branch:[ \t]*/, "", v); sub(/[ \t]+$/, "", v)
             if (v ~ /^".*"$/ || v ~ /^\047.*\047$/) v = substr(v, 2, length(v) - 2)
             if (v == want) { found = 1; exit }
           }
           END { exit !found }' "$f"; then
        add "spec-file ${f#"$r"/}"
      fi
    done < <(find "$r/.feature-dev" \( -name 'SPEC-*.md' -o -name 'PLAN-*.md' \) -type f 2>/dev/null | sort)
  done
fi

for line in "${out[@]+"${out[@]}"}"; do
  printf '%s\n' "$line"
done
exit 0
