#!/usr/bin/env bash
# memory-check.sh — Flag auto-memory files whose claims may no longer be true
#
# Reads a project's auto-memory dir (~/.claude/projects/<encoded>/memory/*.md)
# and prints one line per finding:  <KIND> <file> — <detail>
#
#   STALE           the file's `verify:` command exited non-zero (or timed out)
#   MISSING-REF     a backticked repo path that does not exist, a commit hash
#                   git cannot find, or a MEMORY.md link to a missing file
#   UNVERIFIED-OLD  a `type: project` memory with no `verify:`, not modified
#                   in more than --days days
#   OPEN-CLAIM      no `verify:`, and the text says "not yet fixed", "pending",
#                   "flagged" or "TODO"
#   SKIPPED-VERIFY  a `verify:` that was not run (symlinked file, --max-predicates)
#
# Prints nothing when clean. Advisory: exits 0 whatever it finds; 2 on a usage error.
#
# Usage:
#   memory-check.sh                         # this project's memory, from $PWD
#   memory-check.sh --memory-dir <dir>      # a specific memory dir
#   memory-check.sh --project-root <dir>    # where paths resolve and verify: runs
#   memory-check.sh --days 14               # UNVERIFIED-OLD threshold (default 30)
#   memory-check.sh --timeout 5             # seconds per verify: command (default 5)
#   memory-check.sh --max-predicates 20     # run no verify: at all if more than N
#   memory-check.sh --no-predicates         # never run verify: commands
#   memory-check.sh --quiet-unless-stale    # print only STALE and MISSING-REF
#   memory-check.sh --json                  # JSON array of {kind, file, detail}
#
# `verify:` is a single-line frontmatter field holding a shell command that
# exits 0 while the memory's claim is still true. It runs with `bash -c` from
# the project root, stdin closed, output discarded, under the timeout. Only
# regular files directly inside the memory dir are ever executed.
#
# Requires: bash, git, awk; jq for --json. Works with GNU and BSD userlands.

set -u

DAYS=30
TIMEOUT=5
MAX_PREDICATES=0
RUN_PREDICATES=true
QUIET=false
JSON=false
MEMORY_DIR=""
PROJECT_ROOT=""

usage_error() { echo "memory-check: $*" >&2; exit 2; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --memory-dir)         MEMORY_DIR="${2:-}"; [[ -n "${MEMORY_DIR}" ]] || usage_error "--memory-dir needs a directory"; shift 2 ;;
        --project-root)       PROJECT_ROOT="${2:-}"; [[ -n "${PROJECT_ROOT}" ]] || usage_error "--project-root needs a directory"; shift 2 ;;
        --days)               DAYS="${2:-}"; shift 2 ;;
        --timeout)            TIMEOUT="${2:-}"; shift 2 ;;
        --max-predicates)     MAX_PREDICATES="${2:-}"; shift 2 ;;
        --no-predicates)      RUN_PREDICATES=false; shift ;;
        --quiet-unless-stale) QUIET=true; shift ;;
        --json)               JSON=true; shift ;;
        --help|-h)            sed -n '2,36p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *)                    usage_error "unknown argument: $1 (try --help)" ;;
    esac
done

[[ "${DAYS}" =~ ^[0-9]+$ ]] || usage_error "--days expects a number, got: ${DAYS}"
[[ "${TIMEOUT}" =~ ^[1-9][0-9]*$ ]] || usage_error "--timeout expects a positive number of seconds, got: ${TIMEOUT}"
[[ "${MAX_PREDICATES}" =~ ^[0-9]+$ ]] || usage_error "--max-predicates expects a number, got: ${MAX_PREDICATES}"
if ${JSON} && ! command -v jq >/dev/null 2>&1; then usage_error "--json needs jq (apt install jq / brew install jq)"; fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=project-dir.sh
. "${SCRIPT_DIR}/project-dir.sh"

# ── Locate the project root and the memory dir ────────────────────────────────
if [[ -z "${PROJECT_ROOT}" ]]; then
    PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi
PROJECT_ROOT="$(cd "${PROJECT_ROOT}" 2>/dev/null && pwd -P)" || usage_error "project root does not exist"

if [[ -z "${MEMORY_DIR}" ]]; then
    PROJECTS="$(claude_projects_dir)"
    while IFS= read -r candidate; do
        if [[ -d "${PROJECTS}/$(encode_project_dir "${candidate}")/memory" ]]; then
            MEMORY_DIR="${PROJECTS}/$(encode_project_dir "${candidate}")/memory"
            break
        fi
    done < <(memory_root_candidates "${PWD}")
    # No memory for this project: nothing to check, and nothing to say.
    [[ -n "${MEMORY_DIR}" ]] || exit 0
fi
[[ -d "${MEMORY_DIR}" ]] || usage_error "memory dir does not exist: ${MEMORY_DIR}"
MEMORY_DIR="$(cd "${MEMORY_DIR}" && pwd -P)"

IS_GIT=false
git -C "${PROJECT_ROOT}" rev-parse --git-dir >/dev/null 2>&1 && IS_GIT=true

WORK="$(mktemp -d "${TMPDIR:-/tmp}/memory-check.XXXXXX")" || exit 0
trap 'rm -rf "${WORK}"' EXIT

# ── Findings ──────────────────────────────────────────────────────────────────
: > "${WORK}/findings"
finding() {  # kind file detail
    local detail="${3//$'\t'/ }"
    detail="${detail//$'\n'/ }"
    printf '%s\t%s\t%s\n' "$1" "$2" "${detail}" >> "${WORK}/findings"
}

# ── Portable helpers ──────────────────────────────────────────────────────────
file_mtime() { stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0; }

iso_from_epoch() {
    date -u -d "@$1" '+%Y-%m-%dT%H:%M:%S' 2>/dev/null || date -u -r "$1" '+%Y-%m-%dT%H:%M:%S'
}

# Strip one level of YAML quoting from a single-line scalar.
unquote() {
    local v="$1"
    if [[ ${#v} -ge 2 && "${v:0:1}" == "'" && "${v: -1}" == "'" ]]; then
        v="${v:1:${#v}-2}"; v="${v//\'\'/\'}"
    elif [[ ${#v} -ge 2 && "${v:0:1}" == '"' && "${v: -1}" == '"' ]]; then
        v="${v:1:${#v}-2}"; v="${v//\\\"/\"}"; v="${v//\\\\/\\}"
    fi
    printf '%s' "${v}"
}

# Run "$1" with bash -c from the project root under TIMEOUT seconds; stdin
# closed, output discarded. Returns the exit code, 124 when it timed out.
# GNU/BSD `timeout` and the perl fallback all kill the predicate's whole
# process group, so a hung grandchild does not outlive the check.
run_predicate() {
    local cmd="$1" impl="${MEMORY_CHECK_TIMEOUT_IMPL:-}" rc
    if [[ -z "${impl}" ]]; then
        if command -v timeout >/dev/null 2>&1; then impl=timeout
        elif command -v gtimeout >/dev/null 2>&1; then impl=gtimeout
        else impl=perl
        fi
    fi
    if [[ "${impl}" == perl ]]; then
        ( cd "${PROJECT_ROOT}" && GIT_TERMINAL_PROMPT=0 perl -e '
            my $t = shift; my $pid = fork();
            if (!$pid) { setpgrp(0, 0); exec @ARGV; exit 127 }
            local $SIG{ALRM} = sub { kill "KILL", -$pid; waitpid($pid, 0); exit 124 };
            alarm $t; waitpid($pid, 0);
            exit(($? & 127) ? 1 : ($? >> 8));
          ' "${TIMEOUT}" bash -c "${cmd}" ) </dev/null >/dev/null 2>&1
        rc=$?
    else
        ( cd "${PROJECT_ROOT}" && GIT_TERMINAL_PROMPT=0 "${impl}" -k 1 "${TIMEOUT}" bash -c "${cmd}" ) </dev/null >/dev/null 2>&1
        rc=$?
        [[ ${rc} -eq 137 ]] && rc=124
    fi
    return ${rc}
}

# Repo file basenames, for bare names like `SKILL.md`; built on first use.
basename_known() {
    if [[ ! -f "${WORK}/basenames" ]]; then
        if ${IS_GIT}; then
            git -C "${PROJECT_ROOT}" ls-files -co --exclude-standard 2>/dev/null \
                | awk -F/ '{ print $NF }' | sort -u > "${WORK}/basenames"
        else
            : > "${WORK}/basenames"
        fi
    fi
    grep -qxF -- "$1" "${WORK}/basenames"
}

# Echo the path to check for a backticked span, or nothing when it is not a
# repo-relative file reference.
path_candidate() {
    local s="$1"
    [[ -n "${s}" ]] || return 0
    case "${s}" in
        *[[:space:]]*|/*|~*|*://*|-*|@*|.|..|../*) return 0 ;;
        *[\*\?\<\>\$\{\}\(\)\[\]=\|\;,\"\'\`\\]*) return 0 ;;
    esac
    s="${s#./}"
    s="${s%%#*}"
    while [[ "${s}" =~ ^(.*):[0-9]+(-[0-9]+)?$ ]]; do s="${BASH_REMATCH[1]}"; done
    [[ -n "${s}" ]] || return 0
    if [[ "${s}" == */* ]]; then
        printf '%s' "${s}"; return 0
    fi
    # A bare name starting with '.' is a suffix in prose (`.meta.json`), not a file.
    [[ "${s}" == .* ]] && return 0
    if [[ "${s}" =~ \.(md|sh|bash|zsh|json|jsonl|ts|tsx|js|mjs|cjs|py|yml|yaml|toml|txt|lock|cfg|ini|go|rs|html|css|sql)$ ]]; then
        printf '%s' "${s}"
    fi
}

check_ref() {  # file path
    local file="$1" p="$2" first
    if [[ "${p}" == */* ]]; then
        first="${p%%/*}"
        # A first segment that exists in neither place is not a repo path
        # (`some-package/sub`, `owner/repo`): not ours to judge.
        [[ -e "${PROJECT_ROOT}/${first}" || -e "${MEMORY_DIR}/${first}" ]] || return 0
        [[ -e "${PROJECT_ROOT}/${p}" || -e "${MEMORY_DIR}/${p}" ]] && return 0
        finding MISSING-REF "${file}" "\`${p}\` does not exist under the project root"
    else
        [[ -e "${PROJECT_ROOT}/${p}" || -e "${MEMORY_DIR}/${p}" ]] && return 0
        basename_known "${p}" && return 0
        finding MISSING-REF "${file}" "\`${p}\` is not a file anywhere in the project"
    fi
}

# Frontmatter fields as "key<TAB>value": verify, type, modified, description
# (top level or under metadata:). Only single-line scalars.
read_frontmatter() {
    awk '
        NR == 1 { if ($0 !~ /^---[ \t\r]*$/) exit; next }
        /^---[ \t\r]*$/ { exit }
        {
            line = $0; sub(/\r$/, "", line)
            if (match(line, /^[A-Za-z_][A-Za-z0-9_]*:/)) {
                parent = substr(line, 1, RLENGTH - 1); key = parent; val = substr(line, RLENGTH + 1)
            } else if (line ~ /^[ \t]+[A-Za-z_][A-Za-z0-9_]*:/) {
                sub(/^[ \t]+/, "", line); match(line, /^[A-Za-z_][A-Za-z0-9_]*:/)
                key = parent "." substr(line, 1, RLENGTH - 1); val = substr(line, RLENGTH + 1)
            } else next
            sub(/^[ \t]+/, "", val); sub(/[ \t]+$/, "", val)
            if (key == "verify" || key == "metadata.verify") k = "verify"
            else if (key == "type" || key == "metadata.type") k = "type"
            else if (key == "modified" || key == "metadata.modified") k = "modified"
            else if (key == "description") k = "description"
            else next
            if (!(k in seen)) { seen[k] = 1; print k "\t" val }
        }
    ' "$1"
}

read_body() {
    awk '
        NR == 1 && $0 ~ /^---[ \t\r]*$/ { infm = 1; next }
        infm && /^---[ \t\r]*$/ { infm = 0; next }
        !infm { print }
    ' "$1"
}

# Backticked spans outside fenced code blocks, one per line.
backtick_spans() {
    awk '
        /^[ \t]*(```|~~~)/ { fence = !fence; next }
        fence { next }
        { n = split($0, part, "`"); for (i = 2; i <= n; i += 2) if (i < n) print part[i] }
    ' "$1"
}

# 7–40 char lowercase hex tokens with at least one digit and one letter.
# '-' and '_' count as word characters, so UUID segments never match.
commit_like() {
    awk '
        {
            gsub(/[^0-9A-Za-z_-]/, " ")
            for (i = 1; i <= NF; i++) {
                t = $i
                if (length(t) >= 7 && length(t) <= 40 && t ~ /^[0-9a-f]+$/ && t ~ /[0-9]/ && t ~ /[a-f]/) print t
            }
        }
    ' "$1"
}

# ── Pass 1: parse ─────────────────────────────────────────────────────────────
FILES=()
while IFS= read -r f; do FILES+=("${f}"); done < <(
    cd "${MEMORY_DIR}" && for f in ./*.md; do [[ -e "${f}" ]] && printf '%s\n' "${f#./}"; done | LC_ALL=C sort
)

# Nothing to check (no memory files, maybe just the index). This also keeps
# bash 3.2's `set -u` away from the empty-array expansions below.
[[ ${#FILES[@]} -gt 0 ]] || exit 0

declare -a VERIFY=() TYPE=() MODIFIED=() DESCRIPTION=()
predicate_count=0
for i in "${!FILES[@]}"; do
    VERIFY[i]=""; TYPE[i]=""; MODIFIED[i]=""; DESCRIPTION[i]=""
    [[ "${FILES[i]}" == MEMORY.md ]] && continue
    while IFS=$'\t' read -r key val; do
        case "${key}" in
            verify)      VERIFY[i]="$(unquote "${val}")" ;;
            type)        TYPE[i]="$(unquote "${val}")" ;;
            modified)    MODIFIED[i]="$(unquote "${val}")" ;;
            description) DESCRIPTION[i]="$(unquote "${val}")" ;;
        esac
    done < <(read_frontmatter "${MEMORY_DIR}/${FILES[i]}")
    [[ -n "${VERIFY[i]}" ]] && predicate_count=$((predicate_count + 1))
done

SKIP_ALL_PREDICATES=false
if ! ${RUN_PREDICATES}; then
    SKIP_ALL_PREDICATES=true
elif [[ ${MAX_PREDICATES} -gt 0 && ${predicate_count} -gt ${MAX_PREDICATES} ]]; then
    SKIP_ALL_PREDICATES=true
    finding SKIPPED-VERIFY "*" "${predicate_count} verify: commands exceed --max-predicates ${MAX_PREDICATES}; none were run"
fi

NOW="$(date +%s)"
CUTOFF_EPOCH=$((NOW - DAYS * 86400))
CUTOFF_ISO="$(iso_from_epoch "${CUTOFF_EPOCH}")"

# ── Pass 2: check ─────────────────────────────────────────────────────────────
for i in "${!FILES[@]}"; do
    name="${FILES[i]}"
    path="${MEMORY_DIR}/${name}"

    if [[ "${name}" == MEMORY.md ]]; then
        # The index: every linked memory file must exist.
        while IFS= read -r target; do
            [[ "${target}" == *://* || "${target}" == /* ]] && continue
            target="${target%%#*}"
            [[ -n "${target}" && ! -e "${MEMORY_DIR}/${target}" ]] \
                && finding MISSING-REF "${name}" "index links to ${target}, which does not exist"
        done < <(grep -oE '\]\([^)]+\.md(#[^)]*)?\)' "${path}" 2>/dev/null | sed -E 's/^\]\(//; s/\)$//' | sort -u)
        continue
    fi

    read_body "${path}" > "${WORK}/body"
    { printf '%s\n' "${DESCRIPTION[i]}"; cat "${WORK}/body"; } > "${WORK}/text"
    verify="${VERIFY[i]}"

    # a) PREDICATE
    if [[ -n "${verify}" ]] && ! ${SKIP_ALL_PREDICATES}; then
        if [[ -L "${path}" || "$(cd "$(dirname "${path}")" && pwd -P)" != "${MEMORY_DIR}" ]]; then
            finding SKIPPED-VERIFY "${name}" "symlinked or outside the memory dir; verify: not run"
        else
            run_predicate "${verify}"
            rc=$?
            if [[ ${rc} -eq 124 ]]; then
                finding STALE "${name}" "verify timed out after ${TIMEOUT}s: ${verify}"
            elif [[ ${rc} -ne 0 ]]; then
                finding STALE "${name}" "verify exited ${rc}: ${verify}"
            fi
        fi
    fi

    # b) REFERENCES
    backtick_spans "${WORK}/text" | while IFS= read -r span; do
        p="$(path_candidate "${span}")"
        [[ -n "${p}" ]] && printf '%s\n' "${p}"
    done | sort -u > "${WORK}/refs"
    while IFS= read -r p; do check_ref "${name}" "${p}"; done < "${WORK}/refs"

    if ${IS_GIT}; then
        while IFS= read -r h; do
            git -C "${PROJECT_ROOT}" cat-file -e "${h}^{commit}" 2>/dev/null \
                || finding MISSING-REF "${name}" "commit ${h} not found in this repository"
        done < <(commit_like "${WORK}/text" | sort -u)
    fi

    # c) AGE and OPEN-CLAIM — only for memories nothing verifies
    [[ -n "${verify}" ]] && continue

    if [[ "${TYPE[i]}" == project ]]; then
        modified="${MODIFIED[i]}"
        if [[ "${modified}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2} ]]; then
            stamp="${modified:0:19}"; stamp="${stamp/ /T}"
            [[ "${stamp}" < "${CUTOFF_ISO}" ]] \
                && finding UNVERIFIED-OLD "${name}" "type project, no verify:, modified ${modified:0:10} (older than ${DAYS} days)"
        else
            mtime="$(file_mtime "${path}")"
            [[ ${mtime} -gt 0 && ${mtime} -lt ${CUTOFF_EPOCH} ]] \
                && finding UNVERIFIED-OLD "${name}" "type project, no verify:, file unchanged for $(( (NOW - mtime) / 86400 )) days"
        fi
    fi

    claim="$(grep -m1 -iE 'not yet fixed|pending|flagged' "${WORK}/text" || grep -m1 -E 'TODO' "${WORK}/text" || true)"
    if [[ -n "${claim}" ]]; then
        claim="$(printf '%s' "${claim}" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//' | cut -c1-120)"
        finding OPEN-CLAIM "${name}" "open claim with no verify: \"${claim}\""
    fi
done

# ── Output ────────────────────────────────────────────────────────────────────
if ${QUIET}; then
    awk -F'\t' '$1 == "STALE" || $1 == "MISSING-REF"' "${WORK}/findings" > "${WORK}/shown"
else
    cp "${WORK}/findings" "${WORK}/shown"
fi

if ${JSON}; then
    jq -Rn '[inputs | split("\t") | {kind: .[0], file: .[1], detail: .[2]}]' < "${WORK}/shown"
else
    awk -F'\t' '{ printf "%s %s — %s\n", $1, $2, $3 }' "${WORK}/shown"
fi
exit 0
