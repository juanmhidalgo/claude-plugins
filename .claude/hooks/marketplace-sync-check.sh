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
# rather than persisting silently. The comparison itself is the `marketplace`
# check of scripts/release-check.sh (the pre-commit gate); this hook only
# decides when to run it and wraps the result as an advisory.
#
# Bypass with: SKIP_VERSION_CHECK=1 (shared with version-bump-check.sh).

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

# Only react to the two file kinds that can introduce drift.
case "$rel_path" in
  .claude-plugin/marketplace.json) ;;
  */.claude-plugin/plugin.json) ;;
  *) exit 0 ;;
esac

# The gate's script lives next to this hook in the same checkout; it is run with
# the edited file's repo as cwd so the test fixtures exercise it too.
release_check="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../scripts" && pwd)/release-check.sh"
[ -x "$release_check" ] || exit 0

drift=0
while IFS= read -r line; do
  case "$line" in
    "[release-check] marketplace: "*)
      line=${line#"[release-check] marketplace: "}
      note "[marketplace-sync-check] $line"
      case "$line" in "Version drift for "*) drift=1 ;; esac
      ;;
  esac
done < <(cd "$repo_root" && "$release_check" --tree --only marketplace 2>/dev/null)

if [ "$drift" = "1" ]; then
  note "[marketplace-sync-check]   Update marketplace.json so each version mirrors its plugin.json."
  note "[marketplace-sync-check]   Edit the version lines in place — re-serializing the file reflows every inline array."
  note "[marketplace-sync-check]   To bypass: export SKIP_VERSION_CHECK=1"
fi

emit_advisory

exit 0
