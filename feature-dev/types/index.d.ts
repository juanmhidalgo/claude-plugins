/** A SPEC-*.md or PLAN-*.md changed after its latest browser review. */
export type PendingArtifact = {
  /** File name, e.g. `SPEC-billing.md`: what reviews match on. */
  name: string
  /** Path relative to the project root, passed to /feature-dev:review. */
  path: string
  /** The artifact's mtime when the band last looked. */
  mtimeMs: number
  /** `http://localhost:<port>/` of a live review server for it, if any. */
  url?: string
}

declare module 'claude-code' {
  interface PluginState {
    'feature-dev': {
      /** Artifacts not reviewed since their last change. */
      pending: PendingArtifact[]
      /** name → mtimeMs at dismissal; hidden until the mtime changes. */
      dismissed: Record<string, number>
    }
  }
}
