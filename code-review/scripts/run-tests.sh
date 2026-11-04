#!/usr/bin/env bash
# run-tests.sh — Phase 5 of /code-review:pipeline as one step: find the project's
# test runner, run it with the output captured to a file, report one JSON line.
#
#   run-tests.sh [--runner <name>] [--out <dir>]
#
# Discovery, in the current directory, first match wins:
#   make    a Makefile (or GNUmakefile/makefile) with a `test` target   -> make test
#   npm     package.json with a `test` script                            -> <pm> test
#           where <pm> is pnpm (pnpm-lock.yaml), yarn (yarn.lock) or npm.
#           npm's scaffold script ("no test specified") does not count.
#   pytest  pytest.ini, conftest.py, or pyproject.toml / setup.cfg / tox.ini
#           naming pytest                                                -> uv run pytest
#           when uv.lock exists and uv is installed, else pytest
#   cargo   Cargo.toml                                                   -> cargo test
#   go      go.mod                                                       -> go test ./...
# A Makefile target goes first because it is authored for the project; the
# others are inferred from manifests.
#
# --runner <make|npm|pnpm|yarn|pytest|cargo|go> skips discovery and runs that one.
# --out <dir> is where the log lands (default: <git-dir>/code-review-tests, or
# ./.code-review-tests outside a repository). One file per run.
#
# Output: one JSON line on stdout, always these keys:
#   {"runner":"make","command":"make test","exit":1,"passed":false,
#    "log":"/abs/path/run-<stamp>.log","tail":"<last 30 lines, JSON-escaped>"}
# Control characters other than tab and newline are dropped from `tail`.
# The runner's own output goes to the log only, never to stdout.
#
# Exit codes
#   0   tests passed
#   1   tests failed (the runner's exit code is in `exit`)
#   2   usage error
#   10  no runner found (nothing on stdout)
#   11  a runner was found but its command is not installed (nothing on stdout)

set -uo pipefail

runner=""
out_dir=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --runner) [ "$#" -ge 2 ] || { echo "usage: run-tests.sh [--runner <name>] [--out <dir>]" >&2; exit 2; }; runner=$2; shift 2 ;;
    --runner=*) runner=${1#--runner=}; shift ;;
    --out) [ "$#" -ge 2 ] || { echo "usage: run-tests.sh [--runner <name>] [--out <dir>]" >&2; exit 2; }; out_dir=$2; shift 2 ;;
    --out=*) out_dir=${1#--out=}; shift ;;
    -h|--help) sed -n '2,36p' "$0"; exit 0 ;;
    *) echo "run-tests.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done

json_escape() {
  # Backslash and quote escaped, tab and newline as \t \n, every other control
  # character dropped (ANSI colour codes in test output would break the JSON).
  LC_ALL=C tr -d '\000-\010\013-\037\177' | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/\t/\\t/g' | sed -e ':a' -e 'N' -e '$!ba' -e 's/\n/\\n/g'
}

has_make_test() {
  local f
  for f in GNUmakefile makefile Makefile; do
    [ -f "$f" ] && grep -Eq '^test[[:space:]]*:' "$f" && return 0
  done
  return 1
}

has_npm_test() {
  [ -f package.json ] || return 1
  local script
  # The script's value, with escaped quotes allowed inside it; the first "test"
  # key in the file, which is the scripts entry in practice.
  script=$(sed -n 's/.*"test"[[:space:]]*:[[:space:]]*"\(\([^"\\]\|\\.\)*\)".*/\1/p' package.json | head -n 1)
  [ -n "$script" ] || return 1
  case "$script" in *"no test specified"*) return 1 ;; esac
  return 0
}

node_pm() {
  if [ -f pnpm-lock.yaml ]; then echo pnpm
  elif [ -f yarn.lock ]; then echo yarn
  else echo npm
  fi
}

has_pytest() {
  [ -f pytest.ini ] && return 0
  [ -f conftest.py ] && return 0
  local f
  for f in pyproject.toml setup.cfg tox.ini; do
    [ -f "$f" ] && grep -q 'pytest' "$f" && return 0
  done
  return 1
}

pytest_command() {
  if [ -f uv.lock ] && command -v uv >/dev/null 2>&1; then echo "uv run pytest"; else echo "pytest"; fi
}

# Discovery: first match wins.
if [ -z "$runner" ]; then
  if has_make_test; then runner='make'
  elif has_npm_test; then runner=$(node_pm)
  elif has_pytest; then runner=pytest
  elif [ -f Cargo.toml ]; then runner=cargo
  elif [ -f go.mod ]; then runner=go
  else
    echo "run-tests.sh: no test runner found in $PWD (looked for a Makefile test target, package.json test script, pytest config, Cargo.toml, go.mod)" >&2
    exit 10
  fi
fi

case "$runner" in
  make) cmd="make test" ;;
  npm) cmd="npm test" ;;
  pnpm) cmd="pnpm test" ;;
  yarn) cmd="yarn test" ;;
  pytest) cmd=$(pytest_command) ;;
  cargo) cmd="cargo test" ;;
  go) cmd="go test ./..." ;;
  *) echo "run-tests.sh: unknown runner '$runner' (make|npm|pnpm|yarn|pytest|cargo|go)" >&2; exit 2 ;;
esac

bin=${cmd%% *}
command -v "$bin" >/dev/null 2>&1 || { echo "run-tests.sh: runner '$runner' needs '$bin', which is not installed" >&2; exit 11; }

if [ -z "$out_dir" ]; then
  if git_dir=$(git rev-parse --git-dir 2>/dev/null); then
    out_dir="$git_dir/code-review-tests"
  else
    out_dir="$PWD/.code-review-tests"
  fi
fi
mkdir -p "$out_dir" || { echo "run-tests.sh: cannot create $out_dir" >&2; exit 2; }
out_dir=$(cd "$out_dir" && pwd)
log="$out_dir/run-$(date +%Y%m%d-%H%M%S)-$$.log"

{ echo "# $cmd"; echo "# cwd: $PWD"; } > "$log"
# shellcheck disable=SC2086  # the command is one of the fixed strings above
$cmd >> "$log" 2>&1 < /dev/null
code=$?

if [ "$code" -eq 0 ]; then passed=true; else passed=false; fi
tail_text=$(tail -n 30 "$log" | json_escape)
printf '{"runner":"%s","command":"%s","exit":%d,"passed":%s,"log":"%s","tail":"%s"}\n' \
  "$runner" "$cmd" "$code" "$passed" "$(printf '%s' "$log" | json_escape)" "$tail_text"

[ "$code" -eq 0 ] && exit 0
exit 1
