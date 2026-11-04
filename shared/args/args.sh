#!/usr/bin/env bash
# args.sh - Parse a slash command's $ARGUMENTS into one JSON line, without jq.
#
# Contract
#   Input:  the raw arguments as "$@". Both forms work:
#             args.sh $ARGUMENTS      (the shell already split the words)
#             args.sh "$ARGUMENTS"    (one argument; it is split on whitespace)
#           A single argument is always split on whitespace; an empty single
#           argument means no tokens. Tokens never contain whitespace, so
#           a spec path with spaces cannot be passed (quotes are not parsed).
#   Output: one line, always these four keys, in this order:
#             {"pane":true|false|null,"spec":"<value>"|null,
#              "effort":"low"|"medium"|"high"|"max"|null,"positional":["..."]}
#   Rules:
#     --pane      -> pane true.   --no-pane -> pane false; false wins if both appear.
#     --spec X    -> spec "X": the next token, whatever it is, is consumed.
#     --spec=X    -> spec "X" (X may be empty). A trailing --spec with nothing
#                    after it is left in positional so the caller can see it.
#     low|medium|high|max  -> effort, exact match, the FIRST one only; later
#                    ones are positional.
#     anything else, including an unknown --flag, is positional, in order.
#     The last --spec wins. `"` and `\` inside values are JSON-escaped.
#   Exit:   0 always. Nothing is a usage error: any input parses.
#
# Inside a command file `$ARGUMENTS` is substituted TEXTUALLY into a !` ` block
# before the shell runs, so wrap it in single quotes to keep `"`, `$(...)` and
# backticks in the user's input from being executed:
#   !`bash "${CLAUDE_PLUGIN_ROOT}/scripts/args.sh" '$ARGUMENTS'`
# A single quote in the user's input still breaks that line (the block's output
# becomes the shell error "unmatched '", measured); there is no quoting that
# survives every character under textual substitution. The shell runs with no
# positional parameters of its own ("$@" is empty, "$#" is 0), so $ARGUMENTS
# must be spelled out; `$1` in a command file is the SECOND word (0-indexed).

set -u

tokens=()
if [ "$#" -eq 1 ]; then
  set -f
  # shellcheck disable=SC2086  # intentional word splitting, globbing is off
  set -- $1
  set +f
fi
tokens=("$@")

pane=null
spec=null
spec_set=0
effort=null
positional=()

json_escape() {
  local s=$1
  s=${s//\\/\\\\}
  s=${s//\"/\\\"}
  printf '%s' "$s"
}

i=0
n=${#tokens[@]}
while [ "$i" -lt "$n" ]; do
  tok=${tokens[$i]}
  case $tok in
    --pane)
      [ "$pane" = false ] || pane=true
      ;;
    --no-pane)
      pane=false
      ;;
    --spec=*)
      spec=${tok#--spec=}
      spec_set=1
      ;;
    --spec)
      if [ $((i + 1)) -lt "$n" ]; then
        i=$((i + 1))
        spec=${tokens[$i]}
        spec_set=1
      else
        positional+=("$tok")
      fi
      ;;
    low|medium|high|max)
      if [ "$effort" = null ]; then
        effort=$tok
      else
        positional+=("$tok")
      fi
      ;;
    *)
      positional+=("$tok")
      ;;
  esac
  i=$((i + 1))
done

out='{"pane":'"$pane"',"spec":'
if [ "$spec_set" -eq 1 ]; then
  out+='"'"$(json_escape "$spec")"'"'
else
  out+='null'
fi
out+=',"effort":'
if [ "$effort" = null ]; then
  out+='null'
else
  out+='"'"$effort"'"'
fi
out+=',"positional":['
first=1
for p in "${positional[@]+"${positional[@]}"}"; do
  [ "$first" -eq 1 ] || out+=','
  first=0
  out+='"'"$(json_escape "$p")"'"'
done
out+=']}'
printf '%s\n' "$out"
exit 0
