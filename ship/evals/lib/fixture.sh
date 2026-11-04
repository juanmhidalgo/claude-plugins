#!/usr/bin/env bash
# Sourced by each case's scaffold.sh. Runs in the empty eval workspace with a
# minimal environment, so the git identity is set locally.
#
# ship_repo   : two commits on master (README.md, src/app.py). No remote.
# ship_origin : a bare origin in .origin.git (hidden through .git/info/exclude
#               so the tree stays clean), master pushed with an upstream.
set -euo pipefail

ship_repo() {
  git init -q -b master .
  git config user.email eval@example.com
  git config user.name eval
  git config commit.gpgsign false
  mkdir -p src
  printf '# Widget\n\nA sample project.\n' > README.md
  printf 'def main():\n    return 0\n' > src/app.py
  git add README.md src/app.py
  git commit -qm "feat: initial widget"
  printf '\nSee src/app.py for the entrypoint.\n' >> README.md
  git commit -qam "docs: point at the entrypoint"
}

ship_origin() {
  git init -q -b master --bare .origin.git
  printf '.origin.git/\n' >> .git/info/exclude
  git remote add origin "$PWD/.origin.git"
  git push -q -u origin master
}
