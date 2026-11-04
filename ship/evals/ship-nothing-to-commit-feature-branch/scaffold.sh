#!/usr/bin/env bash
. "$(dirname "${BASH_SOURCE[0]}")/../lib/fixture.sh"
ship_repo
ship_origin
git checkout -qb feat/widget
git push -q -u origin feat/widget
