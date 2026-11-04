#!/usr/bin/env bash
. "$(dirname "${BASH_SOURCE[0]}")/../lib/fixture.sh"
fixture_repo
fake_gh_state "FAKE_HEAD_REF=feature" "FAKE_HEAD_OID=$B"
