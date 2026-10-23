# NODE mode: upgrading the Node.js runtime

Same skeleton as a package upgrade, but the "package" is Node itself, the blocking risk is
usually a **native addon or a dependency's engine floor** rather than first-party code, and the
version is declared in many places that drift apart.

<verify_against_changelog priority="critical">
Do not report removals or behaviour changes from memory. For every major in the range, fetch
the release announcement (`https://nodejs.org/en/blog/release/v<N>.0.0`) and the deprecations
page (`https://nodejs.org/api/deprecations.html`, filtering for "End-of-Life" and runtime
deprecations). For support status, fetch `https://nodejs.org/dist/index.json` (the `lts` field)
or the release schedule (`https://raw.githubusercontent.com/nodejs/Release/main/schedule.json`).
The lists below are where to start looking, not the answer.
</verify_against_changelog>

## 1. Where the version is declared

Grep them all and report the ones that disagree — a mismatch is a finding on its own,
independent of the verdict. **No declaration at all except CI** is also a finding: nothing
stops a developer, the deploy host or a dependency's engine floor from drifting.

| File | Key |
|------|-----|
| `package.json` | `engines.node`, `volta.node`, `packageManager`, `devDependencies["@types/node"]` |
| `.nvmrc`, `.node-version`, `.tool-versions` | nvm / fnm / asdf / mise |
| `.npmrc` | `engine-strict=true` (turns engine mismatches from warnings into install failures) |
| `.github/workflows/*.yml` | `actions/setup-node` `node-version`, `node-version-file`, matrix entries |
| `Dockerfile`, `docker-compose.yml` | `FROM node:<N>`, `-alpine` vs `-slim` (musl vs glibc matters for native addons), build args |
| hosting config | Azure App Service / Functions `WEBSITE_NODE_DEFAULT_VERSION` or `linuxFxVersion`, Lambda `runtime: nodejsN.x`, Vercel/Netlify `engines` or project setting, Cloud Run base image, buildpack `engines` |
| tool targets | `tsconfig.json` `target`/`lib`, esbuild/vite `target: 'node<N>'`, babel `@babel/preset-env` `targets.node` |

`@types/node` is a runtime declaration too: a major ahead of the runtime lets code typecheck
against APIs that do not exist in production; a major behind hides new ones.

## 2. Dependency compatibility — the usual blocker

Two different failure modes, as with Python:

- **Engine floor or ceiling** — a dependency's `engines.node` excludes the target (rare for a
  floor when going up; common for ceilings on old tooling, `"node": "<=18"`). Read it from the
  lock (`package-lock.json` stores `engines` per package) or `npm view <pkg> engines`. Under
  `engine-strict` it fails the install; otherwise it is a warning nobody reads.
- **Native addons** — packages that compile or download a binary keyed to the Node ABI
  (`NODE_MODULE_VERSION`). Find them in the lock: `hasInstallScript: true`, a `binding.gyp`,
  dependencies on `node-gyp`, `node-pre-gyp`, `prebuild-install`, `node-gyp-build`. Then:
  - N-API / Node-API addons (`node-addon-api`, `napi` in the package) are ABI-stable across
    majors — usually safe.
  - Addons with per-ABI prebuilds: check a prebuilt binary exists for the target ABI and the
    deploy platform (glibc vs musl, arm64 vs x64) in the package's release assets. Missing ⇒
    a source build on the deploy host, which needs a toolchain the slim/alpine image may lack.
  Typical suspects: `bcrypt`, `sharp`, `canvas`, `sqlite3` / `better-sqlite3`, `node-sass`,
  `grpc` (legacy), `re2`, `argon2`, `fsevents`, anything wrapping a C library.

Also check **tooling** pinned in CI — test runners, bundlers, TypeScript, linters each carry
their own supported-Node range, and a red CI on the toolchain is still the upgrade blocked.

## 3. Runtime changes to scan for

Grep targets to start from, each confirmed against the fetched release notes for that major:

- Removed or End-of-Life APIs from the deprecations page — grep each `DEP0xxx` symbol that went
  EOL in the range (e.g. old `url.parse` behaviours, `util.is*` helpers, `punycode`,
  `Buffer()` without `new`, `fs.rmdir(recursive)`).
- OpenSSL major changes — legacy ciphers/hashes (`md4`, small RSA keys), the
  `--openssl-legacy-provider` flag in scripts, `crypto.createCipher`.
- Global and module-loader changes — `fetch`/`WebSocket`/`navigator` becoming globals (shadows
  polyfills like `node-fetch` or `isomorphic-fetch` and changes their behaviour),
  `require(esm)` support, import attributes syntax (`assert` → `with`), loader hook APIs.
- `--experimental-*` and `--no-*` flags in `scripts`, `NODE_OPTIONS`, Dockerfiles, or CI — flags
  that graduated or were removed make the process refuse to start.
- Test runner, `node:test`, permission model, or TypeScript stripping flags if the repo uses
  them.

## 4. Deployment reality

A runtime upgrade is safe only where it runs. Name the base image tag, the hosting service's
supported Node versions (fetch the provider's page — managed runtimes lag Node releases), and
the target's status: **odd majors never become LTS** and are unsuitable for production; an
even major is only LTS from its October promotion; and a version past end-of-life gets no
security fixes. `<N>.0.0` in production is its own risk line.

## 5. Verdict

Same capping rules as [report-format.md](report-format.md), plus: a native addon with no
target-ABI prebuild for the deploy platform and no Node-API build is NO-GO until either a
prebuild ships or the deploy image gains a build toolchain — and that is a change to the
deploy, reported as its own risk.
