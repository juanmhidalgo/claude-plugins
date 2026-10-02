import { describe, expect, mock, test } from 'claude-code/testing'
import type { On } from 'claude-code'

import { bandLine, basename, dataDirFor, pluginOf, versionFrom } from '../hooks/lib'
import { EMPTY_RUN } from '../hooks/lib'

const SID = 'sess-1'
const CWD = '/work/secret-client/my-project'
const SECRET = 'TOP-SECRET-PROMPT-TEXT'

type World = {
  files: Map<string, string>
  toasts: string[]
  clock: ReturnType<typeof mock.clock>
}

// The engine beneath the plugin: an in-memory fs, a fixed session, a clock.
const world = (on: On): World => {
  const files = new Map<string, string>()
  const toasts: string[] = []
  const clock = mock.clock(on, { now: 1_000_000 })
  mock.env(on, { HOME: '/home/u' })
  on('session.id', () => ({ value: SID }))
  on('session.cwd', () => ({ value: CWD }))
  on('fs.exists', ($, e) => ({ value: files.has(e.path) }))
  on('fs.read', ($, e) => {
    const text = files.get(e.path)
    if (text === undefined) throw new Error('ENOENT')
    return { value: text }
  })
  on('fs.write', ($, e) => {
    files.set(e.path, e.text)
    return { value: undefined }
  })
  on('ui.toast', ($, e) => {
    toasts.push(e.text)
    return { value: undefined }
  })
  return { files, toasts, clock }
}

const lines = (w: World): Array<{ [k: string]: unknown }> => {
  const all = [...w.files.entries()].filter(([p]) => p.includes('/sessions/'))
  return all.flatMap(([, t]) => t.trim().split('\n').filter(Boolean).map(l => JSON.parse(l)))
}

describe('lib', () => {
  test('pure helpers', async () => {
    expect(basename('/a/b/my-proj')).toBe('my-proj')
    expect(basename('C:\\x\\y\\')).toBe('y')
    expect(pluginOf('feature-dev:tdd-runner')).toBe('feature-dev')
    expect(pluginOf('Explore')).toBe(null)
    expect(dataDirFor('/h/.claude', 'plugin-recorder', '/h/.claude/plugins/cache/my-mkt/plugin-recorder/0.1.0')).toBe(
      '/h/.claude/plugins/data/plugin-recorder-my-mkt',
    )
    expect(dataDirFor('/h/.claude/', 'plugin-recorder', '/src/plugin-recorder')).toBe(
      '/h/.claude/plugins/data/plugin-recorder-inline',
    )
    const json = JSON.stringify({
      plugins: {
        'feature-dev@m': [
          { scope: 'project', projectPath: '/other', version: '1.0.0' },
          { scope: 'user', version: '1.30.1' },
        ],
      },
    })
    expect(versionFrom(json, 'feature-dev', '/x')).toBe('1.30.1')
    expect(versionFrom(json, 'feature-dev', '/other')).toBe('1.0.0')
    expect(versionFrom('not json', 'feature-dev', '/x')).toBe(null)
  })

  test('band line is quiet with nothing running', async () => {
    expect(bandLine(EMPTY_RUN, 0)).toBe(null)
    const line = bandLine(
      {
        ...EMPTY_RUN,
        label: 'feature-dev:tdd',
        turnStartedAt: 0,
        done: 12,
        running: { a: { type: 'feature-dev:tdd-runner', startedAt: 34 * 60_000 } },
      },
      38 * 60_000,
    )
    expect(line).toBe('tdd · 12 subagents done · tdd-runner running 4m · turn 38m')
  })
})

describe('recording', () => {
  test('an Agent call is recorded with metadata only, and a failure toasts', async ($, on) => {
    const w = world(on)
    on('tool.call', { tool: 'Agent' }, () => ({ result: 'boom', isError: true as const, text: SECRET }))

    await $.tool.call({ tool: 'Agent', subagent_type: 'feature-dev:backend-explorer', prompt: SECRET, description: SECRET })

    const recs = lines(w)
    expect(recs).toHaveLength(1)
    expect(recs[0]).toMatchObject({
      v: 1,
      sid: SID,
      ev: 'agent',
      subagent_type: 'feature-dev:backend-explorer',
      plugin: 'feature-dev',
      status: 'error',
    })
    const path = [...w.files.keys()][0]!
    expect(path).toBe(`/home/u/.claude/plugins/data/plugin-recorder-inline/sessions/${SID}.jsonl`)
    const raw = [...w.files.values()].join('')
    expect(raw.includes(SECRET)).toBe(false)
    expect(raw.includes('/work/')).toBe(false)
    expect(w.toasts).toEqual(['Subagent feature-dev:backend-explorer failed'])
  })

  test('a successful sync call does not toast and appends, never overwrites', async ($, on) => {
    const w = world(on)
    on('tool.call', { tool: 'Agent' }, () => ({ result: { status: 'completed', agentId: 'ag1', totalToolUseCount: 3 } }))

    await $.tool.call({ tool: 'Agent', subagent_type: 'Explore', prompt: 'p', description: 'd' })
    w.clock.advance(5_000)
    await $.tool.call({ tool: 'Agent', subagent_type: 'Explore', prompt: 'p', description: 'd' })

    const recs = lines(w)
    expect(recs).toHaveLength(2)
    expect(recs[1]).toMatchObject({ ev: 'agent', status: 'completed', plugin: null, toolUses: 3, agentId: 'ag1' })
    expect(w.toasts).toEqual([])
  })

  test('a typed plugin skill is recorded once, with its project as a basename', async ($, on) => {
    const w = world(on)
    on('session.start', ($, e) => ({ cwd: e.cwd }))
    on('command.run', () => ({ text: '' }))
    on('skill.prompt', ($, e) => ({ text: e.text }))

    await $.session.start({ cwd: CWD, surface: null, isInteractive: false })
    await $.command.run({
      command: 'feature-dev:tdd',
      args: SECRET,
      origin: { kind: 'composer' },
      presentation: { isFullscreen: false, columns: 120 },
    })
    await $.skill.prompt({ skill: 'feature-dev:tdd', text: SECRET })
    await $.skill.prompt({ skill: 'my-private-skill', text: SECRET })

    const recs = lines(w)
    expect(recs.map(r => r.ev)).toEqual(['session.start', 'invoke'])
    expect(recs[0]).toMatchObject({ project: 'my-project', interactive: false })
    expect(recs[1]).toMatchObject({ kind: 'command', plugin: 'feature-dev', name: 'feature-dev:tdd' })
    expect([...w.files.values()].join('').includes(SECRET)).toBe(false)
  })
})

describe('band', () => {
  test('quiet when idle, shows a running subagent', async ($, on) => {
    world(on)
    const props = {
      hasSurvey: false,
      isWorking: true,
      maxRows: 10,
      bodyColumns: 100,
      scroll: { offset: 0, bodyRows: 9 },
      view: {},
    }

    const idle = await $.ui.mount({ plugin: 'plugin-recorder', surface: 'terminal', component: 'AbovePrompt', props })
    expect(await idle.find({ key: 'band' })).toBe(undefined)
    await idle.unmount()

    // Hold an Agent call open so it counts as running while we draw.
    let release: () => void = () => {}
    const held = new Promise<void>(r => {
      release = r
    })
    on('tool.call', { tool: 'Agent' }, async () => {
      await held
      return { result: { status: 'completed', agentId: 'ag2' } }
    })
    const call = $.tool.call({ tool: 'Agent', subagent_type: 'feature-dev:tdd-runner', prompt: 'p', description: 'd' })
    // Let the hook's pre-call state write land before drawing.
    for (let i = 0; i < 20; i++) await Promise.resolve()

    const busy = await $.ui.mount({ plugin: 'plugin-recorder', surface: 'terminal', component: 'AbovePrompt', props })
    expect((await busy.find({ key: 'band' }))?.text).toMatch(/tdd-runner running/)
    await busy.unmount()

    release()
    await call
  })
})
