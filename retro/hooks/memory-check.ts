// Pure helpers for the /memory-check command, kept apart so tests import them.

/** Splits the typed arguments on whitespace; memory-check.sh takes only flags and paths. */
export const commandArgs = (args: string): string[] => args.trim().split(/\s+/).filter(Boolean)

/** The command's reply for a finished memory-check.sh run. */
export const commandText = (run: { exitCode: number; stdout: string; stderr: string }): string => {
  if (run.exitCode !== 0) {
    return `memory-check failed (exit ${run.exitCode}): ${run.stderr.trim() || 'no error output'}`
  }
  const out = run.stdout.trim()

  return out === '' ? 'memory-check: no findings.' : out
}
