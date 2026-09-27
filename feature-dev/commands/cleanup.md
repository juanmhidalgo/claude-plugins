---
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - AskUserQuestion
  - Write
  - Bash(rm SPEC-*.md)
  - Bash(rm PLAN-*.md)
  - Bash(gh pr view *)
  - Bash(gh pr comment *)
description: |
  Use to bulk-delete completed/abandoned SPEC-*.md and PLAN-*.md artifacts. Lists only safe candidates and requires Y/N confirm.
  Offers first to rescue a spec's Decisions Log and unticked QA items as a comment on its branch's PR or into docs/decisions/.
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

## Context
- **Repository**: !`git remote get-url origin`
- **Current branch**: !`git branch --show-current`

## Phase 0: Discover Artifacts

1. Use Glob with pattern `SPEC-*.md` in the repo root.
2. Use Glob with pattern `PLAN-*.md` in the repo root.
3. For each SPEC, Read its YAML frontmatter and capture `feature`, `slug`, `date`, `branch`, `status`.
4. For each PLAN, Read its YAML frontmatter and capture `feature`, `slug`, `date`, `source_spec`, `run_status`, `completed_steps`. If `source_spec` is set to a path, Read that file's frontmatter and capture its `status`.

If both Globs return zero files, STOP and tell the user: "No SPEC or PLAN files found at the project root. Nothing to clean up." Do not proceed.

## Phase 1: Categorize

Build three lists.

**Safe to delete:**
- SPECs with `status: implemented` — feature is done; auto-discovery already filters these out.
- PLANs whose `source_spec` file does not exist — orphaned, source spec was deleted.
- PLANs whose `source_spec` points to a SPEC with `status: implemented` **and** whose `run_status` is not `in-progress` / `halted` — leftover from an interrupted `/feature-dev:tdd` run that didn't reach the auto-delete step.

**Active work (never offer for deletion):**
- PLANs with `run_status: in-progress` or `run_status: halted` — a `/feature-dev:tdd` run is mid-flight or resumable. **This overrides every "safe to delete" rule above.** Deleting one of these discards the `completed_steps:` record and strands a dirty working tree with no way to tell which steps already landed.
- SPECs with `status: draft` or `status: approved` — work in progress.
- PLANs whose `source_spec` points to a SPEC with `status: draft` or `status: approved` — active work.

**Ambiguous (do not offer by default — user can delete manually):**
- PLANs with `source_spec: null` — could be standalone work the user is still iterating on.
- SPECs with malformed or missing `status:` frontmatter — broken artifact, surface but don't auto-include.

## Phase 1b: Detect Rescuable Content

Specs are gitignored, so anything that exists only in one is gone once it is deleted. For each SPEC in the safe-to-delete list, Read the body and record:

- **Decisions** — the entries under `## Decisions Log` (written by `/feature-dev:tdd`), up to the next `## ` heading or end of file. Non-empty means at least one entry, not just the heading.
- **Pending QA** — every unticked `- [ ]` line under `## QA Checklist`, up to the next `## ` heading. Keep the `###` group heading (`Happy path` / `Edge cases` / `Error states`) each item sits under; ticked `- [x]` items were verified by the user and are not rescued. An unticked item may have been checked and never ticked, so it is reported as unticked, not as unrun.

A SPEC with neither is not rescuable and goes straight to Phase 2.

## Phase 2: Present and Confirm

Present a structured summary to the user:

```
Feature-dev cleanup — candidate inventory

Safe to delete (N files):
  SPECs:
    - SPEC-<slug>.md — "<feature>" (<date>) — status: implemented[ — holds: N decisions, M unticked QA items]
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

If the "Safe to delete" list is non-empty and Phase 1b found rescuable content, run Phase 2a before the confirmation below; otherwise go straight to it.

### Phase 2a: Rescue

1. **Find each spec's PR.** A spec's PR is the one for the branch in its own frontmatter `branch:`, not the current branch — cleanup often runs from another branch than the one the feature shipped on. For each rescuable spec with a `branch:`, run `gh pr view <branch> --json number,state,comments`. Offer the PR option only when that returns `state: OPEN`. A spec with no `branch:`, a "no pull requests found" error, or a merged or closed PR means no PR option for that spec — say which in one line.
2. **Build the text per spec.** Headed with the spec's slug so a rerun can recognise them:

   ```markdown
   ## Decisions — <slug>

   <the Decisions Log entries, verbatim>

   ## Pending QA — <slug>

   Unticked QA items:

   <the unticked items, verbatim, under their group headings>
   ```

   Include only the sections the spec has content for.
3. **Ask.** One AskUserQuestion question per rescuable spec, at most 4 per call — batch the rest into further calls. Header `Rescue` (the header is capped at 12 characters, so the slug goes in the question), question naming the spec and what it holds (e.g. "SPEC-<slug>.md holds 3 decisions and 2 unticked QA items. Keep them before deleting?"). Options:
   - `Comment on PR #<n>` — preview: the exact comment text from step 2. Omitted when step 1 found no open PR for this spec.
   - `Save to docs/decisions/<slug>.md` — preview: the file content. The description says it is a tracked file the user commits; this command does not commit.
   - `Delete anyway` — nothing is kept; the Phase 3 report lists what was lost.
4. **Apply the choice.** Writing to a PR is visible to reviewers, so it happens only for a spec where the user picked that option — never as a default or a fallback from a failed save. The rescue is a new comment; the PR body is never edited, because a body rewrite can overwrite what the author or a bot put there since it was read.
   - **PR**: if the comments from step 1 already contain every heading this spec's text has (`## Decisions — <slug>`, `## Pending QA — <slug>`), report "already on PR #<n>" and treat the spec as rescued — a rerun never posts twice. Otherwise Write the step 2 sections not already there to a file at a path unique to this spec and run — `feature-dev-cleanup-<slug>-<random>.md` in the session scratchpad if one is listed, else under `/tmp/`. Read the path first and pick another name if it already exists, so a stale file from an earlier run is never posted. Run `gh pr comment <n> --body-file <file>`. Then re-run `gh pr view <branch> --json comments` and confirm a comment now carries each heading; a heading still missing after posting is a failed rescue.
   - **File**: if `docs/decisions/<slug>.md` exists, Read it and Write its content plus the sections it does not already have; otherwise Write a new file with a `# <feature>` title and the sections.
   - **Failure**: if `gh` or Write fails, or the verification above finds a heading missing, show the error verbatim and mark the spec **rescue failed**. A failed spec is removed from the delete list — deleting it would lose exactly what the user chose to keep. Its plan (if any) is still deleted only if it qualified on its own.

Then continue to the confirmation, with N recounted after removing rescue-failed specs:

- Question: "Delete N safe-to-delete files? This is irreversible — these files are not in git."
- Header: "Delete" (the header is capped at 12 characters)
- Options:
  - `Yes, delete all N` — proceed with deletion
  - `Cancel` — stop, delete nothing

## Phase 3: Delete

If the user chose `Cancel`, report "Cancelled. No files deleted.", then one line per spec already rescued in Phase 2a (`Rescued SPEC-<slug>.md → PR #<n>` or `→ docs/decisions/<slug>.md (uncommitted — commit it yourself)`) — the comment or file already exists and cancelling does not undo it — and STOP.

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
3. Add one line per rescuable spec with its outcome: `Rescued SPEC-<slug>.md → PR #<n>` (comment) or `→ docs/decisions/<slug>.md (uncommitted — commit it yourself)`; `Kept SPEC-<slug>.md — rescue failed: <error>`; or, for `Delete anyway`, `Lost from SPEC-<slug>.md:` followed by the decisions (one line each) and the unticked QA items, so the loss is on record in this session.

## Rules

- **Never delete files outside the candidate list.** The categorization in Phase 1 is the source of truth — do not improvise.
- **Never write to a PR without the user picking that option for that spec, and never edit its body.** A PR is read by others; the choice to publish a working artifact's contents there is the user's, and a comment adds to the PR without touching what anyone else wrote.
- **Never delete without the explicit confirmation in Phase 2.** Even if the user invoked this command intentionally, the destructive step requires an in-command Y/N gate.
- **Never delete files that are tracked by git.** The local-artifact convention says SPEC/PLAN should be `.gitignore`d; if a SPEC or PLAN somehow ended up tracked, surface it as a warning and skip — the user must decide whether to commit or untrack first.
- **Never recurse into subdirectories.** Both Glob patterns must run only at the repo root. SPEC/PLAN files belong at the root by convention; files elsewhere are out of scope.
- **No partial-list selection.** This is an intentional UX choice: surgical deletion is the user's job (`rm <specific-file>`); this command exists for bulk cleanup of unambiguous candidates only.
