#!/usr/bin/env bash
# factory-outcome.sh - the write side of a factory stage: the only place a
# `<!-- factory:… -->` marker is typed. A command never writes one by hand.
#
# Every comment starts with its marker line. done | question | parked are the
# three outcomes (the comment, then the status:* flip, in that order); progress
# and decision are intermediate comments with no flip; flip is the label flip
# alone, for the idempotent restart after a crash between the comment and the flip.
# parked without --from flips whatever single status:* label the issue has, and
# only posts when it has none (or two): the park must land even on a malformed issue.
#
# Usage:
#   factory-outcome.sh done      <N> --stage <s> --run <id> --body-file <f> [--sha <head>] [--to <label>]
#   factory-outcome.sh question  <N> --stage <s> --run <id> --body-file <f> --from <label> [--id <uuid>]
#   factory-outcome.sh parked    <N> --stage <s> --run <id> --body-file <f> --reason <slug> [--from <label>]
#   factory-outcome.sh progress  <N> --stage <s> --run <id> --step <n>/<T> [--sha <head>] [--body-file <f>]
#   factory-outcome.sh decision  <N> --stage <s> --run <id> --body-file <f>
#   factory-outcome.sh flip      <N> --stage <s>
#
# Common: --repo <owner/name> (else FACTORY_REPO, else `gh repo view`). Bodies
# are always files, never argv. --sha defaults to `git rev-parse HEAD`.
#
# Markers:
#   <!-- factory:done stage=<s> sha=<head> run=<id> -->
#   <!-- factory:question id=<uuid> stage=<s> from=<label> run=<id> -->
#   <!-- factory:parked stage=<s> reason=<slug> run=<id> -->
#   <!-- factory:progress stage=<s> step=<n>/<T> sha=<head> run=<id> -->
#   <!-- factory:decision stage=<s> run=<id> -->          (first line too: the marker rule has no exception)
#
# The flip is `gh issue edit --remove-label <from> --add-label <to>`, refused
# (exit 3, nothing posted) when <from> is not on the issue: a human moved it
# meanwhile. The caller then ends `parked --reason status-moved --from <from>`,
# which posts its comment and, since <from> is absent, flips nothing: the
# human's label wins. done derives <to> from factory-issue.sh next-status
# (the lane table) unless --to is given; a stage whose done leaves the status
# unchanged (implement on a re-run, harden) makes no edit call.
#
# Exit codes: 0 ok · 2 bad arguments · 3 refused flip (status-moved) · gh's own
# code when a gh call fails (nothing is retried here; the caller retries once).

set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
usage() { sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }
die() { echo "factory-outcome: $*" >&2; exit "${2:-2}"; }

[ $# -ge 2 ] || usage
cmd=$1; issue=$2; shift 2
[[ $issue =~ ^[1-9][0-9]*$ ]] || die "issue number expected, got '$issue'"

repo=${FACTORY_REPO:-} stage= run= body= sha= to= from= qid= reason= step=
while [ $# -gt 0 ]; do
  case $1 in
    --repo) repo=$2 ;; --stage) stage=$2 ;; --run) run=$2 ;; --body-file) body=$2 ;;
    --sha) sha=$2 ;; --to) to=$2 ;; --from) from=$2 ;; --id) qid=$2 ;;
    --reason) reason=$2 ;; --step) step=$2 ;;
    -h|--help) usage ;;
    *) die "unknown option '$1'" ;;
  esac
  [ $# -ge 2 ] || die "$1 needs a value"
  shift 2
done

case $stage in spec|plan|implement|harden|ship) ;; *) die "--stage must be one of spec | plan | implement | harden | ship" ;; esac
if [ -z "$repo" ]; then
  repo=$(gh repo view --json nameWithOwner -q .nameWithOwner) || die "cannot resolve the repository (pass --repo or set FACTORY_REPO)"
fi
need_run() { [[ $run =~ ^[A-Za-z0-9._:-]+$ ]] || die "--run <id> is required ([A-Za-z0-9._:-])"; }
need_body() { [ -n "$body" ] && [ -s "$body" ] || die "--body-file must name a non-empty file"; }
need_sha() {
  [ -n "$sha" ] || sha=$(git rev-parse HEAD 2>/dev/null) || die "--sha is required outside a git repository"
  [[ $sha =~ ^[0-9a-f]{7,40}$ ]] || die "--sha must be a commit hash"
}
label_ok() { [[ $1 =~ ^status:[a-z-]+$ ]] || die "$2 must be a status:* label, got '$1'"; }

has_label() {  # has_label <label>: 0 when the issue carries it
  gh issue view "$issue" --repo "$repo" --json labels -q '.labels[].name' | grep -qx -- "$1"
}

post() {  # post <marker> <body-file|-> <heading|''>: the marker is always the first line
  local marker=$1 src=$2 heading=$3 tmp
  tmp=$(mktemp "${TMPDIR:-/tmp}/factory-outcome.XXXXXX")
  {
    printf '%s\n' "$marker"
    [ -z "$heading" ] || printf '%s\n\n' "$heading"
    if [ "$src" != - ]; then cat -- "$src"; fi
  } >"$tmp"
  gh issue comment "$issue" --repo "$repo" --body-file "$tmp"
  rm -f "$tmp"
}

flip() {  # flip <from> <to>: no call when equal
  [ "$1" = "$2" ] && { echo "status unchanged: $1"; return 0; }
  gh issue edit "$issue" --repo "$repo" --remove-label "$1" --add-label "$2"
  echo "flipped $1 -> $2"
}

case $cmd in
  done)
    need_run; need_body; need_sha
    current=$("$here/factory-issue.sh" status "$issue" --repo "$repo")
    if [ -z "$to" ]; then
      to=$("$here/factory-issue.sh" next-status "$issue" "$stage" --repo "$repo") || {
        rc=$?; [ "$rc" -eq 3 ] && die "refused: status moved (#$issue is $current); end parked --reason status-moved" 3; exit "$rc"; }
    else
      label_ok "$to" --to
    fi
    post "<!-- factory:done stage=$stage sha=$sha run=$run -->" "$body" ""
    flip "$current" "$to" ;;
  question)
    need_run; need_body; [ -n "$from" ] || die "--from <status label> is required"; label_ok "$from" --from
    [ -n "$qid" ] || qid=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid 2>/dev/null || python3 -c 'import uuid; print(uuid.uuid4())')
    has_label "$from" || die "refused: $from is not on #$issue (status moved); end parked --reason status-moved --from $from" 3
    post "<!-- factory:question id=$qid stage=$stage from=$from run=$run -->" "$body" "**Question from the factory** (stage \`$stage\`)"
    flip "$from" status:waiting-human ;;
  parked)
    need_run; need_body; [[ $reason =~ ^[a-z0-9-]+$ ]] || die "--reason <slug> is required ([a-z0-9-])"
    post "<!-- factory:parked stage=$stage reason=$reason run=$run -->" "$body" "**Parked by the factory** (stage \`$stage\`, reason \`$reason\`)"
    if [ -n "$from" ]; then
      label_ok "$from" --from
      if has_label "$from"; then flip "$from" status:needs-human
      else echo "no flip: $from is not on #$issue (moved by hand; that label wins)"; fi
    elif current=$("$here/factory-issue.sh" status "$issue" --repo "$repo" 2>/dev/null); then
      flip "$current" status:needs-human
    else
      echo "no flip: #$issue has no single status:* label"
    fi ;;
  progress)
    need_run; need_sha; [[ $step =~ ^[0-9]+/[0-9]+$ ]] || die "--step <n>/<T> is required"
    if [ -n "$body" ]; then need_body; src=$body; else src=-; fi
    post "<!-- factory:progress stage=$stage step=$step sha=$sha run=$run -->" "$src" "Step $step of the plan pushed as \`$sha\`." ;;
  decision)
    need_run; need_body
    post "<!-- factory:decision stage=$stage run=$run -->" "$body" "" ;;
  flip)
    current=$("$here/factory-issue.sh" status "$issue" --repo "$repo")
    to=$("$here/factory-issue.sh" next-status "$issue" "$stage" --repo "$repo") || {
      rc=$?; [ "$rc" -eq 3 ] && die "refused: status moved (#$issue is $current)" 3; exit "$rc"; }
    flip "$current" "$to" ;;
  *) usage ;;
esac
