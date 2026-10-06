#!/usr/bin/env bash
# sync.sh - Copy shared files into the plugins that use them, or check for drift.
#
# Plugins cannot read each other's files at runtime, so a file several plugins
# need is kept once under shared/<name>/ and copied into each plugin listed in
# shared/<name>/plugins (one plugin directory per line):
#   *.sh -> <plugin>/scripts/<file>
#   *.md -> <plugin>/references/<file>
#
# Usage: shared/sync.sh --check   exit 1 and list every copy that differs or is missing
#        shared/sync.sh --write   overwrite the copies from the canonical files

set -euo pipefail

mode=${1:-}
[ "$mode" = --check ] || [ "$mode" = --write ] || { echo "usage: shared/sync.sh --check | --write" >&2; exit 2; }

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
drift=0

for group in "$repo_root"/shared/*/; do
  manifest="$group/plugins"
  [ -f "$manifest" ] || continue
  while IFS= read -r plugin; do
    plugin=${plugin%%#*}
    plugin=${plugin//[[:space:]]/}
    [ -n "$plugin" ] || continue
    for src in "$group"*; do
      file=$(basename "$src")
      case $file in
        *.sh) dest="$repo_root/$plugin/scripts/$file" ;;
        *.md) dest="$repo_root/$plugin/references/$file" ;;
        *) continue ;;
      esac
      rel=${dest#"$repo_root/"}
      if [ "$mode" = --write ]; then
        mkdir -p "$(dirname "$dest")"
        cp -p "$src" "$dest"
        echo "synced $rel"
      elif ! cmp -s "$src" "$dest"; then
        [ -e "$dest" ] && echo "differs: $rel" || echo "missing: $rel"
        drift=1
      fi
    done
  done <"$manifest"
done

exit "$drift"
