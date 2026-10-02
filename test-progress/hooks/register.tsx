// test-progress: a band above the prompt while a Bash test command runs, and
// a one-row summary after it ends, until the next prompt.
//
// Reads one file only: the progress file a test runner plugin writes at
// <tmp>/claude-<uid>/test-progress/<session-id>.progress. Writes nothing:
// every value lives in $.state for this session.

import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { TestBand, TestProgress, TestSummary } from '../types'
import {
  EMPTY_BAND,
  detectRunner,
  isCurrent,
  latestRun,
  parseExitCode,
  parseProgress,
  parsePytestSummary,
  runningSegments,
  summarySegments,
} from './lib'

const BAND = atom({ plugin: 'test-progress', key: 'band' } as const, EMPTY_BAND)

const TICK_MS = 1_000
const CLAUDE_DIR = /^claude-\d+$/

// The test-progress directories found so far. A mod cannot ask for the uid,
// so the `claude-<uid>` directory is found by listing the tmp roots.
let progressDirs: string[] = []

async function tmpRoots($: EngineInterface): Promise<string[]> {
  const fromEnv = ((await $.env.get('TMPDIR')) ?? '').replace(/\/+$/, '')
  return [...new Set([fromEnv, '/tmp'].filter(Boolean))]
}

async function findProgressDirs($: EngineInterface): Promise<string[]> {
  const dirs: string[] = []
  for (const root of await tmpRoots($)) {
    const entries = await $.fs.list(root).catch(() => [])
    for (const entry of entries) {
      if (entry.kind === 'dir' && CLAUDE_DIR.test(entry.name)) dirs.push(`${root}/${entry.name}/test-progress`)
    }
  }
  return dirs
}

/** The session's progress file, parsed, or null when there is none. */
async function readProgress($: EngineInterface): Promise<TestProgress | null> {
  const sid = await $.session.id()
  if (progressDirs.length === 0) progressDirs = await findProgressDirs($)
  for (const dir of progressDirs) {
    const path = `${dir}/${sid}.progress`
    try {
      if (!(await $.fs.exists(path))) continue
      const text = await $.fs.read(path)
      const parsed = typeof text === 'string' ? parseProgress(text) : null
      if (parsed) return parsed
    } catch {
      // Removed between exists and read: the run just ended.
    }
  }
  return null
}

async function tick($: EngineInterface): Promise<void> {
  try {
    const progress = await readProgress($)
    if (progress) {
      await update($, BAND, b => {
        const running = { ...b.running }
        for (const [id, run] of Object.entries(running)) {
          if (isCurrent(progress, run.startedAt)) running[id] = { ...run, progress }
        }
        return { ...b, running }
      })
    }
    $.ui.invalidate('ui.render')
  } catch {
    // A failed poll only costs one frame of the band.
  }
}

type BashResult = { stdout?: string; interrupted?: boolean; backgroundTaskId?: string }

export const register: Register = on => {
  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    if (e.tool !== 'Bash') return next(e)
    const runner = detectRunner(e.command)
    if (!runner) return next(e)

    // A background run returns at once; its progress is not polled.
    if (e.run_in_background) {
      const res = await next(e)
      if (res.deny === undefined) {
        const summary: TestSummary = {
          runner,
          outcome: 'background',
          exitCode: null,
          durationMs: 0,
          passed: null,
          failed: null,
          errors: null,
        }
        await update($, BAND, b => ({ ...b, summary })).catch(() => {})
      }
      return res
    }

    const id = e.tool_use_id ?? `call-${Math.random().toString(36).slice(2)}`
    const startedAt = await $.clock.now()
    await update($, BAND, b => ({ ...b, running: { ...b.running, [id]: { runner, startedAt, progress: null } } }))
    const timer = $.clock.every(TICK_MS, () => void tick($))

    let res: Awaited<ReturnType<typeof next>> | undefined
    let threw: unknown = undefined
    try {
      res = await next(e)
    } catch (err) {
      threw = err
    } finally {
      timer.cancel()
    }

    try {
      const now = await $.clock.now()
      const last = (await read($, BAND)).running[id]?.progress ?? null
      let summary: TestSummary | null = null
      if (res?.deny === undefined) {
        const result = (res?.isError ? {} : (res?.result ?? {})) as BashResult
        const text = res?.text ?? result.stdout ?? ''
        const outcome: TestSummary['outcome'] =
          threw !== undefined || result.interrupted ? 'interrupted'
          : result.backgroundTaskId ? 'backgrounded'
          : 'done'
        const fromOutput = parsePytestSummary(text)
        const counts =
          fromOutput ??
          (last && outcome !== 'backgrounded' ? { passed: Math.max(0, last.done - last.failed), failed: last.failed, errors: 0 } : null)
        summary = {
          runner: last?.runner ?? runner,
          outcome,
          exitCode: res?.isError ? parseExitCode(res.text) : res ? 0 : null,
          durationMs: now - startedAt,
          passed: outcome === 'backgrounded' ? null : (counts?.passed ?? null),
          failed: counts?.failed ?? null,
          errors: counts?.errors ?? null,
        }
      }
      await update($, BAND, b => {
        const running = { ...b.running }
        delete running[id]
        return { running, summary: summary ?? b.summary }
      })
    } catch {
      // The band must never cost the tool call its result.
    }

    if (threw !== undefined) throw threw
    return res!
  })

  on('prompt.submit', async ($, e, next) => {
    await update($, BAND, b => (b.summary ? { ...b, summary: null } : b)).catch(() => {})
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const band: TestBand = await read($, BAND)
    const run = latestRun(band)
    const segments = run ? runningSegments(run, await $.clock.now()) : band.summary ? summarySegments(band.summary) : null
    if (!segments) return next(e)

    // Draw above whatever the plugins beneath and the engine draw, never instead.
    const below = await next(e)
    const { Box, Text, Button } = $.ui.resolve(e)
    return (
      <Box flexDirection="column">
        <Box key="test-progress">
          <Box key="test-progress-line">
            {segments.map((s, i) => (
              <Text key={`seg-${i}`} color={s.color} dimColor={s.color ? undefined : true} wrap="truncate">
                {s.text}
              </Text>
            ))}
          </Box>
          {run ? null : (
            <Text key="sep"> </Text>
          )}
          {run ? null : (
            <Button key="dismiss" role="dismiss" dimColor onPress={() => update($, BAND, b => ({ ...b, summary: null }))}>
              Dismiss
            </Button>
          )}
        </Box>
        {below}
      </Box>
    )
  })
}
