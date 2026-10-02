import type { Register } from 'claude-code'

import { commandArgs, commandText } from './memory-check'

// /memory-check: runs scripts/memory-check.sh in the session's directory and
// shows its output as the command's reply. No Claude turn, no model call.
export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'memory-check',
      description: 'Flag auto-memory files that may be stale (retro memory-check.sh)',
    })

    return next(e)
  })

  on('command.run', { command: 'memory-check' }, async ($, e) => {
    const script = `${$.plugin.root}/scripts/memory-check.sh`
    const argv = ['bash', script, ...commandArgs(e.args)]
    try {
      const run = await $.process.run(argv, { timeoutMs: 120_000, stdin: '' })

      return { text: commandText(run) }
    } catch (error) {
      return { text: `memory-check did not finish: ${error instanceof Error ? error.message : String(error)}` }
    }
  })
}
