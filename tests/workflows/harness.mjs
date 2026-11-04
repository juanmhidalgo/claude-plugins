// Test harness for the Workflow scripts (code-review/workflows/*.js, feature-dev/workflows/*.js,
// github-issues/workflows/*.js). Loads a script, splits off its `export const meta` literal and
// runs the body with stubbed globals: the test supplies `agent`, the harness supplies `parallel`
// and `pipeline` with the semantics of the Workflow tool reference, and records every agent call.
//
// Usage:
//   const wf = await loadWorkflow('code-review/workflows/review.js')
//   const { result, calls } = await wf.run(args, (prompt, opts) => ...)
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const REPO_ROOT = fileURLToPath(new URL('../../', import.meta.url))

// `export const meta = {...}` is a pure literal whose closing brace sits at column 0.
const META_RE = /^export const meta = (\{[\s\S]*?\n\})\s*\n/m

export async function loadWorkflow(relPath) {
  const file = path.resolve(REPO_ROOT, relPath)
  const src = await readFile(file, 'utf8')
  const match = META_RE.exec(src)
  if (!match) throw new Error(`${relPath}: no \`export const meta = {...}\` literal found`)
  const meta = new Function(`return (${match[1]})`)()
  const body = src.replace('export const meta', 'const meta')
  // Same wrapping the Workflow tool applies: a plain async body with top-level await and return.
  const factory = new Function(
    'agent', 'parallel', 'pipeline', 'phase', 'log', 'args', 'budget', 'workflow',
    `return (async () => {${body}\n})()`,
  )
  return { meta, file, run: (args, stub, extra) => run(factory, args, stub, extra) }
}

// parallel(thunks): a barrier that never rejects; a thunk that throws resolves to null.
export const parallel = (thunks) => Promise.all(thunks.map(async (thunk) => {
  try { return await thunk() } catch { return null }
}))

// pipeline(items, ...stages): each item runs through the stages independently. A stage receives
// (prevResult, originalItem, index); a stage that throws drops the item to null and skips the rest.
export const pipeline = (items, ...stages) => Promise.all(items.map(async (item, index) => {
  let prev = item
  for (const stage of stages) {
    try { prev = await stage(prev, item, index) } catch { return null }
  }
  return prev
}))

async function run(factory, args, stub, { workflow } = {}) {
  if (typeof stub !== 'function') throw new TypeError('run(args, stub): stub must be a function (prompt, opts) => result')
  const calls = []
  const logs = []
  const phases = []
  const agent = async (prompt, opts = {}) => {
    const call = { order: calls.length, prompt, opts }
    calls.push(call)
    const result = await stub(prompt, opts, call)
    call.result = result
    return result
  }
  const budget = { total: null, spent: () => 0, remaining: () => Infinity }
  const nested = workflow || (() => { throw new Error('workflow() is not stubbed in this test') })
  const result = await factory(agent, parallel, pipeline, (t) => phases.push(t), (m) => logs.push(m), args, budget, nested)
  return { result, calls, logs, phases }
}

// Helpers for assertions on the recorded calls.
export const labels = (calls) => calls.map((c) => c.opts.label)
export const callsFor = (calls, label) => calls.filter((c) => c.opts.label === label)

// sequence(a, b, c): a stub piece that returns a, then b, then c, then c again for every later call.
export function sequence(...values) {
  let i = 0
  return () => values[Math.min(i++, values.length - 1)]
}
