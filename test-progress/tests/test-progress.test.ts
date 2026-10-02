import { describe, expect, mock, test } from 'claude-code/testing'
import type { TestBody } from 'claude-code/testing'
import type { On, RenderElement } from 'claude-code'

import {
  detectRunner,
  formatDuration,
  joinSegments,
  parseExitCode,
  parseProgress,
  parsePytestSummary,
  progressBar,
  runningSegments,
  summarySegments,
} from '../hooks/lib'

const SID = 'sess-1'
const NOW = 1_700_000_000_000
const DIR = '/tmp/claude-1000/test-progress'
const FILE = `${DIR}/${SID}.progress`

describe('detectRunner', () => {
  test('matches test commands at command position', async () => {
    const positives: Array<[string, string]> = [
      ['pytest', 'pytest'],
      ['pytest -x tests/unit', 'pytest'],
      ['py.test -q', 'pytest'],
      ['.venv/bin/pytest tests/', 'pytest'],
      ['python -m pytest -k slow', 'pytest'],
      ['python3.12 -m pytest', 'pytest'],
      ['uv run pytest -x', 'pytest'],
      ['uv run --with pytest-xdist pytest -n 4', 'pytest'],
      ['uv run python -m pytest', 'pytest'],
      ['poetry run pytest', 'pytest'],
      ['cd backend && uv run pytest', 'pytest'],
      ['PYTHONPATH=. DJANGO_SETTINGS_MODULE=x.settings pytest', 'pytest'],
      ['timeout 600 python -m pytest', 'pytest'],
      ['time pytest 2>&1 | tail -20', 'pytest'],
      ['source .venv/bin/activate; pytest', 'pytest'],
      ['make test', 'make test'],
      ['make -C backend test-unit', 'make test'],
      ['npm test', 'npm test'],
      ['npm run test:unit', 'npm test'],
      ['(cd web && pnpm test)', 'pnpm test'],
      ['pnpm vitest run', 'vitest'],
      ['npx vitest run src/', 'vitest'],
      ['npx jest --ci', 'jest'],
      ['vitest', 'vitest'],
      ['jest', 'jest'],
      ['go test ./...', 'go test'],
      ['cargo test --workspace', 'cargo test'],
      ['git stash list\npytest tests/', 'pytest'],
    ]
    for (const [cmd, runner] of positives) expect([cmd, detectRunner(cmd)]).toEqual([cmd, runner])
  })

  test('ignores runners named as arguments, in quotes, heredocs or comments', async () => {
    const negatives = [
      'grep -rn pytest .',
      'rg "go test" docs/',
      'echo "run pytest next"',
      "echo 'make test'",
      'git commit -m "make test passes"',
      'cat <<EOF > notes.md\npytest\nmake test\nEOF',
      "cat > x.sh <<'END'\nnpm test\nEND\nls",
      'pip install pytest',
      'uv add --dev pytest',
      'poetry install',
      'which pytest',
      'man jest',
      'python -m pip install pytest',
      'python manage.py test',
      'make build',
      'make -C tests build',
      'npm install',
      'npm run build',
      'go build ./...',
      'cargo build',
      'ls tests/  # then pytest',
      'vim jest.config.js',
      'pytest-watch',
      'bash -c "pytest -x"',
    ]
    for (const cmd of negatives) expect([cmd, detectRunner(cmd)]).toEqual([cmd, null])
  })
})

describe('lib', () => {
  test('parses the progress file and the pytest summary', async () => {
    expect(parseProgress('pytest\t412\t980\t3\t1700000000\n')).toEqual({
      runner: 'pytest',
      done: 412,
      total: 980,
      failed: 3,
      startedEpoch: 1_700_000_000,
    })
    expect(parseProgress('pytest\t1\t2\n')).toBe(null)
    expect(parseProgress('pytest\tx\t2\t0\t1\n')).toBe(null)
    expect(parseProgress('')).toBe(null)

    const out = 'tests/a.py ....F\n===== 3 failed, 977 passed, 2 skipped in 130.12s (0:02:10) =====\n'
    expect(parsePytestSummary(out)).toEqual({ passed: 977, failed: 3, errors: 0 })
    expect(parsePytestSummary('1 passed, 1 error in 0.10s')).toEqual({ passed: 1, failed: 0, errors: 1 })
    expect(parsePytestSummary('ok  pkg/foo 0.2s')).toBe(null)

    expect(parseExitCode('Exit code 2\nboom')).toBe(2)
    expect(parseExitCode('boom')).toBe(null)
    expect(formatDuration(42_900)).toBe('42s')
    expect(formatDuration(70_000)).toBe('1m10s')
    expect(formatDuration(3_725_000)).toBe('1h02m')
    expect(progressBar(412, 980)).toBe('████░░░░░░')
    expect(progressBar(0, 0)).toBe('░░░░░░░░░░')
  })

  test('band text', async () => {
    const run = { runner: 'pytest', startedAt: 0, progress: null }
    expect(joinSegments(runningSegments(run, 70_000))).toBe('🧪 pytest · running 1m10s')
    const progress = { runner: 'pytest', done: 700, total: 1000, failed: 3, startedEpoch: 0 }
    const busy = runningSegments({ ...run, progress }, 70_000)
    expect(joinSegments(busy)).toBe('🧪 pytest ███████░░░ 700/1000 · 3 failed · 1m10s')
    expect(busy.find(s => s.text === '3 failed')?.color).toBe('red')
    expect(joinSegments(runningSegments({ ...run, progress: { ...progress, failed: 0 } }, 1_000))).toBe(
      '🧪 pytest ███████░░░ 700/1000 · 1s',
    )

    const base = { runner: 'pytest', outcome: 'done' as const, exitCode: 1, durationMs: 130_000, errors: 0 }
    expect(joinSegments(summarySegments({ ...base, passed: 977, failed: 3 }))).toBe(
      '🧪 pytest done · 977 passed · 3 failed · 2m10s',
    )
    expect(joinSegments(summarySegments({ ...base, runner: 'go test', passed: null, failed: null, errors: null }))).toBe(
      '🧪 go test done · exit code 1 · 2m10s',
    )
    expect(
      joinSegments(summarySegments({ ...base, outcome: 'background', passed: null, failed: null, errors: null })),
    ).toBe('🧪 pytest · started in background')
  })
})

type World = { files: Map<string, string>; clock: ReturnType<typeof mock.clock> }

// The engine beneath the plugin: a session id, a /tmp holding claude-1000,
// an in-memory fs, a clock.
const world = (on: On): World => {
  const files = new Map<string, string>()
  const clock = mock.clock(on, { now: NOW })
  mock.env(on, {})
  on('session.id', () => ({ value: SID }))
  on('fs.list', ($, e) => ({
    value: e.path === '/tmp' ? [{ name: 'claude-1000', kind: 'dir' as const, size: 0, mtimeMs: 0, isLink: false }] : [],
  }))
  on('fs.exists', ($, e) => ({ value: files.has(e.path) }))
  on('fs.read', ($, e) => {
    const text = files.get(e.path)
    if (text === undefined) throw new Error('ENOENT')
    return { value: text }
  })
  on('ui.render', { component: 'AbovePrompt' }, ($, e) => {
    const { Box } = $.ui.resolve(e)
    return h(Box, { key: 'engine' }) as RenderElement
  })
  return { files, clock }
}

const PROPS = {
  hasSurvey: false,
  isWorking: true,
  maxRows: 10,
  bodyColumns: 100,
  scroll: { offset: 0, bodyRows: 9 },
  view: {},
}

const bandText = async ($: Parameters<TestBody>[0]): Promise<string | undefined> => {
  const ui = await $.ui.mount({ plugin: 'test-progress', surface: 'terminal', component: 'AbovePrompt', props: PROPS })
  const row = await ui.find({ key: 'test-progress-line' })
  const engine = await ui.find({ key: 'engine' })
  await ui.unmount()
  expect(engine).toBeDefined() // the band sits above the engine's, never instead
  return row?.text
}

describe('band', () => {
  test('running, with progress, then a summary until the next prompt', async ($, on) => {
    const w = world(on)
    on('prompt.submit', ($, e) => ({ text: e.text }))
    let release: () => void = () => {}
    const held = new Promise<void>(r => {
      release = r
    })
    let reached: () => void = () => {}
    const isReached = new Promise<void>(r => {
      reached = r
    })
    on('tool.call', { tool: 'Bash' }, async () => {
      reached()
      await held
      return {
        result: {
          stdout: '===== 3 failed, 977 passed in 130.00s =====',
          stderr: '',
          interrupted: false,
        },
      }
    })

    expect(await bandText($)).toBe(undefined)

    const call = $.tool.call({ tool: 'Bash', command: 'uv run pytest -q', description: 'Run tests' })
    await isReached
    expect(await bandText($)).toBe('🧪 pytest · running 0s')

    w.files.set(FILE, `pytest\t412\t980\t3\t${NOW / 1000}\n`)
    await w.clock.advance(70_000)
    expect(await bandText($)).toBe('🧪 pytest ████░░░░░░ 412/980 · 3 failed · 1m10s')

    w.files.delete(FILE)
    await w.clock.advance(60_000)
    release()
    await call
    expect(await bandText($)).toBe('🧪 pytest done · 977 passed · 3 failed · 2m10s')

    await $.prompt.submit({ text: 'next', wait: false, origin: { kind: 'composer' } })
    expect(await bandText($)).toBe(undefined)
  })

  test('a stale progress file is ignored, and the exit code shows without counts', async ($, on) => {
    const w = world(on)
    w.files.set(FILE, `pytest\t5\t9\t0\t${NOW / 1000 - 3600}\n`)
    on('tool.call', { tool: 'Bash' }, async () => {
      await w.clock.sleep(5_000)
      return { isError: true as const, result: 'Exit code 1', text: 'Exit code 1\nFAIL' }
    })
    const call = $.tool.call({ tool: 'Bash', command: 'go test ./...', description: 'Run tests' })
    await w.clock.advance(5_000)
    await call
    expect(await bandText($)).toBe('🧪 go test done · exit code 1 · 5s')
  })

  test('a background run is noted, and Dismiss clears it', async ($, on) => {
    world(on)
    on('tool.call', { tool: 'Bash' }, () => ({
      result: { stdout: '', stderr: '', interrupted: false, backgroundTaskId: 'b1' },
    }))
    await $.tool.call({ tool: 'Bash', command: 'pytest', description: 'Run tests', run_in_background: true })
    const ui = await $.ui.mount({ plugin: 'test-progress', surface: 'terminal', component: 'AbovePrompt', props: PROPS })
    expect((await ui.find({ key: 'test-progress-line' }))?.text).toBe('🧪 pytest · started in background')
    expect(await ui.find({ key: 'dismiss' })).toBeDefined()
    await ui.press({ key: 'dismiss' })
    await ui.unmount()
    expect(await bandText($)).toBe(undefined)
  })

  test('other Bash commands are left alone', async ($, on) => {
    world(on)
    on('tool.call', { tool: 'Bash' }, () => ({ result: { stdout: 'pytest', stderr: '', interrupted: false } }))
    await $.tool.call({ tool: 'Bash', command: 'grep -rn pytest .', description: 'Search' })
    expect(await bandText($)).toBe(undefined)
  })
})
