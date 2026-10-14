#!/usr/bin/env bash
# Stages the fixture project into the eval run's working directory and gives
# it a short, deterministic git history, so history-explorer has commits to
# read and the plan's Baseline has a HEAD sha. No network: the remote is only
# a name for `git remote get-url origin` in the command's context block.
set -euo pipefail

fixture="$(cd "$(dirname "${BASH_SOURCE[0]}")/fixture" && pwd)"

git init -q -b master .
git remote add origin https://example.com/sample/task-tracker.git

commit() {
  local date="$1" message="$2"
  GIT_AUTHOR_DATE="$date" GIT_COMMITTER_DATE="$date" git commit -q -m "$message"
}

printf '.feature-dev/\n__pycache__/\n' > .gitignore
mkdir -p app tests
cp "$fixture/README.md" .
cp "$fixture/app/__init__.py" "$fixture/app/tasks.py" app/
git add .gitignore README.md app
commit "2026-01-05T10:00:00Z" "feat: in-memory task store"

cp "$fixture/tests/__init__.py" "$fixture/tests/test_tasks.py" tests/
git add tests
commit "2026-01-08T10:00:00Z" "test: cover task store filters and serialization"

mkdir -p web/src
cp "$fixture/web/src/taskList.js" web/src/
git add web
commit "2026-01-12T10:00:00Z" "feat(web): render the task list"

# The spec is a local working artifact (gitignored), staged the way
# /feature-dev:spec leaves it: `new` creates the draft feature and prints the
# SPEC path, the fixture is copied there, then `approve` records the approval
# (it requires the SPEC to exist). FEATURES_ROOT lets a smoke test stage
# into a temp dir; by default it is the current directory.
features="$(dirname "${BASH_SOURCE[0]}")/../../scripts/features.py"
root="${FEATURES_ROOT:-.}"
spec_path="$(python3 "$features" new task-due-dates --kind spec --root "$root")"
cp "$fixture/SPEC-task-due-dates.md" "$root/$spec_path"
python3 "$features" approve task-due-dates --root "$root" >/dev/null
