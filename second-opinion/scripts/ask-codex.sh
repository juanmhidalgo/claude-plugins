#!/usr/bin/env bash
# ask-codex.sh — Wrapper para invocar Codex CLI en modo no interactivo desde Claude Code
#
# Uso:
#   ask-codex.sh "<prompt>"                          # Básico, read-only
#   ask-codex.sh "<prompt>" --timeout 120            # Con timeout custom
#   ask-codex.sh "<prompt>" --json                   # Output JSON estructurado
#   ask-codex.sh "<prompt>" --writable               # Permite escritura en workspace
#   ask-codex.sh "<prompt>" --schema schema.json     # Valida output contra JSON Schema
#   ask-codex.sh "<prompt>" --model gpt-5.3-codex    # Modelo específico
#   echo "<prompt largo>" | ask-codex.sh -           # Prompt desde stdin
#
# Requiere:
#   - Codex CLI instalado (npm i -g @openai/codex)
#   - CODEX_API_KEY o autenticación previa con `codex login`

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
TIMEOUT=180
JSON_MODE=false
WRITABLE=false
OUTPUT_SCHEMA=""
MODEL=""
EPHEMERAL=true
OUTPUT_FILE=""

# ── Colores para stderr ──────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[ask-codex]${NC} $*" >&2; }
warn() { echo -e "${YELLOW}[ask-codex]${NC} $*" >&2; }
err() { echo -e "${RED}[ask-codex]${NC} $*" >&2; }

# ── Validaciones ─────────────────────────────────────────────────────────────
if ! command -v codex &>/dev/null; then
    err "Codex CLI no está instalado. Instalalo con: npm i -g @openai/codex"
    exit 1
fi

if [[ -z "${CODEX_API_KEY:-}" ]]; then
    if [[ ! -f "${HOME}/.codex/auth.json" ]] && [[ ! -f "${HOME}/.config/codex/auth.json" ]]; then
        warn "No se encontró CODEX_API_KEY ni auth guardada. Puede fallar la autenticación."
    fi
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
        --schema)
            require_arg "$@"
            OUTPUT_SCHEMA="$2"
            shift 2
            ;;
        --model)
            require_arg "$@"
            MODEL="$2"
            shift 2
            ;;
        --output|-o)
            require_arg "$@"
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --no-ephemeral)
            EPHEMERAL=false
            shift
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
    err "Uso: ask-codex.sh \"<prompt>\" [opciones]"
    exit 1
fi

# ── Construir comando ───────────────────────────────────────────────────────
CMD=(codex exec)

# Sandbox: read-only por defecto, workspace-write si --writable
if [[ "$WRITABLE" == true ]]; then
    CMD+=(--full-auto --sandbox workspace-write)
fi

# Ephemeral: no persistir archivos de sesión
if [[ "$EPHEMERAL" == true ]]; then
    CMD+=(--ephemeral)
fi

# JSON mode
if [[ "$JSON_MODE" == true ]]; then
    CMD+=(--json)
fi

# Output schema
if [[ -n "$OUTPUT_SCHEMA" ]]; then
    CMD+=(--output-schema "$OUTPUT_SCHEMA")
fi

# Modelo
if [[ -n "$MODEL" ]]; then
    CMD+=(--model "$MODEL")
fi

# Output file
if [[ -n "$OUTPUT_FILE" ]]; then
    CMD+=(-o "$OUTPUT_FILE")
fi

# Skip git repo check si no estamos en un repo git
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    CMD+=(--skip-git-repo-check)
fi

# Prompt al final
CMD+=("$PROMPT")

# ── Ejecutar ─────────────────────────────────────────────────────────────────
PROMPT_SUFFIX=""; (( ${#PROMPT} > 100 )) && PROMPT_SUFFIX="..."
log "Ejecutando Codex (timeout: ${TIMEOUT}s)..."
log "Prompt: ${PROMPT:0:100}${PROMPT_SUFFIX}"

STDERR_FILE=$(mktemp "${TMPDIR:-/tmp}/ask-codex-stderr.XXXXXX")
trap 'rm -f "$STDERR_FILE"' EXIT

EXIT_CODE=0
timeout "$TIMEOUT" "${CMD[@]}" 2>"$STDERR_FILE" || EXIT_CODE=$?

if [[ $EXIT_CODE -eq 124 ]]; then
    err "TIMEOUT: Codex no respondió en ${TIMEOUT}s"
    [[ -s "$STDERR_FILE" ]] && cat "$STDERR_FILE" >&2
    exit 124
elif [[ $EXIT_CODE -ne 0 ]]; then
    err "Codex finalizó con código de error: $EXIT_CODE"
    [[ -s "$STDERR_FILE" ]] && cat "$STDERR_FILE" >&2
    exit $EXIT_CODE
fi
