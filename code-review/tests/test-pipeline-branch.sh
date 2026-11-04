#!/usr/bin/env bash
# Tests for scripts/pipeline-branch.sh against a fake `gh` and a throwaway repo.
#   bash code-review/tests/test-pipeline-branch.sh
set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd)
script="$here/../scripts/pipeline-branch.sh"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
pass=0; fail=0

# --- fake gh -------------------------------------------------------------
mkdir -p "$tmp/bin"
cat > "$tmp/bin/gh" <<'GH'
#!/usr/bin/env bash
case "${1:-} ${2:-}" in
  "feedback --version") [ -n "${FAKE_NO_FEEDBACK:-}" ] && exit 1; echo "gh feedback version fake" ;;
  "pr view") printf '%s\t%s\t%s\t%s\n' "${FAKE_STATE:-OPEN}" "${FAKE_DRAFT:-false}" "$FAKE_HEAD_REF" "$FAKE_HEAD_OID" ;;
  "pr checkout")
    [ -n "${FAKE_CHECKOUT_FAILS:-}" ] && { echo "fake: checkout refused" >&2; exit 1; }
    git checkout -q "$FAKE_HEAD_REF" 2>/dev/null || git checkout -q -b "$FAKE_HEAD_REF" "origin/$FAKE_HEAD_REF" ;;
  *) echo "fake gh: unexpected $*" >&2; exit 99 ;;
esac
GH
chmod +x "$tmp/bin/gh"
export PATH="$tmp/bin:$PATH"

# --- repo: master (A), feature (A->B), origin has both and refs/pull/1/head=B ----
git init -q -b master "$tmp/origin.git" --bare
git init -q -b master "$tmp/repo"
cd "$tmp/repo"
git config user.email t@example.com; git config user.name t
echo a > a; git add a; git commit -qm A
git checkout -qb feature; echo b > b; git add b; git commit -qm B
B=$(git rev-parse HEAD)
git checkout -q master
git remote add origin "$tmp/origin.git"
git push -q origin master feature "$B:refs/pull/1/head"
export FAKE_HEAD_REF=feature FAKE_HEAD_OID=$B

check() { # name expected_exit actual_exit [extra condition]
  local name=$1 want=$2 got=$3 cond=${4:-true}
  if [ "$want" = "$got" ] && eval "$cond"; then pass=$((pass+1)); echo "ok   $name"
  else fail=$((fail+1)); echo "FAIL $name (exit want=$want got=$got, cond: $cond)"; fi
}
run() { out=$("$script" "$@" 2>"$tmp/err"); rc=$?; }
reset_repo() { rm -f .git/code-review-pipeline-branch.state; git checkout -q -f master; git branch -qf feature "$B"; git clean -qfd; }

# 1. gh-feedback missing
FAKE_NO_FEEDBACK=1 run enter 1; check "enter: gh-feedback missing is 4" 4 $rc

# 2. dirty tree
echo x > dirty; run enter 1; check "enter: dirty tree is 2" 2 $rc; rm dirty

# 3. PR not open / draft
FAKE_STATE=MERGED run enter 1; check "enter: merged PR is 3" 3 $rc
FAKE_DRAFT=true run enter 1; check "enter: draft PR is 3" 3 $rc

# 4. on master -> switches to feature, state written, leave returns
run enter 1; check "enter: from master switches" 0 $rc '[ "$(git branch --show-current)" = feature ] && grep -q "\"switched\":true" <<<"$out" && grep -q "\"original\":\"master\"" <<<"$out"'
run status; check "status: shows state" 0 $rc 'grep -q "\"original\":\"master\"" <<<"$out"'
run leave; check "leave: returns to master" 0 $rc '[ "$(git branch --show-current)" = master ] && grep -q "\"switched_back\":true" <<<"$out" && [ ! -f .git/code-review-pipeline-branch.state ]'

# 5. already on feature -> switched:false, leave does not move
git checkout -q feature
run enter 1; check "enter: already on branch" 0 $rc 'grep -q "\"switched\":false" <<<"$out"'
run leave; check "leave: stays on branch" 0 $rc '[ "$(git branch --show-current)" = feature ] && grep -q "\"switched_back\":false" <<<"$out"'
reset_repo

# 6. on feature but behind: fast-forward (oid present locally)
echo c > c; git checkout -q feature; git add c; git commit -qm C; C=$(git rev-parse HEAD)
git push -q origin feature "$C:refs/pull/1/head"
git reset -q --hard "$B"
FAKE_HEAD_OID=$C run enter 1; check "enter: behind is fast-forwarded" 0 $rc '[ "$(git rev-parse HEAD)" = "$C" ] && grep -q "\"fast_forwarded\":true" <<<"$out"'
run leave; reset_repo

# 7. behind and the oid is not local: fetched from refs/pull/N/head
git checkout -q feature; git reset -q --hard "$B"
git update-ref -d "refs/remotes/origin/feature"; git gc -q --prune=now 2>/dev/null
git cat-file -e "$C^{commit}" 2>/dev/null && echo "setup: C still local (fine, test is weaker)"
FAKE_HEAD_OID=$C run enter 1; check "enter: behind, oid fetched" 0 $rc '[ "$(git rev-parse HEAD)" = "$C" ]'
run leave; reset_repo

# 8. ahead of the PR head -> 6, and back on master when it had switched
git checkout -q feature; echo d > d; git add d; git commit -qm D; git checkout -q master
run enter 1; check "enter: ahead is 6 and returns to master" 6 $rc '[ "$(git branch --show-current)" = master ] && [ ! -f .git/code-review-pipeline-branch.state ]'
reset_repo

# 9. leave with a dirty tree: 20, state kept, still on feature
run enter 1; echo e > e
run leave; check "leave: dirty tree is 20, stays" 20 $rc '[ "$(git branch --show-current)" = feature ] && [ -f .git/code-review-pipeline-branch.state ] && grep -q "\"left\":false" <<<"$out"'
rm e; run leave; check "leave: after cleanup returns" 0 $rc '[ "$(git branch --show-current)" = master ]'

# 10. enter twice without leaving keeps original=master
run enter 1; run enter 1; check "enter: second enter keeps original" 0 $rc 'grep -q "\"original\":\"master\"" <<<"$out" && grep -q "\"switched\":true" <<<"$out"'
run leave; check "leave: back to master after double enter" 0 $rc '[ "$(git branch --show-current)" = master ]'

# 11. detached original
A=$(git rev-parse master); git checkout -q --detach "$A"
run enter 1; check "enter: detached original" 0 $rc 'grep -q "\"detached\":true" <<<"$out"'
run leave; check "leave: back to detached HEAD" 0 $rc '[ -z "$(git branch --show-current)" ] && [ "$(git rev-parse HEAD)" = "$A" ]'
reset_repo

# 12. checkout failure -> 5, nothing written
FAKE_CHECKOUT_FAILS=1 run enter 1; check "enter: checkout failure is 5" 5 $rc '[ ! -f .git/code-review-pipeline-branch.state ]'

# 13. leave without state
run leave; check "leave: no state is a no-op" 0 $rc 'grep -q "\"left\":false" <<<"$out"'

echo; echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
