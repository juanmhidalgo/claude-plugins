#!/usr/bin/env bash
# PostToolUse hook: warn when a plugin's copy of a shared file drifts from its
# canonical version under shared/<name>/.
#
# Plugins cannot read each other's files at runtime, so shared/sync.sh copies
# each shared file into every plugin that lists it. Editing the canonical file
# without syncing leaves stale copies; editing a copy directly gets overwritten
# by the next sync. Fires on edits under shared/ or to any synced copy, and
# runs the full check, so drift introduced earlier surfaces on the next edit.
#
# Bypass with: SKIP_VERSION_CHECK=1 (shared with the other advisory hooks).

set -euo pipefail

# PostToolUse stderr on exit 0 never reaches Claude: advisories go out as JSON.
emit_advisory() {
  [ -n "$1" ] || return 0
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$1" | jq -Rs '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:.}}'
  else
    printf '%s' "$1" >&2
  fi
}

[ "${SKIP_VERSION_CHECK:-}" = "1" ] && exit 0

input=$(cat)
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')
[ -n "$file_path" ] || exit 0

repo_root=$(git -C "$(dirname "$file_path")" rev-parse --show-toplevel 2>/dev/null) || exit 0
case "$file_path" in
  "$repo_root"/*) rel_path="${file_path#"$repo_root/"}" ;;
  *) exit 0 ;;
esac

sync="$repo_root/shared/sync.sh"
[ -x "$sync" ] || exit 0

# React to the canonical files, and to a plugin copy of any of them.
relevant=0
case "$rel_path" in
  shared/*) relevant=1 ;;
  */scripts/*|*/references/*)
    name=$(basename "$rel_path")
    for canonical in "$repo_root"/shared/*/"$name"; do
      [ -e "$canonical" ] && relevant=1
    done
    ;;
esac
[ "$relevant" = 1 ] || exit 0

if drift=$("$sync" --check 2>&1); then
  exit 0
fi

msg="[shared-sync-check] Shared files are out of sync with their plugin copies:"$'\n'
while IFS= read -r line; do
  msg+="[shared-sync-check]   $line"$'\n'
done <<<"$drift"
case "$rel_path" in
  shared/*) msg+="[shared-sync-check]   Run shared/sync.sh --write to copy the canonical files into the plugins."$'\n' ;;
  *) msg+="[shared-sync-check]   '$rel_path' is a synced copy: make the change in shared/ instead, then run shared/sync.sh --write (a direct edit is overwritten by the next sync)."$'\n' ;;
esac
msg+="[shared-sync-check]   To bypass: export SKIP_VERSION_CHECK=1"$'\n'
emit_advisory "$msg"
exit 0
