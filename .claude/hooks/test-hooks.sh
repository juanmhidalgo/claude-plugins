#!/usr/bin/env bash
# Tests for the two PostToolUse advisory hooks in this directory.
#
# Each case builds a throwaway git repo shaped like this marketplace, pipes a
# realistic PostToolUse payload into a hook, and asserts on stdout. The hooks
# must speak JSON on stdout (hookSpecificOutput.additionalContext): stderr on
# exit 0 never reaches Claude, so a warning that only goes there is invisible.
#
# Usage: bash .claude/hooks/test-hooks.sh        (-v prints every hook's stdout)

set -uo pipefail

hooks_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
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
  mkdir -p "$dir/.claude-plugin" "$dir/demo/.claude-plugin" "$dir/demo/commands"
  cat >"$dir/.claude-plugin/marketplace.json" <<'JSON'
{
  "name": "test-marketplace",
  "plugins": [
    { "name": "demo", "source": "./demo", "version": "1.0.0" }
  ]
}
JSON
  printf '{ "name": "demo", "version": "1.0.0" }\n' >"$dir/demo/.claude-plugin/plugin.json"
  printf '# Changelog\n' >"$dir/demo/CHANGELOG.md"
  printf 'Say hi.\n' >"$dir/demo/commands/hello.md"
  printf '# Readme\n' >"$dir/README.md"
  git -C "$dir" add -A
  git -C "$dir" commit -qm init
  printf '%s' "$dir"
}

payload() {
  jq -n --arg fp "$1" '{
    session_id: "test", hook_event_name: "PostToolUse", tool_name: "Edit",
    tool_input: { file_path: $fp, old_string: "a", new_string: "b" },
    tool_response: { filePath: $fp, success: true }
  }'
}

# run_case <name> <hook> <file_path> <expect: silent|warn> [grep pattern] [env...]
run_case() {
  local name=$1 hook=$2 file=$3 expect=$4 pattern=${5:-} out rc
  shift 5 2>/dev/null || shift $#
  out=$(payload "$file" | env "$@" "$hooks_dir/$hook" 2>/dev/null)
  rc=$?
  local ok=1
  [ "$rc" -eq 0 ] || ok=0
  if [ "$expect" = silent ]; then
    [ -z "$out" ] || ok=0
  else
    printf '%s' "$out" | jq -e '.hookSpecificOutput.hookEventName == "PostToolUse"
      and (.hookSpecificOutput.additionalContext | type == "string")' >/dev/null 2>&1 || ok=0
    [ -z "$pattern" ] || printf '%s' "$out" | jq -r '.hookSpecificOutput.additionalContext' \
      | grep -q -- "$pattern" || ok=0
  fi
  if [ "$ok" = 1 ]; then
    pass=$((pass + 1)); echo "PASS  $name"
  else
    fail=$((fail + 1)); echo "FAIL  $name (exit $rc)"
  fi
  if [ "$verbose" = 1 ] || [ "$ok" = 0 ]; then
    printf '      stdout: %s\n' "${out:-<empty>}"
  fi
}

# --- version-bump-check.sh -------------------------------------------------
repo=$(make_fixture)
echo "edit" >>"$repo/demo/commands/hello.md"
run_case "version-bump: plugin edit without bump warns" \
  version-bump-check.sh "$repo/demo/commands/hello.md" warn "plugin.json' is unchanged"
run_case "version-bump: SKIP_VERSION_CHECK=1 silences it" \
  version-bump-check.sh "$repo/demo/commands/hello.md" silent "" SKIP_VERSION_CHECK=1

sed -i.bak 's/1.0.0/1.0.1/' "$repo/demo/.claude-plugin/plugin.json" && rm -f "$repo/demo/.claude-plugin/plugin.json.bak"
echo "- 1.0.1 change" >>"$repo/demo/CHANGELOG.md"
run_case "version-bump: plugin edit with bump + changelog is silent" \
  version-bump-check.sh "$repo/demo/commands/hello.md" silent ""

echo "edit" >>"$repo/README.md"
run_case "version-bump: non-plugin file is silent" \
  version-bump-check.sh "$repo/README.md" silent ""
rm -rf "$repo"

# --- marketplace-sync-check.sh ---------------------------------------------
repo=$(make_fixture)
sed -i.bak 's/1.0.0/1.1.0/' "$repo/demo/.claude-plugin/plugin.json" && rm -f "$repo/demo/.claude-plugin/plugin.json.bak"
run_case "marketplace-sync: plugin.json bumped, registry stale warns" \
  marketplace-sync-check.sh "$repo/demo/.claude-plugin/plugin.json" warn "Version drift for 'demo'"
run_case "marketplace-sync: SKIP_VERSION_CHECK=1 silences it" \
  marketplace-sync-check.sh "$repo/demo/.claude-plugin/plugin.json" silent "" SKIP_VERSION_CHECK=1

sed -i.bak 's/"1.0.0"/"1.1.0"/' "$repo/.claude-plugin/marketplace.json" && rm -f "$repo/.claude-plugin/marketplace.json.bak"
run_case "marketplace-sync: registry mirrors plugin.json is silent" \
  marketplace-sync-check.sh "$repo/demo/.claude-plugin/plugin.json" silent ""
run_case "marketplace-sync: non-plugin file is silent" \
  marketplace-sync-check.sh "$repo/README.md" silent ""

printf '{ not json' >"$repo/.claude-plugin/marketplace.json"
run_case "marketplace-sync: malformed registry warns" \
  marketplace-sync-check.sh "$repo/.claude-plugin/marketplace.json" warn "not valid JSON"
rm -rf "$repo"

echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
