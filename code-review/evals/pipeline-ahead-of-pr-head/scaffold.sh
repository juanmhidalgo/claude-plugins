#!/usr/bin/env bash
. "$(dirname "${BASH_SOURCE[0]}")/../lib/fixture.sh"
fixture_repo
# The local feature branch has a commit D the PR head (B) lacks.
git checkout -q feature; echo d > d; git add d; git commit -qm "D: local only"
git checkout -q master
fake_gh_state "FAKE_HEAD_REF=feature" "FAKE_HEAD_OID=$B"
