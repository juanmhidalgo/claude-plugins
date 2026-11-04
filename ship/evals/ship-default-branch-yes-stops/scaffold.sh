#!/usr/bin/env bash
. "$(dirname "${BASH_SOURCE[0]}")/../lib/fixture.sh"
ship_repo
ship_origin
printf '\nChanged while on master.\n' >> README.md
