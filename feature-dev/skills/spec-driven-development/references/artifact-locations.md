# Artifact locations

Where `SPEC-*.md` and `PLAN-*.md` live, and where a feature's state is kept, for every
feature-dev command. Commands link here instead of restating it.

## Layout

```
.feature-dev/
└── features/<slug>/
    ├── feature.json          # state; written only by features.py
    ├── SPEC-<slug>.md        # content; written by the agent
    ├── PLAN-<slug>.md        # a plan born from a spec lives in that spec's folder
    ├── reviews/              # /feature-dev:review verdicts, <YYYYMMDDTHHMMSSZ>[-<n>].md
    │   └── .url              # pointer to the live review server
    └── history/              # snapshots for the review diff
```

One folder per feature. A plan without a spec gets its own `features/<slug>/` folder.
Everything here is a local working artifact: gitignored, never committed. Nothing else
under `.feature-dev/` is read.

The previous layout (separate `specs/`, `plans/`, `reviews/` and `history/` folders
directly under `.feature-dev/`, and `SPEC-*.md` / `PLAN-*.md` at the project root) is
not read and is not migrated. Delete those by hand.

## State: `feature.json`

`feature.json` holds the feature's status, the spec approval, plan progress and the
linked issue. Only `features.py` writes it (atomically); never edit it by hand, and
editing SPEC or PLAN content never changes it. SPEC/PLAN frontmatter keeps only
descriptive keys: `type`, `feature`, `slug`, `date`, `branch`, `repos`.

States: `draft` -> `approved` -> `planned` -> `running` <-> `halted` -> `implemented`.
A folder whose `feature.json` is missing or unparseable is listed as `invalid` and
refuses transitions. The transitions are the table in `scripts/features.py`.

```
${CLAUDE_PLUGIN_ROOT}/scripts/features.py <subcommand> --root <repo root>
```

| Subcommand | Effect |
|---|---|
| `new <slug> --kind spec\|plan [--spec X]` | Creates the folder and `feature.json`; prints the path to Write |
| `approve <slug>` | Marks the spec `approved` |
| `plan <slug> --steps N [--from-spec] [--replace]` | Records the plan (`planned`) |
| `step <slug> done\|halt\|resume` | Records `/feature-dev:tdd` progress |
| `implemented <slug>` | Closes the feature once every step is done |
| `link-issue <slug>` | Records the linked issue |
| `delete <slug> [--force] [--dry-run]` | Removes the folder |
| `list [--json]` | Lists features with state and artifact paths |

Use `list --json` instead of Glob to find artifacts: Glob can skip the gitignored
`.feature-dev/`. The PLAN is kept after `implemented`; `/feature-dev:cleanup` removes
finished features through `features.py delete`.

## Writing: where a new artifact goes

`features.py new <slug> --kind spec|plan` prints the path to Write
(`.feature-dev/features/<slug>/SPEC-<slug>.md` or `PLAN-<slug>.md`). Write creates no
state: the state change is always a `features.py` call.

An argument that names an existing file is used as given, wherever it is.

## References between artifacts

A plan lives in its spec's folder, so no `source_spec:` key is needed. A plan for a spec
in a sibling repo names that spec by path in its body. Print paths, not bare names, in
every `Next:` line, so the command it suggests opens the right file.
