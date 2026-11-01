#!/bin/bash
# tree-hash.sh - Print one hash of the working tree's full state: index, unstaged
# changes, and the contents of untracked files. Commands that run the
# code-review:review workflow take it before and after each run; a different hash
# means a reviewer changed the tree.
#
# Usage: tree-hash.sh
# Read-only. Exits 1 outside a git repository.

set -euo pipefail
git rev-parse --git-dir >/dev/null 2>&1 || { echo "not a git repository" >&2; exit 1; }

{
  git diff --cached --binary
  git diff --binary
  git status --porcelain --untracked-files=all
  git ls-files --others --exclude-standard -z | xargs -0 -r git hash-object --
} | git hash-object --stdin
