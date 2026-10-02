// test-progress's $.state contract: what the band reads. Session memory only;
// nothing here is written to $.store or to disk.

/** One snapshot of the progress file: `runner done total failed started`. */
export type TestProgress = {
  runner: string
  done: number
  total: number
  failed: number
  /** Seconds since the epoch, as the test runner wrote it. */
  startedEpoch: number
}

/** A foreground test command the Bash tool is running now. */
export type TestRun = {
  /** Runner detected from the command (`pytest`, `go test`, ...). */
  runner: string
  startedAt: number
  /** The last progress file read during this run, or null. */
  progress: TestProgress | null
}

/** How the last test command ended, shown until the next prompt. */
export type TestSummary = {
  runner: string
  /** `done` (exited), `interrupted`, `background` (run_in_background), `backgrounded` (moved mid-run). */
  outcome: 'done' | 'interrupted' | 'background' | 'backgrounded'
  exitCode: number | null
  durationMs: number
  passed: number | null
  failed: number | null
  errors: number | null
}

export type TestBand = {
  /** Running test commands keyed by tool_use_id. */
  running: { [id: string]: TestRun }
  summary: TestSummary | null
}

declare module 'claude-code' {
  interface PluginState {
    'test-progress': { band: TestBand }
  }
}
