#!/usr/bin/env bash
# Sourced by each case's scaffold.sh. The scaffold runs in the empty eval
# workspace with a minimal environment (PATH, a temporary HOME, TMPDIR), so
# the git identity is set locally and nothing depends on the user's config.
#
# fixture_repo builds the same repo test-pipeline-branch.sh uses:
#   master  : A
#   feature : A -> B            (B is the PR #1 head)
#   origin  : bare, in .origin.git, holding master, feature and
#             refs/pull/1/head = B; excluded through .git/info/exclude so the
#             working tree stays clean.
# It leaves the checkout on master and exports B.
set -euo pipefail

fixture_repo() {
  git init -q -b master .
  git config user.email eval@example.com
  git config user.name eval
  git config commit.gpgsign false
  echo a > a; git add a; git commit -qm "A: initial"
  git checkout -qb feature; echo b > b; git add b; git commit -qm "B: feature work"
  B=$(git rev-parse HEAD)
  git checkout -q master
  git init -q -b master --bare .origin.git
  printf '.origin.git/\n' >> .git/info/exclude
  git remote add origin "$PWD/.origin.git"
  git push -q origin master feature "$B:refs/pull/1/head"
  export B
}

# fake_gh_state KEY=VALUE ... writes the fake gh's per-case state.
fake_gh_state() {
  : > .git/fake-gh.env
  for kv in "$@"; do printf '%s\n' "$kv" >> .git/fake-gh.env; done
}
