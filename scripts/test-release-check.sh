#!/usr/bin/env bash
# Tests for scripts/release-check.sh and the .githooks/pre-commit gate.
#
# Each case builds a throwaway git repo shaped like this marketplace (one
# plugin "demo", a marketplace.json, a shared/ group), stages a change set, runs
# release-check.sh --staged and asserts on the exit code and the report. The
# last cases run a real `git commit` through .githooks/pre-commit.
#
# Usage: bash scripts/test-release-check.sh        (-v prints every report)

set -uo pipefail

scripts_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo_dir=$(cd "$scripts_dir/.." && pwd)
verbose=0
[ "${1:-}" = "-v" ] && verbose=1

pass=0
fail=0

make_fixture() {
  local dir
  dir=$(mktemp -d)
  git -C "$dir" init -q
  git -C "$dir" config user.email test@example.com
  git -C "$dir" config user.name test
  mkdir -p "$dir/.claude-plugin" "$dir/demo/.claude-plugin" "$dir/demo/commands" \
    "$dir/shared/tool" "$dir/scripts" "$dir/.githooks" "$dir/.claude/hooks"
  cat >"$dir/.claude-plugin/marketplace.json" <<'JSON'
{
  "name": "test-marketplace",
  "plugins": [
    {
      "name": "demo",
      "source": "./demo",
      "version": "1.0.0",
      "keywords": ["a", "b"]
    }
  ]
}
JSON
  printf '{ "name": "demo", "version": "1.0.0" }\n' >"$dir/demo/.claude-plugin/plugin.json"
  printf '# Changelog\n\n## [1.0.0] - 2026-01-01\n\n- first\n' >"$dir/demo/CHANGELOG.md"
  printf 'Say hi.\n' >"$dir/demo/commands/hello.md"
  printf '# Readme\n' >"$dir/README.md"
  printf 'rule\n' >"$dir/.claude/hooks/x.sh"
  cp "$repo_dir/shared/sync.sh" "$dir/shared/sync.sh"
  printf 'demo\n' >"$dir/shared/tool/plugins"
  printf 'echo v1\n' >"$dir/shared/tool/tool.sh"
  "$dir/shared/sync.sh" --write >/dev/null
  cp "$scripts_dir/release-check.sh" "$dir/scripts/release-check.sh"
  cp "$repo_dir/.githooks/pre-commit" "$dir/.githooks/pre-commit"
  git -C "$dir" add -A
  git -C "$dir" commit -qm init
  printf '%s' "$dir"
}

# bump <repo> <version>: plugin.json + marketplace.json, in place (sed, never re-serialized)
bump() {
  sed -i.bak "s/\"version\": \"[0-9.]*\"/\"version\": \"$2\"/" "$1/demo/.claude-plugin/plugin.json" "$1/.claude-plugin/marketplace.json"
  rm -f "$1/demo/.claude-plugin/plugin.json.bak" "$1/.claude-plugin/marketplace.json.bak"
}
add_heading() { printf '\n## [%s] - 2026-02-02\n\n- change\n' "$2" >>"$1/demo/CHANGELOG.md"; }

# run_case <name> <repo> <expected rc> <pattern that must appear> [pattern that must NOT appear] [env...]
# Runs release-check.sh --staged in <repo>; "" as a pattern skips that assertion.
run_case() {
  local name=$1 repo=$2 want_rc=$3 want=$4 unwanted=${5:-} out rc
  shift 5 2>/dev/null || shift $#
  out=$(cd "$repo" && env "$@" "$repo/scripts/release-check.sh" --staged 2>&1)
  rc=$?
  local ok=1
  [ "$rc" -eq "$want_rc" ] || ok=0
  [ -z "$want" ] || printf '%s' "$out" | grep -q -- "$want" || ok=0
  [ -z "$unwanted" ] || ! printf '%s' "$out" | grep -q -- "$unwanted" || ok=0
  if [ "$ok" = 1 ]; then
    pass=$((pass + 1)); echo "PASS  $name"
  else
    fail=$((fail + 1)); echo "FAIL  $name (exit $rc, wanted $want_rc)"
  fi
  if [ "$verbose" = 1 ] || [ "$ok" = 0 ]; then
    printf '      report: %s\n' "${out:-<empty>}"
  fi
}

# --- passing cases ------------------------------------------------------------
repo=$(make_fixture)
run_case "nothing staged passes" "$repo" 0 "" "release-check"

echo "edit" >>"$repo/demo/commands/hello.md"
bump "$repo" 1.0.1
add_heading "$repo" 1.0.1
git -C "$repo" add -A
run_case "plugin edit + bump + heading + mirror passes" "$repo" 0 "" "release-check"
git -C "$repo" commit -qm "1.0.1"

sed -i.bak 's/^## \[1.0.1\] - 2026-02-02$/## 1.0.2 (2026-02-02)/' "$repo/demo/CHANGELOG.md" && rm -f "$repo/demo/CHANGELOG.md.bak"
bump "$repo" 1.0.2
git -C "$repo" add -A
run_case "unbracketed heading style '## 1.0.2 (date)' passes" "$repo" 0 "" "changelog:"
git -C "$repo" commit -qm "1.0.2"

# The heading at the top of a long changelog, read from the index: a quiet grep
# that exits on the first match used to SIGPIPE `git show` and fail under pipefail.
{ echo "## 1.0.3 (2026-02-03)"; echo; for i in $(seq 1 20000); do echo "- filler line $i"; done; cat "$repo/demo/CHANGELOG.md"; } >"$repo/demo/CHANGELOG.new" && mv "$repo/demo/CHANGELOG.new" "$repo/demo/CHANGELOG.md"
bump "$repo" 1.0.3
git -C "$repo" add -A
run_case "heading at the top of a long staged changelog passes" "$repo" 0 "" "changelog:"
git -C "$repo" commit -qm "1.0.3"

echo "edit" >>"$repo/README.md"
echo "edit" >>"$repo/.claude/hooks/x.sh"
printf '# comment\n' >>"$repo/shared/tool/plugins"
git -C "$repo" add -A
run_case "root, .claude/ and shared/ files do not need a bump" "$repo" 0 "" "release-check"
rm -rf "$repo"

# --- (a) bump ------------------------------------------------------------------
repo=$(make_fixture)
echo "edit" >>"$repo/demo/commands/hello.md"
git -C "$repo" add -A
run_case "plugin edit without bump fails" "$repo" 1 "bump: demo/ has changes but demo/.claude-plugin/plugin.json still says 1.0.0"
run_case "bump violation does not also report the changelog" "$repo" 1 "1 violation(s)" "changelog:"

bump "$repo" 1.0.1
add_heading "$repo" 1.0.1
run_case "bump left in the working tree, not staged, still fails" "$repo" 1 "still says 1.0.0"
git -C "$repo" add -A
run_case "staging the bump clears it" "$repo" 0 "" "release-check"
rm -rf "$repo"

repo=$(make_fixture)
printf '{ "name": "demo", "version": "1.0.1", "description": "x" }\n' >"$repo/demo/.claude-plugin/plugin.json"
git -C "$repo" add -A
run_case "a plugin.json-only change still needs a bump (here: bumped, but no heading)" "$repo" 1 "changelog: demo/CHANGELOG.md has no heading for 1.0.1"
rm -rf "$repo"

repo=$(make_fixture)
printf '{ not json' >"$repo/demo/.claude-plugin/plugin.json"
git -C "$repo" add -A
run_case "unreadable plugin.json fails" "$repo" 1 'bump: demo/.claude-plugin/plugin.json has no readable "version"'
rm -rf "$repo"

# --- (b) changelog -------------------------------------------------------------
repo=$(make_fixture)
echo "edit" >>"$repo/demo/commands/hello.md"
bump "$repo" 1.0.1
git -C "$repo" add -A
run_case "bump without a CHANGELOG heading fails" "$repo" 1 "changelog: demo/CHANGELOG.md has no heading for 1.0.1"

printf '\n- mentions 1.0.1 in a bullet, not a heading\n' >>"$repo/demo/CHANGELOG.md"
git -C "$repo" add -A
run_case "the version in a bullet is not a heading" "$repo" 1 "no heading for 1.0.1"

add_heading "$repo" 1.0.10
git -C "$repo" add -A
run_case "a heading for 1.0.10 does not satisfy 1.0.1" "$repo" 1 "no heading for 1.0.1"

add_heading "$repo" 1.0.1
run_case "heading in the working tree but not staged still fails" "$repo" 1 "no heading for 1.0.1"
git -C "$repo" add -A
run_case "staging the heading clears it" "$repo" 0 "" "release-check"

git -C "$repo" rm -qf demo/CHANGELOG.md
run_case "a plugin without CHANGELOG.md fails" "$repo" 1 "changelog: demo/ has no CHANGELOG.md"
rm -rf "$repo"

# --- (c) marketplace -----------------------------------------------------------
repo=$(make_fixture)
echo "edit" >>"$repo/demo/commands/hello.md"
sed -i.bak 's/1.0.0/1.1.0/' "$repo/demo/.claude-plugin/plugin.json" && rm -f "$repo/demo/.claude-plugin/plugin.json.bak"
add_heading "$repo" 1.1.0
git -C "$repo" add -A
run_case "plugin.json bumped, registry stale fails" "$repo" 1 "marketplace: Version drift for 'demo': marketplace.json says '1.0.0', ./demo/.claude-plugin/plugin.json says '1.1.0'"

sed -i.bak 's/"1.0.0"/"1.1.0"/' "$repo/.claude-plugin/marketplace.json" && rm -f "$repo/.claude-plugin/marketplace.json.bak"
run_case "registry fixed on disk but not staged still fails" "$repo" 1 "Version drift for 'demo'"
git -C "$repo" add -A
run_case "staging the registry clears it" "$repo" 0 "" "release-check"
git -C "$repo" commit -qm "1.1.0"

sed -i.bak 's/"1.1.0"/"1.2.0"/' "$repo/.claude-plugin/marketplace.json" && rm -f "$repo/.claude-plugin/marketplace.json.bak"
git -C "$repo" add -A
run_case "registry ahead of plugin.json fails too" "$repo" 1 "marketplace.json says '1.2.0', ./demo/.claude-plugin/plugin.json says '1.1.0'"
git -C "$repo" checkout -q -- .claude-plugin/marketplace.json

printf '{ not json' >"$repo/.claude-plugin/marketplace.json"
git -C "$repo" add -A
run_case "malformed registry fails" "$repo" 1 "marketplace: .claude-plugin/marketplace.json is not valid JSON"
rm -rf "$repo"

# drift that predates the commit is reported even when the commit touches something else
repo=$(make_fixture)
sed -i.bak 's/"1.0.0"/"0.9.0"/' "$repo/.claude-plugin/marketplace.json" && rm -f "$repo/.claude-plugin/marketplace.json.bak"
git -C "$repo" add -A && git -C "$repo" commit -qm "drift slipped in"
echo "edit" >>"$repo/README.md"
git -C "$repo" add -A
run_case "pre-existing registry drift fails an unrelated commit" "$repo" 1 "Version drift for 'demo'"
rm -rf "$repo"

# --- (d) shared ------------------------------------------------------------------
repo=$(make_fixture)
printf 'echo v2\n' >"$repo/shared/tool/tool.sh"
git -C "$repo" add -A
run_case "canonical shared file edited without sync fails" "$repo" 1 "shared:   differs: demo/scripts/tool.sh"

"$repo/shared/sync.sh" --write >/dev/null
run_case "shared check reads the working tree: synced copy passes before it is staged" "$repo" 0 "" "shared:"
# the copy landed in demo/scripts/, so demo/ needs a bump: that is check (a), not (d)
bump "$repo" 1.0.1
add_heading "$repo" 1.0.1
git -C "$repo" add -A
run_case "synced copy staged with the plugin bump passes" "$repo" 0 "" "release-check"
rm -rf "$repo"

# --- new plugin -------------------------------------------------------------------
repo=$(make_fixture)
mkdir -p "$repo/fresh/.claude-plugin" "$repo/fresh/commands"
printf '{ "name": "fresh", "version": "0.1.0" }\n' >"$repo/fresh/.claude-plugin/plugin.json"
printf 'Hi.\n' >"$repo/fresh/commands/hi.md"
git -C "$repo" add -A
run_case "new plugin: no HEAD version passes (a) but still needs a CHANGELOG" "$repo" 1 "changelog: fresh/ has no CHANGELOG.md" "bump:"

printf '# Changelog\n\n## [0.1.0] - 2026-02-02\n' >"$repo/fresh/CHANGELOG.md"
git -C "$repo" add -A
run_case "new plugin with its CHANGELOG passes" "$repo" 0 "" "release-check"
rm -rf "$repo"

# --- several violations at once, bypass ---------------------------------------------
repo=$(make_fixture)
echo "edit" >>"$repo/demo/commands/hello.md"
sed -i.bak 's/"1.0.0"/"0.5.0"/' "$repo/.claude-plugin/marketplace.json" && rm -f "$repo/.claude-plugin/marketplace.json.bak"
printf 'echo v2\n' >"$repo/shared/tool/tool.sh"
git -C "$repo" add -A
run_case "all violations are listed together" "$repo" 1 "3 violation(s)"
run_case "SKIP_VERSION_CHECK=1 exits 0 and says so" "$repo" 0 "3 violation(s) ignored: SKIP_VERSION_CHECK=1 bypassed the gate" "" SKIP_VERSION_CHECK=1
run_case "the bypass still prints the violations" "$repo" 0 "bump: demo/ has changes" "" SKIP_VERSION_CHECK=1
run_case "SKIP_VERSION_CHECK=0 is not a bypass" "$repo" 1 "3 violation(s). Fix them" "" SKIP_VERSION_CHECK=0
rm -rf "$repo"

# --- --only -----------------------------------------------------------------------------
repo=$(make_fixture)
echo "edit" >>"$repo/demo/commands/hello.md"
sed -i.bak 's/"1.0.0"/"0.5.0"/' "$repo/.claude-plugin/marketplace.json" && rm -f "$repo/.claude-plugin/marketplace.json.bak"
git -C "$repo" add -A
out=$(cd "$repo" && scripts/release-check.sh --staged --only marketplace 2>&1); rc=$?
if [ "$rc" -eq 1 ] && printf '%s' "$out" | grep -q "Version drift" && ! printf '%s' "$out" | grep -q "bump:"; then
  pass=$((pass + 1)); echo "PASS  --only marketplace runs that check alone"
else
  fail=$((fail + 1)); echo "FAIL  --only marketplace runs that check alone (exit $rc)"; printf '      report: %s\n' "$out"
fi
rm -rf "$repo"

# --- the git hook, end to end ----------------------------------------------------------
repo=$(make_fixture)
git -C "$repo" config core.hooksPath .githooks
echo "edit" >>"$repo/demo/commands/hello.md"
git -C "$repo" add -A
if out=$(git -C "$repo" commit -qm "no bump" 2>&1); then
  fail=$((fail + 1)); echo "FAIL  pre-commit: commit without bump should be refused"; printf '      output: %s\n' "$out"
else
  if printf '%s' "$out" | grep -q "still says 1.0.0" && [ "$(git -C "$repo" rev-list --count HEAD)" = 1 ]; then
    pass=$((pass + 1)); echo "PASS  pre-commit: commit without bump is refused"
  else
    fail=$((fail + 1)); echo "FAIL  pre-commit: refused for the wrong reason"; printf '      output: %s\n' "$out"
  fi
fi

if out=$(cd "$repo" && SKIP_VERSION_CHECK=1 git commit -qm "bypassed" 2>&1) && [ "$(git -C "$repo" rev-list --count HEAD)" = 2 ] \
  && printf '%s' "$out" | grep -q "bypassed the gate"; then
  pass=$((pass + 1)); echo "PASS  pre-commit: SKIP_VERSION_CHECK=1 lets the commit through and says so"
else
  fail=$((fail + 1)); echo "FAIL  pre-commit: bypass"; printf '      output: %s\n' "$out"
fi

echo "edit" >>"$repo/demo/commands/hello.md"
bump "$repo" 1.0.1
add_heading "$repo" 1.0.1
git -C "$repo" add -A
if out=$(git -C "$repo" commit -qm "1.0.1" 2>&1) && [ "$(git -C "$repo" rev-list --count HEAD)" = 3 ]; then
  pass=$((pass + 1)); echo "PASS  pre-commit: a compliant commit goes through silently"
else
  fail=$((fail + 1)); echo "FAIL  pre-commit: compliant commit"; printf '      output: %s\n' "$out"
fi
rm -rf "$repo"

echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
