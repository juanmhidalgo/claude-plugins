#!/usr/bin/env bash
# Offline tests for factory-issue.sh and factory-outcome.sh.
#
# A stub `gh` on PATH serves a recorded issue from $GH_STATE (labels and
# comments as JSON), mutates it on `issue comment` / `issue edit`, and logs
# every call to $GH_LOG, so the tests assert both on what the scripts print
# and on what they wrote, in which order. No network, no real gh.
#
# Usage: bash factory/scripts/test_factory_scripts.sh   (-v prints every command's output)

set -uo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
verbose=0; [ "${1:-}" = -v ] && verbose=1
pass=0; fail=0

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/bin" "$work/repo"
export GH_STATE="$work/state.json" GH_LOG="$work/gh.log" PATH="$work/bin:$PATH"
unset FACTORY_REPO

# A git repo so --sha can default to HEAD.
git -C "$work/repo" init -q && git -C "$work/repo" -c user.email=t@e.com -c user.name=t commit -q --allow-empty -m init
head_sha=$(git -C "$work/repo" rev-parse HEAD)

cat >"$work/bin/gh" <<'STUB'
#!/usr/bin/env bash
# gh stub: `issue view` reads $GH_STATE, `issue comment` / `issue edit` mutate it, every call is logged.
set -euo pipefail
printf '%s\n' "$*" >>"$GH_LOG"
case "$1 $2" in
  "repo view")
    if printf '%s\n' "$@" | grep -q nameWithOwner; then echo "stub-owner/stub-repo"; else echo '{"defaultBranchRef":{"name":"main"}}'; fi ;;
  "issue view")
    jq_expr=.
    while [ $# -gt 0 ]; do case $1 in -q) jq_expr=$2; shift ;; esac; shift; done
    jq -r "$jq_expr" "$GH_STATE" ;;
  "issue comment")
    file=
    while [ $# -gt 0 ]; do case $1 in --body-file) file=$2; shift ;; esac; shift; done
    [ -n "$file" ] || { echo "stub: --body-file required" >&2; exit 1; }
    n=$(jq '.comments | length' "$GH_STATE")
    jq --rawfile body "$file" --arg at "2026-11-01T10:00:$(printf '%02d' "$n")Z" \
      '.comments += [{author: {login: "stub-owner"}, body: $body, createdAt: $at}]' "$GH_STATE" >"$GH_STATE.tmp" && mv "$GH_STATE.tmp" "$GH_STATE" ;;
  "issue edit")
    rm= add=
    while [ $# -gt 0 ]; do case $1 in --remove-label) rm=$2; shift ;; --add-label) add=$2; shift ;; esac; shift; done
    jq --arg rm "$rm" --arg add "$add" '.labels |= (map(select(.name != $rm)) + [{name: $add}])' "$GH_STATE" >"$GH_STATE.tmp" && mv "$GH_STATE.tmp" "$GH_STATE" ;;
  *) echo "stub gh: unsupported: $*" >&2; exit 1 ;;
esac
STUB
chmod +x "$work/bin/gh"

# state <labels…> -- <comment>…   each comment is "login|body" (body with \n escapes)
state() {
  local labels=() comments=()
  while [ $# -gt 0 ] && [ "$1" != -- ]; do labels+=("$1"); shift; done
  [ "${1:-}" = -- ] && shift
  local i=0 json='{"labels":[],"comments":[]}'
  for l in "${labels[@]+"${labels[@]}"}"; do json=$(jq --arg n "$l" '.labels += [{name: $n}]' <<<"$json"); done
  for c in "$@"; do
    json=$(jq --arg login "${c%%|*}" --arg body "$(printf '%b' "${c#*|}")" --arg at "2026-11-01T09:00:$(printf '%02d' "$i")Z" \
      '.comments += [{author: {login: $login}, body: $body, createdAt: $at}]' <<<"$json"); i=$((i+1))
  done
  printf '%s' "$json" >"$GH_STATE"
  : >"$GH_LOG"
}

labels_now() { jq -r '[.labels[].name] | sort | join(" ")' "$GH_STATE"; }
last_comment() { jq -r '.comments | last | .body' "$GH_STATE"; }
last_line() { last_comment | sed -e '/^$/d' | tail -1; }
comment_count() { jq '.comments | length' "$GH_STATE"; }
export -f labels_now last_comment last_line comment_count

# run <name> <expected-rc> <expected-stdout-pattern|''> <cmd…>
run() {
  local name=$1 want_rc=$2 want_out=$3; shift 3
  local out rc
  out=$(cd "$work/repo" && "$@" 2>"$work/err"); rc=$?
  local ok=1
  [ "$rc" -eq "$want_rc" ] || ok=0
  if [ -n "$want_out" ]; then printf '%s' "$out" | grep -q -- "$want_out" || ok=0; fi
  if [ "$ok" = 1 ]; then pass=$((pass+1)); echo "PASS  $name"; else fail=$((fail+1)); echo "FAIL  $name (rc=$rc, wanted $want_rc; stdout: ${out:-<empty>}; stderr: $(cat "$work/err"))"; fi
  [ "$verbose" = 1 ] && printf '      stdout: %s\n' "${out:-<empty>}"
  return 0
}
# check <name> <condition…>
check() { local name=$1; shift; if "$@"; then pass=$((pass+1)); echo "PASS  $name"; else fail=$((fail+1)); echo "FAIL  $name"; fi; }
eq() { [ "$1" = "$2" ] || { echo "      got: $1" >&2; echo "      want: $2" >&2; return 1; }; }

ISSUE="$here/factory-issue.sh"; OUT="$here/factory-outcome.sh"
R=(--repo o/r)

# --- factory-issue.sh status / lane ----------------------------------------
state status:needs-spec factory:auto type:feature
run "status: prints the one status label" 0 '^status:needs-spec$' "$ISSUE" status 7 "${R[@]}"
run "status: FACTORY_REPO replaces --repo" 0 '^status:needs-spec$' env FACTORY_REPO=o/r "$ISSUE" status 7
run "status: repo from gh repo view when nothing else" 0 '^status:needs-spec$' "$ISSUE" status 7
check "status: gh repo view was called for the repo" grep -q 'repo view --json nameWithOwner' "$GH_LOG"
state factory:auto
run "status: no status label exits 2" 2 '' "$ISSUE" status 7 "${R[@]}"
state status:ready status:needs-spec factory:auto
run "status: two status labels exit 2" 2 '' "$ISSUE" status 7 "${R[@]}"
state status:ready factory:plan-gate
run "lane: plan-gate" 0 '^plan-gate$' "$ISSUE" lane 7 "${R[@]}"
state status:ready factory:spec-gate
run "lane: spec-gate" 0 '^spec-gate$' "$ISSUE" lane 7 "${R[@]}"
state status:ready factory:hold
run "lane: factory:hold is not a lane (exit 2)" 2 '' "$ISSUE" lane 7 "${R[@]}"
run "bad issue number exits 2" 2 '' "$ISSUE" status x "${R[@]}"

# --- factory-issue.sh last-marker / answer ----------------------------------
state status:in-progress factory:auto
run "last-marker: none without comments" 0 '^none$' "$ISSUE" last-marker 7 "${R[@]}"
state status:in-progress factory:auto -- 'h|just a human note' \
  'bot|<!-- factory:progress stage=implement step=1/3 sha=abc1234 run=r1 -->\nStep 1 pushed' \
  'bot|<!-- factory:done stage=implement sha=abc1234 run=r1 -->\n## TDD Results'
run "last-marker: done after progress (progress is not an outcome)" 0 '^done stage=implement sha=abc1234 run=r1$' "$ISSUE" last-marker 7 "${R[@]}"
state status:waiting-human factory:auto -- 'bot|<!-- factory:done stage=spec sha=abc1234 run=r1 -->\nreport' \
  'bot|<!-- factory:question id=u1 stage=plan from=status:needs-plan run=r2 -->\n**Question from the factory**\n\nWhich?'
run "last-marker: latest question wins over an earlier done" 0 '^question id=u1 stage=plan from=status:needs-plan run=r2$' "$ISSUE" last-marker 7 "${R[@]}"
run "answer: no human comment after the question exits 1" 1 '' "$ISSUE" answer 7 "${R[@]}"
state status:needs-plan factory:auto -- 'bot|<!-- factory:question id=u1 stage=plan from=status:needs-plan run=r2 -->\nWhich?' \
  'owner|Option 2, please' 'bot|<!-- factory:decision stage=plan run=r3 -->\nnot an answer' 'owner|and also keep the index'
out=$(cd "$work/repo" && "$ISSUE" answer 7 "${R[@]}")
check "answer: prints the human comments only, newest last" eq "$(printf '%s' "$out" | grep -c '^--- owner')" 2
check "answer: skips the marker comment between them" bash -c '! printf "%s" "$1" | grep -q "not an answer"' _ "$out"
check "answer: newest last" bash -c 'printf "%s" "$1" | tail -1 | grep -q "keep the index"' _ "$out"
state status:needs-plan factory:auto -- 'owner|a comment before any question'
run "answer: no question marker at all exits 1" 1 '' "$ISSUE" answer 7 "${R[@]}"
state status:in-progress factory:auto -- 'bot|<!-- factory:parked stage=harden reason=fix-tests-red run=r4 -->\n**Parked by the factory**'
run "last-marker: parked" 0 '^parked stage=harden reason=fix-tests-red run=r4$' "$ISSUE" last-marker 7 "${R[@]}"

# --- factory-issue.sh next-status (the lane table) ---------------------------
state status:needs-spec factory:auto;      run "next-status: spec/auto -> needs-plan" 0 '^status:needs-plan$' "$ISSUE" next-status 7 spec "${R[@]}"
state status:needs-spec factory:spec-gate; run "next-status: spec/spec-gate -> spec-review" 0 '^status:spec-review$' "$ISSUE" next-status 7 spec "${R[@]}"
state status:needs-spec factory:plan-gate; run "next-status: spec/plan-gate -> spec-review" 0 '^status:spec-review$' "$ISSUE" next-status 7 spec "${R[@]}"
state status:needs-plan factory:auto;      run "next-status: plan/auto -> ready" 0 '^status:ready$' "$ISSUE" next-status 7 plan "${R[@]}"
state status:needs-plan factory:spec-gate; run "next-status: plan/spec-gate -> ready" 0 '^status:ready$' "$ISSUE" next-status 7 plan "${R[@]}"
state status:needs-plan factory:plan-gate; run "next-status: plan/plan-gate -> plan-review" 0 '^status:plan-review$' "$ISSUE" next-status 7 plan "${R[@]}"
state status:ready factory:auto;           run "next-status: implement from ready -> in-progress" 0 '^status:in-progress$' "$ISSUE" next-status 7 implement "${R[@]}"
state status:in-progress factory:auto;     run "next-status: implement re-run stays in-progress" 0 '^status:in-progress$' "$ISSUE" next-status 7 implement "${R[@]}"
state status:in-progress factory:auto;     run "next-status: harden stays in-progress" 0 '^status:in-progress$' "$ISSUE" next-status 7 harden "${R[@]}"
state status:in-progress factory:auto;     run "next-status: ship -> in-review" 0 '^status:in-review$' "$ISSUE" next-status 7 ship "${R[@]}"
state status:needs-plan factory:auto;      run "next-status: status moved exits 3" 3 '' "$ISSUE" next-status 7 spec "${R[@]}"
state status:needs-spec;                   run "next-status: no lane exits 2" 2 '' "$ISSUE" next-status 7 spec "${R[@]}"
state status:needs-spec factory:auto;      run "next-status: unknown stage exits 2" 2 '' "$ISSUE" next-status 7 deploy "${R[@]}"

# --- factory-outcome.sh done -------------------------------------------------
printf '## Spec written\n\n- AC-1 ok\n' >"$work/body.md"
state status:needs-spec factory:auto
run "done: posts and flips (spec/auto)" 0 'flipped status:needs-spec -> status:needs-plan' "$OUT" done 7 --stage spec --run r1 --body-file "$work/body.md" "${R[@]}"
check "done: labels flipped" eq "$(labels_now)" "factory:auto status:needs-plan"
check "done: comment starts with the marker, sha from HEAD" eq "$(last_comment | head -1)" "<!-- factory:done stage=spec sha=$head_sha run=r1 -->"
check "done: body follows the marker" bash -c 'printf "%s" "$(last_comment)" | grep -q "AC-1 ok"'
check "done: the comment is posted before the flip" bash -c 'grep -n "issue comment" "$GH_LOG" | head -1 | cut -d: -f1 | xargs -I{} test {} -lt "$(grep -n "issue edit" "$GH_LOG" | head -1 | cut -d: -f1)"'
state status:in-progress factory:auto
run "done: harden leaves the status unchanged (no edit call)" 0 'status unchanged' "$OUT" done 7 --stage harden --run r1 --body-file "$work/body.md" --sha abc1234 "${R[@]}"
check "done: no gh issue edit for an unchanged status" bash -c '! grep -q "issue edit" "$GH_LOG"'
check "done: --sha overrides HEAD" eq "$(last_comment | head -1)" "<!-- factory:done stage=harden sha=abc1234 run=r1 -->"
state status:in-progress factory:plan-gate
run "done: --to overrides the lane table" 0 'flipped status:in-progress -> status:in-review' "$OUT" done 7 --stage ship --run r1 --body-file "$work/body.md" --to status:in-review "${R[@]}"
state status:needs-plan factory:auto
run "done: refused when the status moved (exit 3)" 3 '' "$OUT" done 7 --stage spec --run r1 --body-file "$work/body.md" "${R[@]}"
check "done: nothing posted on a refused flip" eq "$(comment_count)" 0
check "done: no edit on a refused flip" bash -c '! grep -q "issue edit" "$GH_LOG"'
state status:needs-spec factory:auto
run "done: empty body file exits 2" 2 '' "$OUT" done 7 --stage spec --run r1 --body-file /dev/null "${R[@]}"
run "done: bad stage exits 2" 2 '' "$OUT" done 7 --stage deploy --run r1 --body-file "$work/body.md" "${R[@]}"
run "done: missing --run exits 2" 2 '' "$OUT" done 7 --stage spec --body-file "$work/body.md" "${R[@]}"
check "done: argument errors post nothing" eq "$(comment_count)" 0

# --- factory-outcome.sh question --------------------------------------------
printf 'Which repos are in scope?\n\nOptions:\n1. API only (Recommended)\n2. API and the mobile app\n' >"$work/q.md"
state status:needs-spec factory:auto
run "question: posts and flips to waiting-human" 0 'flipped status:needs-spec -> status:waiting-human' "$OUT" question 7 --stage spec --run r1 --from status:needs-spec --body-file "$work/q.md" --id 11111111-2222-3333-4444-555555555555 "${R[@]}"
check "question: marker carries id, stage, from, run" eq "$(last_comment | head -1)" "<!-- factory:question id=11111111-2222-3333-4444-555555555555 stage=spec from=status:needs-spec run=r1 -->"
check "question: heading on line 2, then the body" bash -c 'printf "%s" "$(last_comment)" | sed -n 2p | grep -q "^\*\*Question from the factory\*\* (stage \`spec\`)$"'
check "question: options reach the comment" bash -c 'printf "%s" "$(last_comment)" | grep -q "(Recommended)"'
check "question: labels" eq "$(labels_now)" "factory:auto status:waiting-human"
state status:needs-spec factory:auto
run "question: id generated when not given" 0 'flipped' "$OUT" question 7 --stage spec --run r1 --from status:needs-spec --body-file "$work/q.md" "${R[@]}"
check "question: generated id is a uuid" bash -c 'printf "%s" "$(last_comment | head -1)" | grep -Eq "id=[0-9a-f-]{36} "'
state status:needs-plan factory:auto
run "question: refused when from is absent (exit 3)" 3 '' "$OUT" question 7 --stage spec --run r1 --from status:needs-spec --body-file "$work/q.md" "${R[@]}"
check "question: nothing posted when refused" eq "$(comment_count)" 0
run "question: --from required" 2 '' "$OUT" question 7 --stage spec --run r1 --body-file "$work/q.md" "${R[@]}"

# --- factory-outcome.sh parked ----------------------------------------------
printf 'Push rejected.\n\nHow to recover:\n```\ngit fetch origin\n```\n' >"$work/p.md"
state status:in-progress factory:auto
run "parked: posts and flips to needs-human" 0 'flipped status:in-progress -> status:needs-human' "$OUT" parked 7 --stage implement --run r1 --reason push-rejected --from status:in-progress --body-file "$work/p.md" "${R[@]}"
check "parked: marker" eq "$(last_comment | head -1)" "<!-- factory:parked stage=implement reason=push-rejected run=r1 -->"
check "parked: heading names the reason" bash -c 'printf "%s" "$(last_comment)" | sed -n 2p | grep -q "reason \`push-rejected\`"'
state status:in-progress factory:auto
run "parked: without --from flips the current status" 0 'flipped status:in-progress -> status:needs-human' "$OUT" parked 7 --stage implement --run r1 --reason step-gap --body-file "$work/p.md" "${R[@]}"
state status:blocked factory:auto
run "parked: status-moved posts but does not flip (the human's label wins)" 0 'no flip: status:in-progress is not on #7' "$OUT" parked 7 --stage implement --run r1 --reason status-moved --from status:in-progress --body-file "$work/p.md" "${R[@]}"
check "parked: comment posted anyway" eq "$(comment_count)" 1
check "parked: labels untouched" eq "$(labels_now)" "factory:auto status:blocked"
run "parked: reason must be a slug" 2 '' "$OUT" parked 7 --stage implement --run r1 --reason "Push Rejected" --body-file "$work/p.md" "${R[@]}"
state factory:auto
run "parked: no status label at all still posts, no flip" 0 'no flip: #7 has no single status' "$OUT" parked 7 --stage spec --run r1 --reason not-eligible --body-file "$work/p.md" "${R[@]}"
check "parked: comment posted on a malformed issue" eq "$(comment_count)" 1

# --- progress / decision / flip ---------------------------------------------
state status:in-progress factory:auto
run "progress: posts, no flip" 0 '' "$OUT" progress 7 --stage implement --run r1 --step 2/5 --sha abc1234 "${R[@]}"
check "progress: marker" eq "$(last_comment | head -1)" "<!-- factory:progress stage=implement step=2/5 sha=abc1234 run=r1 -->"
check "progress: default body names the step" bash -c 'printf "%s" "$(last_comment)" | grep -q "Step 2/5 of the plan pushed"'
check "progress: no edit call" bash -c '! grep -q "issue edit" "$GH_LOG"'
run "progress: --step must be n/T" 2 '' "$OUT" progress 7 --stage implement --run r1 --step two "${R[@]}"
printf '## Decision — my-feature\n\n- **[repo: r · step 2]** the API owns the code.\n' >"$work/d.md"
run "decision: posts with the marker as the first line" 0 '' "$OUT" decision 7 --stage implement --run r1 --body-file "$work/d.md" "${R[@]}"
check "decision: marker first" eq "$(last_comment | head -1)" "<!-- factory:decision stage=implement run=r1 -->"
check "decision: heading on line 2" eq "$(last_comment | sed -n 2p)" "## Decision — my-feature"
check "decision: answer does not read it as a human comment" bash -c '! (cd "$0" && "$1" answer 7 --repo o/r | grep -q "my-feature")' "$work/repo" "$ISSUE"
check "decision: last-marker ignores it" eq "$(cd "$work/repo" && "$ISSUE" last-marker 7 "${R[@]}")" "none"
state status:needs-spec factory:spec-gate
run "flip: only the label flip (idempotent restart)" 0 'flipped status:needs-spec -> status:spec-review' "$OUT" flip 7 --stage spec "${R[@]}"
check "flip: no comment posted" eq "$(comment_count)" 0
state status:needs-plan factory:spec-gate
run "flip: refused when the status moved" 3 '' "$OUT" flip 7 --stage spec "${R[@]}"

echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
