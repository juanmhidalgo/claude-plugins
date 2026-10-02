// Pure helpers for test-progress: command detection, progress-file parsing,
// and the band's text. No `$` here, so every function is unit-testable.

import type { TestBand, TestProgress, TestRun, TestSummary } from '../types'

export const EMPTY_BAND: TestBand = { running: {}, summary: null }

// ---------------------------------------------------------------------------
// Detecting a test command
// ---------------------------------------------------------------------------

// Wrappers that run the next word as a command: `uv run pytest`, `time go test`.
const RUN_WRAPPERS: { [head: string]: string | null } = {
  uv: 'run',
  poetry: 'run',
  pdm: 'run',
  hatch: 'run',
  pipenv: 'run',
  rye: 'run',
  npx: null,
  bunx: null,
  pnpx: null,
  env: null,
  time: null,
  nice: null,
  nohup: null,
  exec: null,
  command: null,
  timeout: null,
}

// Long and short flags of those wrappers that take a separate value.
const VALUE_FLAGS = new Set([
  '--with',
  '--with-requirements',
  '--with-editable',
  '--python',
  '-p',
  '--extra',
  '--group',
  '--package',
  '--env-file',
  '--directory',
  '--project',
  '--index',
  '-C',
  '-P',
  '-n',
  '--signal',
  '--kill-after',
])

const ASSIGNMENT = /^[A-Za-z_][A-Za-z0-9_]*=/

/** Drops heredoc bodies: their lines are data, never commands. */
export function stripHeredocs(command: string): string {
  const out: string[] = []
  const pending: string[] = []
  for (const line of command.split('\n')) {
    if (pending.length > 0) {
      if (line.trim() === pending[0]) pending.shift()
      continue
    }
    out.push(line)
    for (const m of line.matchAll(/(?<!<)<<-?\s*(['"]?)([A-Za-z_][\w.-]*)\1/g)) pending.push(m[2]!)
  }
  return out.join('\n')
}

/** The command split into simple commands, quotes and comments removed. */
export function simpleCommands(command: string): string[][] {
  const text = stripHeredocs(command)
    .replace(/'[^']*'|"(?:[^"\\]|\\.)*"/g, ' Q ')
    .replace(/(^|\s)#[^\n]*/g, '$1')
  return text
    .split(/&&|\|\||\$\(|[;&|\n(){}`]/)
    .map(s => s.trim().split(/\s+/).filter(Boolean))
    .filter(t => t.length > 0)
}

const basenameOf = (word: string): string => word.slice(word.lastIndexOf('/') + 1)

/** Skips flags (and a flag's value) from `i`; returns the first index past them. */
function skipFlags(tokens: string[], i: number): number {
  while (i < tokens.length) {
    const t = tokens[i]!
    if (ASSIGNMENT.test(t)) {
      i += 1
    } else if (t.startsWith('-')) {
      i += !t.includes('=') && VALUE_FLAGS.has(t) ? 2 : 1
    } else {
      break
    }
  }
  return i
}

/** The test runner one simple command starts, or null. */
export function runnerOf(tokens: string[]): string | null {
  let i = skipFlags(tokens, 0) // leading VAR=value assignments
  for (;;) {
    const head = tokens[i]
    if (head === undefined) return null
    const name = basenameOf(head)
    if (!(name in RUN_WRAPPERS)) break
    const sub = RUN_WRAPPERS[name]
    if (sub) {
      if (tokens[i + 1] !== sub) return null // `uv add pytest`, `poetry install`
      i += 2
    } else {
      i += 1
    }
    i = skipFlags(tokens, i)
    if (name === 'timeout' && /^\d+(\.\d+)?[smhd]?$/.test(tokens[i] ?? '')) i += 1
  }

  const head = basenameOf(tokens[i]!)
  const rest = tokens.slice(i + 1)
  const firstArg = rest[skipFlags(rest, 0)]

  if (head === 'pytest' || head === 'py.test') return 'pytest'
  if (/^python[0-9.]*$/.test(head)) {
    for (let j = 0; j < rest.length; j++) {
      const t = rest[j]!
      if (t === '-m') return rest[j + 1] === 'pytest' || rest[j + 1] === 'py.test' ? 'pytest' : null
      if (!t.startsWith('-')) return null // a script: `python manage.py test` is not detected
    }
    return null
  }
  if (head === 'vitest' || head === 'jest') return head
  if (head === 'make' || head === 'gmake') {
    for (let j = skipFlags(rest, 0); j < rest.length; j = skipFlags(rest, j + 1)) {
      if (/^tests?([-_:][\w:-]*)?$/.test(rest[j]!)) return 'make test'
    }
    return null
  }
  if (head === 'npm' || head === 'pnpm' || head === 'yarn' || head === 'bun') {
    if (firstArg === 'test' || firstArg === 't') return `${head} test`
    if (firstArg === 'run' || firstArg === 'run-script') {
      const script = rest[skipFlags(rest, rest.indexOf(firstArg) + 1)]
      return script !== undefined && /^test([:_-][\w:-]*)?$/.test(script) ? `${head} test` : null
    }
    if ((firstArg === 'exec' || firstArg === 'dlx' || firstArg === 'x') && head !== 'npm') {
      const tool = rest[skipFlags(rest, rest.indexOf(firstArg) + 1)]
      return tool === 'vitest' || tool === 'jest' ? tool : null
    }
    if (head !== 'npm' && (firstArg === 'vitest' || firstArg === 'jest')) return firstArg
    return null
  }
  if (head === 'go' && firstArg === 'test') return 'go test'
  if (head === 'cargo' && (firstArg === 'test' || firstArg === 'nextest')) return 'cargo test'
  return null
}

/**
 * The test runner a Bash command starts, matched at command position only:
 * a runner named inside quotes, a heredoc, a comment or as an argument
 * (`grep pytest`, `echo "make test"`) does not count.
 */
export function detectRunner(command: string): string | null {
  for (const tokens of simpleCommands(command)) {
    const runner = runnerOf(tokens)
    if (runner) return runner
  }
  return null
}

// ---------------------------------------------------------------------------
// Parsing what the runner reports
// ---------------------------------------------------------------------------

/** One progress-file line: `runner \t done \t total \t failed \t started_epoch`. */
export function parseProgress(text: string): TestProgress | null {
  const fields = text.split('\n')[0]!.trim().split('\t')
  if (fields.length < 5 || !fields[0]) return null
  const [done, total, failed, startedEpoch] = fields.slice(1, 5).map(Number) as [number, number, number, number]
  if (![done, total, failed, startedEpoch].every(n => Number.isFinite(n) && n >= 0)) return null
  return { runner: fields[0], done, total, failed, startedEpoch }
}

export type Counts = { passed: number | null; failed: number | null; errors: number | null }

/** Counts from pytest's final summary line (`3 failed, 977 passed in 130.1s`). */
export function parsePytestSummary(text: string): Counts | null {
  const lines = text.split('\n')
  for (let k = lines.length - 1; k >= 0; k--) {
    const line = lines[k]!
    if (!/\bin \d+(\.\d+)?s\b/.test(line)) continue
    if (!/\b\d+ (passed|failed|errors?|skipped|deselected|xfailed|xpassed)\b|no tests ran/.test(line)) continue
    const count = (re: RegExp): number => {
      const m = line.match(re)
      return m ? Number(m[1]) : 0
    }
    return {
      passed: count(/(\d+) passed/),
      failed: count(/(\d+) failed/),
      errors: count(/(\d+) errors?\b/),
    }
  }
  return null
}

/** The exit code Bash reports in an errored result's text (`Exit code 2`). */
export function parseExitCode(text: string | undefined): number | null {
  const m = text?.match(/^Exit code (\d+)/m)
  return m ? Number(m[1]) : null
}

// ---------------------------------------------------------------------------
// The band's text
// ---------------------------------------------------------------------------

export type Segment = { text: string; color?: 'red' }

const pad2 = (n: number): string => String(n).padStart(2, '0')

export function formatDuration(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000))
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.floor(s / 60)}m${pad2(s % 60)}s`
  return `${Math.floor(s / 3600)}h${pad2(Math.floor((s % 3600) / 60))}m`
}

export function progressBar(done: number, total: number, width = 10): string {
  const filled = total > 0 ? Math.min(width, Math.floor((done / total) * width)) : 0
  return '█'.repeat(filled) + '░'.repeat(width - filled)
}

export const joinSegments = (segments: Segment[]): string => segments.map(s => s.text).join('')

/** The newest running run, or null. */
export function latestRun(band: TestBand): TestRun | null {
  let latest: TestRun | null = null
  for (const run of Object.values(band.running)) if (!latest || run.startedAt >= latest.startedAt) latest = run
  return latest
}

export function runningSegments(run: TestRun, now: number): Segment[] {
  const elapsed = formatDuration(now - run.startedAt)
  const p = run.progress
  if (!p) return [{ text: `🧪 ${run.runner} · running ${elapsed}` }]
  const out: Segment[] = [{ text: `🧪 ${p.runner} ${progressBar(p.done, p.total)} ${p.done}/${p.total}` }]
  if (p.failed > 0) out.push({ text: ' · ' }, { text: `${p.failed} failed`, color: 'red' })
  out.push({ text: ` · ${elapsed}` })
  return out
}

export function summarySegments(s: TestSummary): Segment[] {
  const took = formatDuration(s.durationMs)
  if (s.outcome === 'background') return [{ text: `🧪 ${s.runner} · started in background` }]
  if (s.outcome === 'backgrounded') return [{ text: `🧪 ${s.runner} · moved to background after ${took}` }]
  const verb = s.outcome === 'interrupted' ? 'interrupted' : 'done'
  if (s.passed === null) {
    const code = s.exitCode === null ? '' : ` · exit code ${s.exitCode}`
    return [{ text: `🧪 ${s.runner} ${verb}${code} · ${took}` }]
  }
  const out: Segment[] = [{ text: `🧪 ${s.runner} ${verb} · ${s.passed} passed` }]
  if ((s.failed ?? 0) > 0) out.push({ text: ' · ' }, { text: `${s.failed} failed`, color: 'red' })
  if ((s.errors ?? 0) > 0) out.push({ text: ' · ' }, { text: `${s.errors} errors`, color: 'red' })
  out.push({ text: ` · ${took}` })
  return out
}

/**
 * A progress file belongs to this run only if the runner started it after
 * the command did (minus slack): a file a killed run left behind is ignored.
 */
export function isCurrent(p: TestProgress, runStartedAt: number, slackMs = 5_000): boolean {
  return p.startedEpoch * 1000 >= runStartedAt - slackMs
}
