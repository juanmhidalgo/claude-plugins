#!/usr/bin/env bash
# ask-gemini.sh — Wrapper para invocar Gemini CLI en modo no interactivo desde Claude Code
#
# Uso:
#   ask-gemini.sh "<prompt>"                          # Básico, read-only (plan mode)
#   ask-gemini.sh "<prompt>" --timeout 180            # Con timeout custom
#   ask-gemini.sh "<prompt>" --json                   # Output JSON estructurado
#   ask-gemini.sh "<prompt>" --writable               # Permite escritura (yolo mode)
#   ask-gemini.sh "<prompt>" --model gemini-2.5-pro   # Modelo específico
#   ask-gemini.sh "<prompt>" --sandbox                # Ejecutar en sandbox
#   echo "<prompt largo>" | ask-gemini.sh -           # Prompt desde stdin
#
# Requiere:
#   - Gemini CLI instalado (npm i -g @anthropic-ai/gemini o similar)
#   - GEMINI_API_KEY o autenticación previa

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
TIMEOUT=180
JSON_MODE=false
WRITABLE=false
SANDBOX=false
MODEL=""

# ── Colores para stderr ──────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[ask-gemini]${NC} $*" >&2; }
warn() { echo -e "${YELLOW}[ask-gemini]${NC} $*" >&2; }
err() { echo -e "${RED}[ask-gemini]${NC} $*" >&2; }

# ── Validaciones ─────────────────────────────────────────────────────────────
if ! command -v gemini &>/dev/null; then
    err "Gemini CLI no está instalado."
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
        --writable)
            WRITABLE=true
            shift
            ;;
        --sandbox)
            SANDBOX=true
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
    err "Uso: ask-gemini.sh \"<prompt>\" [opciones]"
    exit 1
fi

# ── Construir comando ───────────────────────────────────────────────────────
CMD=(gemini)

# Approval mode: default (requiere aprobación) por defecto, yolo si --writable
if [[ "$WRITABLE" == true ]]; then
    CMD+=(--approval-mode yolo)
fi

# Sandbox
if [[ "$SANDBOX" == true ]]; then
    CMD+=(-s)
fi

# JSON mode
if [[ "$JSON_MODE" == true ]]; then
    CMD+=(-o json)
else
    CMD+=(-o text)
fi

# Modelo
if [[ -n "$MODEL" ]]; then
    CMD+=(-m "$MODEL")
fi

# Prompt en modo no interactivo
CMD+=(-p "$PROMPT")

# ── Ejecutar ─────────────────────────────────────────────────────────────────
PROMPT_SUFFIX=""; (( ${#PROMPT} > 100 )) && PROMPT_SUFFIX="..."
log "Ejecutando Gemini (timeout: ${TIMEOUT}s)..."
log "Prompt: ${PROMPT:0:100}${PROMPT_SUFFIX}"

STDERR_FILE=$(mktemp "${TMPDIR:-/tmp}/ask-gemini-stderr.XXXXXX")
trap 'rm -f "$STDERR_FILE"' EXIT

EXIT_CODE=0
timeout "$TIMEOUT" "${CMD[@]}" 2>"$STDERR_FILE" || EXIT_CODE=$?

if [[ $EXIT_CODE -eq 124 ]]; then
    err "TIMEOUT: Gemini no respondió en ${TIMEOUT}s"
    [[ -s "$STDERR_FILE" ]] && cat "$STDERR_FILE" >&2
    exit 124
elif [[ $EXIT_CODE -ne 0 ]]; then
    err "Gemini finalizó con código de error: $EXIT_CODE"
    [[ -s "$STDERR_FILE" ]] && cat "$STDERR_FILE" >&2
    exit $EXIT_CODE
fi
