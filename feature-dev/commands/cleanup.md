---
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - AskUserQuestion
  - Bash(rm SPEC-*.md)
  - Bash(rm PLAN-*.md)
description: |
  Use to bulk-delete completed/abandoned SPEC-*.md and PLAN-*.md artifacts. Lists only safe candidates and requires Y/N confirm.
  Do NOT use during active feature work — destructive on confirmed candidates.
keywords:
  - cleanup
  - feature-dev
  - artifact-cleanup
  - implemented-specs
triggers:
  - "clean up old specs"
  - "delete completed specs"
  - "cleanup feature-dev artifacts"
  - "remove implemented specs"
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this command and proceed with your assigned task.
</SUBAGENT-STOP>

## Context
- **Repository**: !`git remote get-url origin`
- **Current branch**: !`git branch --show-current`

## Phase 0: Discover Artifacts

1. Use Glob with pattern `SPEC-*.md` in the repo root.
2. Use Glob with pattern `PLAN-*.md` in the repo root.
3. For each SPEC, Read its YAML frontmatter and capture `feature`, `slug`, `date`, `status`.
4. For each PLAN, Read its YAML frontmatter and capture `feature`, `slug`, `date`, `source_spec`. If `source_spec` is set to a path, Read that file's frontmatter and capture its `status`.

If both Globs return zero files, STOP and tell the user: "No SPEC or PLAN files found at the project root. Nothing to clean up." Do not proceed.

## Phase 1: Categorize

Build three lists.

**Safe to delete:**
- SPECs with `status: implemented` — feature is done; auto-discovery already filters these out.
- PLANs whose `source_spec` file does not exist — orphaned, source spec was deleted.
- PLANs whose `source_spec` points to a SPEC with `status: implemented` — leftover from an interrupted `/feature-dev:tdd` run that didn't reach the auto-delete step.

**Active work (never offer for deletion):**
- SPECs with `status: draft` or `status: approved` — work in progress.
- PLANs whose `source_spec` points to a SPEC with `status: draft` or `status: approved` — active work.

**Ambiguous (do not offer by default — user can delete manually):**
- PLANs with `source_spec: null` — could be standalone work the user is still iterating on.
- SPECs with malformed or missing `status:` frontmatter — broken artifact, surface but don't auto-include.

## Phase 2: Present and Confirm

Present a structured summary to the user:

```
Feature-dev cleanup — candidate inventory

Safe to delete (N files):
  SPECs:
    - SPEC-<slug>.md — "<feature>" (<date>) — status: implemented
    ...
  PLANs:
    - PLAN-<slug>.md — "<feature>" (<date>) — reason: <orphan | source_spec implemented>
    ...

Active work (left alone, M files):
  - SPEC-<slug>.md — "<feature>" — status: <draft|approved>
  ...

Ambiguous (not auto-included, K files):
  - PLAN-<slug>.md — "<feature>" — reason: source_spec is null
  ...
```

If the "Safe to delete" list is empty, STOP and tell the user: "No safe-delete candidates. M active-work files left alone, K ambiguous files surfaced for manual review." Do not prompt.

If the "Safe to delete" list is non-empty, use AskUserQuestion with a single Y/N confirmation:

- Question: "Delete N safe-to-delete files? This is irreversible — these files are not in git."
- Header: "Confirm delete"
- Options:
  - `Yes, delete all N` — proceed with deletion
  - `Cancel` — stop, delete nothing

## Phase 3: Delete

If the user chose `Cancel`, report "Cancelled. No files deleted." and STOP.

If the user chose `Yes, delete all N`:

1. For each file in the "Safe to delete" list, run the appropriate `rm` command:
   - SPEC files: `rm SPEC-<slug>.md`
   - PLAN files: `rm PLAN-<slug>.md`
2. Report the result with one line per deleted file:
   ```
   Deleted SPEC-<slug>.md
   Deleted PLAN-<slug>.md
   ...
   Total: N files removed.
   ```

## Rules

- **Never delete files outside the candidate list.** The categorization in Phase 1 is the source of truth — do not improvise.
- **Never delete without the explicit confirmation in Phase 2.** Even if the user invoked this command intentionally, the destructive step requires an in-command Y/N gate.
- **Never delete files that are tracked by git.** The local-artifact convention says SPEC/PLAN should be `.gitignore`d; if a SPEC or PLAN somehow ended up tracked, surface it as a warning and skip — the user must decide whether to commit or untrack first.
- **Never recurse into subdirectories.** Both Glob patterns must run only at the repo root. SPEC/PLAN files belong at the root by convention; files elsewhere are out of scope.
- **No partial-list selection.** This is an intentional UX choice: surgical deletion is the user's job (`rm <specific-file>`); this command exists for bulk cleanup of unambiguous candidates only.
