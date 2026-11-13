#!/usr/bin/env bash
# agent-bash-guard.sh - PreToolUse entry point for agent_bash_guard.py.
#
# Canonical copy: shared/agent-bash-guard/ (shared/sync.sh copies it into each
# plugin's scripts/). Runs on every Bash call of every session that has the
# plugin, so the common case — a call from the main session, whose hook input
# has no agent_type — exits here without starting Python.
#
# Usage (hooks.json): bash agent-bash-guard.sh <plugin root>   (hook JSON on stdin)
input=$(cat)
case $input in
  *'"agent_type"'*) ;;
  *) exit 0 ;;
esac
[ "${AGENT_BASH_GUARD:-audit}" = off ] && exit 0
printf '%s' "$input" | python3 -B "$(dirname "${BASH_SOURCE[0]}")/agent_bash_guard.py" "${1:-}"
exit 0
