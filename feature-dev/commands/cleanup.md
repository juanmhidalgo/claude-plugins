---
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - AskUserQuestion
  - Write
  - Edit
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py purge *)
  - Bash(gh pr view *)
  - Bash(gh pr comment *)
  - Bash(gh auth status)
  - Bash(gh issue view *)
  - Bash(gh issue edit *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/issue_spec.py *)
  - Bash(ls -1A .feature-dev/*)
  - Bash(curl -s -o /dev/null --max-time 2 http://127.0.0.1:*)
description: |
  Use to bulk-delete completed/abandoned SPEC-*.md and PLAN-*.md artifacts, together with their local review history and feedback under .feature-dev/ and any orphaned review data. Lists only safe candidates and requires Y/N confirm.
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

5. List the review data with `ls -1A .feature-dev/history` and `ls -1A .feature-dev/reviews` — not Glob, which can skip the gitignored `.feature-dev/`. A "No such file or directory" error means there is none of that kind. For each history directory, `ls -1A .feature-dev/history/<dir>` gives its snapshot count.

If both Globs return zero files and step 5 found nothing, STOP and tell the user: "No SPEC, PLAN or review data found. Nothing to clean up." Do not proceed.

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

## Phase 1a: Review Data

`/spec`, explore-plan and `/feature-dev:review` keep, per slug, snapshots in `.feature-dev/history/<slug>/`, review files `.feature-dev/reviews/<slug>-<YYYYMMDDTHHMMSSZ>[-<n>].md`, and, while a review page is served, a pointer `.feature-dev/reviews/.<slug>.url`. They are gitignored and local, and nothing else ever deletes them.

1. **Group by on-disk slug.** A history directory's name is its slug. A review file's slug is its name minus the `-<timestamp>[-<n>].md` suffix — never match by prefix, since `foo-*` also matches `foo-bar-…`. A pointer's slug is its name minus the leading `.` and the `.url`.
2. **Map each SPEC/PLAN to its on-disk slug** the way `review_server.py` derives it: frontmatter `slug:` (else the file name minus `SPEC-`/`PLAN-` and `.md`), every run of characters outside `A-Za-z0-9._-` replaced by `-`, leading and trailing `-`/`.` stripped, `artifact` if nothing is left. A SPEC and its PLAN share the slug.
3. **Classify each slug's data:**
   - **Goes with the deletion**: the slug's SPEC/PLAN files are all in the safe-to-delete list, so none survives this run. SPECs later marked rescue-failed survive, so their slug drops out of this group.
   - **Orphaned**: no SPEC or PLAN at the root maps to the slug, the slug has at least one review file, **and** every one of its review files names an `artifact:` (frontmatter) that no longer exists. Read each review file's frontmatter and Read that path, relative to the project root; a "does not exist" error means it is gone. An artifact can live outside the root, or have been renamed while its review stayed, so the missing root SPEC/PLAN alone does not prove the data is unused.
   - **Ambiguous review data**: no SPEC or PLAN at the root maps to the slug, but it has only history and no review file, or a review whose `artifact:` still exists. Listed with that reason, never deleted.
   - **Kept**: any other slug — something with that slug remains (active, ambiguous, or not offered). This covers every slug whose PLAN is `in-progress`/`halted`, which the same override as in Phase 1 protects: a resumed run and its review round still read that history.
4. **Check pointers.** For every `.url` file — whatever its slug's group, except a kept slug protected by an `in-progress`/`halted` PLAN — Read it and probe `<url>alive` (the pointer ends in `/`): `curl -s -o /dev/null --max-time 2 <url>alive`. `/alive` answers without a token and without resetting the server's idle timer, so the probe never keeps a forgotten review open. Exit 7 (connection refused) means no server — the pointer is stale. Any other exit means something answers — a **review in progress**:
   - take the whole slug out of both review-data groups (the server still reads its history and will write a review there);
   - move the slug's SPEC/PLAN from Safe to delete to Active work with reason `review in progress` — the review's verdict is about to be applied to that file;
   - say "review server running at <url> — submit or close it, then rerun".

   Every stale pointer, of any group, goes in the stale-pointer list and is deleted on its own `--pointer`, because `review_server.py url` would otherwise keep printing a dead URL.

## Phase 1b: Detect Rescuable Content

Specs are gitignored, so anything that exists only in one is gone once it is deleted. For each SPEC in the safe-to-delete list:

1. **Published and current.** If the SPEC's frontmatter has `issue: <owner>/<repo>#<N>`, run the [gh preflight](../skills/spec-driven-development/references/issue-store.md#gh-preflight) — on failure, treat the SPEC as **not current** (per its "cleanup's 'published and current' check" rule) and continue to step 2. On success, compute the three [Fingerprints](../skills/spec-driven-development/references/issue-store.md#fingerprints): local (`issue_spec.py section <SPEC> | issue_spec.py fingerprint -`), recorded (the frontmatter's `issue_fingerprint:`), and issue (`gh issue view <N> --repo <owner>/<repo> --json body -q .body | issue_spec.py fingerprint -`). All three equal → the SPEC is **published and current**: skip step 2 for it, it is not rescuable, and it goes straight to Phase 2 without the rescue question — it still follows the existing status rules for deletion. Any mismatch → the SPEC is **not current**: note its `#<N>`, and continue to step 2, where a SPEC with `issue:` is rescuable regardless of what step 2 finds — the mismatch itself (an unpublished local edit, or an issue that moved since the last publish) is the thing that would otherwise be lost silently. A SPEC with no `issue:` at all also continues to step 2, under the decision/QA gate below — nothing in this step changes for it.
2. Read the body and record:
   - **Decisions** — the entries under `## Decisions Log` (written by `/feature-dev:tdd`), up to the next `## ` heading or end of file. Non-empty means at least one entry, not just the heading.
   - **Pending QA** — every unticked `- [ ]` line under `## QA Checklist`, up to the next `## ` heading. Keep the `###` group heading (`Happy path` / `Edge cases` / `Error states`) each item sits under; ticked `- [x]` items were verified by the user and are not rescued. An unticked item may have been checked and never ticked, so it is reported as unticked, not as unrun.

A published-and-current SPEC is not rescuable and goes straight to Phase 2. A SPEC with `issue:` that is not current is always rescuable, even with neither a decision nor pending QA — its difference from issue `#<N>` is itself worth a rescue question, via `Republish to #<N>` in Phase 2a (below). A SPEC with no `issue:` is rescuable only when it has a decision or pending QA; otherwise it goes straight to Phase 2.

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

Review data going with them (S slugs):
  - <slug> — 3 snapshots, 2 reviews
  ...

Orphaned review data (O slugs — no SPEC or PLAN left, and every review's artifact is gone):
  - <slug> — 1 snapshot, 2 reviews
  ...

Ambiguous review data (left alone, A slugs):
  - <slug> — 2 snapshots, 0 reviews — reason: <history only | review of <artifact> which still exists>
  ...

Stale server pointers (P, no server answering):
  - .feature-dev/reviews/.<slug>.url
```

Counts only — never list the individual files. Omit empty groups, and also list any slug skipped for a live server.

If the "Safe to delete" list, both deletable review-data groups and the stale pointers are all empty, STOP and tell the user: "No safe-delete candidates. M active-work files left alone, K ambiguous files surfaced for manual review." Do not prompt.

If the "Safe to delete" list is non-empty and Phase 1b found rescuable content, run Phase 2a before the confirmation below; otherwise go straight to it.

### Phase 2a: Rescue

1. **Find each spec's PR.** A spec's PR is the one for the branch in its own frontmatter `branch:`, not the current branch — cleanup often runs from another branch than the one the feature shipped on. For each rescuable spec with a `branch:` **and at least one decision or pending QA item**, run `gh pr view <branch> --json number,state,comments`. Offer the PR option only when that returns `state: OPEN`. A spec with no `branch:`, a "no pull requests found" error, or a merged or closed PR means no PR option for that spec — say which in one line. Skip this step for a spec that is rescuable only because it is not current (no decision, no pending QA) — there is nothing to put in a PR comment.
2. **Build the text per spec.** Skip this step too for a spec rescuable only because it is not current — it has no decisions or QA to write up; its rescue text is the issue diff itself, covered directly in step 3's question. For every other rescuable spec, headed with the slug so a rerun can recognise them:

   ```markdown
   ## Decisions — <slug>

   <the Decisions Log entries, verbatim>

   ## Pending QA — <slug>

   Unticked QA items:

   <the unticked items, verbatim, under their group headings>
   ```

   Include only the sections the spec has content for.
3. **Ask.** One AskUserQuestion question per rescuable spec, at most 4 per call — batch the rest into further calls. Header `Rescue` (the header is capped at 12 characters, so the slug goes in the question). Question:
   - **Has a decision or pending QA item** (whether or not it is also not current): name what it holds, e.g. "SPEC-<slug>.md holds 3 decisions and 2 unticked QA items. Keep them before deleting?"
   - **Rescuable only because it is not current** (no decision, no pending QA — an `issue:` fingerprint mismatch is the only reason it is here): "SPEC-<slug>.md differs from issue #<N> — local edits were never published, or the issue changed since. Keep it before deleting?"

   Options:
   - `Comment on PR #<n>` — preview: the exact comment text from step 2. Omitted when step 1 found no open PR for this spec, or when the spec has neither a decision nor pending QA to comment (step 1/2 were skipped for it).
   - `Save to docs/decisions/<slug>.md` — preview: the file content. The description says it is a tracked file the user commits; this command does not commit. Omitted for the same no-decision/no-QA case.
   - `Delete anyway` — nothing is kept; the Phase 3 report lists what was lost.
   - `Republish to #<N>` — only offered when the spec's frontmatter has `issue: <owner>/<repo>#<N>`. A rescuable spec with one is already not current (Phase 1b step 1 sends a published-and-current spec straight to Phase 2, never through this question). Preview: "runs the publish algorithm against issue #<N>". Picking it runs [issue-store.md's Publish algorithm](../skills/spec-driven-development/references/issue-store.md#publish-ac-1-ac-2-ac-3-ac-4-ac-5-ac-7) against this spec and target `#<N>`, start to finish — its `gh` preflight, the AC-4 conflict ask if the issue's section changed since the last publish, and the AC-5 re-read-and-verify. Do not restate those steps here — follow the reference. For a spec with no decision/QA content, this and `Delete anyway` are the only two options.
4. **Apply the choice.** Writing to a PR is visible to reviewers, so it happens only for a spec where the user picked that option — never as a default or a fallback from a failed save. The rescue is a new comment; the PR body is never edited, because a body rewrite can overwrite what the author or a bot put there since it was read.
   - **PR**: if the comments from step 1 already contain every heading this spec's text has (`## Decisions — <slug>`, `## Pending QA — <slug>`), report "already on PR #<n>" and treat the spec as rescued — a rerun never posts twice. Otherwise Write the step 2 sections not already there to a file at a path unique to this spec and run — `feature-dev-cleanup-<slug>-<random>.md` in the session scratchpad if one is listed, else under `/tmp/`. Read the path first and pick another name if it already exists, so a stale file from an earlier run is never posted. Run `gh pr comment <n> --body-file <file>`. Then re-run `gh pr view <branch> --json comments` and confirm a comment now carries each heading; a heading still missing after posting is a failed rescue.
   - **File**: if `docs/decisions/<slug>.md` exists, Read it and Write its content plus the sections it does not already have; otherwise Write a new file with a `# <feature>` title and the sections.
   - **Republish**: run the reference's Publish algorithm linked in step 3, against `#<N>` from the spec's own `issue:` frontmatter. On the reference's AC-4 mismatch ask, offer only "overwrite the issue" or "cancel" — this command does not carry Import's tools (no `gh issue create`, no `review_server.py snapshot`), so "import the issue's version instead" is out of scope here; treat that pick the same as **Failure** below, since nothing was published. On a verified publish (the reference's step 7, which writes `issue_fingerprint:` to the spec via Edit), the spec's content now lives on the issue and it keeps its place in the delete list.
   - **Failure**: if `gh` or Write fails, or the verification above finds a heading missing (PR) or a fingerprint mismatch (Republish), show the error verbatim and mark the spec **rescue failed** — for Republish, say the **republish failed**. A failed spec is removed from the delete list — deleting it would lose exactly what the user chose to keep (for Republish, the content the republish tried to save). Its plan (if any) is still deleted only if it qualified on its own.

Then continue to the confirmation, with N recounted after removing rescue-failed specs, and a rescue-failed spec's slug moved from "going with them" to kept (Phase 1a step 3). R is the slugs going with them plus the orphaned ones; P is the stale pointers.

Build the Phase 3 `purge` command now and run it once with `--dry-run`. Exit 2 means an argument is invalid and nothing would be deleted — show the error and fix or drop that argument before asking. A `skipped … tracked by git` line takes that path out of the counts: the question must not promise a deletion that will not happen.

- Question: "Delete N safe-to-delete files, review data for R slugs and P stale pointers? This is irreversible — none of it is in git." Drop each part that is zero.
- Header: "Delete" (the header is capped at 12 characters)
- Options:
  - `Yes, delete all` — proceed with deletion
  - `Cancel` — stop, delete nothing

## Phase 3: Delete

If the user chose `Cancel`, report "Cancelled. No files deleted.", then one line per spec already rescued in Phase 2a (`Rescued SPEC-<slug>.md → PR #<n>` or `→ docs/decisions/<slug>.md (uncommitted — commit it yourself)`) — the comment or file already exists and cancelling does not undo it — and STOP.

If the user chose `Yes, delete all`:

1. Run one command that names exactly what the confirmation counted — never `rm`:
   ```
   ${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py purge --artifact <SPEC-/PLAN- file> … --slug <slug> … --pointer <slug> …
   ```
   - `--artifact` once per file in the "Safe to delete" list (the bare file name, e.g. `SPEC-<slug>.md`).
   - `--slug` once per slug going with the deletion or orphaned. It removes `.feature-dev/history/<slug>/` and only the review files named exactly `<slug>-<timestamp>[-<n>].md` — never a longer slug's.
   - `--pointer` once per stale pointer's slug.

   `purge` validates every argument before touching anything (names, slug characters, symlinks, paths that resolve outside `.feature-dev/`), and exit 2 means it deleted nothing — show the error and stop. It skips git-tracked files and prints `skipped <path>: <reason>` for each. Exit 1 means a deletion failed: show its `failed` lines.
2. Report the result from `purge`'s output, with one line per deleted file or slug:
   ```
   Deleted SPEC-<slug>.md
   Deleted PLAN-<slug>.md
   Deleted review data for <slug> — 3 snapshots, 2 reviews
   Deleted orphaned review data for <slug> — 1 snapshot, 2 reviews
   Removed stale pointer .<slug>.url
   Skipped <path> — tracked by git
   ...
   Total: N files, review data for R slugs and P stale pointers removed.
   ```
3. Add one line per rescuable spec with its outcome: `Rescued SPEC-<slug>.md → PR #<n>` (comment) or `→ docs/decisions/<slug>.md (uncommitted — commit it yourself)`; `Republished SPEC-<slug>.md → issue #<n>` (Republish, verified); `Kept SPEC-<slug>.md — rescue failed: <error>` (or, for Republish, `— republish failed: <error>`); or, for `Delete anyway`, `Lost from SPEC-<slug>.md:` followed by the decisions (one line each) and the unticked QA items, so the loss is on record in this session.

## Rules

- **Never delete files outside the candidate list.** The categorization in Phase 1 and Phase 1a is the source of truth — do not improvise. Nothing is deleted that the confirmation question did not count.
- **Never write to a PR without the user picking that option for that spec, and never edit its body.** A PR is read by others; the choice to publish a working artifact's contents there is the user's, and a comment adds to the PR without touching what anyone else wrote.
- **Never delete without the explicit confirmation in Phase 2.** Even if the user invoked this command intentionally, the destructive step requires an in-command Y/N gate.
- **Never delete files that are tracked by git** — SPEC/PLAN files and `.feature-dev/` entries alike. The local-artifact convention says both should be `.gitignore`d; if one somehow ended up tracked, surface it as a warning and skip — the user must decide whether to commit or untrack first. `purge` enforces this and reports each skip.
- **Never recurse into subdirectories.** Both Glob patterns must run only at the repo root. SPEC/PLAN files belong at the root by convention; files elsewhere are out of scope. `.feature-dev/` is the one exception, and only the entries Phase 1a listed.
- **Review data follows its slug, not its file.** A SPEC and a PLAN share a slug, so deleting one while the other stays must keep the history the survivor's next review diffs against.
- **Delete only through `review_server.py purge`, never `rm`.** A pre-approved `rm` pattern ends in a wildcard that also matches extra paths (`rm SPEC-a.md ~/x`, `rm -r .feature-dev/history/../..`); `purge` accepts names, not paths, and refuses anything else. A `--slug` is one `ls` printed or one derived per Phase 1a step 2 — a slug read raw from frontmatter can differ from the sanitized one on disk.
- **Liveness is `curl` on `/alive`, not `review_server.py url`.** `url` only reports that the pointer file exists; a server killed without cleanup leaves it behind and `url` still exits 0. Probe `/alive`, not the page: the page resets the server's idle timer and renders the whole document.
- **No partial-list selection.** This is an intentional UX choice: surgical deletion is the user's job (`rm <specific-file>`); this command exists for bulk cleanup of unambiguous candidates only.
