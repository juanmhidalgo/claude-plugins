# project-dir.sh — sourced, not executed. Where Claude Code keeps a project's files.
#
# Shared by session-digest.sh and memory-check.sh so both derive the
# ~/.claude/projects/<encoded-cwd> directory the same way.

# Claude Code encodes the project cwd by replacing '/', '.' and '_' with '-'.
# Verified against every local project directory; replacing only '/' (a common
# mistake) breaks on any path containing a dot, e.g. ~/.claude.
encode_project_dir() {
    printf '%s' "$1" | sed 's/[\/._]/-/g'
}

# The directory holding the per-project folders, honoring CLAUDE_CONFIG_DIR.
claude_projects_dir() {
    printf '%s/projects' "${CLAUDE_CONFIG_DIR:-${HOME}/.claude}"
}

# Auto-memory is keyed by the git repository, not by the cwd: every worktree
# and subdirectory of one repo shares the main checkout's memory dir. Prints
# the candidate roots for <dir> in the order to try them: the main checkout
# (parent of the common git dir), the worktree top level, then <dir> itself.
memory_root_candidates() {
    local dir="$1" common top
    common="$(git -C "${dir}" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
    top="$(git -C "${dir}" rev-parse --show-toplevel 2>/dev/null || true)"
    if [[ -n "${common}" ]]; then dirname "${common}"; fi
    if [[ -n "${top}" ]]; then printf '%s\n' "${top}"; fi
    printf '%s\n' "${dir}"
}
