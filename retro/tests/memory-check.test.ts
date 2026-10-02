import { describe, expect, test } from 'claude-code/testing'
import type { On, ProcessRunResult } from 'claude-code'

import { commandArgs, commandText } from '../hooks/memory-check'

const PRESENTATION = { isFullscreen: false, columns: 120 }

// The engine beneath the plugin: records every process run and answers with `result`.
const world = (on: On, result: ProcessRunResult | Error) => {
  const runs: Array<{ argv: readonly string[]; cwd?: string }> = []
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  on('command.run', () => ({ text: 'core ran it' }))
  on('process.run', ($, e) => {
    runs.push({ argv: e.argv, cwd: e.init?.cwd })
    if (result instanceof Error) throw result
    return { value: result }
  })
  return { runs }
}

const ran = (stdout: string, exitCode = 0, stderr = ''): ProcessRunResult => ({
  exitCode,
  stdout,
  stderr,
  isStdoutTruncated: false,
  isStderrTruncated: false,
})

const memoryCheck = ($: Parameters<Parameters<typeof test>[1]>[0], args = '') =>
  $.command.run({ command: 'memory-check', args, origin: { kind: 'composer' }, presentation: PRESENTATION })

describe('helpers', () => {
  test('arguments split on whitespace', async () => {
    expect(commandArgs('')).toEqual([])
    expect(commandArgs('  --days 7   --json ')).toEqual(['--days', '7', '--json'])
  })

  test('reply text', async () => {
    expect(commandText(ran(''))).toBe('memory-check: no findings.')
    expect(commandText(ran('STALE a.md — verify exited 1: false\n'))).toBe('STALE a.md — verify exited 1: false')
    expect(commandText(ran('', 2, 'memory-check: --days expects a number\n'))).toBe(
      'memory-check failed (exit 2): memory-check: --days expects a number',
    )
  })
})

describe('/memory-check', () => {
  test('runs the script with the typed flags and shows its findings', async ($, on) => {
    const w = world(on, ran('STALE hook-bug.md — verify exited 1: grep -q x hooks/check.sh\n'))
    await $.session.start({ cwd: '/work/project', surface: null, isInteractive: true })

    const reply = await memoryCheck($, '--days 7')

    expect(reply.text).toBe('STALE hook-bug.md — verify exited 1: grep -q x hooks/check.sh')
    expect(w.runs).toHaveLength(1)
    const argv = w.runs[0]!.argv
    expect(argv[0]).toBe('bash')
    expect(argv[1]!.endsWith('/scripts/memory-check.sh')).toBe(true)
    expect(argv.slice(2)).toEqual(['--days', '7'])
  })

  test('says so when there is nothing to report', async ($, on) => {
    world(on, ran(''))
    await $.session.start({ cwd: '/work/project', surface: null, isInteractive: true })

    expect((await memoryCheck($)).text).toBe('memory-check: no findings.')
  })

  test('a usage error shows stderr, and a crash does not throw', async ($, on) => {
    world(on, ran('', 2, 'memory-check: unknown argument: --nope'))
    await $.session.start({ cwd: '/work/project', surface: null, isInteractive: true })
    expect((await memoryCheck($, '--nope')).text).toBe('memory-check failed (exit 2): memory-check: unknown argument: --nope')
  })

  test('a run that cannot start is reported, not thrown', async ($, on) => {
    world(on, new Error('timed out'))
    await $.session.start({ cwd: '/work/project', surface: null, isInteractive: true })
    expect((await memoryCheck($)).text).toContain('memory-check did not finish')
  })

  test('other commands are left alone', async ($, on) => {
    const w = world(on, ran('x'))
    await $.session.start({ cwd: '/work/project', surface: null, isInteractive: true })
    const reply = await $.command.run({ command: 'compact', args: '', origin: { kind: 'composer' }, presentation: PRESENTATION })
    expect(reply.text).toBe('core ran it')
    expect(w.runs).toHaveLength(0)
  })
})
