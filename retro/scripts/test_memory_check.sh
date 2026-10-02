#!/usr/bin/env bash
# test_memory_check.sh — Tests for memory-check.sh and memory-check-hook.sh
#
# Builds a throwaway git repo and memory dir under a temp dir and asserts on
# every finding kind, the predicate that flips after a commit, a predicate
# that hangs, the output modes, and the SessionStart hook.
#
# Usage: bash retro/scripts/test_memory_check.sh

set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
CHECK="${HERE}/memory-check.sh"
HOOK="${HERE}/memory-check-hook.sh"

T="$(mktemp -d "${TMPDIR:-/tmp}/memory-check-test.XXXXXX")"
trap 'rm -rf "${T}"' EXIT

PASS=0
FAIL=0
ok()   { PASS=$((PASS + 1)); printf 'ok   %s\n' "$1"; }
bad()  { FAIL=$((FAIL + 1)); printf 'FAIL %s\n' "$1"; [[ -n "${2:-}" ]] && printf '     %s\n' "$2" | sed 's/^/     /'; }
has()  { if grep -qF -- "$2" <<<"$3"; then ok "$1"; else bad "$1" "expected '$2' in: $3"; fi; }
lacks(){ if grep -qF -- "$2" <<<"$3"; then bad "$1" "did not expect '$2' in: $3"; else ok "$1"; fi; }
eq()   { if [[ "$2" == "$3" ]]; then ok "$1"; else bad "$1" "expected [$2], got [$3]"; fi; }

# ── Fixture: a repo with a hook whose content gets fixed in a later commit ────
REPO="${T}/repo"
MEM="${T}/mem"
mkdir -p "${REPO}/hooks" "${REPO}/plugin/skills/session" "${MEM}"
git -C "${REPO}" init -q
git -C "${REPO}" config user.email test@example.com
git -C "${REPO}" config user.name test
git -C "${REPO}" config commit.gpgsign false
printf 'echo "advice" >&2\n' > "${REPO}/hooks/check.sh"
printf -- '---\nname: s\n---\n' > "${REPO}/plugin/skills/session/SKILL.md"
git -C "${REPO}" add -A
git -C "${REPO}" commit -q -m init
HEAD_SHA="$(git -C "${REPO}" rev-parse HEAD)"

now_iso="$(date -u '+%Y-%m-%dT%H:%M:%S.000Z')"

# The real case: the file keeps its name, its content gets fixed later.
cat > "${MEM}/hook-bug.md" <<EOF
---
name: hook-bug
description: "hooks/check.sh writes its advice to stderr, which never reaches Claude"
verify: 'grep -q ">&2" hooks/check.sh'
metadata:
  type: project
  modified: 2020-01-01T00:00:00.000Z
---

\`hooks/check.sh\` writes to stderr. Not yet fixed.
EOF

cat > "${MEM}/hang.md" <<EOF
---
name: hang
description: a predicate that never returns
verify: sleep 30
metadata:
  type: project
---
body
EOF

cat > "${MEM}/refs.md" <<EOF
---
name: refs
description: references
metadata:
  type: feedback
---
Exists: \`hooks/check.sh\`, \`./hooks/check.sh:1\`, \`SKILL.md\`, \`plugin/skills/session/SKILL.md#top\`.
Missing: \`hooks/gone.sh\` and \`nowhere-at-all.md\`.
Not repo paths: \`some-package/sub\`, \`~/.claude/settings.json\`, \`/etc/hosts\`, \`.meta.json\`, \`a b/c.md\`.
Real commit ${HEAD_SHA:0:9}; fake commit deadbee1cafe; session 4f9e9d9f-3109-4e16-8d6d-24495f4e5b62.

\`\`\`bash
cat fenced/never-checked.sh
\`\`\`
EOF

cat > "${MEM}/old.md" <<EOF
---
name: old
description: an old project claim with no verify
metadata:
  type: project
  modified: 2020-01-01T00:00:00.000Z
---
Some fact about the project.
EOF

cat > "${MEM}/old-mtime.md" <<EOF
---
name: old-mtime
description: no modified field, old file
type: project
---
Some fact.
EOF
touch -t 202001010000 "${MEM}/old-mtime.md"

cat > "${MEM}/recent.md" <<EOF
---
name: recent
description: a recent project claim
metadata:
  type: project
  modified: ${now_iso}
---
Fresh fact.
EOF

cat > "${MEM}/open.md" <<EOF
---
name: open
description: user feedback
metadata:
  type: feedback
---
The flaky test is still pending a fix.
EOF

cat > "${MEM}/verified-open.md" <<EOF
---
name: verified-open
description: an open claim backed by a passing predicate
verify: "test -f hooks/check.sh"
metadata:
  type: project
  modified: 2020-01-01T00:00:00.000Z
---
TODO: this is checked by verify, so no OPEN-CLAIM and no UNVERIFIED-OLD.
EOF

cat > "${MEM}/MEMORY.md" <<EOF
- [Hook bug](hook-bug.md) — stderr
- [Gone](deleted-memory.md) — removed file
EOF

run() { bash "${CHECK}" --memory-dir "${MEM}" --project-root "${REPO}" --timeout 1 "$@"; }

echo "── findings by kind"
start=$(date +%s)
out="$(run)"; rc=$?
elapsed=$(( $(date +%s) - start ))
eq   "exit 0 with findings" 0 "${rc}"
lacks "flip: predicate passes before the fix" "STALE hook-bug.md" "${out}"
has  "hang: STALE on timeout" "STALE hang.md — verify timed out after 1s: sleep 30" "${out}"
if [[ ${elapsed} -le 6 ]]; then ok "hang: timeout is enforced (${elapsed}s)"; else bad "hang: took ${elapsed}s"; fi
has  "MISSING-REF path with /" 'MISSING-REF refs.md — `hooks/gone.sh` does not exist' "${out}"
has  "MISSING-REF bare file name" 'MISSING-REF refs.md — `nowhere-at-all.md` is not a file' "${out}"
has  "MISSING-REF fake commit" "MISSING-REF refs.md — commit deadbee1cafe not found" "${out}"
lacks "existing path is fine" '`hooks/check.sh`' "${out}"
lacks "path:line and #anchor are stripped" 'check.sh:1' "${out}"
lacks "bare name found deep in the repo" '`SKILL.md`' "${out}"
lacks "real commit is fine" "${HEAD_SHA:0:9}" "${out}"
lacks "UUID segment is not a commit" "4f9e9d9f" "${out}"
lacks "external package path skipped" "some-package" "${out}"
lacks "home/absolute paths skipped" "settings.json" "${out}"
lacks "dot-suffix skipped" ".meta.json" "${out}"
lacks "fenced code skipped" "never-checked" "${out}"
has  "MISSING-REF index link" "MISSING-REF MEMORY.md — index links to deleted-memory.md" "${out}"
has  "UNVERIFIED-OLD via metadata.modified" "UNVERIFIED-OLD old.md — type project, no verify:, modified 2020-01-01" "${out}"
has  "UNVERIFIED-OLD via mtime" "UNVERIFIED-OLD old-mtime.md — type project, no verify:, file unchanged for" "${out}"
lacks "recent memory not old" "recent.md" "${out}"
has  "OPEN-CLAIM pending" "OPEN-CLAIM open.md" "${out}"
lacks "verify: suppresses OPEN-CLAIM and UNVERIFIED-OLD" "verified-open.md" "${out}"
lacks "verify: suppresses age checks on the flip file" "UNVERIFIED-OLD hook-bug.md" "${out}"

echo "── the real case: content fixed, file name unchanged"
printf 'echo "{\\"additionalContext\\": \\"advice\\"}"\n' > "${REPO}/hooks/check.sh"
git -C "${REPO}" commit -q -am "fix: emit additionalContext"
out="$(run)"
has  "flip: STALE after the fixing commit" "STALE hook-bug.md — verify exited 1: grep -q \">&2\" hooks/check.sh" "${out}"
lacks "a path-existence check alone would miss it" "MISSING-REF hook-bug.md" "${out}"

echo "── perl timeout fallback"
if command -v perl >/dev/null 2>&1; then
    start=$(date +%s)
    out="$(MEMORY_CHECK_TIMEOUT_IMPL=perl run --quiet-unless-stale)"
    elapsed=$(( $(date +%s) - start ))
    has "perl: hang times out" "STALE hang.md — verify timed out after 1s" "${out}"
    has "perl: failing predicate still STALE" "STALE hook-bug.md — verify exited 1" "${out}"
    if [[ ${elapsed} -le 6 ]]; then ok "perl: timeout is enforced (${elapsed}s)"; else bad "perl: took ${elapsed}s"; fi
else
    echo "skip perl not installed"
fi

echo "── output modes"
out="$(run --quiet-unless-stale)"
lacks "quiet: no OPEN-CLAIM" "OPEN-CLAIM" "${out}"
lacks "quiet: no UNVERIFIED-OLD" "UNVERIFIED-OLD" "${out}"
has  "quiet: keeps STALE" "STALE hook-bug.md" "${out}"
has  "quiet: keeps MISSING-REF" "MISSING-REF refs.md" "${out}"

if command -v jq >/dev/null 2>&1; then
    json="$(run --json)"
    text_count="$(run | wc -l | tr -d ' ')"
    eq "json: one object per finding" "${text_count}" "$(jq 'length' <<<"${json}")"
    eq "json: fields" '"STALE"' "$(jq '[.[] | select(.file == "hook-bug.md")][0].kind' <<<"${json}")"
fi

echo "── predicates: only regular files in the memory dir, and a cap"
MARK="${T}/ran-marker"
OUTSIDE="${T}/outside"
mkdir -p "${OUTSIDE}"
cat > "${OUTSIDE}/evil.md" <<EOF
---
name: evil
verify: touch ${MARK}
---
x
EOF
ln -s "${OUTSIDE}/evil.md" "${MEM}/linked.md"
out="$(run)"
has  "symlinked memory: verify not run" "SKIPPED-VERIFY linked.md" "${out}"
if [[ -e "${MARK}" ]]; then bad "symlinked predicate executed"; else ok "symlinked predicate never executed"; fi
rm -f "${MEM}/linked.md"

out="$(run --max-predicates 1)"
has  "cap: reports skipped predicates" "SKIPPED-VERIFY * — 3 verify: commands exceed --max-predicates 1" "${out}"
lacks "cap: no predicate ran" "STALE" "${out}"
out="$(run --no-predicates)"
lacks "--no-predicates: none ran" "STALE" "${out}"

echo "── clean and usage"
CLEAN="${T}/clean"
mkdir -p "${CLEAN}"
cat > "${CLEAN}/fine.md" <<EOF
---
name: fine
verify: test -d hooks
metadata:
  type: project
---
\`hooks/check.sh\` exists.
EOF
out="$(bash "${CHECK}" --memory-dir "${CLEAN}" --project-root "${REPO}")"; rc=$?
eq "clean: no output" "" "${out}"
eq "clean: exit 0" 0 "${rc}"
bash "${CHECK}" --days nope >/dev/null 2>&1; eq "usage error exits 2" 2 "$?"
bash "${CHECK}" --memory-dir "${T}/does-not-exist" >/dev/null 2>&1; eq "missing explicit dir exits 2" 2 "$?"

echo "── default memory dir: derived from the repo, shared by worktrees"
CFG="${T}/cfg"
REPO_REAL="$(cd "${REPO}" && pwd -P)"
ENC="$(printf '%s' "${REPO_REAL}" | sed 's/[\/._]/-/g')"
mkdir -p "${CFG}/projects/${ENC}/memory"
cp "${MEM}/hook-bug.md" "${CFG}/projects/${ENC}/memory/"
out="$(cd "${REPO}/hooks" && CLAUDE_CONFIG_DIR="${CFG}" bash "${CHECK}" --quiet-unless-stale)"
has "derived from a subdirectory" "STALE hook-bug.md" "${out}"
git -C "${REPO}" worktree add -q "${T}/wt" -b wt-branch 2>/dev/null
out="$(cd "${T}/wt" && CLAUDE_CONFIG_DIR="${CFG}" bash "${CHECK}" --quiet-unless-stale)"
has "derived from a worktree (main checkout's memory)" "STALE hook-bug.md" "${out}"
out="$(cd "${T}" && CLAUDE_CONFIG_DIR="${CFG}" bash "${CHECK}")"; rc=$?
eq "no memory for this dir: silent" "" "${out}"
eq "no memory for this dir: exit 0" 0 "${rc}"

echo "── SessionStart hook"
if command -v jq >/dev/null 2>&1; then
    payload="$(jq -n --arg cwd "${REPO}" '{session_id: "s", transcript_path: "/dev/null", cwd: $cwd, hook_event_name: "SessionStart", source: "startup"}')"
    out="$(printf '%s' "${payload}" | CLAUDE_CONFIG_DIR="${CFG}" bash "${HOOK}")"; rc=$?
    eq  "hook: exit 0" 0 "${rc}"
    eq  "hook: event name" '"SessionStart"' "$(jq '.hookSpecificOutput.hookEventName' <<<"${out}")"
    has "hook: context names the stale file" "STALE hook-bug.md" "$(jq -r '.hookSpecificOutput.additionalContext' <<<"${out}")"
    has "hook: context says what to do" "update or delete the memory file" "$(jq -r '.hookSpecificOutput.additionalContext' <<<"${out}")"

    out="$(printf '%s' "${payload}" | RETRO_MEMORY_CHECK=off CLAUDE_CONFIG_DIR="${CFG}" bash "${HOOK}")"
    eq "hook: RETRO_MEMORY_CHECK=off is silent" "" "${out}"

    clean_payload="$(jq -n --arg cwd "${T}" '{cwd: $cwd, hook_event_name: "SessionStart", source: "startup"}')"
    out="$(printf '%s' "${clean_payload}" | CLAUDE_CONFIG_DIR="${CFG}" bash "${HOOK}")"
    eq "hook: silent with nothing to report" "" "${out}"
else
    echo "skip hook tests: jq not installed"
fi

echo
echo "${PASS} passed, ${FAIL} failed"
[[ ${FAIL} -eq 0 ]]
