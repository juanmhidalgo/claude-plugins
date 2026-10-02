# Artifact locations

Where `SPEC-*.md` and `PLAN-*.md` live, for every feature-dev command. Commands link
here instead of restating it.

## Layout

```
<artifacts_dir>/            # plugin option `artifacts_dir`, default .feature-dev
├── specs/SPEC-<slug>.md
└── plans/PLAN-<slug>.md
.feature-dev/
├── reviews/                # /feature-dev:review verdicts and .<slug>.url pointers
└── history/<slug>/         # snapshots for the review diff
```

`reviews/` and `history/` always stay under `.feature-dev/`; the option moves only
specs and plans. Everything here is a local working artifact: gitignored, never
committed.

## The folder value

Each command's Context line gives the folder as `${user_config.artifacts_dir}`.
When that text is still a literal `${user_config...}` placeholder, the option was
never saved: the folder is `.feature-dev`. Pass the value to the script exactly as
shown either way; the script applies the same rule.

## Reading: find an artifact

```
${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py artifacts --dir "<folder>" [--kind spec|plan]
```

It prints one path per line, relative to the project root: `<folder>/specs/` and
`<folder>/plans/` first, then legacy files at the root. A name present in both is
listed once, from the folder. Use this instead of Glob, which can skip the
gitignored `.feature-dev/`.

**Legacy files at the root** (written before 1.32.0) are still found, reviewed,
planned from, edited in place and cleaned up. Nothing moves them. Move one by
hand into the folder if you want; once a name exists in the folder, that copy is
the one listed.

An argument that names an existing file is used as given, wherever it is.

## Writing: where a new artifact goes

```
${CLAUDE_PLUGIN_ROOT}/scripts/review_server.py artifacts --dir "<folder>" --new SPEC-<slug>.md
```

It prints the path to Write (`<folder>/specs/SPEC-<slug>.md`, or `plans/` for a
PLAN). Write creates the folder. Writes only ever go to that path, never to the
root. When updating an artifact that was found at the root, keep editing it in
place: only a brand-new file goes to the folder.

## References between artifacts

A plan's `source_spec:` holds the spec's path as found (folder or root). Print
paths, not bare names, in every `Next:` line, so the command it suggests opens
the right file.
