#!/usr/bin/env bash
# Runs the code-review eval suite offline: a fake `gh` goes first on PATH (the
# run inherits PATH, nothing else from the shell), the nested-session
# variables are unset so the child claude behaves like a top-level one, and
# the scaffolds build each case's repo. Extra arguments go to
# `claude plugin eval`, e.g.:
#
#   code-review/evals/run.sh                          # every case, default model
#   code-review/evals/run.sh --model haiku --runs 1   # cheapest pass
#   code-review/evals/run.sh --case 'pipeline-dirty*' --keep-temp
set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
plugin=$(cd "$here/.." && pwd)

# The agent cannot read the eval directory, so the fake gh is copied out of it.
bin=$(mktemp -d)
trap 'rm -rf "$bin"' EXIT
cp "$here/bin/gh" "$bin/gh"
chmod +x "$bin/gh"

unset CLAUDECODE CLAUDE_CODE_ENTRYPOINT CHILD_SESSION

PATH="$bin:$PATH" claude plugin eval "$plugin" \
  --scaffold \
  --allow-tools Bash \
  --ablation none \
  --no-publish \
  --trust-plugin \
  "$@"
