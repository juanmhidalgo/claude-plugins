#!/usr/bin/env bash
# Tests for scripts/run-tests.sh against fixture directories and stub runners.
#   bash code-review/tests/test-run-tests.sh
set -uo pipefail

here=$(cd "$(dirname "$0")" && pwd)
script="$here/../scripts/run-tests.sh"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
pass=0; fail=0

# --- stub runners: each runs the project's own test script or exits as told ---
mkdir -p "$tmp/bin"
for pm in npm pnpm yarn; do
  cat > "$tmp/bin/$pm" <<STUB
#!/usr/bin/env bash
# stub $pm: runs the package.json test script with sh
[ "\${1:-}" = test ] || { echo "stub $pm: unexpected \$*" >&2; exit 99; }
script=\$(sed -n 's/.*"test"[[:space:]]*:[[:space:]]*"\\(\\([^"\\\\]\\|\\\\.\\)*\\)".*/\\1/p' package.json | head -n 1)
echo "stub $pm running: \$script"
sh -c "\$script"
STUB
  chmod +x "$tmp/bin/$pm"
done
cat > "$tmp/bin/pytest" <<'STUB'
#!/usr/bin/env bash
echo "stub pytest $*"
[ -f FAIL ] && { echo "1 failed"; exit 1; }
echo "3 passed"
STUB
cat > "$tmp/bin/uv" <<'STUB'
#!/usr/bin/env bash
echo "stub uv $*"
[ "${1:-} ${2:-}" = "run pytest" ] || exit 99
exec pytest "${@:3}"
STUB
chmod +x "$tmp/bin/pytest" "$tmp/bin/uv"
export PATH="$tmp/bin:$PATH"

check() { # name expected_exit actual_exit [extra condition]
  local name=$1 want=$2 got=$3 cond=${4:-true}
  if [ "$want" = "$got" ] && eval "$cond"; then pass=$((pass+1)); echo "ok   $name"
  else fail=$((fail+1)); echo "FAIL $name (exit want=$want got=$got, cond: $cond)"; echo "     out: $out"; echo "     err: $(cat "$tmp/err")"; fi
}
run() { # fixture-dir [args...]
  local dir=$1; shift
  out=$(cd "$dir" && "$script" "$@" 2>"$tmp/err"); rc=$?
}
field() { # key -> value of a string/number/bool field in $out, without jq
  sed -n "s/.*\"$1\":\"\\{0,1\\}\([^\",}]*\)\"\\{0,1\\}.*/\1/p" <<<"$out"
}
log_of() { sed -n 's/.*"log":"\([^"]*\)".*/\1/p' <<<"$out"; }
valid_json() { command -v python3 >/dev/null 2>&1 || return 0; python3 -I -c 'import json,sys; json.loads(sys.stdin.read())' <<<"$out" 2>/dev/null; }
fixture() { local d="$tmp/fx/$1"; mkdir -p "$d"; echo "$d"; }

# 1. Makefile test target, passing
d=$(fixture make-pass); printf 'test:\n\t@echo running make tests\n\t@true\n' > "$d/Makefile"
run "$d" --out "$d/out"; check "make: passing target is 0" 0 $rc '[ "$(field runner)" = make ] && [ "$(field command)" = "make test" ] && [ "$(field passed)" = true ] && valid_json'
check "make: log file holds the output" 0 $rc 'grep -q "running make tests" "$(log_of)"'

# 2. Makefile test target, failing
d=$(fixture make-fail); printf 'test:\n\t@echo "assert 1 == 2 \\"boom\\" \\\\ back"\n\t@exit 3\n' > "$d/Makefile"
run "$d" --out "$d/out"; check "make: failing target is 1, exit kept" 1 $rc '[ "$(field passed)" = false ] && [ "$(field exit)" = 2 ] && valid_json'
check "make: tail is JSON-escaped" 1 $rc 'grep -q "assert 1 == 2 \\\\\"boom\\\\\" \\\\\\\\ back" <<<"$out"'

# 3. Makefile without a test target, nothing else -> 10
d=$(fixture make-no-target); printf 'build:\n\t@true\n' > "$d/Makefile"
run "$d" --out "$d/out"; check "make: no test target is 10" 10 $rc '[ -z "$out" ]'

# 4. package.json test script exit 0, stub npm
d=$(fixture npm-pass); printf '{\n  "name": "x",\n  "scripts": {\n    "test": "exit 0"\n  }\n}\n' > "$d/package.json"
run "$d" --out "$d/out"; check "npm: exit 0 script passes" 0 $rc '[ "$(field runner)" = npm ] && [ "$(field command)" = "npm test" ] && grep -q "stub npm running" "$(log_of)"'

# 5. package.json test script exit 1
d=$(fixture npm-fail); printf '{"scripts": {"test": "exit 1"}}\n' > "$d/package.json"
run "$d" --out "$d/out"; check "npm: exit 1 script fails" 1 $rc '[ "$(field passed)" = false ] && [ "$(field exit)" = 1 ]'

# 6. lockfile picks the package manager
d=$(fixture pnpm); printf '{"scripts": {"test": "exit 0"}}\n' > "$d/package.json"; : > "$d/pnpm-lock.yaml"
run "$d" --out "$d/out"; check "npm: pnpm-lock.yaml picks pnpm" 0 $rc '[ "$(field runner)" = pnpm ] && [ "$(field command)" = "pnpm test" ]'
d=$(fixture yarn); printf '{"scripts": {"test": "exit 0"}}\n' > "$d/package.json"; : > "$d/yarn.lock"
run "$d" --out "$d/out"; check "npm: yarn.lock picks yarn" 0 $rc '[ "$(field runner)" = yarn ]'

# 7. npm's scaffold test script does not count
d=$(fixture npm-scaffold); printf '{"scripts": {"test": "echo \\"Error: no test specified\\" && exit 1"}}\n' > "$d/package.json"
run "$d" --out "$d/out"; check "npm: scaffold script is not a runner" 10 $rc

# 8. pyproject naming pytest, stub pytest
d=$(fixture pytest-pass); printf '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n' > "$d/pyproject.toml"
run "$d" --out "$d/out"; check "pytest: pyproject config runs pytest" 0 $rc '[ "$(field runner)" = pytest ] && [ "$(field command)" = pytest ] && grep -q "3 passed" "$(log_of)"'
: > "$d/FAIL"
run "$d" --out "$d/out"; check "pytest: failure is 1 with the tail" 1 $rc '[ "$(field passed)" = false ] && grep -q "1 failed" <<<"$out"'

# 9. uv.lock -> uv run pytest
d=$(fixture pytest-uv); printf '[tool.pytest.ini_options]\n' > "$d/pyproject.toml"; : > "$d/uv.lock"
run "$d" --out "$d/out"; check "pytest: uv.lock runs uv run pytest" 0 $rc '[ "$(field command)" = "uv run pytest" ] && grep -q "stub uv run pytest" "$(log_of)"'

# 10. pytest.ini alone, conftest alone
d=$(fixture pytest-ini); : > "$d/pytest.ini"
run "$d" --out "$d/out"; check "pytest: pytest.ini is enough" 0 $rc '[ "$(field runner)" = pytest ]'
d=$(fixture pytest-conftest); : > "$d/conftest.py"
run "$d" --out "$d/out"; check "pytest: conftest.py is enough" 0 $rc '[ "$(field runner)" = pytest ]'

# 11. Makefile wins over package.json and pyproject
d=$(fixture order); printf 'test:\n\t@true\n' > "$d/Makefile"; printf '{"scripts": {"test": "exit 1"}}\n' > "$d/package.json"; printf '[tool.pytest.ini_options]\n' > "$d/pyproject.toml"
run "$d" --out "$d/out"; check "order: Makefile first" 0 $rc '[ "$(field runner)" = make ]'
rm "$d/Makefile"
run "$d" --out "$d/out"; check "order: package.json before pyproject" 1 $rc '[ "$(field runner)" = npm ]'

# 12. --runner skips discovery
d=$(fixture override); printf 'test:\n\t@exit 1\n' > "$d/Makefile"
run "$d" --runner pytest --out "$d/out"; check "--runner: forces pytest over the Makefile" 0 $rc '[ "$(field runner)" = pytest ]'
run "$d" --runner=pytest --out "$d/out"; check "--runner=: same" 0 $rc '[ "$(field runner)" = pytest ]'
run "$d" --runner nope --out "$d/out"; check "--runner: unknown name is 2" 2 $rc
run "$d" --bogus; check "unknown flag is 2" 2 $rc

# 13. empty directory -> 10
d=$(fixture empty)
run "$d" --out "$d/out"; check "empty dir is 10" 10 $rc '[ -z "$out" ] && grep -q "no test runner" "$tmp/err"'

# 14. default --out is <git-dir>/code-review-tests in a repository
d=$(fixture default-out); printf 'test:\n\t@true\n' > "$d/Makefile"; git init -q "$d"
run "$d"; check "default out dir is .git/code-review-tests" 0 $rc 'case "$(log_of)" in "$d/.git/code-review-tests/run-"*.log) [ -f "$(log_of)" ] ;; *) false ;; esac'

# 15. default --out outside a repository
d=$(fixture default-out-norepo); printf 'test:\n\t@true\n' > "$d/Makefile"
run "$d"; check "default out dir outside git is ./.code-review-tests" 0 $rc 'case "$(log_of)" in "$d/.code-review-tests/run-"*.log) true ;; *) false ;; esac'

# 16. runner found, command missing -> 11 (cargo stub removed from a PATH of stubs only)
d=$(fixture cargo-missing); : > "$d/Cargo.toml"
out=$(cd "$d" && PATH="$tmp/bin:$(dirname "$(command -v tail)")" "$script" --out "$d/out" 2>"$tmp/err"); rc=$?
if command -v cargo >/dev/null 2>&1 && [ "$(dirname "$(command -v cargo)")" = "$(dirname "$(command -v tail)")" ]; then
  echo "skip cargo missing is 11 (cargo lives next to tail on this machine)"
else
  check "runner found, command missing is 11" 11 $rc '[ -z "$out" ] && grep -q "not installed" "$tmp/err"'
fi

# 17. control characters are dropped from the tail, tabs kept
d=$(fixture ansi); printf 'test:\n\t@printf "\\033[31mred\\033[0m\\tcol\\n"\n\t@true\n' > "$d/Makefile"
run "$d" --out "$d/out"; check "tail: ANSI dropped, tab escaped" 0 $rc 'grep -q "0m\\\\tcol" <<<"$out" && ! grep -q $'"'"'\033'"'"' <<<"$out" && valid_json'

echo; echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
