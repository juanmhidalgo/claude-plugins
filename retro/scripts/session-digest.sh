#!/usr/bin/env bash
# session-digest.sh — Measured metrics and friction signals from Claude Code session logs
#
# Reads ~/.claude/projects/<encoded-cwd>/<session-id>.jsonl and prints a compact
# digest: cost, durations, turn shape, tool histogram, and friction events
# (tool errors, permission denials, hook blocks, slow turns).
#
# Everything printed is measured from the log. Nothing is inferred.
#
# Usage:
#   session-digest.sh                          # most recent session of $PWD
#   session-digest.sh --list                   # list sessions for $PWD
#   session-digest.sh --session <id>           # one specific session
#   session-digest.sh --last 3                 # the 3 most recent sessions
#   session-digest.sh --project <dir>          # a different project (default: $PWD)
#   session-digest.sh --prompts                # include the human prompt texts
#   session-digest.sh --prompt-chars 400       # truncation width for --prompts
#
# Scope: one project at a time, on purpose. There is no "all projects" mode —
# ~/.claude/projects holds transcripts from every repo you have ever opened.
#
# Requires: jq

# No `pipefail`: several pipelines here end in `head -N`, which closes the pipe
# and SIGPIPEs jq. With pipefail that aborts the whole digest mid-section.
set -eu

PROJECT_DIR="${PWD}"
SESSION_ID=""
LAST_N=1
LIST_ONLY=false
SHOW_PROMPTS=false
PROMPT_CHARS=200

die() { echo "Error: $*" >&2; exit 1; }

command -v jq >/dev/null 2>&1 || die "jq is required (apt install jq / brew install jq)"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --project)      PROJECT_DIR="${2:?--project needs a directory}"; shift 2 ;;
        --session)      SESSION_ID="${2:?--session needs an id}"; shift 2 ;;
        --last)         LAST_N="${2:?--last needs a number}"; shift 2 ;;
        --list)         LIST_ONLY=true; shift ;;
        --prompts)      SHOW_PROMPTS=true; shift ;;
        --prompt-chars) PROMPT_CHARS="${2:?--prompt-chars needs a number}"; shift 2 ;;
        --help|-h)      sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *)              die "unknown argument: $1 (try --help)" ;;
    esac
done

[[ "${LAST_N}" =~ ^[0-9]+$ ]] || die "--last expects a number, got: ${LAST_N}"
[[ "${PROMPT_CHARS}" =~ ^[0-9]+$ ]] || die "--prompt-chars expects a number"

# ── Locate the logs ───────────────────────────────────────────────────────────
# Claude Code encodes the project cwd by replacing '/', '.' and '_' with '-'.
# Verified against every local project directory; replacing only '/' (a common
# mistake) breaks on any path containing a dot, e.g. ~/.claude.
encode_project_dir() {
    printf '%s' "$1" | sed 's/[\/._]/-/g'
}

PROJECT_DIR="$(cd "${PROJECT_DIR}" 2>/dev/null && pwd || printf '%s' "${PROJECT_DIR}")"
LOGS_DIR="${HOME}/.claude/projects/$(encode_project_dir "${PROJECT_DIR}")"

[[ -d "${LOGS_DIR}" ]] || die "no session logs for ${PROJECT_DIR} (looked in ${LOGS_DIR})"

mapfile -t ALL_SESSIONS < <(find "${LOGS_DIR}" -maxdepth 1 -name '*.jsonl' -type f -printf '%T@ %p\n' 2>/dev/null \
    | sort -rn | cut -d' ' -f2-)

[[ ${#ALL_SESSIONS[@]} -gt 0 ]] || die "no .jsonl session files in ${LOGS_DIR}"

# ── Helpers ───────────────────────────────────────────────────────────────────
human_ms() {
    local ms="${1:-0}" s
    [[ "${ms}" =~ ^[0-9]+$ ]] || { printf 'n/a'; return; }
    s=$(( ms / 1000 ))
    printf '%dh %02dm %02ds' $(( s / 3600 )) $(( (s % 3600) / 60 )) $(( s % 60 ))
}

# A "human turn" is a user entry that is neither a tool result, nor a subagent
# turn, nor injected meta. Counting every {"type":"user"} entry instead — the
# obvious shortcut — is wrong by roughly an order of magnitude: tool results
# dominate the file.
# Emits exactly one whitespace-collapsed line per human-origin entry, so every
# consumer can count with `grep -c` without a multi-line prompt inflating the number.
#
# Two filters, because two consumers want different things: the slash-command
# histogram needs the `<command-name>` wrappers, and the turn count and prompt
# listing must not have them — a session driven by slash commands otherwise
# reports several times the real number of human turns and buries the prose the
# retro actually cites.
HUMAN_RAW_FILTER='select(.type=="user" and (.isMeta != true) and (.isSidechain != true))
  | (.message.content
      | if type == "string" then .
        else (map(select(.type == "text") | .text) | join(" "))
        end)
  | gsub("\\s+"; " ")
  | select(length > 0)
  | select(startswith("<local-command-stdout>") | not)
  | select(startswith("Caveat:") | not)
  | select(startswith("<task-notification>") | not)'

HUMAN_TURN_FILTER="${HUMAN_RAW_FILTER}
  | select(startswith(\"<command-name>\") | not)
  | select(startswith(\"<command-message>\") | not)
  | select(startswith(\"<local-command-caveat>\") | not)"

if [[ "${LIST_ONLY}" == true ]]; then
    printf 'Sessions for %s\n\n' "${PROJECT_DIR}"
    printf '%-38s %-20s %10s %8s %s\n' "SESSION" "LAST ACTIVITY" "SIZE" "TURNS" "COST"
    for f in "${ALL_SESSIONS[@]}"; do
        id="$(basename "${f}" .jsonl)"
        mtime="$(date -r "${f}" '+%Y-%m-%d %H:%M' 2>/dev/null || printf 'unknown')"
        size="$(du -h "${f}" | cut -f1)"
        turns="$(jq -r "${HUMAN_TURN_FILTER}" "${f}" 2>/dev/null | grep -c '' || true)"
        cost="$(jq -r 'select(.type=="cost-state") | .totalCostUSD' "${f}" 2>/dev/null | tail -1)"
        [[ -n "${cost}" ]] && cost="$(printf '$%.2f' "${cost}")" || cost="n/a"
        printf '%-38s %-20s %10s %8s %s\n' "${id}" "${mtime}" "${size}" "${turns}" "${cost}"
    done
    exit 0
fi

# ── Pick the sessions to digest ───────────────────────────────────────────────
SESSIONS=()
if [[ -n "${SESSION_ID}" ]]; then
    f="${LOGS_DIR}/${SESSION_ID}.jsonl"
    [[ -f "${f}" ]] || die "session not found: ${f}"
    SESSIONS=("${f}")
else
    for f in "${ALL_SESSIONS[@]:0:${LAST_N}}"; do SESSIONS+=("${f}"); done
fi

TMPDIR_RUN="$(mktemp -d)"
trap 'rm -rf "${TMPDIR_RUN}"' EXIT

# ── Digest one session ────────────────────────────────────────────────────────
digest_session() {
    local f="$1"
    local id; id="$(basename "${f}" .jsonl)"

    echo "================================================================"
    echo "SESSION ${id}"
    echo "================================================================"

    # -- Identity -------------------------------------------------------------
    # grep -m1 stops at the first match instead of streaming a multi-megabyte
    # file through jq just to read the header fields.
    local meta first last
    meta="$(grep -m1 '"cwd":' "${f}" || true)"
    if [[ -n "${meta}" ]]; then
        printf '%s' "${meta}" | jq -r '"cwd:     \(.cwd)\nbranch:  \(.gitBranch // "?")\nversion: \(.version // "?")"'
    fi
    first="$(jq -r 'select(.timestamp) | .timestamp' "${f}" 2>/dev/null | head -1)"
    last="$(jq -r 'select(.timestamp) | .timestamp' "${f}" | tail -1)"
    echo "window:  ${first} -> ${last}"
    echo

    # -- Cost and effort (from the cost-state record Claude Code writes) -------
    echo "-- COST & EFFORT --"
    local cost_line
    cost_line="$(jq -c 'select(.type=="cost-state")' "${f}" | tail -1)"
    if [[ -n "${cost_line}" ]]; then
        local wall api tool
        wall="$(printf '%s' "${cost_line}" | jq -r '.totalDuration // 0')"
        api="$(printf '%s'  "${cost_line}" | jq -r '.totalAPIDuration // 0')"
        tool="$(printf '%s' "${cost_line}" | jq -r '.totalToolDuration // 0')"
        printf '%s' "${cost_line}" | jq -r '"cost:          $\(.totalCostUSD // 0 | .*10000 | round / 10000)"'
        echo "wall clock:    $(human_ms "${wall}")"
        echo "api time:      $(human_ms "${api}")   tool time: $(human_ms "${tool}")"
        printf '%s' "${cost_line}" | jq -r '"lines:         +\(.totalLinesAdded // 0) / -\(.totalLinesRemoved // 0)"'
        printf '%s' "${cost_line}" | jq -r '.modelUsage // {} | to_entries[] |
            "model:         \(.key)  in=\(.value.inputTokens) out=\(.value.outputTokens) think=\(.value.thinkingTokens) cache_read=\(.value.cacheReadInputTokens) $\(.value.costUSD*10000|round/10000)"' 
    else
        echo "(no cost-state record — session may still be open or predates cost tracking)"
    fi
    echo

    # -- Shape ----------------------------------------------------------------
    # Note: subagent transcripts are NOT inlined in this file — `isSidechain` is
    # false on every entry in current Claude Code versions. So delegation is
    # measured by counting Agent/Task tool calls, not by splitting on that flag.
    echo "-- SHAPE --"
    local human_turns slash_cmds asst_turns tool_calls subagents skills_used
    human_turns="$(jq -r "${HUMAN_TURN_FILTER}" "${f}" | grep -c '' || true)"
    slash_cmds="$(jq -r "${HUMAN_RAW_FILTER}" "${f}" | grep -o '<command-name>[^<]*</command-name>' \
        | sed 's/<[^>]*>//g' | sort | uniq -c | sort -rn || true)"
    asst_turns="$(jq -r 'select(.type=="assistant") | 1' "${f}" | grep -c '' || true)"
    tool_calls="$(jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use") | .name' "${f}" | grep -c '' || true)"
    subagents="$(jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use" and (.name=="Agent" or .name=="Task")) | (.input.subagent_type // "unspecified")' "${f}" | sort | uniq -c | sort -rn || true)"
    skills_used="$(jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use" and .name=="Skill") | (.input.skill // "?")' "${f}" | sort | uniq -c | sort -rn || true)"
    echo "human turns:        ${human_turns}"
    echo "assistant turns:    ${asst_turns}"
    echo "tool calls:         ${tool_calls}"
    if [[ -n "${slash_cmds}" ]]; then
        echo "slash commands:"; echo "${slash_cmds}" | sed 's/^/  /'
    fi
    if [[ -n "${skills_used}" ]]; then
        echo "skills invoked:"; echo "${skills_used}" | sed 's/^/  /'
    fi
    if [[ -n "${subagents}" ]]; then
        echo "subagents spawned:"; echo "${subagents}" | sed 's/^/  /'
    fi
    echo

    # -- Tool histogram -------------------------------------------------------
    echo "-- TOOLS --"
    jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use") | .name' "${f}" \
        | sort | uniq -c | sort -rn | head -15 | awk '{printf "  %-34s %s\n", $2, $1}'
    echo

    # -- Friction -------------------------------------------------------------
    # Tool names live on the assistant's tool_use block; errors and denials live
    # on the matching user tool_result. Join them by tool_use id, streaming, so
    # a multi-megabyte session never has to be slurped into memory.
    local names errors denials
    names="${TMPDIR_RUN}/names.tsv"
    errors="${TMPDIR_RUN}/errors.tsv"
    denials="${TMPDIR_RUN}/denials.tsv"

    jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use") | [.id, .name] | @tsv' "${f}" \
        | sort -k1,1 > "${names}"

    # A denial also arrives as an is_error tool_result. Excluding entries that carry
    # toolDenialKind keeps one round trip from being counted twice — once here and
    # once under denials — which inflates the bucket Phase 2 ranks first.
    # Only the first non-empty line of the message is kept: a failing command's
    # stdout otherwise collapses into the error text and swamps the actual reason.
    jq -r 'select(.type=="user" and (.toolDenialKind | not))
           | .message.content[]? | select(.type=="tool_result" and .is_error==true)
           | [ .tool_use_id,
               ( (.content | if type=="array" then (map(.text? // "") | join("\n")) else (. // "") end)
                 | split("\n") | map(select(test("\\S"))) | (.[0] // "")
                 | gsub("\\s+"; " ") | .[0:160] ) ] | @tsv' "${f}" \
        | sort -k1,1 > "${errors}"

    jq -r 'select(.type=="user" and .toolDenialKind) as $e
           | $e.message.content[]? | select(.type=="tool_result")
           | [.tool_use_id, $e.toolDenialKind] | @tsv' "${f}" \
        | sort -k1,1 > "${denials}"

    echo "-- FRICTION --"

    local err_count den_count
    err_count="$(grep -c '' < "${errors}" || true)"
    den_count="$(grep -c '' < "${denials}" || true)"

    echo "tool errors:        ${err_count}"
    if [[ "${err_count}" -gt 0 ]]; then
        join -t$'\t' -1 1 -2 1 -o '2.2,1.2' "${errors}" "${names}" 2>/dev/null \
            | sort | uniq -c | sort -rn | head -10 \
            | sed 's/^ *//; s/\t/ | /g' | awk '{printf "  x%s\n", $0}'
    fi

    echo "permission denials: ${den_count}"
    if [[ "${den_count}" -gt 0 ]]; then
        join -t$'\t' -1 1 -2 1 -o '2.2,1.2' "${denials}" "${names}" 2>/dev/null \
            | sort | uniq -c | sort -rn \
            | sed 's/^ *//; s/\t/ | /g' | awk '{printf "  x%s\n", $0}'
    fi

    local hook_blocks hook_errs
    hook_blocks="$(jq -r 'select(.preventedContinuation == true) | 1' "${f}" | grep -c '' || true)"
    hook_errs="$(jq -r 'select((.hookErrors // []) | length > 0) | (.hookErrors | tostring)' "${f}" | grep -c '' || true)"
    echo "hook blocks:        ${hook_blocks} prevented continuation, ${hook_errs} hook errors"
    if [[ "${hook_errs}" -gt 0 ]]; then
        jq -r 'select((.hookErrors // []) | length > 0) | (.hookErrors | tostring | .[0:200])' "${f}" | head -5 | sed 's/^/  /'
    fi

    echo "slowest turns:"
    jq -r 'select(.type=="system" and .subtype=="turn_duration") | [.durationMs, .timestamp] | @tsv' "${f}" \
        | sort -rn | head -5 | while IFS=$'\t' read -r ms ts; do
            printf '  %-12s %s\n' "$(human_ms "${ms}")" "${ts}"
        done
    echo

    # -- Prompts --------------------------------------------------------------
    if [[ "${SHOW_PROMPTS}" == true ]]; then
        echo "-- HUMAN TURNS (truncated to ${PROMPT_CHARS} chars) --"
        jq -r "${HUMAN_TURN_FILTER}" "${f}" \
            | cut -c1-"${PROMPT_CHARS}" | nl -ba -w3 -s'. ' | sed 's/^/  /'
        echo
    fi
}

printf 'Project: %s\nLogs:    %s\nSessions digested: %d\n\n' "${PROJECT_DIR}" "${LOGS_DIR}" "${#SESSIONS[@]}"

for f in "${SESSIONS[@]}"; do
    digest_session "${f}"
done

if [[ "${#SESSIONS[@]}" -gt 1 ]]; then
    echo "================================================================"
    echo "ROLLUP across ${#SESSIONS[@]} sessions"
    echo "================================================================"
    total_cost=0
    for f in "${SESSIONS[@]}"; do
        c="$(jq -r 'select(.type=="cost-state") | .totalCostUSD' "${f}" | tail -1)"
        [[ -n "${c}" ]] && total_cost="$(awk -v a="${total_cost}" -v b="${c}" 'BEGIN{printf "%.4f", a+b}')"
    done
    printf 'total cost:   $%s\n' "${total_cost}"
    echo "tool calls (all sessions):"
    for f in "${SESSIONS[@]}"; do
        jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use") | .name' "${f}"
    done | sort | uniq -c | sort -rn | head -15 | awk '{printf "  %-34s %s\n", $2, $1}'
fi
