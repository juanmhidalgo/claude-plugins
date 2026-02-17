#!/usr/bin/env bash
# ask-claude.sh — Wrapper para invocar Claude Code CLI en modo no interactivo desde otros agentes
#
# Uso:
#   ask-claude.sh "<prompt>"                          # Básico, read-only
#   ask-claude.sh "<prompt>" --timeout 180            # Con timeout custom
#   ask-claude.sh "<prompt>" --model sonnet           # Modelo específico (sonnet, opus, haiku)
#   ask-claude.sh "<prompt>" --json                   # Output JSON estructurado
#   echo "<prompt largo>" | ask-claude.sh -           # Prompt desde stdin
#
# Requiere:
#   - Claude Code CLI instalado
#   - Autenticación previa (claude auth login o API key)

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
TIMEOUT=180
JSON_MODE=false
MODEL=""

# ── Colores para stderr ──────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[ask-claude]${NC} $*" >&2; }
warn() { echo -e "${YELLOW}[ask-claude]${NC} $*" >&2; }
err() { echo -e "${RED}[ask-claude]${NC} $*" >&2; }

# ── Validaciones ─────────────────────────────────────────────────────────────
if ! command -v claude &>/dev/null; then
    err "Claude Code CLI no está instalado."
    exit 1
fi

# ── Parse args ───────────────────────────────────────────────────────────────
PROMPT=""

require_arg() { [[ $# -ge 2 ]] || { err "$1 requiere un argumento"; exit 1; }; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --timeout)
            require_arg "$@"
            TIMEOUT="$2"
            shift 2
            ;;
        --json)
            JSON_MODE=true
            shift
            ;;
        --model)
            require_arg "$@"
            MODEL="$2"
            shift 2
            ;;
        --help|-h)
            head -20 "$0" | tail -n +2 | sed 's/^# \?//'
            exit 0
            ;;
        -)
            PROMPT="-"
            shift
            ;;
        --)
            shift
            break
            ;;
        -*)
            err "Flag desconocido: $1"
            exit 1
            ;;
        *)
            if [[ -z "$PROMPT" ]]; then
                PROMPT="$1"
            else
                err "Prompt ya definido. Usá comillas para prompts con espacios."
                exit 1
            fi
            shift
            ;;
    esac
done

# Consumir args restantes después de --
if [[ -z "$PROMPT" ]] && [[ $# -gt 0 ]]; then
    PROMPT="$1"
fi

# Si el prompt es "-", leer de stdin
if [[ "$PROMPT" == "-" ]]; then
    PROMPT="$(cat)"
fi

if [[ -z "$PROMPT" ]]; then
    err "Uso: ask-claude.sh \"<prompt>\" [opciones]"
    exit 1
fi

# ── Construir comando ───────────────────────────────────────────────────────
CMD=(claude -p --no-session-persistence --permission-mode plan)

# Unset CLAUDECODE para permitir ejecución anidada
export CLAUDECODE=

# JSON mode
if [[ "$JSON_MODE" == true ]]; then
    CMD+=(--output-format json)
fi

# Modelo
if [[ -n "$MODEL" ]]; then
    CMD+=(--model "$MODEL")
fi

# Prompt al final
CMD+=("$PROMPT")

# ── Ejecutar ─────────────────────────────────────────────────────────────────
PROMPT_SUFFIX=""; (( ${#PROMPT} > 100 )) && PROMPT_SUFFIX="..."
log "Ejecutando Claude (timeout: ${TIMEOUT}s)..."
log "Prompt: ${PROMPT:0:100}${PROMPT_SUFFIX}"

STDERR_FILE=$(mktemp "${TMPDIR:-/tmp}/ask-claude-stderr.XXXXXX")
trap 'rm -f "$STDERR_FILE"' EXIT

EXIT_CODE=0
timeout "$TIMEOUT" "${CMD[@]}" 2>"$STDERR_FILE" || EXIT_CODE=$?

if [[ $EXIT_CODE -eq 124 ]]; then
    err "TIMEOUT: Claude no respondió en ${TIMEOUT}s"
    [[ -s "$STDERR_FILE" ]] && cat "$STDERR_FILE" >&2
    exit 124
elif [[ $EXIT_CODE -ne 0 ]]; then
    err "Claude finalizó con código de error: $EXIT_CODE"
    [[ -s "$STDERR_FILE" ]] && cat "$STDERR_FILE" >&2
    exit $EXIT_CODE
fi
