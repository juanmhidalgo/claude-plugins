#!/usr/bin/env bash
# plugin-runs.sh — How one plugin behaved across ALL projects, from plugin-recorder's files
#
# Reads the metadata-only JSONL that the plugin-recorder mod writes per session
# (~/.claude/plugins/data/plugin-recorder-*/sessions/*.jsonl) and reports, for one
# plugin: invocations by command/skill and version, subagent calls and their
# failures, turn durations, and all of it broken down by project basename.
#
# This is the one cross-project view in retro, on purpose: plugin-recorder stores
# no prompt text, no tool inputs beyond subagent_type, and no full paths, so
# reading every project's file exposes names, counts and durations only. It never
# opens ~/.claude/projects transcripts.
#
# Usage:
#   plugin-runs.sh <plugin>                  # e.g. feature-dev
#   plugin-runs.sh <plugin> --days 14        # only the last 14 days
#   plugin-runs.sh <plugin> --project <base> # only one project basename
#   plugin-runs.sh --list                    # plugins seen in the recordings
#
# Env: PLUGIN_RECORDER_DIR overrides where the sessions/*.jsonl files are read from.
# Exit: 0 with a notice when plugin-recorder has recorded nothing (not installed).
#
# Requires: jq, bash

set -eu

PLUGIN=""
DAYS=""
ONLY_PROJECT=""
LIST=false

die() { echo "Error: $*" >&2; exit 1; }

command -v jq >/dev/null 2>&1 || die "jq is required (apt install jq / brew install jq)"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --days)    DAYS="${2:?--days needs a number}"; shift 2 ;;
        --project) ONLY_PROJECT="${2:?--project needs a basename}"; shift 2 ;;
        --list)    LIST=true; shift ;;
        --help|-h) sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*)        die "unknown argument: $1 (try --help)" ;;
        *)         PLUGIN="$1"; shift ;;
    esac
done

[[ -z "${DAYS}" || "${DAYS}" =~ ^[0-9]+$ ]] || die "--days expects a number, got: ${DAYS}"
[[ "${LIST}" == true || -n "${PLUGIN}" ]] || die "name a plugin (or --list)"

CONFIG_DIR="${CLAUDE_CONFIG_DIR:-${HOME}/.claude}"
shopt -s nullglob
if [[ -n "${PLUGIN_RECORDER_DIR:-}" ]]; then
    FILES=("${PLUGIN_RECORDER_DIR}"/*.jsonl "${PLUGIN_RECORDER_DIR}"/sessions/*.jsonl)
else
    FILES=("${CONFIG_DIR}"/plugins/data/plugin-recorder-*/sessions/*.jsonl)
fi
shopt -u nullglob

if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "No plugin-recorder data found (looked in ${PLUGIN_RECORDER_DIR:-${CONFIG_DIR}/plugins/data/plugin-recorder-*/sessions}/)."
    echo "Install the plugin-recorder plugin to record plugin runs across projects;"
    echo "until then only this project's transcripts can be analyzed (session-digest.sh)."
    exit 0
fi

CUTOFF=""
if [[ -n "${DAYS}" ]]; then
    CUTOFF="$(date -u -d "-${DAYS} days" '+%Y-%m-%dT%H:%M:%S' 2>/dev/null \
        || date -u -v-"${DAYS}"d '+%Y-%m-%dT%H:%M:%S')"
fi

# Every line is one small metadata object; a bad line (a write cut short) is skipped.
stream() { cat "${FILES[@]}" | jq -cR 'fromjson? | select(type == "object" and .ev)'; }

if [[ "${LIST}" == true ]]; then
    printf 'Plugins seen in %d recorded session file(s):\n' "${#FILES[@]}"
    stream | jq -r 'select(.plugin) | .plugin' | sort | uniq -c | sort -rn \
        | awk '{printf "  %-28s %s events\n", $2, $1}'
    exit 0
fi

stream | jq -rn --arg p "${PLUGIN}" --arg cutoff "${CUTOFF}" --arg only "${ONLY_PROJECT}" '
  def mine: ((.plugin // "") == $p) or ((.ctx // "") | startswith($p + ":"));
  def dur: (. / 1000 | floor) as $s
    | if $s >= 3600 then "\($s/3600|floor)h\(($s%3600)/60|floor|tostring|if length<2 then "0"+. else . end)m"
      elif $s >= 60 then "\($s/60|floor)m\($s%60|tostring|if length<2 then "0"+. else . end)s"
      else "\($s)s" end;
  def stats: (map(.durationMs // 0) | sort) as $d
    | if ($d|length) == 0 then "-"
      else "median \($d[($d|length)/2|floor] | dur), max \($d[-1] | dur), total \($d|add|dur)" end;

  [inputs | select($cutoff == "" or (.ts // "") >= $cutoff)] as $all
  | ($all | map(select(.ev == "session.start")) | map({key: .sid, value: .project}) | from_entries) as $proj
  | [$all[] | . + {project: ($proj[.sid] // "?")}
     | select($only == "" or .project == $only)] as $rows
  | ($rows | map(select(mine))) as $m
  | ($m | map(select(.ev == "invoke"))) as $inv
  | ($m | map(select(.ev == "agent" or .ev == "agent.spawn"))) as $ag
  | ($ag | map(select(.status == "error" or .status == "denied"))) as $fail
  | ($m | map(select(.ev == "turn" and .agentId == null))) as $main
  | ($m | map(select(.ev == "turn" and .agentId != null))) as $sub

  | "Plugin: \($p)   (plugin-recorder, \($all | map(.sid) | unique | length) sessions read"
    + (if $cutoff != "" then ", since \($cutoff)Z" else "" end)
    + (if $only != "" then ", project \($only)" else "" end) + ")",
    "Sessions where it ran: \($m | map(.sid) | unique | length)",
    "",
    "-- INVOCATIONS --",
    (if ($inv|length) == 0 then "  (none recorded)" else
      ($inv | group_by([.name, (.version // "?")]) | sort_by(-length)[]
        | "  \(length)x  \(.[0].name)  v\(.[0].version // "?")  (\(map(.kind) | unique | join("/")))") end),
    "",
    "-- SUBAGENT CALLS (by subagent_type) --",
    (if ($ag|length) == 0 then "  (none recorded)" else
      ($ag | group_by(.subagent_type) | sort_by(-length)[]
        | "  \(.[0].subagent_type): \(length) calls, "
          + "\(map(select(.status == "completed")) | length) ok, "
          + "\(map(select(.status == "async_launched")) | length) background, "
          + "\(map(select(.status == "error")) | length) error, "
          + "\(map(select(.status == "denied")) | length) denied  |  \(map(select(.ev == "agent")) | stats)") end),
    "",
    "-- SPAWN / CALL FAILURES: \($fail | length) --",
    ($fail | sort_by(.ts)[] | "  \(.ts)  \(.project)  \(.subagent_type)  \(.status)  session \(.sid)"),
    "",
    "-- TURNS --",
    "  main-loop turns under \($p) commands: \($main | length)  |  \($main | stats)",
    "  subagent turns: \($sub | length)  |  \($sub | stats)  |  ended in error: \($sub | map(select(.reason == "error")) | length)",
    ($main | sort_by(-(.durationMs // 0)) | .[0:5][]
      | "    slow: \(.durationMs | dur)  \(.project)  \(.ctx // "-")  \(.ts)  session \(.sid)"),
    "",
    "-- BY PROJECT --",
    (if ($m|length) == 0 then "  (none)" else
      ($m | group_by(.project) | sort_by(-length)[]
        | "  \(.[0].project): \(map(.sid) | unique | length) sessions, "
          + "\(map(select(.ev == "invoke")) | length) invocations, "
          + "\(map(select(.ev == "agent")) | length) subagent calls, "
          + "\(map(select(.status == "error" or .status == "denied")) | length) failures") end)
'
