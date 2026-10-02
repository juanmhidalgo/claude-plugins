// Review band: the SPEC/PLAN files changed since their latest browser review,
// with a way into /feature-dev:review. One pending artifact gets its own row;
// two or more collapse into one summary row that "Show all" expands.
//
// Only recent changes are shown: an artifact modified within the last
// `review_band_window_hours`, or since this session started. Old legacy files
// that were never reviewed in the browser stay out of the way.
//
// Draws only where the engine raises `AbovePrompt` (the interactive terminal
// and desktop). Under `claude -p`, VS Code, --safe-mode or disableAllHooks
// nothing here runs, and the text suggestions in spec.md / explore-plan.md
// stay the way in.
import { atom, read, update } from 'claude-code'
import type { EngineInterface, FsEntry, Register } from 'claude-code'

import type { PendingArtifact } from '../types'

const pendingAtom = atom({ plugin: 'feature-dev', key: 'pending' } as const, [] as PendingArtifact[])
const dismissedAtom = atom({ plugin: 'feature-dev', key: 'dismissed' } as const, {} as Record<string, number>)
const sessionStartAtom = atom({ plugin: 'feature-dev', key: 'sessionStart' } as const, 0)
const expandedAtom = atom({ plugin: 'feature-dev', key: 'expanded' } as const, false)

/** Mirrors ARTIFACT_NAME in scripts/review_server.py. */
const ARTIFACT_NAME = /^(SPEC|PLAN)-[A-Za-z0-9._-]+\.md$/
/** History copies (`SPEC-x.<n>.md`) are snapshots, never artifacts. */
const HISTORY_COPY = /\.\d+\.md$/
/** Mirrors REVIEW_SUFFIX in scripts/review_server.py. */
const REVIEW_FILE = /-\d{8}T\d{6}Z(?:-\d+)?\.md$/
const SERVER_URL = /^http:\/\/127\.0\.0\.1:(\d{1,5})\/$/
const REVIEW_COMMAND = 'feature-dev:review'

type Paths = {
  /** Absolute project root; artifact paths shown to the command are relative to it. */
  root: string
  /** Folders holding SPEC-*.md / PLAN-*.md, searched in order; first name wins. */
  artifactDirs: string[]
  /** Where review_server.py writes reviews and `.<slug>.url` pointers. */
  reviewsDir: string
}

const DEFAULT_ARTIFACTS_DIR = '.feature-dev'
/** The `artifacts_dir` option, set by register(); same rules as artifacts_dir() in review_server.py. */
let artifactsDir = DEFAULT_ARTIFACTS_DIR

const DEFAULT_WINDOW_HOURS = 24
const HOUR_MS = 60 * 60 * 1000
/** The `review_band_window_hours` option, set by register(). */
let windowHours = DEFAULT_WINDOW_HOURS

/**
 * Defensive, like cleanArtifactsDir: the engine validates `options` against
 * userConfig before register() runs, but a literal `${user_config.…}` (an
 * unsaved option in a command's text) or a non-number still means the default.
 */
function cleanWindowHours(raw: unknown): number {
  if (typeof raw === 'string' && raw.includes('${')) return DEFAULT_WINDOW_HOURS
  const value = typeof raw === 'number' ? raw : typeof raw === 'string' ? Number(raw.trim()) : NaN
  return Number.isFinite(value) && value >= 1 ? value : DEFAULT_WINDOW_HOURS
}

function cleanArtifactsDir(raw: unknown): string {
  const value = typeof raw === 'string' ? raw.trim() : ''
  const parts = value.split('/').filter(p => p !== '' && p !== '.')
  if (value.includes('${') || value.startsWith('/') || parts.includes('..') || parts.length === 0) {
    return DEFAULT_ARTIFACTS_DIR
  }
  return parts.join('/')
}

/**
 * The one place artifact and review locations are resolved: specs in
 * `<artifacts_dir>/specs`, plans in `<artifacts_dir>/plans`, then legacy
 * files at the project root (a name in both is taken from the folder).
 */
export async function artifactPaths($: EngineInterface): Promise<Paths> {
  const root = (await $.session.root()).replace(/\/+$/, '')
  return {
    root,
    artifactDirs: [`${root}/${artifactsDir}/specs`, `${root}/${artifactsDir}/plans`, root],
    reviewsDir: `${root}/.feature-dev/reviews`,
  }
}

function frontmatter(text: string): Record<string, string> {
  const lines = text.split(/\r?\n/)
  const out: Record<string, string> = {}
  if (lines[0]?.trim() !== '---') return out
  for (const line of lines.slice(1)) {
    if (line.trim() === '---') break
    const m = /^([A-Za-z_][\w-]*):\s*(.*?)\s*(?:#.*)?$/.exec(line)
    if (m?.[1] !== undefined) out[m[1]] = (m[2] ?? '').trim().replace(/^['"]+|['"]+$/g, '')
  }
  return out
}

/** Same derivation as artifact_slug() in review_server.py. */
function slugOf(name: string, front: Record<string, string>): string {
  const raw = front.slug || name.replace(/\.md$/, '').replace(/^(SPEC|PLAN)-/, '')
  const slug = raw.replace(/[^A-Za-z0-9._-]+/g, '-').replace(/^[-.]+|[-.]+$/g, '')
  return slug || 'artifact'
}

function baseName(path: string): string {
  return path.split(/[\\/]/).pop() ?? path
}

async function list($: EngineInterface, dir: string): Promise<readonly FsEntry[]> {
  try {
    return await $.fs.list(dir)
  } catch {
    return []
  }
}

async function liveUrl($: EngineInterface, pointer: string): Promise<string | undefined> {
  try {
    const raw = (await $.fs.read(pointer)).trim()
    const port = SERVER_URL.exec(raw)?.[1]
    if (port === undefined) return undefined
    const alive = await $.http.fetch(`${raw}alive`)
    // A Link takes https: or http://localhost only; the server accepts both Host spellings.
    return alive.status === 204 ? `http://localhost:${port}/` : undefined
  } catch {
    return undefined
  }
}

/**
 * Artifacts whose mtime is newer than every review that names them, and
 * recent: within the window, or modified since this session started.
 */
export async function scanPending($: EngineInterface): Promise<PendingArtifact[]> {
  const paths = await artifactPaths($)
  const now = await $.clock.now()
  const sessionStart = await read($, sessionStartAtom)
  const isRecent = (mtimeMs: number) =>
    mtimeMs >= now - windowHours * HOUR_MS || (sessionStart > 0 && mtimeMs >= sessionStart)
  const reviewEntries = await list($, paths.reviewsDir)
  const reviews = reviewEntries.filter(e => e.kind === 'file' && REVIEW_FILE.test(e.name))
  const pointers = new Set(reviewEntries.filter(e => e.name.endsWith('.url')).map(e => e.name))
  const reviewedName = new Map<string, string>()
  const seen = new Set<string>()
  const pending: PendingArtifact[] = []

  for (const dir of paths.artifactDirs) {
    for (const entry of await list($, dir)) {
      const { name } = entry
      if (entry.kind !== 'file' || !ARTIFACT_NAME.test(name) || HISTORY_COPY.test(name) || seen.has(name)) continue
      seen.add(name)
      if (!isRecent(entry.mtimeMs)) continue
      let isReviewed = false
      for (const review of reviews) {
        if (review.mtimeMs < entry.mtimeMs) continue
        let named = reviewedName.get(review.name)
        if (named === undefined) {
          const text = await $.fs.read(`${paths.reviewsDir}/${review.name}`).catch(() => '')
          named = baseName(frontmatter(text).artifact ?? '')
          reviewedName.set(review.name, named)
        }
        if (named === name) {
          isReviewed = true
          break
        }
      }
      if (isReviewed) continue
      const absolute = `${dir}/${name}`
      const text = await $.fs.read(absolute).catch(() => '')
      const pointer = `.${slugOf(name, frontmatter(text))}.url`
      const url = pointers.has(pointer) ? await liveUrl($, `${paths.reviewsDir}/${pointer}`) : undefined
      const path = absolute.startsWith(`${paths.root}/`) ? absolute.slice(paths.root.length + 1) : absolute
      pending.push({ name, path, mtimeMs: entry.mtimeMs, ...(url ? { url } : {}) })
    }
  }
  return pending
}

async function refresh($: EngineInterface): Promise<void> {
  try {
    const pending = await scanPending($)
    await update($, pendingAtom, () => pending)
  } catch {
    // A scan that fails leaves the last band in place rather than flashing it away.
  }
}

async function openReview($: EngineInterface, path: string): Promise<void> {
  const commands = await $.command.list()
  const command =
    commands.find(c => c.name === REVIEW_COMMAND)?.name ??
    commands.find(c => c.plugin === 'feature-dev' && c.name.split(':').pop() === 'review')?.name
  if (command === undefined) {
    $.ui.toast(`/${REVIEW_COMMAND} is not available in this session`)
    return
  }
  // As if the person typed `/feature-dev:review <path>`: a typed command is
  // not blocked by disable-model-invocation, and its verdict gets applied.
  await $.command.run({ command, args: path })
}

export const register: Register = (on, options) => {
  if (options.review_band === false) return
  artifactsDir = cleanArtifactsDir(options.artifacts_dir)
  windowHours = cleanWindowHours(options.review_band_window_hours)

  on('session.start', async ($, e, next) => {
    const result = await next(e)
    // A hot reload fires session.start again; keep the first start time.
    if ((await read($, sessionStartAtom)) === 0) {
      const now = await $.clock.now()
      await update($, sessionStartAtom, prev => prev || now)
    }
    if (e.isInteractive) await refresh($)
    return result
  })

  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    if (e.agentId === undefined) await refresh($)
    return result
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey || e.props.view.agentId !== undefined) return next(e)
    const dismissed = await read($, dismissedAtom)
    const rows = (await read($, pendingAtom)).filter(p => dismissed[p.name] !== p.mtimeMs)
    if (rows.length === 0) return next(e)

    const { Box, Text, Button, Link } = $.ui.resolve(e)
    /** The live review page when its server answers, else a button that runs the command. */
    const openOrLink = (p: PendingArtifact, key: string, label: string, linkLabel: string) =>
      p.url ? (
        <Link key={`link:${key}`} href={p.url} label={linkLabel} />
      ) : (
        <Button
          key={`open:${key}`}
          label={label}
          variant="primary"
          onPress={() => openReview($, p.path).catch(err => $.ui.toast(`Could not open the review: ${String(err)}`))}
        />
      )
    const row = (p: PendingArtifact) => (
      <Box key={`row:${p.name}`} flexDirection="row" gap={1}>
        <Text wrap="truncate-middle">{p.name} · not reviewed since last change</Text>
        {openOrLink(p, p.name, 'Open review', 'Review page')}
        <Button
          key={`dismiss:${p.name}`}
          label="Dismiss"
          onPress={() => update($, dismissedAtom, d => ({ ...d, [p.name]: p.mtimeMs }))}
        />
      </Box>
    )
    if (rows.length === 1) return <Box flexDirection="column">{rows.map(row)}</Box>

    const expanded = await read($, expandedAtom)
    if (expanded) {
      return (
        <Box flexDirection="column">
          <Box key="summary" flexDirection="row" gap={1}>
            <Text>{rows.length} not reviewed</Text>
            <Button key="collapse" label="Collapse" onPress={() => update($, expandedAtom, () => false)} />
          </Box>
          {rows.map(row)}
        </Box>
      )
    }

    const latest = rows.reduce((a, b) => (b.mtimeMs > a.mtimeMs ? b : a))
    return (
      <Box flexDirection="column">
        <Box key="summary" flexDirection="row" gap={1}>
          <Text>{rows.length} not reviewed</Text>
          {openOrLink(latest, 'latest', `Open ${latest.name}`, `Open ${latest.name}`)}
          <Button key="show-all" label="Show all" onPress={() => update($, expandedAtom, () => true)} />
          <Button
            key="dismiss-all"
            label="Dismiss all"
            onPress={() =>
              update($, dismissedAtom, d => ({ ...d, ...Object.fromEntries(rows.map(p => [p.name, p.mtimeMs])) }))
            }
          />
        </Box>
      </Box>
    )
  })
}
