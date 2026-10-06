#!/bin/bash
# review-pane.sh - Run a review command in a fresh Claude Code session in a sibling Herdr pane
#
# Usage:
#   review-pane.sh check
#       Exit 0 when running inside a Herdr pane with a reachable server.
#   review-pane.sh open <name-hint> <report-path>
#       Split a sibling pane (focus stays here), start `claude` in it, print
#       {"pane_id": ..., "agent": ...}. The report's directory is passed to the
#       new session with --add-dir so it can write the report there.
#   review-pane.sh run <agent> <report-path> <command...>
#       Submit <command> to the agent, wait until it settles (approval prompts
#       in the pane are waited through, with a Herdr notification), then ask it
#       to save what it presented to <report-path>. Blocks until done: run it
#       in the background. Prints the report path on success.
#
# Exit codes:
#   0 ok | 2 usage | 10 not inside Herdr | 11 pane split failed
#   12 agent did not start | 13 prompt not taken | 14 no report written

set -euo pipefail

die() { local code=$1; shift; echo "review-pane: $*" >&2; exit "$code"; }

require_herdr() {
  [ "${HERDR_ENV:-}" = 1 ] || die 10 "not running inside a Herdr pane (HERDR_ENV != 1)"
  command -v herdr >/dev/null || die 10 "herdr not found in PATH"
  command -v jq >/dev/null || die 10 "jq not found in PATH"
  herdr pane current --current >/dev/null 2>&1 || die 10 "Herdr server not reachable from this pane"
}

# Wide pane -> split right; narrow or tall -> split down. Terminal cells are
# about twice as tall as wide, so width >= 2*height is visually landscape.
split_direction() {
  local rect width height
  rect=$(herdr pane layout --current | jq -c --arg p "$HERDR_PANE_ID" \
    '.result.layout.panes[] | select(.pane_id == $p) | .rect')
  width=$(jq -r '.width // 0' <<<"$rect")
  height=$(jq -r '.height // 0' <<<"$rect")
  if [ "$width" -ge 160 ] && [ "$width" -ge $((height * 2)) ]; then
    echo right
  else
    echo down
  fi
}

# Agent names must match [a-z][a-z0-9_-]{0,31} and be unique among live agents.
unique_agent_name() {
  local base name n=2
  base=$(printf 'review-%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_-' '-' | cut -c1-29)
  base=${base%-}
  name=$base
  while herdr agent get "$name" >/dev/null 2>&1; do
    name="${base}-${n}"
    n=$((n + 1))
  done
  echo "$name"
}

agent_status() {
  herdr agent get "$1" 2>/dev/null | jq -r '.result.agent.agent_status // "gone"'
}

# Wait until the agent is ready for input. A blocked agent is waiting on the
# user in its pane: notify once and keep waiting for them to answer it.
wait_settled() {
  local agent=$1 status notified=0
  while :; do
    herdr agent wait "$agent" >/dev/null 2>&1 || true
    status=$(agent_status "$agent")
    case $status in
      idle|done) return 0 ;;
      gone) die 13 "agent '$agent' is no longer running" ;;
      blocked)
        if [ "$notified" = 0 ]; then
          herdr notification show "Review needs you" \
            --body "Agent '$agent' is waiting on an approval in its pane" --sound request >/dev/null 2>&1 || true
          notified=1
        fi
        herdr agent wait "$agent" --until idle --until done --until working >/dev/null 2>&1 || true
        ;;
      *) herdr agent wait "$agent" --until idle --until done --until blocked >/dev/null 2>&1 || true ;;
    esac
  done
}

cmd_open() {
  [ $# -eq 2 ] || die 2 "usage: review-pane.sh open <name-hint> <report-path>"
  require_herdr
  local hint=$1 report=$2 report_dir direction pane agent out
  report_dir=$(dirname "$report")
  mkdir -p "$report_dir"
  direction=$(split_direction)

  # The pane's shell comes from the Herdr server, not from this process, so it
  # does not inherit CLAUDECODE and the new claude starts as a top-level session.
  out=$(herdr pane split --current --direction "$direction" --cwd "$PWD" --no-focus 2>&1) \
    || die 11 "pane split failed: $out"
  pane=$(jq -r '.result.pane.pane_id' <<<"$out")
  [ -n "$pane" ] && [ "$pane" != null ] || die 11 "pane split returned no pane id: $out"

  agent=$(unique_agent_name "$hint")
  if ! out=$(herdr agent start "$agent" --kind claude --pane "$pane" --timeout 60000 \
      -- --add-dir "$report_dir" 2>&1); then
    die 12 "agent did not start in pane $pane (left open for inspection): $out"
  fi
  jq -n --arg pane "$pane" --arg agent "$agent" --arg direction "$direction" \
    '{pane_id: $pane, agent: $agent, direction: $direction}'
}

cmd_run() {
  [ $# -ge 3 ] || die 2 "usage: review-pane.sh run <agent> <report-path> <command...>"
  require_herdr
  local agent=$1 report=$2 out
  shift 2
  local command="$*"

  rm -f "$report"
  out=$(herdr agent prompt "$agent" "$command" --wait 2>&1) || die 13 "review prompt not taken: $out"
  wait_settled "$agent"

  out=$(herdr agent prompt "$agent" \
    "Write the complete review you just presented to $report as Markdown, exactly as presented: every finding with its severity, file:line, failure scenario and verification line, plus any summary table. Do not re-run or change the review. Reply with only the path." \
    --wait 2>&1) || die 13 "save prompt not taken: $out"
  wait_settled "$agent"

  [ -s "$report" ] || die 14 "agent '$agent' settled but $report is missing or empty"
  echo "$report"
}

case ${1:-} in
  check) shift; require_herdr ;;
  open) shift; cmd_open "$@" ;;
  run) shift; cmd_run "$@" ;;
  *) die 2 "usage: review-pane.sh check | open <name-hint> <report-path> | run <agent> <report-path> <command...>" ;;
esac
