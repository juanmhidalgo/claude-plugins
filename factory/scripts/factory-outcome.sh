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
#   factory-outcome.sh done      <N> --stage <s> --run <id> --body-file <f> [--to <label>] [--sha <head>] [--files-file <f>]
#   factory-outcome.sh question  <N> --stage <s> --run <id> --body-file <f> --from <label> [--id <uuid>]
#   factory-outcome.sh parked    <N> --stage <s> --run <id> --body-file <f> --reason <slug> [--from <label>]
#   factory-outcome.sh progress  <N> --stage <s> --run <id> --step <n>/<T> [--sha <head>] [--body-file <f>]
#   factory-outcome.sh decision  <N> --stage <s> --run <id> --body-file <f>
#   factory-outcome.sh flip      <N> --stage <s>
#
# Common: --repo <owner/name> (else FACTORY_REPO, else `gh repo view`). Bodies
# are always files, never argv.
#
# The sha of a done marker is read from git, never typed: `git -C
# "${FACTORY_WORKDIR:-$PWD}" rev-parse HEAD` (the stage runs with the clone as
# cwd). Outside a git repository done dies (exit 2). --sha is optional there
# and only a cross-check: when given it must equal that HEAD (the full hash or
# an abbreviation of it), else `refused: --sha differs from git HEAD` (exit 2),
# nothing posted. progress keeps --sha as an override and defaults to the same HEAD.
#
# --files-file <f> (done, --stage plan only; any other stage: exit 2, "files only
# on plan") names a file with one repo-relative path per line, blank lines
# ignored: every file the plan creates, edits or deletes, tests included. Each
# path must be relative (no leading / or ./), have no . or .. or empty segment,
# no trailing /, and contain no space, comma, double quote, *, ?, <, >, backslash
# or control character. One bad line → `refused: bad path in --files-file:
# <line>` (exit 2, nothing posted). The paths are sorted (byte order), deduped,
# joined with commas and appended to the marker as files="…", always quoted;
# an empty file omits the attribute. The daemon reads files= for its open-PR
# gate and its base-moved replan.
#
# Markers:
#   <!-- factory:done stage=<s> sha=<head> run=<id> -->
#   <!-- factory:done stage=plan sha=<head> run=<id> files="src/a.py,tests/test_a.py" -->   (plan, with --files-file)
#   <!-- factory:question id=<uuid> stage=<s> from=<label> run=<id> -->
#   <!-- factory:parked stage=<s> reason=<slug> run=<id> -->
#   <!-- factory:progress stage=<s> step=<n>/<T> sha=<head> run=<id> -->
#   <!-- factory:decision stage=<s> run=<id> -->          (first line too: the marker rule has no exception)
#
# One marker is never typed here: `<!-- factory:replan by=daemon reason=base-moved
# sha=<old plan sha> base=<master sha> files="…" run=<daemon run id> -->` is the
# daemon's, posted when master moved on files the plan names. It is not an
# outcome (last-marker ignores it); factory-issue.sh replan reads it for the
# plan stage.
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

repo=${FACTORY_REPO:-} stage= run= body= sha= to= from= qid= reason= step= files_file= files=
while [ $# -gt 0 ]; do
  case $1 in
    -h|--help) usage ;;
    --*) [ $# -ge 2 ] || die "$1 needs a value" ;;
  esac
  case $1 in
    --repo) repo=$2 ;; --stage) stage=$2 ;; --run) run=$2 ;; --body-file) body=$2 ;;
    --sha) sha=$2 ;; --to) to=$2 ;; --from) from=$2 ;; --id) qid=$2 ;;
    --reason) reason=$2 ;; --step) step=$2 ;; --files-file) files_file=$2 ;;
    *) die "unknown option '$1'" ;;
  esac
  shift 2
done

case $stage in spec|plan|implement|harden|ship) ;; *) die "--stage must be one of spec | plan | implement | harden | ship" ;; esac
if [ -z "$repo" ]; then
  repo=$(gh repo view --json nameWithOwner -q .nameWithOwner) || die "cannot resolve the repository (pass --repo or set FACTORY_REPO)"
fi
need_run() { [[ $run =~ ^[A-Za-z0-9._:-]+$ ]] || die "--run <id> is required ([A-Za-z0-9._:-])"; }
need_body() { [ -n "$body" ] && [ -s "$body" ] || die "--body-file must name a non-empty file"; }
git_head() { git -C "${FACTORY_WORKDIR:-$PWD}" rev-parse HEAD 2>/dev/null; }
need_sha() {  # progress: --sha, else HEAD
  [ -n "$sha" ] || sha=$(git_head) || die "--sha is required outside a git repository"
  [[ $sha =~ ^[0-9a-f]{7,40}$ ]] || die "--sha must be a commit hash"
}
head_sha() {  # done: always HEAD; --sha, when given, must be HEAD or an abbreviation of it
  local head
  head=$(git_head) || die "refused: ${FACTORY_WORKDIR:-$PWD} is not a git repository (the done sha is read from git HEAD)"
  if [ -n "$sha" ]; then
    [[ $sha =~ ^[0-9a-f]{7,40}$ ]] || die "--sha must be a commit hash"
    [[ $head == "$sha"* ]] || die "refused: --sha differs from git HEAD ($sha vs $head); the sha is read from git, drop --sha"
  fi
  sha=$head
}
label_ok() { [[ $1 =~ ^status:[a-z-]+$ ]] || die "$2 must be a status:* label, got '$1'"; }

path_ok() {  # path_ok <p>: 0 when <p> is a canonical repo-relative path the marker can carry
  local p=$1
  [ -n "$p" ] || return 1
  case $p in
    /*|./*|*/) return 1 ;;
    *' '*|*,*|*\"*|*\**|*\?*|*'<'*|*'>'*|*\\*) return 1 ;;
  esac
  [[ $p =~ [[:cntrl:]] ]] && return 1
  case "/$p/" in */../*|*/./*|*//*) return 1 ;; esac
  return 0
}
files_attr() {  # done --files-file: one path per line → files=' files="a,b"' (sorted, deduped); '' when the file is empty
  local line list
  [ -n "$files_file" ] || return 0
  [ "$stage" = plan ] || die "refused: --files-file is accepted with --stage plan only (files only on plan)"
  [ -r "$files_file" ] && [ ! -d "$files_file" ] || die "--files-file must name a readable file"
  while IFS= read -r line || [ -n "$line" ]; do
    [ -n "$line" ] || continue
    path_ok "$line" || die "refused: bad path in --files-file: $line"
  done <"$files_file"
  list=$({ grep -v '^$' -- "$files_file" || true; } | LC_ALL=C sort -u | paste -sd, -)
  [ -n "$list" ] || return 0
  files=" files=\"$list\""
}

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
    need_run; need_body; files_attr; head_sha
    current=$("$here/factory-issue.sh" status "$issue" --repo "$repo")
    if [ -z "$to" ]; then
      to=$("$here/factory-issue.sh" next-status "$issue" "$stage" --repo "$repo") || {
        rc=$?; [ "$rc" -eq 3 ] && die "refused: status moved (#$issue is $current); end parked --reason status-moved" 3; exit "$rc"; }
    else
      label_ok "$to" --to
    fi
    post "<!-- factory:done stage=$stage sha=$sha run=$run$files -->" "$body" ""
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
