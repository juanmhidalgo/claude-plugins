// Pure helpers: no `$`, so they are trivially testable and cannot leak data.

import type { RecorderRun } from '../types'

export const SCHEMA_VERSION = 1

export const EMPTY_RUN: RecorderRun = {
  label: null,
  labelAt: 0,
  turnStartedAt: null,
  done: 0,
  failed: 0,
  running: {},
  agentTypes: {},
  startedFor: null,
}

/** Last path segment, either separator. Never the full path. */
export const basename = (path: string): string => {
  const parts = path.split(/[\\/]/).filter(p => p.length > 0)
  return parts[parts.length - 1] ?? ''
}

/** `feature-dev:tdd` -> `feature-dev`; a name with no namespace has no plugin. */
export const pluginOf = (name: string | undefined): string | null => {
  if (!name) return null
  const i = name.indexOf(':')
  return i > 0 ? name.slice(0, i) : null
}

/** `feature-dev:tdd` -> `tdd`. */
export const shortName = (name: string): string => {
  const i = name.lastIndexOf(':')
  return i >= 0 ? name.slice(i + 1) : name
}

/**
 * The data directory Claude Code gives a plugin as ${CLAUDE_PLUGIN_DATA}:
 * `<config>/plugins/data/<name>-<marketplace>`, or `<name>-inline` for a
 * plugin loaded with --plugin-dir. A mod's `$` has no accessor for it, so it
 * is derived from where the plugin was installed (`plugins/cache/<mkt>/<name>/<ver>`).
 */
export const dataDirFor = (configDir: string, name: string, root: string): string => {
  const m = root.replace(/\\/g, '/').match(/\/plugins\/cache\/([^/]+)\/([^/]+)\/[^/]+\/?$/)
  const suffix = m ? m[1] : 'inline'
  const id = `${name}-${suffix}`.replace(/[^A-Za-z0-9_-]/g, '-')
  return `${configDir.replace(/[\\/]+$/, '')}/plugins/data/${id}`
}

type Installed = {
  plugins?: Record<string, Array<{ scope?: string; projectPath?: string; version?: string }>>
}

/**
 * Version of `plugin` from installed_plugins.json: the entry for this project,
 * else the user-scope one, else the first. Only the version string leaves here.
 */
export const versionFrom = (json: string, plugin: string, cwd: string): string | null => {
  let data: Installed
  try {
    data = JSON.parse(json) as Installed
  } catch {
    return null
  }
  for (const [key, entries] of Object.entries(data.plugins ?? {})) {
    if (key.split('@')[0] !== plugin || !Array.isArray(entries)) continue
    const pick =
      entries.find(x => x.projectPath === cwd) ??
      entries.find(x => x.scope === 'user') ??
      entries[0]
    return pick?.version ?? null
  }
  return null
}

const minutes = (ms: number): string => {
  const m = Math.floor(ms / 60_000)
  if (m < 1) return `${Math.max(0, Math.floor(ms / 1000))}s`
  if (m < 60) return `${m}m`
  return `${Math.floor(m / 60)}h${String(m % 60).padStart(2, '0')}m`
}

/**
 * The band's one line, or null when no subagent is running (the band stays
 * quiet). e.g. `tdd · 12 subagents done · tdd-runner running 4m · turn 38m`.
 */
export const bandLine = (run: RecorderRun, now: number): string | null => {
  const running = Object.values(run.running)
  if (running.length === 0) return null
  const oldest = [...running].sort((a, b) => a.startedAt - b.startedAt)[0]!
  const parts: string[] = []
  if (run.label) parts.push(shortName(run.label))
  parts.push(`${run.done} subagent${run.done === 1 ? '' : 's'} done`)
  if (run.failed > 0) parts.push(`${run.failed} failed`)
  const more = running.length > 1 ? ` (+${running.length - 1} more)` : ''
  parts.push(`${shortName(oldest.type)} running ${minutes(now - oldest.startedAt)}${more}`)
  if (run.turnStartedAt !== null) parts.push(`turn ${minutes(now - run.turnStartedAt)}`)
  return parts.join(' · ')
}
