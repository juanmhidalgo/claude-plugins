#!/usr/bin/env bash
# release-check.sh - the release gate for this marketplace.
#
# Checks the rules of CLAUDE.md <critical_rules> deterministically and reports
# every violation at once:
#   bump         a plugin directory with changes bumps the version in its
#                .claude-plugin/plugin.json (a brand-new plugin has nothing to bump)
#   changelog    the plugin's CHANGELOG.md has a heading for that new version,
#                "## [1.2.3] - 2026-01-01" or "## 1.2.3 (2026-01-01)"
#   marketplace  every version in .claude-plugin/marketplace.json mirrors the
#                plugin.json of its source
#   shared       shared/sync.sh --check reports no drift between shared/<name>/
#                and the plugin copies
#
# A plugin directory is a top-level directory with .claude-plugin/plugin.json.
# Files anywhere else (repo root, shared/, .claude/, tests/, scripts/) never
# trigger the bump and changelog checks.
#
# Usage: scripts/release-check.sh --staged      what `git commit` would record (the index)
#        scripts/release-check.sh [--tree]      the working tree against HEAD (default)
#        ... --only <check> [--only <check>]    a subset: bump, changelog, marketplace, shared
#
# Exit 1 with the violations listed, 0 when clean, 2 on usage or missing tools.
# SKIP_VERSION_CHECK=1 (the same variable the advisory hooks honor) bypasses the
# gate: the violations are still printed, the bypass is announced, the exit is 0.
# .githooks/pre-commit runs `--staged`; enable it once per clone with
# `git config core.hooksPath .githooks`.

set -uo pipefail

usage() {
  sed -n '2,/^$/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

mode=tree
only=()
while [ $# -gt 0 ]; do
  case $1 in
    --staged) mode=staged ;;
    --tree) mode=tree ;;
    --only)
      [ -n "${2:-}" ] || { echo "release-check: --only needs a check name" >&2; exit 2; }
      only+=("$2"); shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "release-check: unknown argument '$1'" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

command -v jq >/dev/null 2>&1 || { echo "release-check: jq is required" >&2; exit 2; }
repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || { echo "release-check: not inside a git repository" >&2; exit 2; }
cd "$repo_root" || exit 2

have_head=1
git rev-parse -q --verify HEAD >/dev/null 2>&1 || have_head=0

violations=0
report() { printf '[release-check] %s\n' "$1"; }
fail() { violations=$((violations + 1)); report "$1"; }
wants() {
  [ ${#only[@]} -eq 0 ] && return 0
  local c
  for c in "${only[@]}"; do [ "$c" = "$1" ] && return 0; done
  return 1
}

# --- where the files come from -------------------------------------------
# In --staged mode every file is read from the index (`git show :path`), so a
# bump that sits in the working tree but was not `git add`ed does not count:
# the commit would not carry it. In --tree mode files are read from disk.
content() {
  if [ "$mode" = staged ]; then git show ":$1" 2>/dev/null; else cat "$1" 2>/dev/null; fi
}
exists() {
  if [ "$mode" = staged ]; then git cat-file -e ":$1" 2>/dev/null; else [ -f "$1" ]; fi
}
head_content() { [ "$have_head" = 1 ] && git show "HEAD:$1" 2>/dev/null; }
head_exists() { [ "$have_head" = 1 ] && git cat-file -e "HEAD:$1" 2>/dev/null; }
changed_files() {
  if [ "$mode" = staged ]; then
    git diff --cached --name-only
  else
    {
      [ "$have_head" = 1 ] && git diff --name-only HEAD
      git ls-files --others --exclude-standard
    } | sort -u
  fi
}
version_of() { jq -r '.version // empty' 2>/dev/null; }

is_plugin() { exists "$1/.claude-plugin/plugin.json" || head_exists "$1/.claude-plugin/plugin.json"; }

# --- bump + changelog, per plugin with changes ----------------------------
check_plugin() {
  local plugin=$1 manifest="$1/.claude-plugin/plugin.json" changelog="$1/CHANGELOG.md" new old
  # plugin.json gone from the change set: the whole plugin is being removed.
  exists "$manifest" || return 0
  new=$(content "$manifest" | version_of)
  if [ -z "$new" ]; then
    fail "bump: $manifest has no readable \"version\" (invalid JSON or missing field)."
    return 0
  fi
  if head_exists "$manifest"; then
    old=$(head_content "$manifest" | version_of)
    if [ "$new" = "$old" ]; then
      wants bump && fail "bump: $plugin/ has changes but $manifest still says $new, the version at HEAD. Bump it (patch/minor/major) and add a CHANGELOG entry."
      # Until there is a new version there is no heading to look for.
      return 0
    fi
  fi
  wants changelog || return 0
  if ! exists "$changelog"; then
    fail "changelog: $plugin/ has no CHANGELOG.md; add one with a heading for $new."
    return 0
  fi
  local ver_re
  ver_re=$(printf '%s' "$new" | sed 's/[.[\*^$]/\\&/g')
  # Not `grep -q`: with pipefail, a quiet grep that exits on the first match
  # sends SIGPIPE to `git show` and the pipeline fails for a heading it found.
  if ! content "$changelog" | grep -E "^#+[[:space:]]+\[?v?${ver_re}\]?([[:space:]]|$)" >/dev/null; then
    fail "changelog: $changelog has no heading for $new (expected '## [$new] - YYYY-MM-DD' or '## $new (YYYY-MM-DD)')."
  fi
}

if wants bump || wants changelog; then
  while IFS= read -r plugin; do
    [ -n "$plugin" ] || continue
    is_plugin "$plugin" && check_plugin "$plugin"
  done < <(changed_files | grep '/' | cut -d/ -f1 | sort -u)
fi

# --- marketplace mirrors every plugin.json --------------------------------
# Compares the registry with every plugin it lists, not only the plugins with
# changes, so a drift introduced earlier surfaces on the next commit.
check_marketplace() {
  local reg=.claude-plugin/marketplace.json data name source reg_ver manifest actual
  exists "$reg" || return 0
  data=$(content "$reg")
  if ! printf '%s' "$data" | jq empty 2>/dev/null; then
    fail "marketplace: $reg is not valid JSON — cannot verify versions."
    return 0
  fi
  while IFS=$'\t' read -r name source reg_ver; do
    [ -n "$name" ] || continue
    manifest="${source#./}/.claude-plugin/plugin.json"
    exists "$manifest" || continue
    actual=$(content "$manifest" | version_of)
    [ -n "$actual" ] || continue
    [ "$actual" = "$reg_ver" ] || fail "marketplace: Version drift for '$name': marketplace.json says '$reg_ver', $source/.claude-plugin/plugin.json says '$actual'."
  done < <(printf '%s' "$data" | jq -r '.plugins[]? | [.name // "", .source // "", .version // ""] | @tsv')
}
wants marketplace && check_marketplace

# --- shared files in sync with their plugin copies ------------------------
# shared/sync.sh compares the files on disk, so this check looks at the working
# tree even in --staged mode: the index is not consulted here. A drift that was
# fixed on disk but not staged passes, and vice versa; `git add` the copies
# together with the canonical file and the two views agree.
check_shared() {
  local sync=shared/sync.sh drift line
  [ -x "$sync" ] || return 0
  drift=$("$sync" --check 2>&1) && return 0
  fail "shared: shared files are out of sync with their plugin copies (run shared/sync.sh --write, then stage the copies):"
  while IFS= read -r line; do
    [ -n "$line" ] && report "shared:   $line"
  done <<<"$drift"
}
wants shared && check_shared

# --- verdict ----------------------------------------------------------------
[ "$violations" -gt 0 ] || exit 0
if [ "${SKIP_VERSION_CHECK:-}" = "1" ]; then
  report "$violations violation(s) ignored: SKIP_VERSION_CHECK=1 bypassed the gate."
  exit 0
fi
report "$violations violation(s). Fix them, or bypass once with SKIP_VERSION_CHECK=1 git commit ..."
exit 1
