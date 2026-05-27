#!/usr/bin/env bash
# strip-info-logs.sh — PostToolUse hook for second-opinion.
#
# When an ask-*.sh script exits successfully, its stderr contains only info
# logs prefixed with [ask-XXX] (e.g. "Ejecutando Codex...", "Prompt: ..."). On
# success these are pure noise to Claude. This hook empties stderr in that case
# while preserving stdout (the AI's actual response). On failure, stderr is
# preserved intact so error details survive.
#
# Returns hookSpecificOutput.updatedToolOutput per CC 2.1.121.
# Silent no-op if jq is unavailable or input is malformed.

set -u

# Fail closed: if anything goes wrong, exit 0 with no modification so the
# original tool output reaches Claude unchanged.
if ! command -v jq >/dev/null 2>&1; then
    exit 0
fi

INPUT=$(cat 2>/dev/null) || exit 0
[ -z "$INPUT" ] && exit 0

COMMAND=$(jq -r '.tool_input.command // ""' <<<"$INPUT" 2>/dev/null) || exit 0

# Only operate on ask-*.sh invocations from this plugin
if ! [[ "$COMMAND" =~ ask-(codex|gemini|claude|copilot)\.sh ]]; then
    exit 0
fi

EXIT_CODE=$(jq -r '.tool_output.exit_code // 0' <<<"$INPUT" 2>/dev/null) || exit 0
STDOUT=$(jq -r '.tool_output.stdout // ""' <<<"$INPUT" 2>/dev/null) || exit 0
STDERR=$(jq -r '.tool_output.stderr // ""' <<<"$INPUT" 2>/dev/null) || exit 0

if [ "$EXIT_CODE" = "0" ]; then
    NEW_STDERR=""
else
    NEW_STDERR="$STDERR"
fi

jq -n \
    --arg stdout "$STDOUT" \
    --arg stderr "$NEW_STDERR" \
    '{
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "updatedToolOutput": {
                "stdout": $stdout,
                "stderr": $stderr
            }
        }
    }'
