---
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - AskUserQuestion
  - Write
  - Edit
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py purge *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/features.py *)
  - Bash(gh pr view *)
  - Bash(gh pr comment *)
  - Bash(gh auth status)
  - Bash(gh issue view *)
  - Bash(gh issue edit *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/issue_spec.py *)
  - Bash(curl -s -o /dev/null --max-time 2 http://127.0.0.1:*)
description: |
  Use to bulk-delete implemented features (spec, plan, review history and feedback) from .feature-dev/features/, and stale review-server pointers. Lists only safe candidates and requires Y/N confirm.
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
- **Feature store**: each feature lives in `.feature-dev/features/<slug>/`, managed by `${CLAUDE_PLUGIN_ROOT}/scripts/features.py` (pass `--root <repo root>`). Layout: [artifact-locations.md](../skills/spec-driven-development/references/artifact-locations.md).

## Phase 0: Discover Features

Run `${CLAUDE_PLUGIN_ROOT}/scripts/features.py list --json --root <repo root>`. Each entry has `slug`, `status` (`draft`, `approved`, `planned`, `running`, `halted`, `implemented`, `invalid`), `plan` (`steps`, `completed`, `halted_at`, `halt_reason`, or null), `issue` (a ref or null), `artifacts` (`kind`, `path`, `needs_review`) and, for an `invalid` feature, a `reason`. A missing `.feature-dev/features/` is an empty list.

The review history, review files and server pointer of a feature live inside its folder, so one feature is one unit: nothing is matched by slug prefix, and no review data outlives its feature.

If the list is empty, STOP and tell the user: "No features found. Nothing to clean up." Do not proceed.

## Phase 1: Categorize

Build three lists from the `status` of each entry.

**Safe to delete:**
- Features with status `implemented` — the work is done. The `features.py delete` command itself removes only these, so this list and the script agree.

**Active work (never offer for deletion):**
- Status `running` or `halted` — a `/feature-dev:tdd` run is mid-flight or resumable. Deleting one discards its `plan.completed` record and strands a dirty working tree with no way to tell which steps already landed.
- Status `draft`, `approved` or `planned` — work in progress.

**Ambiguous (do not offer by default — the user can delete manually):**
- Status `invalid` — a broken feature folder; surface its `reason`, never include it.

## Phase 1a: Stale review-server pointers

While a review page is served, `.feature-dev/features/<slug>/reviews/.url` holds its address. For every feature that has one, other than a `running` or `halted` feature, Read it and probe `<url>alive` (the pointer ends in `/`): `curl -s -o /dev/null --max-time 2 <url>alive`. `/alive` answers without a token and without resetting the server's idle timer, so the probe never keeps a forgotten review open. Exit 7 (connection refused) means no server — the pointer is stale. Any other exit means something answers — a **review in progress**:
- move the feature from Safe to delete to Active work with reason `review in progress` — the review's verdict is about to be applied to it;
- say "review server running at <url> — submit or close it, then rerun".

Every stale pointer, of any feature, goes in the stale-pointer list and is removed on its own with `review_server.py purge --pointer <slug>`, because `review_server.py url` would otherwise keep printing a dead URL. A pointer of a feature that is deleted below goes with its folder and needs no `purge`.

## Phase 1b: Detect Rescuable Content

The feature folder is gitignored, so anything that exists only in its spec is gone once it is deleted. For each feature in the safe-to-delete list that has a `spec` artifact:

1. **Published and current.** If the feature's `issue` is set (`<owner>/<repo>#<N>`), run the [gh preflight](../skills/spec-driven-development/references/issue-store.md#gh-preflight) — on failure, treat the SPEC as **not current** (per its "cleanup's 'published and current' check" rule) and continue to step 2. On success, compute the three [Fingerprints](../skills/spec-driven-development/references/issue-store.md#fingerprints): local (`issue_spec.py section <SPEC> | issue_spec.py fingerprint -`), recorded (`issue.fingerprint` in the feature's `feature.json`), and issue (`gh issue view <N> --repo <owner>/<repo> --json body -q .body | issue_spec.py fingerprint -`). All three equal → the SPEC is **published and current**: skip step 2 for it, it is not rescuable, and it goes straight to Phase 2 without the rescue question — it still follows the existing status rules for deletion. Any mismatch → the SPEC is **not current**: note its `#<N>`, and continue to step 2, where a SPEC with an `issue` is rescuable regardless of what step 2 finds — the mismatch itself (an unpublished local edit, or an issue that moved since the last publish) is the thing that would otherwise be lost silently. A feature with no `issue` at all also continues to step 2, under the decision/QA gate below — nothing in this step changes for it.
2. Read the body and record:
   - **Decisions** — the entries under `## Decisions Log` (written by `/feature-dev:tdd`), up to the next `## ` heading or end of file. Non-empty means at least one entry, not just the heading.
   - **Pending QA** — every unticked `- [ ]` line under `## QA Checklist`, up to the next `## ` heading. Keep the `###` group heading (`Happy path` / `Edge cases` / `Empty states` / `Error states`) each item sits under; ticked `- [x]` items were verified by the user and are not rescued. An unticked item may have been checked and never ticked, so it is reported as unticked, not as unrun.

A published-and-current SPEC is not rescuable and goes straight to Phase 2. A SPEC with an `issue` that is not current is always rescuable, even with neither a decision nor pending QA — its difference from issue `#<N>` is itself worth a rescue question, via `Republish to #<N>` in Phase 2a (below). A SPEC with no `issue` is rescuable only when it has a decision or pending QA; otherwise it goes straight to Phase 2.

## Phase 2: Present and Confirm

Present a structured summary to the user:

```
Feature-dev cleanup — candidate inventory

Safe to delete (N features):
  - <slug> — "<feature>" — implemented[ — holds: N decisions, M unticked QA items]
  ...

Active work (left alone, M features):
  - <slug> — status: <draft|approved|planned|running|halted|review in progress>
  ...

Ambiguous (not auto-included, K features):
  - <slug> — invalid: <reason>
  ...

Stale server pointers (P, no server answering):
  - <slug>
```

Counts only — never list the individual files. Omit empty groups, and also list any feature skipped for a live server.

If the "Safe to delete" list and the stale pointers are both empty, STOP and tell the user: "No safe-delete candidates. M active features left alone, K ambiguous ones surfaced for manual review." Do not prompt.

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
   - **Has a decision or pending QA item** (whether or not it is also not current): name what it holds, e.g. "the spec of <slug> holds 3 decisions and 2 unticked QA items. Keep them before deleting?"
   - **Rescuable only because it is not current** (no decision, no pending QA — an `issue` fingerprint mismatch is the only reason it is here): "the spec of <slug> differs from issue #<N> — local edits were never published, or the issue changed since. Keep it before deleting?"

   Options:
   - `Comment on PR #<n>` — preview: the exact comment text from step 2. Omitted when step 1 found no open PR for this spec, or when the spec has neither a decision nor pending QA to comment (step 1/2 were skipped for it).
   - `Save to docs/decisions/<slug>.md` — preview: the file content. The description says it is a tracked file the user commits; this command does not commit. Omitted for the same no-decision/no-QA case.
   - `Delete anyway` — nothing is kept; the Phase 3 report lists what was lost.
   - `Republish to #<N>` — only offered when the feature has an `issue` (`<owner>/<repo>#<N>`). A rescuable spec with one is already not current (Phase 1b step 1 sends a published-and-current spec straight to Phase 2, never through this question). Preview: "runs the publish algorithm against issue #<N>". Picking it runs [issue-store.md's Publish algorithm](../skills/spec-driven-development/references/issue-store.md#publish-ac-1-ac-2-ac-3-ac-4-ac-5-ac-7) against this spec and target `#<N>`, start to finish — its `gh` preflight, the AC-4 conflict ask if the issue's section changed since the last publish, and the AC-5 re-read-and-verify. Do not restate those steps here — follow the reference. For a spec with no decision/QA content, this and `Delete anyway` are the only two options.
4. **Apply the choice.** Writing to a PR is visible to reviewers, so it happens only for a spec where the user picked that option — never as a default or a fallback from a failed save. The rescue is a new comment; the PR body is never edited, because a body rewrite can overwrite what the author or a bot put there since it was read.
   - **PR**: if the comments from step 1 already contain every heading this spec's text has (`## Decisions — <slug>`, `## Pending QA — <slug>`), report "already on PR #<n>" and treat the spec as rescued — a rerun never posts twice. Otherwise Write the step 2 sections not already there to a file at a path unique to this spec and run — `feature-dev-cleanup-<slug>-<random>.md` in the session scratchpad if one is listed, else under `/tmp/`. Read the path first and pick another name if it already exists, so a stale file from an earlier run is never posted. Run `gh pr comment <n> --body-file <file>`. Then re-run `gh pr view <branch> --json comments` and confirm a comment now carries each heading; a heading still missing after posting is a failed rescue.
   - **File**: if `docs/decisions/<slug>.md` exists, Read it and Write its content plus the sections it does not already have; otherwise Write a new file with a `# <feature>` title and the sections.
   - **Republish**: run the reference's Publish algorithm linked in step 3, against `#<N>` from the feature's own `issue`. On the reference's AC-4 mismatch ask, offer only "overwrite the issue" or "cancel" — this command does not carry Import's tools (no `gh issue create`, no `review_server.py snapshot`), so "import the issue's version instead" is out of scope here; treat that pick the same as **Failure** below, since nothing was published. On a verified publish (the reference's step 7, which records the fingerprint on the feature), the spec's content now lives on the issue and its feature keeps its place in the delete list.
   - **Failure**: if `gh` or Write fails, or the verification above finds a heading missing (PR) or a fingerprint mismatch (Republish), show the error verbatim and mark the spec **rescue failed** — for Republish, say the **republish failed**. A failed spec's feature is removed from the delete list — deleting it would lose exactly what the user chose to keep (for Republish, the content the republish tried to save). 

Then continue to the confirmation, with N recounted after moving rescue-failed features to Active work. P is the stale pointers.

Run Phase 3's commands now with `--dry-run`: `${CLAUDE_PLUGIN_ROOT}/scripts/features.py delete <slug> --dry-run --root <repo root>` once per feature in the delete list, and `review_server.py purge --pointer <slug> --dry-run` for the stale pointers. Each prints the paths it would remove and removes nothing. A `refused: …` line (exit 1) takes that feature out of the delete list and into Active work or Ambiguous with the refusal as its reason — a git-tracked file inside the folder is refused even with `--force` — so the question never promises a deletion that will not happen.

- Question: "Delete N implemented features and P stale pointers? This is irreversible — none of it is in git." Drop each part that is zero.
- Header: "Delete" (the header is capped at 12 characters)
- Options:
  - `Yes, delete all` — proceed with deletion
  - `Cancel` — stop, delete nothing

## Phase 3: Delete

If the user chose `Cancel`, report "Cancelled. No files deleted.", then one line per spec already rescued in Phase 2a (`Rescued <slug> → PR #<n>` or `→ docs/decisions/<slug>.md (uncommitted — commit it yourself)`) — the comment or file already exists and cancelling does not undo it — and STOP.

If the user chose `Yes, delete all`:

1. Delete each feature in the delete list with the same command as the dry run, without `--dry-run` — never `rm`:
   ```
   ${CLAUDE_PLUGIN_ROOT}/scripts/features.py delete <slug> --root <repo root>
   ```
   It removes the whole feature folder (spec, plan, history, reviews, pointer) only when the feature is `implemented`; any other state is refused naming it. Never pass `--force`: this command deletes only what Phase 1 judged safe. A `refused: …` line (exit 1) means that feature was kept — show it verbatim and count it as kept.
2. Remove each stale pointer of a feature that was not deleted:
   ```
   ${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py purge --pointer <slug> --root <repo root>
   ```
   `purge` skips git-tracked files and symlinks and prints `skipped <path>: <reason>` for each; exit 2 means an argument is invalid and nothing was deleted.
3. Report from the commands' output, one line per deleted feature or pointer:
   ```
   Deleted feature <slug>
   Removed stale pointer <slug>
   Kept <slug> — refused: <reason>
   ...
   Total: N features and P stale pointers removed.
   ```
4. Add one line per rescuable spec with its outcome: `Rescued <slug> → PR #<n>` (comment) or `→ docs/decisions/<slug>.md (uncommitted — commit it yourself)`; `Republished <slug> → issue #<n>` (Republish, verified); `Kept <slug> — rescue failed: <error>` (or, for Republish, `— republish failed: <error>`); or, for `Delete anyway`, `Lost from <slug>'s spec:` followed by the decisions (one line each) and the unticked QA items, so the loss is on record in this session.

## Rules

- **Never delete anything outside the candidate list.** The categorization in Phase 1 is the source of truth — do not improvise. Nothing is deleted that the confirmation question did not count.
- **Never write to a PR without the user picking that option for that spec, and never edit its body.** A PR is read by others; the choice to publish a working artifact's contents there is the user's, and a comment adds to the PR without touching what anyone else wrote.
- **Never delete without the explicit confirmation in Phase 2.** Even if the user invoked this command intentionally, the destructive step requires an in-command Y/N gate.
- **Never delete files that are tracked by git.** `features.py delete` refuses a folder with a tracked file even with `--force`, and `purge` skips tracked files; surface the refusal and let the user decide whether to commit or untrack first.
- **Delete only through `features.py delete` (and `purge --pointer` for stale pointers), never `rm`.** A pre-approved `rm` pattern ends in a wildcard that also matches extra paths; `delete` accepts one feature slug, refuses a symlinked folder or anything outside `.feature-dev/features/`, and removes only an `implemented` feature.
- **Liveness is `curl` on `/alive`, not `review_server.py url`.** `url` only reports that the pointer file exists; a server killed without cleanup leaves it behind and `url` still exits 0. Probe `/alive`, not the page: the page resets the server's idle timer and renders the whole document.
- **No partial-list selection.** This is an intentional UX choice: surgical deletion is the user's job (`features.py delete <slug>`); this command exists for bulk cleanup of unambiguous candidates only.
