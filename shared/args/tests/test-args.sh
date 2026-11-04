#!/usr/bin/env bash
# test-args.sh - Cases for args.sh. Run: bash shared/args/tests/test-args.sh
set -u
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
script="$here/../args.sh"
pass=0
fail=0

# check <name> <expected> <args...>   (args passed as separate words)
check() {
  local name=$1 expected=$2
  shift 2
  local got
  got=$(bash "$script" "$@")
  local rc=$?
  if [ "$got" = "$expected" ] && [ "$rc" -eq 0 ]; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
    printf 'FAIL %s\n  expected: %s\n  got:      %s (exit %s)\n' "$name" "$expected" "$got" "$rc"
  fi
}

# check_one <name> <expected> <single string>   (the "$ARGUMENTS" form)
check_one() {
  check "$1" "$2" "$3"
}

check     'no args' \
          '{"pane":null,"spec":null,"effort":null,"positional":[]}'
check_one 'empty single arg' \
          '{"pane":null,"spec":null,"effort":null,"positional":[]}' ''
check     'positional only' \
          '{"pane":null,"spec":null,"effort":null,"positional":["123"]}' 123
check     'full set, split words' \
          '{"pane":true,"spec":"x.md","effort":"high","positional":["foo"]}' foo --pane --spec x.md high
check_one 'full set, one string' \
          '{"pane":true,"spec":"x.md","effort":"high","positional":["foo"]}' 'foo --pane --spec x.md high'
check_one 'one string, extra whitespace' \
          '{"pane":false,"spec":null,"effort":"low","positional":["a","b"]}' '  a   --no-pane  b  low '
check     'no-pane wins over pane, either order' \
          '{"pane":false,"spec":null,"effort":null,"positional":[]}' --no-pane --pane
check     'pane then no-pane' \
          '{"pane":false,"spec":null,"effort":null,"positional":[]}' --pane --no-pane
check     'spec with equals' \
          '{"pane":null,"spec":"#12","effort":null,"positional":[]}' --spec=#12
check     'spec equals empty value' \
          '{"pane":null,"spec":"","effort":null,"positional":[]}' --spec=
check     'spec consumes next token even if it looks like a flag' \
          '{"pane":null,"spec":"--weird","effort":null,"positional":[]}' --spec --weird
check     'trailing spec stays positional' \
          '{"pane":null,"spec":null,"effort":null,"positional":["42","--spec"]}' 42 --spec
check     'last spec wins' \
          '{"pane":null,"spec":"b.md","effort":null,"positional":[]}' --spec a.md --spec b.md
check     'first effort wins, later ones positional' \
          '{"pane":null,"spec":null,"effort":"medium","positional":["high","max"]}' medium high max
check     'effort is exact match' \
          '{"pane":null,"spec":null,"effort":null,"positional":["High","LOW","highest"]}' High LOW highest
check     'unknown flag is positional, order kept' \
          '{"pane":true,"spec":null,"effort":"low","positional":["--verbose","x","--k=v"]}' --verbose --pane x low --k=v
check     'escapes quotes and backslashes' \
          '{"pane":null,"spec":"a\"b","effort":null,"positional":["c\\d","e\"\\f"]}' --spec 'a"b' 'c\d' 'e"\f'
check     'glob characters are not expanded' \
          '{"pane":null,"spec":null,"effort":null,"positional":["*.md","?"]}' '*.md ?'
check     'url and path tokens pass through' \
          '{"pane":null,"spec":"docs/SPEC-0001.md","effort":"max","positional":["https://github.com/o/r/pull/7"]}' https://github.com/o/r/pull/7 --spec docs/SPEC-0001.md max

printf '%d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
