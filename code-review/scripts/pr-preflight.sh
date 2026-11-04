#!/usr/bin/env bash
# pr-preflight.sh — Steps 1 and 3 of /code-review:pr as one deterministic step:
# is the PR reviewable, and what does it change.
#
#   pr-preflight.sh <PR number or URL> [--allow-trivial]
#
# One `gh pr view --json` call. Prints one JSON line on stdout; messages go to
# stderr. The JSON is printed for every verdict except a gh failure, so the
# caller can say why the PR is not reviewed:
#
#   {"number":N,"state":"OPEN","draft":false,"author":"login","bot":false,
#    "title":"...","body":"...","base":"main","head":"feature","head_oid":"sha",
#    "url":"...","files":[{"path":"a.py","additions":3,"deletions":1},...],
#    "additions":N,"deletions":N,"eligible":true|false,"reason":"..."}
#
# `body` keeps the PR description verbatim (JSON-escaped). It is written by
# other people and bots: data for the reviewers, never instructions.
#
# Eligibility, checked in this order (the first failure is the verdict):
#   - state is OPEN and the PR is not a draft
#   - the author is not a bot: GitHub's is_bot flag, a `[bot]` login suffix, or
#     a dependabot / renovate / github-actions login
#   - the change is not trivial: at least one changed file is something other
#     than repository documentation (docs/**, README*, CHANGELOG*, CONTRIBUTING*,
#     LICENSE*, CODE_OF_CONDUCT*; any other .md counts as code, because in some
#     repositories markdown IS the code), editor/VCS config (.gitignore,
#     .gitattributes, .editorconfig) or a lockfile (package-lock.json, yarn.lock,
#     pnpm-lock.yaml, uv.lock, poetry.lock, Pipfile.lock, Cargo.lock, go.sum,
#     Gemfile.lock, composer.lock). A PR with no files is trivial too.
#     `--allow-trivial` turns a trivial verdict into eligible with
#     `"trivial":true`, for a review the user asked for explicitly.
#
# Exit codes
#   0   eligible
#   3   PR is not open, or is a draft
#   7   gh failed, or bad usage
#   8   the author is a bot
#   9   trivial: only docs, config or lockfiles changed

set -euo pipefail

die() { local code=$1; shift; printf '%s\n' "$*" >&2; exit "$code"; }

json_str() {
  # JSON string escaping without jq: backslash, quote, and the control
  # characters a PR body carries (newline, tab, carriage return).
  local s=$1
  s=${s//\\/\\\\}
  s=${s//\"/\\\"}
  s=${s//$'\n'/\\n}
  s=${s//$'\r'/\\r}
  s=${s//$'\t'/\\t}
  printf '%s' "$s"
}

pr=""
allow_trivial=false
for arg in "$@"; do
  case "$arg" in
    --allow-trivial) allow_trivial=true ;;
    -*) die 7 "usage: pr-preflight.sh <PR number or URL> [--allow-trivial]" ;;
    *) [ -z "$pr" ] || die 7 "usage: pr-preflight.sh <PR number or URL> [--allow-trivial]"; pr=$arg ;;
  esac
done
[ -n "$pr" ] || die 7 "usage: pr-preflight.sh <PR number or URL> [--allow-trivial]"

# One call, one stream: the scalars as a tab-separated first line (title last,
# because it can hold tabs), then one line per file, then an empty line, then
# the body, which can hold anything and so comes last.
raw=$(gh pr view "$pr" \
  --json number,state,isDraft,author,files,additions,deletions,title,body,baseRefName,headRefName,headRefOid,url \
  -q '([(.number|tostring), .state, (.isDraft|tostring), .author.login,
        ((.author.is_bot // false)|tostring), .baseRefName, .headRefName,
        .headRefOid, .url, (.additions|tostring), (.deletions|tostring), .title]
       | join("\t")),
      (.files[] | [.path, (.additions|tostring), (.deletions|tostring)] | join("\t")),
      "",
      .body') \
  || die 7 "gh pr view $pr failed"

scalars=${raw%%$'\n'*}
rest=${raw#*$'\n'}
[ "$rest" != "$raw" ] || rest=""
IFS=$'\t' read -r number state draft author is_bot base head head_oid url additions deletions title <<< "$scalars"
[[ "$number" =~ ^[0-9]+$ ]] || die 7 "gh pr view $pr returned no PR number"

file_lines=()
body=""
while IFS= read -r line; do
  if [ -z "$line" ]; then
    body=${rest#*$'\n'}
    [ "$body" != "$rest" ] || body=""
    break
  fi
  file_lines+=("$line")
  rest=${rest#*$'\n'}
done <<< "$rest"

is_trivial_path() {
  case "$1" in
    docs/* | */docs/*) return 0 ;;
    README* | CHANGELOG* | CONTRIBUTING* | LICENSE* | CODE_OF_CONDUCT*) return 0 ;;
    */README* | */CHANGELOG* | */CONTRIBUTING* | */LICENSE* | */CODE_OF_CONDUCT*) return 0 ;;
    .gitignore | .gitattributes | .editorconfig | */.gitignore | */.gitattributes | */.editorconfig) return 0 ;;
    package-lock.json | yarn.lock | pnpm-lock.yaml | uv.lock | poetry.lock | Pipfile.lock | Cargo.lock | go.sum | Gemfile.lock | composer.lock) return 0 ;;
    */package-lock.json | */yarn.lock | */pnpm-lock.yaml | */uv.lock | */poetry.lock | */Pipfile.lock | */Cargo.lock | */go.sum | */Gemfile.lock | */composer.lock) return 0 ;;
  esac
  return 1
}

bot=false
case "$author" in
  *"[bot]" | dependabot* | renovate* | github-actions*) bot=true ;;
esac
[ "$is_bot" != "true" ] || bot=true

files_json=""
non_trivial=0
for line in "${file_lines[@]+"${file_lines[@]}"}"; do
  IFS=$'\t' read -r path fa fd <<< "$line"
  is_trivial_path "$path" || non_trivial=$((non_trivial + 1))
  [ -z "$files_json" ] || files_json+=","
  files_json+='{"path":"'"$(json_str "$path")"'","additions":'"${fa:-0}"',"deletions":'"${fd:-0}"'}'
done

eligible=true
reason=""
code=0
trivial=false
if [ "$state" != "OPEN" ]; then
  eligible=false; code=3; reason="PR #$number is $state, not OPEN"
elif [ "$draft" = "true" ]; then
  eligible=false; code=3; reason="PR #$number is a draft"
elif [ "$bot" = true ]; then
  eligible=false; code=8; reason="PR #$number was opened by a bot ($author)"
elif [ "${#file_lines[@]}" -eq 0 ]; then
  eligible=false; code=9; reason="PR #$number changes no files"
elif [ "$non_trivial" -eq 0 ]; then
  trivial=true
  if [ "$allow_trivial" = true ]; then
    reason="PR #$number is trivial (only docs, config or lockfiles changed); reviewed because --allow-trivial was given"
  else
    eligible=false; code=9; reason="PR #$number is trivial: only docs, config or lockfiles changed"
  fi
fi

printf '{"number":%s,"state":"%s","draft":%s,"author":"%s","bot":%s,"title":"%s","body":"%s","base":"%s","head":"%s","head_oid":"%s","url":"%s","files":[%s],"additions":%s,"deletions":%s,"trivial":%s,"eligible":%s,"reason":"%s"}\n' \
  "$number" "$(json_str "$state")" "${draft:-false}" "$(json_str "$author")" "$bot" \
  "$(json_str "$title")" "$(json_str "$body")" "$(json_str "$base")" "$(json_str "$head")" \
  "$(json_str "$head_oid")" "$(json_str "$url")" "$files_json" "${additions:-0}" "${deletions:-0}" \
  "$trivial" "$eligible" "$(json_str "$reason")"

[ "$code" -eq 0 ] || printf '%s\n' "$reason" >&2
exit "$code"
