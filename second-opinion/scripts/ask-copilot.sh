#!/usr/bin/env bash
# ask-copilot.sh — Wrapper para invocar GitHub Copilot CLI en modo no interactivo desde Claude Code
#
# Uso:
#   ask-copilot.sh "<prompt>"                          # Básico, read-only
#   ask-copilot.sh "<prompt>" --timeout 180            # Con timeout custom
#   ask-copilot.sh "<prompt>" --writable               # Permite escritura (allow-all-tools)
#   ask-copilot.sh "<prompt>" --model gpt-4o           # Modelo específico
#   echo "<prompt largo>" | ask-copilot.sh -           # Prompt desde stdin
#
# Requiere:
#   - GitHub Copilot CLI instalado (npm i -g @anthropic-ai/copilot o similar)
#   - Autenticación con GitHub (gh auth login o GITHUB_TOKEN)

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
TIMEOUT=180
WRITABLE=false
MODEL=""

# ── Colores para stderr ──────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[ask-copilot]${NC} $*" >&2; }
warn() { echo -e "${YELLOW}[ask-copilot]${NC} $*" >&2; }
err() { echo -e "${RED}[ask-copilot]${NC} $*" >&2; }

# ── Validaciones ─────────────────────────────────────────────────────────────
if ! command -v copilot &>/dev/null; then
    err "GitHub Copilot CLI no está instalado."
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
        --writable)
            WRITABLE=true
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
    err "Uso: ask-copilot.sh \"<prompt>\" [opciones]"
    exit 1
fi

# ── Construir comando ───────────────────────────────────────────────────────
CMD=(copilot -p "$PROMPT")

# Writable: allow-all-tools si --writable, sino sin permisos de tools
if [[ "$WRITABLE" == true ]]; then
    CMD+=(--allow-all-tools)
fi

# Modelo
if [[ -n "$MODEL" ]]; then
    CMD+=(--model "$MODEL")
fi

# ── Ejecutar ─────────────────────────────────────────────────────────────────
PROMPT_SUFFIX=""; (( ${#PROMPT} > 100 )) && PROMPT_SUFFIX="..."
log "Ejecutando Copilot (timeout: ${TIMEOUT}s)..."
log "Prompt: ${PROMPT:0:100}${PROMPT_SUFFIX}"

STDERR_FILE=$(mktemp "${TMPDIR:-/tmp}/ask-copilot-stderr.XXXXXX")
trap 'rm -f "$STDERR_FILE"' EXIT

EXIT_CODE=0
timeout "$TIMEOUT" "${CMD[@]}" 2>"$STDERR_FILE" || EXIT_CODE=$?

if [[ $EXIT_CODE -eq 124 ]]; then
    err "TIMEOUT: Copilot no respondió en ${TIMEOUT}s"
    [[ -s "$STDERR_FILE" ]] && cat "$STDERR_FILE" >&2
    exit 124
elif [[ $EXIT_CODE -ne 0 ]]; then
    err "Copilot finalizó con código de error: $EXIT_CODE"
    [[ -s "$STDERR_FILE" ]] && cat "$STDERR_FILE" >&2
    exit $EXIT_CODE
fi
