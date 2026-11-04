#!/usr/bin/env bash
. "$(dirname "${BASH_SOURCE[0]}")/../lib/fixture.sh"
ship_repo
git checkout -qb feat/widget
printf '\nChanged on the feature branch.\n' >> README.md
