// plugin-recorder's $.state contract: what the progress band reads.

/** One subagent the band counts as running, keyed by tool_use_id or agentId. */
export type RecorderRunning = {
  type: string
  startedAt: number
}

/** The session's live run: the last plugin invocation and this turn's subagents. */
export type RecorderRun = {
  /** Last plugin command or skill invoked (`feature-dev:tdd`), or null. */
  label: string | null
  labelAt: number
  /** When the current main-loop turn started, or null between turns. */
  turnStartedAt: number | null
  /** Subagents finished (ok) during the current turn. */
  done: number
  /** Subagents that errored or were denied during the current turn. */
  failed: number
  running: { [id: string]: RecorderRunning }
  /** agentId -> subagent_type, so a subagent's turn.complete can be named. */
  agentTypes: { [agentId: string]: string }
  /** Session id whose session.start was already recorded (a hot reload re-fires it). */
  startedFor: string | null
}

declare module 'claude-code' {
  interface PluginState {
    'plugin-recorder': { run: RecorderRun }
  }
}
