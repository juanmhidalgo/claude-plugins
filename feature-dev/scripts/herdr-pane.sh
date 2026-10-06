#!/bin/bash
# herdr-pane.sh - Run a plugin command in a fresh Claude Code session in another Herdr pane
#
# Canonical copy: shared/herdr-pane/herdr-pane.sh. Every plugin's
# scripts/herdr-pane.sh is a synced copy — edit the canonical one, then run
# shared/sync.sh.
#
# Usage:
#   herdr-pane.sh check
#       Exit 0 when running inside a Herdr pane with a reachable server.
#
#   herdr-pane.sh status
#       Print "inside" or "outside" (Herdr), always exit 0. For context blocks.
#
#   herdr-pane.sh open <name> <report-path|-> [--worktree <branch> | --worktree-staged]
#       Start `claude` in a new pane and print JSON:
#         {pane_id, agent, direction, workspace_id, worktree_path, worktree_branch, base_tree}
#       Without a flag: a sibling pane in this tab, on this checkout.
#       --worktree <branch>: a new Herdr worktree workspace with <branch> checked
#         out (the local branch, or one created from origin/<branch>).
#       --worktree-staged: a new Herdr worktree at HEAD on a temporary branch,
#         carrying this checkout's staged diff; base_tree is the staged tree, for
#         staged-patch. Unstaged changes are not carried.
#       The report's directory is passed to the new session with --add-dir.
#
#   herdr-pane.sh run <agent> <report-path> <command...>
#       Submit <command>, wait until it settles (approval prompts and questions
#       in the pane are waited through, with a Herdr notification), then ask the
#       session to save what it presented to <report-path>. Blocks until done:
#       run it in the background. Prints the report path on success.
#
#   herdr-pane.sh send <agent> <command...>
#       Submit <command> and return once the agent has started on it (handoff).
#
#   herdr-pane.sh staged-patch <worktree-path> <base-tree> <patch-path>
#       Write the diff between base-tree and the worktree's index to patch-path.
#       Prints "empty" when the session staged nothing new.
#
#   herdr-pane.sh cleanup <workspace-id> [--force] [--delete-branch <branch>]
#       Remove a worktree workspace this script opened (its pane closes).
#
# Exit codes:
#   0 ok | 2 usage | 10 not inside Herdr | 11 pane or worktree not created
#   12 agent did not start | 13 prompt not taken | 14 no report written
#   15 branch already checked out elsewhere | 16 nothing staged | 17 git failed

set -euo pipefail

die() { local code=$1; shift; echo "herdr-pane: $*" >&2; exit "$code"; }

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
  base=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_-' '-' | sed 's/^[^a-z]*//' | cut -c1-29)
  base=${base%-}
  [ -n "$base" ] || base=pane
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
          herdr notification show "Pane '$agent' needs you" \
            --body "It is waiting on an approval or a question in its pane" --sound request >/dev/null 2>&1 || true
          notified=1
        fi
        herdr agent wait "$agent" --until idle --until "done" --until working >/dev/null 2>&1 || true
        ;;
      *) herdr agent wait "$agent" --until idle --until "done" --until blocked >/dev/null 2>&1 || true ;;
    esac
  done
}

# Create a Herdr worktree workspace; prints the create response.
create_worktree() {
  local out
  out=$(herdr worktree create --cwd "$PWD" --no-focus "$@" 2>&1) || {
    case $out in
      *"already used by worktree"*|*"already checked out"*) die 15 "$(jq -r '.error.message // empty' <<<"$out" 2>/dev/null || echo "$out")" ;;
      *) die 11 "worktree not created: $out" ;;
    esac
  }
  echo "$out"
}

cmd_open() {
  [ $# -ge 2 ] || die 2 "usage: herdr-pane.sh open <name> <report-path|-> [--worktree <branch> | --worktree-staged]"
  require_herdr
  local name=$1 report=$2 mode=sibling branch="" out pane agent
  local direction=null workspace="" wt_path="" wt_branch="" base_tree="" remote_ref=""
  shift 2
  case ${1:-} in
    --worktree) [ -n "${2:-}" ] || die 2 "--worktree needs a branch"; mode=worktree; branch=$2 ;;
    --worktree-staged) mode=staged ;;
    "") ;;
    *) die 2 "unknown option: $1" ;;
  esac

  local agent_args=()
  if [ "$report" != - ]; then
    mkdir -p "$(dirname "$report")"
    agent_args=(-- --add-dir "$(dirname "$report")")
  fi

  case $mode in
    sibling)
      direction=$(split_direction)
      # The pane's shell comes from the Herdr server, not from this process, so it
      # does not inherit CLAUDECODE and the new claude starts as a top-level session.
      out=$(herdr pane split --current --direction "$direction" --cwd "$PWD" --no-focus 2>&1) \
        || die 11 "pane split failed: $out"
      pane=$(jq -r '.result.pane.pane_id' <<<"$out")
      direction="\"$direction\""
      ;;
    worktree)
      git fetch --quiet origin "$branch" 2>/dev/null || true
      git rev-parse --verify --quiet "refs/remotes/origin/$branch" >/dev/null && remote_ref="origin/$branch"
      if git rev-parse --verify --quiet "refs/heads/$branch" >/dev/null; then
        # Fast-forward a stale local branch; a diverged one is left as it is.
        if [ -n "$remote_ref" ] && ! git worktree list --porcelain | grep -qx "branch refs/heads/$branch" \
            && git merge-base --is-ancestor "$branch" "$remote_ref"; then
          git branch -f "$branch" "$remote_ref" >/dev/null
        fi
        out=$(create_worktree --branch "$branch")
      else
        [ -n "$remote_ref" ] || die 17 "branch '$branch' exists neither locally nor on origin"
        out=$(create_worktree --branch "$branch" --base "$remote_ref")
      fi
      ;;
    staged)
      git diff --cached --quiet && die 16 "nothing is staged"
      base_tree=$(git write-tree) || die 17 "git write-tree failed"
      wt_branch="pane/$(printf '%s' "$name" | tr -c 'A-Za-z0-9_-' '-')-$(date +%Y%m%d%H%M%S)"
      out=$(create_worktree --branch "$wt_branch" --base HEAD)
      ;;
  esac

  if [ "$mode" != sibling ]; then
    pane=$(jq -r '.result.root_pane.pane_id' <<<"$out")
    workspace=$(jq -r '.result.workspace.workspace_id' <<<"$out")
    wt_path=$(jq -r '.result.worktree.path' <<<"$out")
    [ -n "$wt_branch" ] || wt_branch=$(jq -r '.result.worktree.branch' <<<"$out")
    if [ -n "$remote_ref" ]; then
      git -C "$wt_path" branch --set-upstream-to="$remote_ref" >/dev/null 2>&1 || true
    fi
    if [ "$mode" = staged ]; then
      git diff --cached --binary | git -C "$wt_path" apply --index \
        || die 17 "could not carry the staged diff into $wt_path (workspace $workspace left open)"
    fi
  fi
  [ -n "$pane" ] && [ "$pane" != null ] || die 11 "no pane id in: $out"

  agent=$(unique_agent_name "$name")
  if ! out=$(herdr agent start "$agent" --kind claude --pane "$pane" --timeout 60000 "${agent_args[@]}" 2>&1); then
    die 12 "agent did not start in pane $pane (left open for inspection): $out"
  fi
  jq -n --arg pane "$pane" --arg agent "$agent" --argjson direction "$direction" \
    --arg workspace "$workspace" --arg wt_path "$wt_path" --arg wt_branch "$wt_branch" --arg base_tree "$base_tree" \
    'def nonempty: if . == "" then null else . end;
     {pane_id: $pane, agent: $agent, direction: $direction,
      workspace_id: ($workspace | nonempty), worktree_path: ($wt_path | nonempty),
      worktree_branch: ($wt_branch | nonempty), base_tree: ($base_tree | nonempty)}'
}

cmd_run() {
  [ $# -ge 3 ] || die 2 "usage: herdr-pane.sh run <agent> <report-path> <command...>"
  require_herdr
  local agent=$1 report=$2 out
  shift 2
  local command="$*"

  rm -f "$report"
  out=$(herdr agent prompt "$agent" "$command" --wait 2>&1) || die 13 "prompt not taken: $out"
  wait_settled "$agent"

  out=$(herdr agent prompt "$agent" \
    "Write the complete result you just presented to $report as Markdown, exactly as presented: every finding or item with its severity, location and evidence, plus any summary table. Do not re-run or change anything. Reply with only the path." \
    --wait 2>&1) || die 13 "save prompt not taken: $out"
  wait_settled "$agent"

  [ -s "$report" ] || die 14 "agent '$agent' settled but $report is missing or empty"
  echo "$report"
}

cmd_send() {
  [ $# -ge 2 ] || die 2 "usage: herdr-pane.sh send <agent> <command...>"
  require_herdr
  local agent=$1 out
  shift
  out=$(herdr agent prompt "$agent" "$*" 2>&1) || die 13 "prompt not taken: $out"
  # Return once the agent has picked it up, not when it finishes.
  herdr agent wait "$agent" --until working --until blocked --timeout 30000 >/dev/null 2>&1 \
    || die 13 "agent '$agent' did not start on the command within 30s"
  echo "$agent"
}

cmd_staged_patch() {
  [ $# -eq 3 ] || die 2 "usage: herdr-pane.sh staged-patch <worktree-path> <base-tree> <patch-path>"
  local wt=$1 base=$2 patch=$3 tree
  tree=$(git -C "$wt" write-tree) || die 17 "git write-tree failed in $wt"
  mkdir -p "$(dirname "$patch")"
  git diff --binary "$base" "$tree" >"$patch" || die 17 "git diff $base $tree failed"
  if [ -s "$patch" ]; then
    git apply --stat "$patch"
  else
    echo empty
  fi
}

cmd_cleanup() {
  [ $# -ge 1 ] || die 2 "usage: herdr-pane.sh cleanup <workspace-id> [--force] [--delete-branch <branch>]"
  require_herdr
  local workspace=$1 force=() branch="" out
  shift
  while [ $# -gt 0 ]; do
    case $1 in
      --force) force=(--force); shift ;;
      --delete-branch) branch=${2:-}; shift 2 ;;
      *) die 2 "unknown option: $1" ;;
    esac
  done
  out=$(herdr worktree remove --workspace "$workspace" "${force[@]}" 2>&1) || die 17 "worktree not removed: $out"
  if [ -n "$branch" ]; then
    git branch -D "$branch" >/dev/null || die 17 "worktree removed, branch '$branch' not deleted"
  fi
  jq -r '.result.path' <<<"$out"
}

case ${1:-} in
  check) shift; require_herdr ;;
  status) if (require_herdr) 2>/dev/null; then echo inside; else echo outside; fi ;;
  open) shift; cmd_open "$@" ;;
  run) shift; cmd_run "$@" ;;
  send) shift; cmd_send "$@" ;;
  staged-patch) shift; cmd_staged_patch "$@" ;;
  cleanup) shift; cmd_cleanup "$@" ;;
  *) die 2 "usage: herdr-pane.sh check | status | open | run | send | staged-patch | cleanup (see the header)" ;;
esac
