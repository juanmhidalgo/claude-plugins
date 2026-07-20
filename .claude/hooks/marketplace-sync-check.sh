#!/usr/bin/env bash
# PostToolUse hook: warn when a plugin's version in .claude-plugin/marketplace.json
# drifts from the version in that plugin's own .claude-plugin/plugin.json.
#
# The marketplace registry mirrors every plugin's version. Bumping plugin.json
# without updating the registry leaves installs pinned to a stale version.
# version-bump-check.sh enforces the bump itself; this enforces the mirror.
#
# Fires on edits to any plugin.json or to marketplace.json, and validates the
# WHOLE registry — so a drift introduced earlier surfaces on the next edit
# rather than persisting silently.
#
# Bypass with: SKIP_VERSION_CHECK=1 (shared with version-bump-check.sh).

set -euo pipefail

if [ "${SKIP_VERSION_CHECK:-}" = "1" ]; then
  exit 0
fi

input=$(cat)
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')

if [ -z "$file_path" ]; then
  exit 0
fi

repo_root=$(git -C "$(dirname "$file_path")" rev-parse --show-toplevel 2>/dev/null) || exit 0

case "$file_path" in
  "$repo_root"/*) rel_path="${file_path#"$repo_root/"}" ;;
  *) exit 0 ;;
esac

# Only react to the two file kinds that can introduce drift.
case "$rel_path" in
  .claude-plugin/marketplace.json) ;;
  */.claude-plugin/plugin.json) ;;
  *) exit 0 ;;
esac

marketplace="$repo_root/.claude-plugin/marketplace.json"
[ -f "$marketplace" ] || exit 0

# A malformed registry is a separate problem — report it and stop, since every
# comparison below would otherwise fail with a misleading "drift" message.
if ! jq empty "$marketplace" 2>/dev/null; then
  echo "[marketplace-sync-check] '.claude-plugin/marketplace.json' is not valid JSON — cannot verify versions." >&2
  exit 0
fi

drift=0
while IFS=$'\t' read -r name source registry_version; do
  [ -n "$name" ] || continue

  manifest="$repo_root/${source#./}/.claude-plugin/plugin.json"
  [ -f "$manifest" ] || continue
  jq empty "$manifest" 2>/dev/null || continue

  actual_version=$(jq -r '.version // empty' "$manifest")
  [ -n "$actual_version" ] || continue

  if [ "$actual_version" != "$registry_version" ]; then
    echo "[marketplace-sync-check] Version drift for '$name': marketplace.json says '$registry_version', $source/.claude-plugin/plugin.json says '$actual_version'." >&2
    drift=1
  fi
done < <(jq -r '.plugins[]? | [.name // "", .source // "", .version // ""] | @tsv' "$marketplace")

if [ "$drift" = "1" ]; then
  echo "[marketplace-sync-check]   Update marketplace.json so each version mirrors its plugin.json." >&2
  echo "[marketplace-sync-check]   Edit the version lines in place — re-serializing the file reflows every inline array." >&2
  echo "[marketplace-sync-check]   To bypass: export SKIP_VERSION_CHECK=1" >&2
fi

exit 0
