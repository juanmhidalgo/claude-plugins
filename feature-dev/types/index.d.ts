/** One feature as `features.py list --json` prints it. */
export type Feature = {
  slug: string
  status: 'draft' | 'approved' | 'planned' | 'running' | 'halted' | 'implemented' | 'invalid'
  plan: { steps: number; completed: number[]; halted_at: number | null; halt_reason: string | null } | null
  /** `owner/repo#N`, when the feature is linked to an issue. */
  issue: string | null
  /** Spec first, then plan; `path` is relative to the project root. */
  artifacts: { kind: 'spec' | 'plan'; path: string; needs_review: boolean }[]
  /** Only on `invalid` features. */
  reason?: string
}

declare module 'claude-code' {
  interface PluginState {
    'feature-dev': {
      /** The last `features.py list --json` result. */
      features: Feature[]
      /** Why the last refresh failed; null when it succeeded. */
      error: string | null
      /** Slugs the person dismissed from the band. */
      dismissed: string[]
      /** Whether the Features pane is open and placed. */
      paneOpen: boolean
      /** Slug awaiting delete confirmation, if any. */
      confirmDelete: string | null
      /** Slug whose actions the pane shows, if any. */
      selected: string | null
    }
  }
}
