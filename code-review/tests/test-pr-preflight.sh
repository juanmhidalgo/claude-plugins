#!/usr/bin/env bash
# Tests for scripts/pr-preflight.sh against a fake `gh`.
#   bash code-review/tests/test-pr-preflight.sh
# shellcheck disable=SC2016,SC2034  # check() evals its condition string; $out, $tmp, $decoded are read there
set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd)
script="$here/../scripts/pr-preflight.sh"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
pass=0; fail=0

# --- fake gh -------------------------------------------------------------
# Prints what the script's single `gh pr view --json ... -q` call prints: one
# tab-separated line of scalars (title last), one line per file as
# "path<TAB>additions<TAB>deletions", an empty line, then the body.
mkdir -p "$tmp/bin"
cat > "$tmp/bin/gh" <<'GH'
#!/usr/bin/env bash
case "${1:-} ${2:-}" in
  "pr view")
    [ -n "${FAKE_FAIL:-}" ] && { echo "GraphQL: Could not resolve to a PullRequest" >&2; exit 1; }
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
      "${FAKE_NUMBER:-42}" "${FAKE_STATE:-OPEN}" "${FAKE_DRAFT:-false}" "${FAKE_LOGIN:-alice}" \
      "${FAKE_IS_BOT:-false}" "${FAKE_BASE:-main}" "${FAKE_HEAD:-feature}" \
      "${FAKE_OID:-0123456789abcdef0123456789abcdef01234567}" \
      "${FAKE_URL:-https://github.com/example/repo/pull/42}" "${FAKE_ADD:-10}" "${FAKE_DEL:-2}" \
      "${FAKE_TITLE:-Add the thing}"
    printf '%s' "${FAKE_FILES-src/app.py	8	1
tests/test_app.py	2	1}"
    [ -z "${FAKE_FILES-x}" ] || printf '\n'
    printf '\n'
    printf '%s\n' "${FAKE_BODY-Closes #7}" ;;
  *) echo "fake gh: unexpected $*" >&2; exit 99 ;;
esac
GH
chmod +x "$tmp/bin/gh"
export PATH="$tmp/bin:$PATH"

check() { # name expected_exit actual_exit [extra condition]
  local name=$1 want=$2 got=$3 cond=${4:-true}
  if [ "$want" = "$got" ] && eval "$cond"; then pass=$((pass+1)); echo "ok   $name"
  else fail=$((fail+1)); echo "FAIL $name (exit want=$want got=$got, cond: $cond)"; echo "     out: $out"; echo "     err: $(cat "$tmp/err")"; fi
}
run() { out=$("$script" "$@" 2>"$tmp/err"); rc=$?; }
# The JSON must parse; python3 is the only parser the repo can assume on a dev box.
valid_json() {
  if command -v python3 >/dev/null 2>&1; then
    python3 -I -c 'import json,sys; json.loads(sys.argv[1])' "$out" 2>/dev/null
  else
    [ "${out:0:1}" = "{" ]
  fi
}

# 0. eligible: the whole payload is there
run 42; check "eligible PR is 0" 0 $rc 'valid_json && grep -q "\"eligible\":true" <<<"$out" && grep -q "\"number\":42" <<<"$out" && grep -q "\"head_oid\":\"0123456789abcdef0123456789abcdef01234567\"" <<<"$out" && grep -q "\"files\":\[{\"path\":\"src/app.py\",\"additions\":8,\"deletions\":1},{\"path\":\"tests/test_app.py\",\"additions\":2,\"deletions\":1}\]" <<<"$out" && grep -q "\"body\":\"Closes #7\"" <<<"$out" && grep -q "\"reason\":\"\"" <<<"$out"'
run https://github.com/example/repo/pull/42; check "a PR URL is accepted" 0 $rc 'grep -q "\"url\":\"https://github.com/example/repo/pull/42\"" <<<"$out"'

# 3. not open, or draft
FAKE_STATE=MERGED run 42; check "merged PR is 3" 3 $rc 'valid_json && grep -q "\"eligible\":false" <<<"$out" && grep -q "\"state\":\"MERGED\"" <<<"$out" && grep -q "not OPEN" <<<"$out"'
FAKE_STATE=CLOSED run 42; check "closed PR is 3" 3 $rc 'grep -q "\"state\":\"CLOSED\"" <<<"$out"'
FAKE_DRAFT=true run 42; check "draft PR is 3" 3 $rc 'grep -q "\"draft\":true" <<<"$out" && grep -q "is a draft" <<<"$out"'
FAKE_STATE=CLOSED FAKE_LOGIN='dependabot[bot]' run 42; check "state is checked before the author" 3 $rc 'grep -q "not OPEN" <<<"$out"'

# 7. gh failed, or bad usage
FAKE_FAIL=1 run 42; check "gh failure is 7, no JSON" 7 $rc '[ -z "$out" ] && grep -q "gh pr view 42 failed" "$tmp/err"'
run; check "no argument is 7" 7 $rc 'grep -q usage "$tmp/err"'
run --help; check "a flag is 7" 7 $rc 'grep -q usage "$tmp/err"'

# 8. bot author
FAKE_IS_BOT=true FAKE_LOGIN=copilot-swe-agent run 42; check "is_bot flag is 8" 8 $rc 'valid_json && grep -q "\"bot\":true" <<<"$out" && grep -q "opened by a bot (copilot-swe-agent)" <<<"$out"'
FAKE_LOGIN='some-app[bot]' run 42; check "[bot] login suffix is 8" 8 $rc 'grep -q "\"bot\":true" <<<"$out"'
FAKE_LOGIN=dependabot run 42; check "dependabot login is 8" 8 $rc 'grep -q "\"bot\":true" <<<"$out"'
FAKE_LOGIN=renovate-bot run 42; check "renovate login is 8" 8 $rc 'grep -q "\"bot\":true" <<<"$out"'
FAKE_LOGIN=github-actions run 42; check "github-actions login is 8" 8 $rc 'grep -q "\"bot\":true" <<<"$out"'
FAKE_LOGIN=robotics-team run 42; check "a human login containing bot is 0" 0 $rc 'grep -q "\"bot\":false" <<<"$out"'

# 9. trivial
FAKE_FILES=$'README.md\t3\t0\ndocs/guide.md\t10\t2' run 42; check "docs only is 9" 9 $rc 'valid_json && grep -q "\"eligible\":false" <<<"$out" && grep -q "trivial" <<<"$out"'
FAKE_FILES=$'package-lock.json\t300\t280\nweb/yarn.lock\t5\t5\nuv.lock\t1\t1' run 42; check "lockfiles only is 9" 9 $rc 'grep -q trivial <<<"$out"'
FAKE_FILES=$'.gitignore\t1\t0\n.editorconfig\t2\t0\napp/.gitattributes\t1\t0' run 42; check "config only is 9" 9 $rc 'grep -q trivial <<<"$out"'
FAKE_FILES='' run 42; check "no files is 9" 9 $rc 'grep -q "\"files\":\[\]" <<<"$out" && grep -q "changes no files" <<<"$out"'
FAKE_FILES=$'README.md\t3\t0\nsrc/main.go\t1\t1' run 42; check "one source file among docs is 0" 0 $rc 'grep -q "\"eligible\":true" <<<"$out"'
FAKE_FILES=$'src/docs_builder.py\t3\t0' run 42; check "docs in a filename is not the docs dir" 0 $rc 'grep -q "\"eligible\":true" <<<"$out"'
FAKE_FILES=$'commands/review.md\t3\t0\nskills/x/SKILL.md\t1\t1' run 42; check "markdown outside docs is code, 0" 0 $rc 'grep -q "\"eligible\":true" <<<"$out" && grep -q "\"trivial\":false" <<<"$out"'
FAKE_FILES=$'README.md\t3\t0\nsub/CHANGELOG.md\t1\t1\nLICENSE\t1\t0' run 42; check "README/CHANGELOG/LICENSE only is 9" 9 $rc 'grep -q "\"trivial\":true" <<<"$out"'
FAKE_FILES=$'README.md\t3\t0' run 42 --allow-trivial; check "--allow-trivial makes a trivial PR eligible" 0 $rc 'grep -q "\"trivial\":true" <<<"$out" && grep -q "\"eligible\":true" <<<"$out" && grep -q "allow-trivial" <<<"$out"'
FAKE_FILES=$'src/a.py\t3\t0' run --allow-trivial 42; check "flag before the PR number works" 0 $rc 'grep -q "\"trivial\":false" <<<"$out"'

# JSON escaping: quotes, backslashes, tabs and newlines in title and body
FAKE_TITLE=$'fix: handle "quoted"\tpaths \\ twice' FAKE_BODY=$'Line one "quoted"\n\nSee `x\\y`\tdone\r' run 42
check "title and body are JSON-escaped" 0 $rc 'valid_json && grep -q "\"title\":\"fix: handle \\\\\"quoted\\\\\"\\\\tpaths \\\\\\\\ twice\"" <<<"$out" && grep -q "\"body\":\"Line one \\\\\"quoted\\\\\"\\\\n\\\\nSee \`x\\\\\\\\y\`\\\\tdone\\\\r\"" <<<"$out"'
if command -v python3 >/dev/null 2>&1; then
  decoded=$(python3 -I -c 'import json,sys; print(json.loads(sys.argv[1])["body"], end="")' "$out" 2>/dev/null); drc=$?
  check "body round-trips through a JSON parser" 0 $drc '[ "$decoded" = "$(printf "Line one \"quoted\"\n\nSee \`x\\\\y\`\tdone\r")" ]'
fi
FAKE_BODY='' run 42; check "empty body is an empty string" 0 $rc 'grep -q "\"body\":\"\"" <<<"$out"'
FAKE_BODY=$'only line' FAKE_FILES='' run 42; check "no files and a body still parse" 9 $rc 'grep -q "\"body\":\"only line\"" <<<"$out" && grep -q "\"files\":\[\]" <<<"$out"'

echo; echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
