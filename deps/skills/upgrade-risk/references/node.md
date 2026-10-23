# Node/JS: manager detection, dry-run resolution, and changelog sources

<flag_caveat>
The flags below are the ones to reach for, not a guarantee about the version installed here.
If a command errors on an unknown flag, run its `--help` and adapt — do not fall back to a
command that *writes*. In particular: `npm install` without `--dry-run`,
`npm install --package-lock-only` (rewrites the lock), `npm audit fix`, `npm update`,
`pnpm install --lockfile-only`, `pnpm audit --fix` (writes overrides into `package.json`),
`yarn up`, `npx npm-check-updates -u`. The no-mutation rule outranks getting the section
answered.
</flag_caveat>

## 1. Detect the manager

| Evidence | Manager | Lock file to read for current versions |
|----------|---------|----------------------------------------|
| `package-lock.json` (or `npm-shrinkwrap.json`) | npm | `package-lock.json` → `packages["node_modules/<pkg>"].version` |
| `pnpm-lock.yaml` | pnpm | `pnpm-lock.yaml` → `importers` for the direct version, `packages` for every copy |
| `yarn.lock` with `__metadata:` | yarn berry (2+) | `yarn.lock` |
| `yarn.lock` without `__metadata:` | yarn classic (1.x) | `yarn.lock` |
| `bun.lock` / `bun.lockb` | bun | `bun.lock` (text); `bun.lockb` is binary — UNKNOWN unless `bun pm ls` is run by the user |
| only `package.json` | unlocked | none — flag it |

`packageManager` in `package.json` (Corepack) and the install command in CI
(`npm ci`, `pnpm install --frozen-lockfile`, `yarn install --immutable`) beat the lock file
the repo root suggests. Two live locks ⇒ say so rather than picking one. Workspaces
(`workspaces` in `package.json`, `pnpm-workspace.yaml`) ⇒ say which workspace(s) depend on the
package; each has its own manifest but they share the root lock.

## 2. Current version — every copy, not one

```bash
npm ls <pkg> --all                 # every path that pulls it in, with versions
npm explain <pkg>                  # why each copy is there
pnpm why <pkg>                     # pnpm
yarn why <pkg>                     # yarn
```

Node lock files routinely hold **several copies** of one package at different versions. Report
each copy and who requires it; "the current version" is only well-defined for the direct one.
A second copy of a library that keeps module-level state (SDK clients, React, a
`instanceof`-checked error class, a type package) is a defect on its own.

## 3. Target version and its metadata

```bash
npm view <pkg> versions --json                       # releases
npm view <pkg> dist-tags                             # latest / next / beta
npm view <pkg>@<target> engines peerDependencies peerDependenciesMeta dependencies deprecated type exports main types
```

What to read from it:

- `engines.node` — a raised floor is a breaking change even in a minor. Compare it against
  the repo's runtime declarations ([node-version.md](node-version.md) §1).
- `peerDependencies` — exact (`"2.1.0"`) vs range (`^2.1.0`). Exact peers mean the family must
  move in lockstep; check every member's target exists (`npm view <member> versions`).
- `deprecated` — a deprecated target is a warning; a deprecated current version is a reason.
- `type: "module"`, `exports` without a `require` condition — the package went **ESM-only**.
  Any `require('<pkg>')` in first-party code, CJS config files (`*.config.cjs`, jest config) or
  ts-node/jest transforms is then an APPLIES.
- `exports` map changes — deep imports (`<pkg>/lib/x`, `<pkg>/dist/x`) that were reachable
  before may now throw `ERR_PACKAGE_PATH_NOT_EXPORTED`.
- Whether a specific symbol still exists or became `@deprecated`: `npm view` cannot answer
  it. WebFetch the target's type declarations from `https://unpkg.com/<pkg>@<target>/` +
  the `types` path from `npm view` (append `?meta` to a directory URL to list files), and quote
  the declaration.
- `types` / bundled types vs a separate `@types/<pkg>` — a package that starts shipping its own
  types makes the `@types` package stale or conflicting.

## 4. Usage scan — places a plain import grep misses

- `import … from '<pkg>'`, `import('<pkg>')`, `require('<pkg>')`, `require.resolve`,
  `import type` (TS type-only — breaks typecheck, not runtime).
- Subpath imports: `'<pkg>/…'` — each is a separate surface the `exports` map controls.
- Config that loads it by name: `vite.config.*`, `webpack.config.*`, `babel.config.*` /
  `.babelrc`, `jest.config.*` (`transform`, `testEnvironment`, `moduleNameMapper`),
  `vitest.config.*`, `eslint.config.*` / `.eslintrc*` (plugins and parsers by string),
  `postcss.config.*`, `tailwind.config.*`, `tsconfig.json` (`types`, `paths`, `plugins`).
- `package.json` `scripts` and the CLI binaries the package ships (`npx <bin>`, CI steps).
- `overrides` (npm), `pnpm.overrides`, `resolutions` (yarn) — a pinned override can make the
  bump a no-op or force an incompatible copy; it is always worth a line in the report.
- Patches: `patches/` (patch-package, `pnpm patch`, yarn `patch:` protocol) — a patch against
  the old version will not apply to the new one.

## 5. Dry-run resolution

```bash
# npm — reports what would change without touching the lock or node_modules
npm install --dry-run '<pkg>@<target>'
npm install --dry-run                              # after nothing: confirms the current lock resolves

# pnpm / yarn — no reliable dry-run install
pnpm why <pkg>; pnpm view <pkg>@<target> peerDependencies
yarn why <pkg>; yarn npm info <pkg>@<target> --fields peerDependencies,engines
```

When the manager has no dry run, Phase 3 is built from the peer and engine metadata plus
`why`, and labelled **resolution inferred from metadata** — weaker than a resolver run, and the
verdict says so. In PR mode, the PR's CI install step is the resolver run
([dependabot-pr.md](dependabot-pr.md) §4).

npm writes `ERESOLVE` and `EBADENGINE` to stderr; if the tool output only shows stdout, rerun
the same command and read stderr rather than concluding it was clean.

Read the output for: `ERESOLVE` and the exact conflicting peer, `EBADENGINE` warnings (npm
warns rather than fails unless `engine-strict=true` in `.npmrc` — check it), packages nested
as a second copy to satisfy an exact peer, and anything moved backwards.

## 6. Changelog sources, in order of trust

1. GitHub releases for the tag range: `https://github.com/<org>/<repo>/releases` — the
   repository URL is in `npm view <pkg> repository.url`. Monorepos tag per package
   (`<pkg>@2.1.0`); fetch the package's tags, not the repo's newest.
2. `CHANGELOG.md` at the target tag, in the package's directory for monorepos.
3. The project's migration guide, when it publishes one.
4. The compare view `https://github.com/<org>/<repo>/compare/v<current>...v<target>` — commit
   subjects only; use it to find `feat!:` / `BREAKING CHANGE` / "drop Node" commits when the
   changelog is thin.

5. Per-commit diffs when there are no releases and the compare view times out: WebFetch
   `https://github.com/<org>/<repo>/commit/<sha>.diff`, or
   `gh api --method GET repos/<org>/<repo>/commits/<sha> --jq '.files[] | {filename, patch}'`.
   For a patch release the diff *is* the changelog — read it rather than the commit subject.

Fetch every release between current and target. For packages that follow conventional commits,
a `chore:` commit that raises the Node floor is a breaking change wearing a `chore` label.

## 7. CVEs

```bash
npm audit --json                   # current lock
npm audit --omit=dev --json        # what ships to production
pnpm audit --json
yarn npm audit --all --recursive   # berry
yarn audit --json                  # classic
```

Audit output reports every vulnerable **copy**; check that the target fixes all of them, not
just the direct one. For the target version, query the global advisory database:
`gh api --method GET /advisories -f ecosystem=npm -f affects=<pkg>@<target> --jq '.[] | {ghsa_id, severity, summary}'`
(empty array ⇒ none published as of today), or the repo's security advisories. Cite ids only
from output seen in this run.
