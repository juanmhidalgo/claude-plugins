#!/usr/bin/env bash
# factory-issue.sh - the read side of a factory stage's GitHub state.
#
# Everything a stage needs to know about its issue before it works: the one
# status label, the lane, the latest outcome marker, the human answer to the
# latest question, and the status a done outcome flips to. Pure reads: the only
# gh calls are `gh issue view` and (without --repo or FACTORY_REPO) `gh repo view`.
#
# Usage:
#   factory-issue.sh status <N>                 the one status:* label (none or several: exit 2)
#   factory-issue.sh lane <N>                   auto | spec-gate | plan-gate (none: exit 2)
#   factory-issue.sh last-marker <N>            "done stage=… sha=… run=…" | "question …" | "parked …" | "none"
#   factory-issue.sh answer <N>                 human comments after the latest question marker, newest last (none: exit 1)
#   factory-issue.sh next-status <N> <stage>    the status:* label a done outcome of <stage> flips to
#
# Options (before the subcommand or after it): --repo <owner/name>. Without it,
# FACTORY_REPO is used, then `gh repo view --json nameWithOwner`.
#
# Exit codes: 0 ok · 1 answer: nothing to read · 2 bad arguments or an issue
# that is not in a state the factory handles (no status, two statuses, no lane)
# · 3 next-status: the issue's status is not the one <stage> starts from
# (status-moved) · gh's own code when a gh call fails.
#
# The marker rule: a comment whose first line is `<!-- factory:… -->` was
# written by a stage; any other comment is a human's, whichever login wrote it.

set -euo pipefail

usage() { sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }
die() { echo "factory-issue: $*" >&2; exit "${2:-2}"; }

repo=${FACTORY_REPO:-}
args=()
while [ $# -gt 0 ]; do
  case $1 in
    --repo) [ $# -ge 2 ] || die "--repo needs a value"; repo=$2; shift 2 ;;
    -h|--help) usage ;;
    *) args+=("$1"); shift ;;
  esac
done
set -- "${args[@]+"${args[@]}"}"
[ $# -ge 2 ] || usage
cmd=$1; issue=$2; shift 2
[[ $issue =~ ^[1-9][0-9]*$ ]] || die "issue number expected, got '$issue'"

if [ -z "$repo" ]; then
  repo=$(gh repo view --json nameWithOwner -q .nameWithOwner) || die "cannot resolve the repository (pass --repo or set FACTORY_REPO)" 2
fi

view() { gh issue view "$issue" --repo "$repo" --json labels,comments; }

# Comments in creation order, each reduced to {login, created, first, body}.
# `first` is the first line of the body with a trailing CR removed.
comments_jq='
  [.comments[]] | sort_by(.createdAt) | map({
    login: (.author.login // ""), created: .createdAt,
    body: (.body | gsub("\r\n"; "\n")),
    first: ((.body | gsub("\r\n"; "\n") | split("\n") | .[0]) // "")
  })'

status_of() {
  local labels n
  labels=$(jq -r '[.labels[].name | select(startswith("status:"))] | .[]' <<<"$1")
  n=$(printf '%s' "$labels" | grep -c . || true)
  case $n in
    1) printf '%s\n' "$labels" ;;
    0) die "no status:* label on #$issue" 2 ;;
    *) die "several status:* labels on #$issue: $(printf '%s' "$labels" | paste -sd' ')" 2 ;;
  esac
}

lane_of() {
  local lanes n
  lanes=$(jq -r '[.labels[].name | select(. == "factory:auto" or . == "factory:spec-gate" or . == "factory:plan-gate")] | .[]' <<<"$1")
  n=$(printf '%s' "$lanes" | grep -c . || true)
  case $n in
    1) printf '%s\n' "${lanes#factory:}" ;;
    0) die "no factory lane label (factory:auto | factory:spec-gate | factory:plan-gate) on #$issue" 2 ;;
    *) die "several lane labels on #$issue: $(printf '%s' "$lanes" | paste -sd' ')" 2 ;;
  esac
}

case $cmd in
  status)
    status_of "$(view)" ;;
  lane)
    lane_of "$(view)" ;;
  last-marker)
    view | jq -r "$comments_jq"' | map(.first | capture("^<!-- factory:(?<kind>done|question|parked)(?<rest>( [^>]*)?) -->\\s*$")?) | if length == 0 then "none" else (last | .kind + .rest) end' ;;
  answer)
    out=$(view | jq -r "$comments_jq"'
      | (map(.first | test("^<!-- factory:question")) | rindex(true)) as $q
      | if $q == null then empty
        else .[$q+1:] | map(select(.first | test("^<!-- factory:") | not))
          | .[] | "--- " + .login + " " + .created + "\n" + .body + "\n" end')
    [ -n "$out" ] || exit 1
    printf '%s\n' "$out" ;;
  next-status)
    [ $# -eq 1 ] || die "next-status needs a stage"
    stage=$1
    data=$(view)
    status=$(status_of "$data")
    lane=$(lane_of "$data")
    case $stage in
      spec) from=status:needs-spec
            case $lane in auto) to=status:needs-plan ;; *) to=status:spec-review ;; esac ;;
      plan) from=status:needs-plan
            case $lane in plan-gate) to=status:plan-review ;; *) to=status:ready ;; esac ;;
      implement)
            case $status in
              status:ready) from=status:ready; to=status:in-progress ;;
              *) from=status:in-progress; to=status:in-progress ;;
            esac ;;
      harden) from=status:in-progress; to=status:in-progress ;;
      ship) from=status:in-progress; to=status:in-review ;;
      *) die "unknown stage '$stage' (spec | plan | implement | harden | ship)" ;;
    esac
    [ "$status" = "$from" ] || die "status-moved: $stage starts from $from, #$issue is $status" 3
    printf '%s\n' "$to" ;;
  *) usage ;;
esac
