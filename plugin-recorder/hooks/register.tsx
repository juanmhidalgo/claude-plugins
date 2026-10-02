// plugin-recorder: metadata-only log of plugin runs, a subagent progress band,
// and an immediate toast when a subagent call fails.
//
// Privacy rule for every record below: names, counts, durations and statuses
// only. Never prompt text, tool inputs other than subagent_type, results,
// file contents, or a full path (the project is its basename).

import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { RecorderRun } from '../types'
import {
  EMPTY_RUN,
  SCHEMA_VERSION,
  bandLine,
  basename,
  dataDirFor,
  pluginOf,
  versionFrom,
} from './lib'

const RUN = atom({ plugin: 'plugin-recorder', key: 'run' } as const, EMPTY_RUN)

// A label is attributed to the turn that starts right after it was invoked.
const LABEL_CARRY_MS = 10_000
// command.run and skill.prompt both fire for a typed /plugin:skill.
const DEDUPE_MS = 5_000
const TICK_MS = 15_000
const TOAST_MS = 15_000

type Record = { [k: string]: unknown }

// Module state is rebuilt on hot reload; the file is re-read before the
// first append, so nothing already written is lost.
const buffers = new Map<string, string>()
let queue: Promise<void> = Promise.resolve()
let dataDir: Promise<string> | null = null
let installed: Promise<string> | null = null
let lastInvoke: { name: string; at: number } | null = null

async function configDir($: EngineInterface): Promise<string> {
  const explicit = await $.env.get('CLAUDE_CONFIG_DIR')
  if (explicit) return explicit
  const home = (await $.env.get('HOME')) ?? (await $.env.get('USERPROFILE')) ?? ''
  return `${home}/.claude`
}

function resolveDataDir($: EngineInterface): Promise<string> {
  const name = $.plugin.name
  const root = $.plugin.root
  dataDir ??= configDir($).then(c => dataDirFor(c, name, root))
  return dataDir
}

async function pluginVersion($: EngineInterface, plugin: string): Promise<string | null> {
  installed ??= configDir($)
    .then(c => $.fs.read(`${c}/plugins/installed_plugins.json`))
    .then(t => (typeof t === 'string' ? t : ''))
    .catch(() => '')
  try {
    return versionFrom(await installed, plugin, await $.session.cwd())
  } catch {
    return null
  }
}

// One file per session, one writer per process: appends are serialized
// through `queue`, so concurrent hooks never interleave a read-modify-write.
function record($: EngineInterface, fields: Record): Promise<void> {
  const job = async () => {
    const sid = await $.session.id()
    const now = await $.clock.now()
    const dir = await resolveDataDir($)
    let path = `${dir}/sessions/${sid}.jsonl`
    let text = buffers.get(path)
    if (text === undefined) {
      text = ''
      if (await $.fs.exists(path)) {
        try {
          const prev = await $.fs.read(path)
          text = typeof prev === 'string' ? prev : ''
        } catch {
          // Unreadable (over the 4 MiB read cap): start a second file rather
          // than overwrite the first. Retro reads every *.jsonl.
          path = `${dir}/sessions/${sid}.${now}.jsonl`
        }
      }
    }
    const line = JSON.stringify({ v: SCHEMA_VERSION, ts: new Date(now).toISOString(), sid, ...fields })
    text += `${line}\n`
    buffers.set(path, text)
    await $.fs.write(path, text)
  }
  queue = queue.then(job).catch(err => {
    $.ui.log(`plugin-recorder: write failed (${String(err).slice(0, 80)})`, { to: 'debug' })
  })
  return queue
}

function toast($: EngineInterface, text: string): void {
  try {
    $.ui.toast(text, { timeoutMs: TOAST_MS })
  } catch {
    // No surface (claude -p): the record is the only trace, by design.
  }
}

async function invoked($: EngineInterface, kind: 'command' | 'skill', name: string): Promise<void> {
  const plugin = pluginOf(name)
  if (!plugin) return
  const now = await $.clock.now()
  if (lastInvoke && lastInvoke.name === name && now - lastInvoke.at < DEDUPE_MS) return
  lastInvoke = { name, at: now }
  await update($, RUN, r => ({ ...r, label: name, labelAt: now }))
  await record($, { ev: 'invoke', kind, plugin, name, version: await pluginVersion($, plugin) })
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const res = await next(e)
    try {
      const sid = await $.session.id()
      const run = await read($, RUN)
      if (run.startedFor !== sid) {
        await update($, RUN, r => ({ ...r, startedFor: sid }))
        const version = (await $.session.version()).version
        await record($, {
          ev: 'session.start',
          project: basename(e.cwd),
          interactive: e.isInteractive,
          cc: version,
        })
      }
      if (e.isInteractive) {
        // Redraw the band while something runs, so its minutes move.
        $.clock.every(TICK_MS, () => {
          void read($, RUN).then(r => {
            if (Object.keys(r.running).length > 0) $.ui.invalidate('ui.render')
          })
        })
      }
    } catch {
      // Recording must never break the session.
    }
    return res
  })

  on('session.end', async ($, e, next) => {
    try {
      await record($, { ev: 'session.end', reason: e.reason })
      await update($, RUN, () => EMPTY_RUN)
    } catch {}
    return next(e)
  })

  on('command.run', async ($, e, next) => {
    try {
      await invoked($, 'command', e.command)
    } catch {}
    return next(e)
  })

  on('skill.prompt', async ($, e, next) => {
    try {
      await invoked($, 'skill', e.skill)
    } catch {}
    return next(e)
  })

  on('turn.start', async ($, e, next) => {
    try {
      const now = await $.clock.now()
      await update($, RUN, r => ({
        ...r,
        label: r.label && now - r.labelAt < LABEL_CARRY_MS ? r.label : null,
        turnStartedAt: now,
        done: 0,
        failed: 0,
      }))
    } catch {}
    return next(e)
  })

  // A spawn the engine refuses never reaches the Agent tool's own result.
  on('agent.spawn', async ($, e, next) => {
    const res = await next(e)
    try {
      if (res.deny !== undefined) {
        await update($, RUN, r => ({ ...r, failed: r.failed + 1 }))
        await record($, { ev: 'agent.spawn', subagent_type: e.subagentType, plugin: pluginOf(e.subagentType), status: 'denied' })
        toast($, `Subagent ${e.subagentType} was refused at spawn`)
      } else if (res.agentId) {
        const id = res.agentId
        await update($, RUN, r => ({ ...r, agentTypes: { ...r.agentTypes, [id]: e.subagentType } }))
      }
    } catch {}
    return res
  })

  on('tool.call', { tool: 'Agent' }, async ($, e, next) => {
    if (e.tool !== 'Agent') return next(e)
    const type = e.subagent_type ?? 'general-purpose'
    const callId = e.tool_use_id ?? `call-${Math.random().toString(36).slice(2)}`
    const startedAt = await $.clock.now()
    const ctx = (await read($, RUN)).label
    await update($, RUN, r => ({ ...r, running: { ...r.running, [callId]: { type, startedAt } } }))

    let res: Awaited<ReturnType<typeof next>> | undefined
    let threw: unknown = undefined
    try {
      res = await next(e)
    } catch (err) {
      threw = err
    }

    try {
      const now = await $.clock.now()
      const result = (res?.result ?? {}) as {
        status?: string
        agentId?: string
        totalDurationMs?: number
        totalToolUseCount?: number
        totalTokens?: number
      }
      const status =
        threw !== undefined ? 'error'
        : res?.deny !== undefined ? 'denied'
        : res?.isError === true ? 'error'
        : (result.status ?? 'completed')
      const isAsync = status === 'async_launched'
      const isFailed = status === 'error' || status === 'denied'

      await update($, RUN, r => {
        const running = { ...r.running }
        const entry = running[callId]
        delete running[callId]
        if (isAsync && result.agentId && entry) running[result.agentId] = entry
        const agentTypes = result.agentId ? { ...r.agentTypes, [result.agentId]: type } : r.agentTypes
        return {
          ...r,
          running,
          agentTypes,
          done: r.done + (isFailed || isAsync ? 0 : 1),
          failed: r.failed + (isFailed ? 1 : 0),
        }
      })

      await record($, {
        ev: 'agent',
        subagent_type: type,
        plugin: pluginOf(type),
        ctx,
        status,
        durationMs: now - startedAt,
        agentId: result.agentId ?? null,
        inSubagent: e.agentId !== undefined,
        toolUses: result.totalToolUseCount ?? null,
        tokens: result.totalTokens ?? null,
      })

      if (isFailed) toast($, `Subagent ${type} ${status === 'denied' ? 'was denied' : 'failed'}`)
    } catch {}

    if (threw !== undefined) throw threw
    return res!
  })

  on('turn.complete', async ($, e, next) => {
    try {
      const run = await read($, RUN)
      const type = e.agentId ? (run.agentTypes[e.agentId] ?? null) : null
      const u = e.usage
      await record($, {
        ev: 'turn',
        agentId: e.agentId ?? null,
        subagent_type: type,
        ctx: run.label,
        reason: e.reason,
        durationMs: e.durationMs,
        model: u?.model ?? null,
        usage: u
          ? {
              in: u.input_tokens,
              out: u.output_tokens,
              cacheRead: u.cache_read_input_tokens ?? 0,
              cacheWrite: u.cache_creation_input_tokens ?? 0,
            }
          : null,
      })

      const agentId = e.agentId
      if (agentId && run.running[agentId]) {
        // A background subagent finished: settle it the way a sync call is.
        const isFailed = e.reason === 'error'
        await update($, RUN, r => {
          const running = { ...r.running }
          delete running[agentId]
          return { ...r, running, done: r.done + (isFailed ? 0 : 1), failed: r.failed + (isFailed ? 1 : 0) }
        })
        if (isFailed) toast($, `Subagent ${type ?? agentId} ended with an error`)
      } else if (!agentId) {
        await update($, RUN, r => ({ ...r, turnStartedAt: null }))
      }
    } catch {}
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const run: RecorderRun = await read($, RUN)
    const line = bandLine(run, await $.clock.now())
    if (line === null) return next(e)
    const { Box, Text } = $.ui.resolve(e)
    return (
      <Box>
        <Text key="band" dimColor wrap="truncate">
          {line}
        </Text>
      </Box>
    )
  })
}
