#!/usr/bin/env bash
# PostToolUse hook: warn when a plugin file is edited without bumping
# the plugin's plugin.json version or updating its CHANGELOG.md.
#
# Repo standard: every plugin modification must bump the plugin.json version
# (semver) and update CHANGELOG.md. See CLAUDE.md <critical_rules>.
#
# Bypass with: SKIP_VERSION_CHECK=1 (e.g. for in-progress edits).

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

if [[ ! "$rel_path" =~ ^([^/]+)/(commands|agents|skills|scripts)/ ]]; then
  exit 0
fi

plugin="${BASH_REMATCH[1]}"
manifest="$repo_root/$plugin/.claude-plugin/plugin.json"
changelog="$repo_root/$plugin/CHANGELOG.md"

if [ ! -f "$manifest" ]; then
  exit 0
fi

manifest_changed=$(git -C "$repo_root" diff --name-only HEAD -- "$plugin/.claude-plugin/plugin.json" 2>/dev/null || true)
changelog_changed=$(git -C "$repo_root" diff --name-only HEAD -- "$plugin/CHANGELOG.md" 2>/dev/null || true)

warned=0
if [ -z "$manifest_changed" ]; then
  echo "[version-bump-check] Edited '$rel_path' but '$plugin/.claude-plugin/plugin.json' is unchanged." >&2
  echo "[version-bump-check]   Bump the version (patch/minor/major) per CLAUDE.md <critical_rules>." >&2
  warned=1
fi

if [ -z "$changelog_changed" ] && [ -f "$changelog" ]; then
  echo "[version-bump-check] Edited '$rel_path' but '$plugin/CHANGELOG.md' is unchanged." >&2
  echo "[version-bump-check]   Add a CHANGELOG entry describing the change." >&2
  warned=1
fi

if [ "$warned" = "1" ]; then
  echo "[version-bump-check]   To bypass: export SKIP_VERSION_CHECK=1" >&2
fi

exit 0
