---
disable-model-invocation: true
allowed-tools:
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py *)
  - Bash(date +%s)
  - Read
  - Glob
  - Grep
  - Edit
  - Write
  - AskUserQuestion
  - Bash(gh auth status)
  - Bash(gh repo view --json nameWithOwner*)
  - Bash(gh issue view *)
  - Bash(git branch --show-current)
  - Bash(${CLAUDE_PLUGIN_ROOT}/scripts/issue_spec.py *)
argument-hint: "<SPEC-*.md or PLAN-*.md path, #issue, owner/repo#issue, or issue URL — optional; asks when several exist>"
description: |
  Use to review a SPEC-*.md or PLAN-*.md in the browser — outline, decision cards, text-anchored comments, diff against the previous version — and apply the verdict.
  Do NOT use for a structural gap check (use /feature-dev:spec-review or /feature-dev:plan-review) or for code review.
keywords:
  - review
  - browser
  - spec
  - plan
  - feature-dev
triggers:
  - "review the spec in the browser"
  - "open the plan for review"
---

## Context
- **Artifact argument**: $ARGUMENTS

The review happens in a local page instead of the chat. Specs and plans of 332–1073 lines were approved 37–72 s after being written, from chat summaries, and nobody opened the files; the page puts the document, its decisions and its changes since the last version in front of the reviewer, and turns what they mark into a file this command applies.

The page is served by `review_server.py` on `127.0.0.1`, on a random free port. It uses the Python 3 standard library only and loads nothing from the network: no CDN, fonts or external scripts, so it is safe on proprietary repos.

## Phase 0: Resolve the artifact

1. **If `$ARGUMENTS` is `#N`, `owner/repo#N`, or an issue URL** → resolve it per [issue-store.md's Argument parsing](../skills/spec-driven-development/references/issue-store.md#argument-parsing), then run [issue-store.md's Import algorithm](../skills/spec-driven-development/references/issue-store.md#import-ac-8-ac-9-ac-10-ac-11-ac-12) against it, start to finish. Do not restate Import's steps here — follow the reference. A failed `gh` preflight, or a failed `gh issue view` call, stops here and names the issue that could not be read. On success, continue as if `$ARGUMENTS` had been the resulting `SPEC-<slug>.md` path (the reference's own step 6). An issue argument only ever produces a SPEC — there is no PLAN equivalent.
2. **If `$ARGUMENTS` names an existing file** → use it. If it does not exist, STOP and report.
3. **If `$ARGUMENTS` is empty** → Glob `SPEC-*.md` and `PLAN-*.md` in the repo root. 0 → STOP and point to `/feature-dev:spec`. 1 → use it. 2+ → AskUserQuestion (label = file name, description = its `feature:` and `status:`).
4. Read its frontmatter. The kind is SPEC or PLAN, from `type:` or the file name prefix. Do not derive the slug yourself: the script sanitizes it, and every file path below comes from the script.
5. If the project's `.gitignore` does not include `.feature-dev/`, add it. It holds review files and version history, which are local working artifacts, as the SPEC and PLAN files are.

## Phase 1: Serve and wait

1. Record the start time with `date +%s`. The review this round produces is the one written after it.
2. Run the server with Bash and `run_in_background: true`:

   ```
   ${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py serve <artifact path>
   ```

3. Tell the user in one line: the review page is opening in the browser, and if it did not open, `${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py url <artifact path>` prints its URL. Then end the turn.

Do not poll, `sleep`, or read the background task's output. The harness re-invokes you when the process exits, and it exits only after a submit or after 4 h without a request. While the page is open and visible it pings the server every minute, so a long read does not count as idle. The task's output is not a stable source; the review file is.

## Phase 2: Read the review

When the background task completes:

1. Run `${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py latest <artifact path> --since <start time>`. It prints the path of the review written for this artifact since the start time. Use it rather than Glob, which can skip the gitignored `.feature-dev/`. **Exit 1, nothing printed** → the server stopped without a review (idle timeout or interrupted). Say "No review submitted", give the command to reopen it, and stop.
2. Read the new file. Frontmatter: `artifact`, `verdict` (`approve` | `approve-with-notes` | `request-changes`), `reviewed_sha256`. Body: numbered items, each `> quoted text` + `§ heading` then the comment; then `## Decision overrides` with lines `D<n>: change to <text>`. `D<n>` is row n of the plan's Key Decisions table.
3. **Check for drift.** Run `${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py sha <artifact path>`. If it differs from `reviewed_sha256`, or the frontmatter says `changed_on_disk_since_served: true`, the reviewer commented on a version that is no longer on disk. Say so, list the items, and apply nothing. Offer another round on the current version. Quotes anchored to text that has since moved are how a correct comment gets applied to the wrong place.

## Phase 3: Apply the verdict

**`approve`**
- SPEC → set `status: approved` with Edit. This is the only verdict that sets it. Then run `${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py settle <artifact path>`, so the review band above the prompt does not report your own status edit as a change nobody reviewed.
- PLAN → plans carry no approval field; nothing to edit.

**`approve-with-notes`**: the notes are context, not change requests.
- Acknowledge each note in one line.
- Record a note where it binds later work: a note constraining how a later step or another repo must behave goes into the spec's `## Decisions Log` (for a PLAN, its `source_spec`), in the entry format `/feature-dev:tdd` uses, with `Binds:`. A note that binds nothing stays in this reply.
- Change nothing in the artifact unless a note explicitly asks for a change. A decision override is an explicit ask, so apply it as under `request-changes`.
- For a SPEC, `status:` stays as it is. If the user wants it approved with the notes, they say so and you set it.

**`request-changes`**: each item and override is a hypothesis about the artifact, not an instruction to paste in.
1. **Snapshot first**: `${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py snapshot <artifact path>`. This copies the reviewed version to `.feature-dev/history/<slug>/`, so the next round shows the diff.
2. **Verify each item** against the artifact, and against the code when the item makes a claim about the code: Read the file, Grep the symbol. Locate the quote under its `§` heading. An item that is wrong about the code, or would contradict an AC or a recorded decision, is not applied; say why in one line, with the `file:line` you checked.
3. **Apply the rest** with Edit. Keep AC ids stable: a new criterion takes the next free number, and a removed one retires its id. In a PLAN, a decision override changes its Key Decisions row and every step that depended on the old choice. A changed or new step follows explore-plan's step contract (Accept, Verify, Covers). A changed `Verify:` has no Baseline row until it is re-baselined, so say so.
4. **Report one line per item**: `<n>. applied — <what changed>` or `<n>. not applied — <why>`, then one line per override.
5. **Offer another round** with AskUserQuestion: **Review again** (recommended; the page will show what changed) / **Done**. On **Review again**, go back to Phase 1.

## Phase 4: Next

End with the next command for the artifact, then stop:

- SPEC → `Next: /feature-dev:explore-plan <spec path>`
- PLAN → `Next: /clear, then /feature-dev:tdd <plan path>`

After a PLAN changed in this command, add: `/feature-dev:plan-review <plan path> re-checks the edited steps`.

## Rules

- **Only `approve` sets `status: approved`.** Notes are not approval, and a review that sets it from anything weaker marks a spec approved that nobody approved.
- **Verify before editing.** A reviewer's comment about the code can be wrong in the same way as a spec's claim. Check it the way `/feature-dev:spec-review` checks claims.
- **A changed artifact is not auto-applied.** On a sha mismatch the comments point at text that may have moved.
- **The artifacts stay local.** Never commit SPEC, PLAN or `.feature-dev/`, and run no git commands against them.
