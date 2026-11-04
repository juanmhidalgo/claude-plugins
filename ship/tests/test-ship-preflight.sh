#!/usr/bin/env bash
# Tests for scripts/ship-preflight.sh against a fake `gh` and a throwaway repo.
#   bash ship/tests/test-ship-preflight.sh
set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd)
script="$here/../scripts/ship-preflight.sh"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
pass=0; fail=0

# --- fake gh -------------------------------------------------------------
mkdir -p "$tmp/bin"
cat > "$tmp/bin/gh" <<'GH'
#!/usr/bin/env bash
case "${1:-} ${2:-}" in
  "auth status") [ -n "${FAKE_UNAUTH:-}" ] && exit 1; echo "Logged in" ;;
  "feedback --version") [ -n "${FAKE_NO_FEEDBACK:-}" ] && exit 1; echo "gh feedback version fake" ;;
  "repo view") [ -n "${FAKE_NO_REPO:-}" ] && exit 1; echo "${FAKE_DEFAULT:-master}" ;;
  "pr list")
    [ -n "${FAKE_PR:-}" ] || exit 0
    printf '%s\t%s\t%s\n' "$FAKE_PR" "https://github.com/o/r/pull/$FAKE_PR" "${FAKE_DRAFT:-false}" ;;
  *) echo "fake gh: unexpected $*" >&2; exit 99 ;;
esac
GH
chmod +x "$tmp/bin/gh"
export PATH="$tmp/bin:$PATH"

# --- repo: master (A), feature (A->B), origin has both -----------------------
git init -q -b master "$tmp/origin.git" --bare
git init -q -b master "$tmp/repo"
cd "$tmp/repo" || exit 1
git config user.email t@example.com; git config user.name t
echo a > a; git add a; git commit -qm A
git checkout -qb feature; echo b > b; git add b; git commit -qm B
B=$(git rev-parse HEAD)
git checkout -q master
git remote add origin "$tmp/origin.git"
git push -q -u origin master
git push -q -u origin feature

check() { # name expected_exit actual_exit [extra condition]
  local name=$1 want=$2 got=$3 cond=${4:-true}
  if [ "$want" = "$got" ] && eval "$cond"; then pass=$((pass+1)); echo "ok   $name"
  else fail=$((fail+1)); echo "FAIL $name (exit want=$want got=$got, cond: $cond)"; echo "     out: $out"; echo "     err: $(cat "$tmp/err")"; fi
}
run() { out=$("$script" "$@" 2>"$tmp/err"); rc=$?; }
has() { grep -q -- "$1" <<<"$out"; }
reset_repo() { git checkout -q -f master; git branch -qf feature "$B"; git clean -qfd; }

# 1. exit 7: not a git repository
mkdir -p "$tmp/plain"; (cd "$tmp/plain" && "$script" >/dev/null 2>"$tmp/err"); rc=$?; out=""
check "not a repo is 7" 7 $rc 'grep -q "not a git repository" "$tmp/err"'
run --bogus; check "unknown flag is 7" 7 $rc

# 2. exit 4: detached HEAD
git checkout -q --detach "$B"
run; check "detached HEAD is 4" 4 $rc
reset_repo

# 3. exit 5: no remote
git remote remove origin
echo x > x
run; check "no remote is 5" 5 $rc
rm x; git remote add origin "$tmp/origin.git"; git fetch -q origin
git branch -q --set-upstream-to=origin/master master; git branch -q --set-upstream-to=origin/feature feature

# 4. exit 2: clean tree, nothing staged (feature, no --yes, even with commits ahead of base)
git checkout -q feature
run; check "clean feature without --yes is 2" 2 $rc 'has "\"mode\":\"commit\"" && has "\"ahead_of_base\":1"'
# clean tree with --yes but nothing ahead of the base
git checkout -q master
run --yes; check "clean and not ahead of base with --yes is 2" 2 $rc 'has "\"ahead_of_base\":0"'

# 5. exit 3: default branch with --yes
echo x > x
run --yes; check "dirty default branch with --yes is 3" 3 $rc 'has "\"on_default_branch\":true" && has "\"untracked\":1"'
# without --yes the same state is 0 and the skill asks
run; check "dirty default branch without --yes is 0" 0 $rc 'has "\"on_default_branch\":true" && has "\"mode\":\"commit\""'
rm x

# 6. exit 0 ready on a feature branch, with the counts
git checkout -q feature
echo c > c; echo bb > b; echo d > d; git add c
run; check "dirty feature is 0 with counts" 0 $rc 'has "\"branch\":\"feature\"" && has "\"default_branch\":\"master\"" && has "\"default_branch_source\":\"gh\"" && has "\"on_default_branch\":false" && has "\"staged\":1" && has "\"unstaged\":1" && has "\"untracked\":1" && has "\"upstream\":\"origin/feature\"" && has "\"remote\":\"origin\"" && has "\"ahead\":0" && has "\"behind\":0" && has "\"pr\":null" && has "\"gh\":\"ok\"" && has "\"gh_feedback\":true" && has "\"pr_templates\":\[\]"'
reset_repo

# 7. exit 0 push mode: --yes, clean tree, ahead of base
git checkout -q feature
run --yes; check "clean feature ahead of base with --yes is push mode" 0 $rc 'has "\"mode\":\"push\"" && has "\"ahead_of_base\":1"'

# 8. ahead/behind vs upstream, and no upstream
echo c > c; git add c; git commit -qm C
git push -q origin feature:refs/heads/moved
git reset -q --hard "$B"
git branch -q --set-upstream-to=origin/moved feature
echo x > x
run; check "behind upstream is reported" 0 $rc 'has "\"upstream\":\"origin/moved\"" && has "\"ahead\":0" && has "\"behind\":1"'
git branch -q --set-upstream-to=origin/feature feature
git checkout -qb loose; echo y > y
run; check "no upstream is null, remote falls back to origin" 0 $rc 'has "\"upstream\":null" && has "\"remote\":\"origin\"" && has "\"ahead\":0" && has "\"behind\":0" && has "\"ahead_of_base\":1"'
rm x y; git checkout -q master; git branch -qD loose; reset_repo

# 9. existing open PR, draft flag
git checkout -q feature; echo x > x
FAKE_PR=12 run; check "open PR is reported" 0 $rc 'has "\"pr\":{\"number\":12,\"url\":\"https://github.com/o/r/pull/12\",\"isDraft\":false}"'
FAKE_PR=12 FAKE_DRAFT=true run; check "draft PR is reported" 0 $rc 'has "\"isDraft\":true"'

# 10. gh unauthenticated: no PR lookup, default branch from the remote HEAD
git remote set-head origin master
FAKE_UNAUTH=1 run; check "gh unauthenticated" 0 $rc 'has "\"gh\":\"unauthenticated\"" && has "\"pr\":null" && has "\"default_branch\":\"master\"" && has "\"default_branch_source\":\"origin-head\""'
# gh ok but repo view fails: same fallback
FAKE_NO_REPO=1 run; check "gh repo view failing falls back to origin/HEAD" 0 $rc 'has "\"default_branch_source\":\"origin-head\""'
git remote set-head origin -d
FAKE_NO_REPO=1 run; check "no origin/HEAD falls back to a local master" 0 $rc 'has "\"default_branch\":\"master\"" && has "\"default_branch_source\":\"local\""'

# 11. gh missing entirely: a PATH that holds every tool the script uses except gh
mkdir -p "$tmp/nogh"
for tool in bash git sed grep head find sort; do ln -s "$(command -v "$tool")" "$tmp/nogh/$tool"; done
out=$(PATH="$tmp/nogh" "$script" 2>"$tmp/err"); rc=$?
check "gh missing" 0 $rc 'has "\"gh\":\"missing\"" && has "\"gh_feedback\":false" && has "\"pr\":null"'

# 12. gh-feedback missing
FAKE_NO_FEEDBACK=1 run; check "gh-feedback missing" 0 $rc 'has "\"gh_feedback\":false"'

# 13. PR templates, sorted, folder entries by name
mkdir -p .github/PULL_REQUEST_TEMPLATE docs
echo t > .github/pull_request_template.md; echo t > docs/pull_request_template.md
echo t > .github/PULL_REQUEST_TEMPLATE/b.md; echo t > .github/PULL_REQUEST_TEMPLATE/a.md
run; check "PR templates listed" 0 $rc 'has "\"pr_templates\":\[\".github/pull_request_template.md\",\"docs/pull_request_template.md\",\".github/PULL_REQUEST_TEMPLATE/a.md\",\".github/PULL_REQUEST_TEMPLATE/b.md\"\]"'
reset_repo

# 14. the JSON line is valid when a parser is around
if command -v python3 >/dev/null 2>&1; then
  git checkout -q feature; echo 'q"uote' > 'we"ird'
  FAKE_PR=3 run; check "JSON parses" 0 $rc 'python3 -c "import json,sys; d=json.loads(sys.argv[1]); assert d[\"pr\"][\"number\"]==3 and d[\"untracked\"]==1" "$out"'
  reset_repo
fi

echo; echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
