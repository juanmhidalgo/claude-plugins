# Changelog

## 0.5.0 (2026-11-02)

### Added
- **Every stage reads the run's real caps.** The daemon now exports `FACTORY_MAX_TURNS`, `FACTORY_BUDGET_USD` and `FACTORY_TIMEOUT_MINUTES` (per-repo overrides applied); each command shows them in its Context as `Caps for this run` and sizes long steps (test suites, review rounds) against them. The numbers in the commands' `Caps are the daemon's (defaults …)` sentence are defaults only; unset variables (manual mode) mean the defaults.
- **`factory-outcome.sh done … --files-file <f>`**: one repo-relative path per line (blank lines ignored) becomes `files="…"` on the done marker, sorted (byte order), deduplicated, always quoted; `plan` only (another stage: exit 2, "files only on plan"); an empty file omits the attribute. A path with a leading `/` or `./`, a `.`/`..`/empty segment, a trailing `/`, a space, comma, double quote, `*`, `?`, `<`, `>`, backslash or control character is `refused: bad path in --files-file: <line>` (exit 2, nothing posted). The `--sha` cross-check is unchanged and runs after the path check.
- **`factory-issue.sh replan <N>`**: prints the attributes and body of the daemon's `<!-- factory:replan by=daemon reason=base-moved sha=… base=… files="…" run=… -->` comment when it is newer than the plan's `done` and than any `question` marker (exit 1 otherwise). `last-marker` ignores it and `answer` skips it: it is not an outcome.
- **`/factory:plan` lists the open factory PRs that touch its area.** Before exploring it runs `gh pr list --state open --json number,headRefName,title,files` (new `allowed-tools` entry), keeps the `factory/*` heads, intersects their files with the plan's, and ends the plan with `## Open PRs touching this area` (`#n <title> — <shared paths>`, or `none`). The plan is still written against `origin/<default>`; the daemon's gate holds the issue while a listed PR is open.
- **`/factory:plan` passes its files to the done marker.** Every path in `Files to Modify`, `Files to Create`, each step's `Impl:`/`Test:` and each deletion goes to a scratch file and `--files-file`; the done comment says `Files: <n>`.
- **`/factory:plan` re-plans on the daemon's `replan` comment.** When one is newer than the plan's `done`, the stage reads the merged change on the files the marker names (`git log -p <sha>..HEAD -- <paths>`), re-explores against the current clone, replaces the published plan section (Publish is an upsert) and posts a fresh `done` with the new `sha` and `files`. The flip-only rule stays for every other re-run; when a `question` and a `replan` are both present the newest marker wins.
- `references/factory-contract.md` §3 documents `files=` and the `replan` marker (daemon-written, not an outcome) and §4 step 3 the re-plan exception; README and the script headers list the new marker. `test_factory_scripts.sh`: 95 → 179 tests.

### Fixed
- `factory-outcome.sh`: an option given as the last argument without its value now exits 2 with `<option> needs a value` instead of dying on an unbound variable (exit 1).

## 0.4.0 (2026-11-01)

### Added
- **Adversarial review axis in `/factory:spec` and `/factory:plan`.** After the validator pass and before Publish, each stage dispatches `discuss:doc-adversary` on the SPEC (sources: the repo root) or the PLAN (sources: the repo root and the SPEC) — paths only, never content, report read from `OUTPUT_PATH` first, one `Evidence` reference spot-checked against the clone. A HIGH finding is a `question` quoting its `Decision at risk`; a MEDIUM finding gets one fix pass (an `A-<n>` assumption in the spec, a rewritten Key Decision in the plan, with the finding's Evidence as basis) and the adversary runs once more, a MEDIUM that survives being a question too; a `do not implement as written` verdict and a `Needs to be resolved` item are questions; no report twice → `parked reason=adversary-unreviewed`. The done comment carries an **Adversarial review** block (verdict, re-run, findings and how each was resolved, falsification attempts). The step runs under all three lanes; a re-run after an answer runs the adversary once with no fix pass. New dependency: `discuss`. Caps raised to pay for it: spec 60 turns · 4 USD · 20 min → 80 · 6 · 30, plan 80 · 6 · 30 → 100 · 9 · 40.

## 0.3.2 (2026-11-01)

### Changed
- **The factory never requests a Copilot review.** `/factory:ship` invokes `/ship` with `--skip-copilot-review`, and the close block says `Copilot: skipped (the factory does not request Copilot; the PR review is the human gate)`. The confirm-and-retry text from 0.3.1 stays in the `/ship` skill, which other repositories use with Copilot; it no longer applies to the stage. The contract (rule 9) and the README say so.

## 0.3.1 (2026-11-01)

### Fixed
- **`/factory:ship` confirms the Copilot request or says `Copilot: not requested`.** After `gh pr edit <n> --add-reviewer @copilot` the stage checks `reviewRequests`, the REST `requested_reviewers` and the timeline, retries once through the REST API with `copilot-pull-request-reviewer[bot]` (ship 2.1.1's step 8), and the close block says `requested (<login>, seen in <listing>)` only when a listing shows it, else `not requested` with why. In the first end-to-end run two accepted calls left no request and the stage reported it as "requested twice".

## 0.3.0 (2026-11-01)

### Added
- **`/factory:ship` honours the repository's PR template.** When `.github/PULL_REQUEST_TEMPLATE.md` (or the other names `/ship` looks for) exists, the PR body keeps the template's headings in their order and maps the factory's pieces into them: `Closes #N` stays line 1, the "what changes" heading gets Summary and the acceptance criteria, a checklist heading keeps the template's items (ticked only when an Evidence line covers them) and gets the Evidence bullets as ticked items, a reviewer-notes heading gets Merge Danger, Rollback Triggers and the harden close block, and `## Factory` is appended last. Unmapped headings keep their template text. Without a template the layout is unchanged. In the first end-to-end run the stage ignored the repository's `Qué cambia` / `Checklist` / `Notas para el reviewer` template.

## 0.2.0 (2026-11-01)

### Changed
- **`factory-outcome.sh done` reads the sha from git, never from the stage.** The marker's `sha=` is `git -C "${FACTORY_WORKDIR:-$PWD}" rev-parse HEAD`; outside a git repository `done` dies (exit 2). `--sha` is now optional and only a cross-check: a value that is not HEAD (or an abbreviation of it) is refused with `refused: --sha differs from git HEAD` (exit 2, nothing posted). In the first end-to-end run the implement stage typed a hash with one wrong character and needed a second done comment to correct it. The contract (§3, §4) and the three stage commands say the call takes no `--sha`. `test_factory_scripts.sh`: 81 → 95 tests (no `--sha`, equal, abbreviated, differing, mistyped, not a repository, `FACTORY_WORKDIR`).

## 0.1.0 (2026-11-01)

### Added
- The five stage commands the factory daemon runs headless, one per tick: `/factory:spec`, `/factory:plan`, `/factory:implement`, `/factory:harden`, `/factory:ship`. Each reads everything from the issue and the branch, composes `feature-dev`, `code-review`, `ship` and `github-issues`, and ends with exactly one outcome on GitHub (`done`, `question`, `parked`) before it stops. None of them asks.
- `references/factory-contract.md`: the shared contract every command includes (identity, the issue-store body sections, the marker rule, outcomes and the lane table, the question protocol, the hard rules).
- `scripts/factory-issue.sh` (status, lane, last-marker, answer, next-status) and `scripts/factory-outcome.sh` (done, question, parked, progress, decision, flip): the only place a `<!-- factory:… -->` marker is typed. `scripts/test_factory_scripts.sh` tests both offline against a stubbed `gh`.
- `references/review-loop.md`, `references/step-loop.md` and `scripts/tree-hash.sh` are synced copies from `shared/`.
