#!/usr/bin/env bash
# PostToolUse hook: warn when a plugin file is edited without bumping
# the plugin's plugin.json version or updating its CHANGELOG.md.
#
# Repo standard: every plugin modification must bump the plugin.json version
# (semver) and update CHANGELOG.md. See CLAUDE.md <critical_rules>.
#
# Bypass with: SKIP_VERSION_CHECK=1 (e.g. for in-progress edits).

set -euo pipefail

# A PostToolUse hook's stderr with exit 0 reaches only the debug log -- it is never
# shown to Claude -- so an advisory has to come back as JSON on stdout. Verified on
# Claude Code 2.1.274: the hook runs, but its stderr never enters the model's context.
advisory=""
note() { advisory="${advisory}$1"$'\n'; }
emit_advisory() {
  [ -n "$advisory" ] || return 0
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$advisory" \
      | jq -Rs '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:.}}'
  else
    # No jq: fall back to the old channel rather than emitting malformed JSON.
    printf '%s' "$advisory" >&2
  fi
}

if [ "${SKIP_VERSION_CHECK:-}" = "1" ]; then
  emit_advisory
  exit 0
fi

input=$(cat)
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')

if [ -z "$file_path" ]; then
  emit_advisory
  exit 0
fi

repo_root=$(git -C "$(dirname "$file_path")" rev-parse --show-toplevel 2>/dev/null) || exit 0

case "$file_path" in
  "$repo_root"/*) rel_path="${file_path#"$repo_root/"}" ;;
  *) exit 0 ;;
esac

if [[ ! "$rel_path" =~ ^([^/]+)/(commands|agents|skills|scripts)/ ]]; then
  emit_advisory
  exit 0
fi

plugin="${BASH_REMATCH[1]}"
manifest="$repo_root/$plugin/.claude-plugin/plugin.json"
changelog="$repo_root/$plugin/CHANGELOG.md"

if [ ! -f "$manifest" ]; then
  emit_advisory
  exit 0
fi

manifest_changed=$(git -C "$repo_root" diff --name-only HEAD -- "$plugin/.claude-plugin/plugin.json" 2>/dev/null || true)
changelog_changed=$(git -C "$repo_root" diff --name-only HEAD -- "$plugin/CHANGELOG.md" 2>/dev/null || true)

warned=0
if [ -z "$manifest_changed" ]; then
  note "[version-bump-check] Edited '$rel_path' but '$plugin/.claude-plugin/plugin.json' is unchanged."
  note "[version-bump-check]   Bump the version (patch/minor/major) per CLAUDE.md <critical_rules>."
  warned=1
fi

if [ -z "$changelog_changed" ] && [ -f "$changelog" ]; then
  note "[version-bump-check] Edited '$rel_path' but '$plugin/CHANGELOG.md' is unchanged."
  note "[version-bump-check]   Add a CHANGELOG entry describing the change."
  warned=1
fi

if [ "$warned" = "1" ]; then
  note "[version-bump-check]   To bypass: export SKIP_VERSION_CHECK=1"
fi

emit_advisory

exit 0
