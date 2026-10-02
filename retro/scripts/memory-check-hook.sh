#!/usr/bin/env bash
# memory-check-hook.sh — SessionStart hook: warn Claude about memories that may be stale
#
# Reads the SessionStart payload on stdin, runs memory-check.sh for the
# session's cwd with --quiet-unless-stale, and only when there are findings
# prints {"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":...}}.
# Silent otherwise. Always exits 0: a broken check must never block a session.
#
# Disable: export RETRO_MEMORY_CHECK=off (or disable the retro plugin).

set -u

[[ "${RETRO_MEMORY_CHECK:-on}" == off ]] && exit 0

payload="$(cat 2>/dev/null || true)"
cwd=""
if command -v jq >/dev/null 2>&1; then
    cwd="$(printf '%s' "${payload}" | jq -r '.cwd // empty' 2>/dev/null || true)"
fi
[[ -n "${cwd}" && -d "${cwd}" ]] || cwd="${PWD}"

findings="$(cd "${cwd}" && "$(dirname "$0")/memory-check.sh" --quiet-unless-stale --max-predicates 20 2>/dev/null || true)"
[[ -n "${findings}" ]] || exit 0

context="retro memory-check: these auto-memory files may be stale. Before relying on any of them, verify the claim against the current code, then update or delete the memory file (and its MEMORY.md line).
${findings}"

if command -v jq >/dev/null 2>&1; then
    jq -n --arg ctx "${context}" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
else
    # SessionStart adds plain stdout to the context too.
    printf '%s\n' "${context}"
fi
exit 0
