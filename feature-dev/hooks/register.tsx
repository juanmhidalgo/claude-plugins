// Feature sidebar: a `Features` pane listing the features of this repository,
// active ones first, then a Done group. The list comes from
// `scripts/features.py list --json`, run through `$.process.run`; the mod reads
// no file itself (AC-20), so the script owns the layout and the state machine.
//
// Draws only where the engine raises `Pane`. Under `claude -p`, VS Code,
// --safe-mode or disableAllHooks nothing here runs.
//
// It also starts planning when a spec gets approved (`plan_after_approve`):
// a turn that moves a feature from draft to approved queues
// /feature-dev:explore-plan for its spec, whichever path approved it
// (/spec, /review, or a plain chat request).
import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Feature } from '../types'

const PANE_ID = 'features'
const PANE_TITLE = 'Features'
const LIST_TIMEOUT_MS = 30_000
/** Dock width the pane asks for; the default share is half the terminal. */
const PANE_COLUMNS = 56

const featuresAtom = atom({ plugin: 'feature-dev', key: 'features' } as const, [] as Feature[])
const errorAtom = atom({ plugin: 'feature-dev', key: 'error' } as const, null as string | null)
export const dismissedAtom = atom({ plugin: 'feature-dev', key: 'dismissed' } as const, [] as string[])
export const paneOpenAtom = atom({ plugin: 'feature-dev', key: 'paneOpen' } as const, false)
export const confirmDeleteAtom = atom({ plugin: 'feature-dev', key: 'confirmDelete' } as const, null as string | null)
export const selectedAtom = atom({ plugin: 'feature-dev', key: 'selected' } as const, null as string | null)

/** Runs `features.py list --json` for the session root and parses its JSON array. */
async function listFeatures($: EngineInterface): Promise<Feature[]> {
  const root = (await $.session.root()).replace(/\/+$/, '')
  const result = await $.process.run(
    ['python3', `${$.plugin.root}/scripts/features.py`, 'list', '--json', '--root', root],
    { timeoutMs: LIST_TIMEOUT_MS },
  )
  if (result.exitCode !== 0) throw new Error(result.stderr.trim() || `features.py exited ${result.exitCode}`)
  const parsed: unknown = JSON.parse(result.stdout)
  if (!Array.isArray(parsed)) throw new Error('features.py list did not print a JSON array')
  return parsed as Feature[]
}

async function refresh($: EngineInterface): Promise<void> {
  try {
    const features = await listFeatures($)
    await update($, featuresAtom, () => features)
    await update($, errorAtom, () => null)
  } catch (err) {
    // The Pane shows this instead of the list; a later successful refresh clears it.
    await update($, errorAtom, () => (err instanceof Error ? err.message : String(err)))
  }
}

/** Runs one of this plugin's commands as if the person typed it. */
async function runCommand($: EngineInterface, full: string, args: string): Promise<void> {
  const short = full.split(':').pop()
  const commands = await $.command.list()
  const command =
    commands.find(c => c.name === full)?.name ??
    commands.find(c => c.plugin === 'feature-dev' && c.name.split(':').pop() === short)?.name
  if (command === undefined) {
    $.ui.toast(`/${full} is not available in this session`)
    return
  }
  // As if the person typed `/<command> <args>`: a typed command is not
  // blocked by disable-model-invocation, and what it decides gets applied.
  await $.command.run({ command, args })
}

const pathOf = (f: Feature, kind: 'spec' | 'plan') => f.artifacts.find(a => a.kind === kind)?.path

const isContinuable = (f: Feature) => ['planned', 'running', 'halted'].includes(f.status)

const isDone = (f: Feature) => f.status === 'implemented'

const needsPlan = (f: Feature) => f.status === 'approved' && pathOf(f, 'plan') === undefined

const GLYPHS: Record<Feature['status'], [string, string]> = {
  draft: ['○', 'subtle'],
  approved: ['◐', 'suggestion'],
  planned: ['◑', 'suggestion'],
  running: ['●', 'claude'],
  halted: ['■', 'warning'],
  implemented: ['✓', 'success'],
  invalid: ['✗', 'error'],
}

/**
 * The feature whose spec this turn approved: draft before the turn, approved
 * after it, and still without a plan. Only one per turn, the first listed.
 */
export function newlyApproved(before: readonly Feature[], after: readonly Feature[]): Feature | undefined {
  const wasDraft = new Set(before.filter(f => f.status === 'draft').map(f => f.slug))
  return after.find(f => wasDraft.has(f.slug) && needsPlan(f) && pathOf(f, 'spec') !== undefined)
}

// A shipped feature is never marked: approving in chat writes no review, so its
// artifacts keep reading "needs review" forever and would pin the band on.
const isMarked = (f: Feature, dismissed: readonly string[]) =>
  !isDone(f) && f.artifacts.some(a => a.needs_review) && !dismissed.includes(f.slug)

/** Features still marked "needs review" once the dismissed ones are left out. */
export const needsReviewCount = (features: readonly Feature[], dismissed: readonly string[]): number =>
  features.filter(f => isMarked(f, dismissed)).length

function label(f: Feature, dismissed: readonly string[]): string {
  const needsReview = isMarked(f, dismissed)
  return `${f.slug} · ${f.status}${needsReview ? ' · needs review' : ''}`
}

export const register: Register = (on, options) => {
  const showPane = options.review_band !== false
  const autoPlan = options.plan_after_approve !== false
  if (!showPane && !autoPlan) return

  // Set when /feature-dev:explore-plan runs, cleared at the end of the turn:
  // explore-plan approves a draft spec itself before planning it, and that
  // approval must not queue a second run.
  let planningThisTurn = false

  on('command.run', { command: 'feature-dev:explore-plan' }, async ($, e, next) => {
    planningThisTurn = true
    return next(e)
  })

  on('session.start', async ($, e, next) => {
    const result = await next(e)
    if (e.isInteractive) {
      // List first; an empty repository gets no pane at all (AC-22).
      await refresh($)
      // A failed list opens the pane too, so the person sees the error and Retry.
      if (showPane && ((await read($, featuresAtom)).length > 0 || (await read($, errorAtom)) !== null)) {
        const opened = await $.ui.open({ id: PANE_ID, title: PANE_TITLE, columns: PANE_COLUMNS })
        if (opened.isPlaced) await update($, paneOpenAtom, () => true)
      }
    }
    return result
  })

  // Whether the pane is shown, from what the engine answers: the band hides
  // while it is (AC-19). Render hooks only read this.
  on('ui.open', async ($, e, next) => {
    const result = await next(e)
    if (e.id === PANE_ID && result.isPlaced) await update($, paneOpenAtom, () => true)
    return result
  })

  on('ui.close', async ($, e, next) => {
    const result = await next(e)
    if (e.id === PANE_ID) await update($, paneOpenAtom, () => false)
    return result
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (!showPane) return next(e)
    if (e.props.hasSurvey || e.props.view.agentId !== undefined) return next(e)
    if (await read($, paneOpenAtom)) return next(e)
    if ((await read($, errorAtom)) !== null) return next(e)
    const count = needsReviewCount(await read($, featuresAtom), await read($, dismissedAtom))
    if (count === 0) return next(e)
    const { Box, Button } = $.ui.resolve(e)
    return (
      <Box flexDirection="row">
        <Button
          key="band"
          label={`${count} need review · ${PANE_TITLE}`}
          variant="primary"
          onPress={async () => {
            const opened = await $.ui.open({ id: PANE_ID, focus: true, columns: PANE_COLUMNS })
            if (opened.isPlaced) await update($, paneOpenAtom, () => true)
          }}
        />
      </Box>
    )
  })

  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    if (e.agentId !== undefined) return result
    const before = await read($, featuresAtom)
    await refresh($)
    const planning = planningThisTurn
    planningThisTurn = false
    if (!autoPlan || planning || e.reason !== 'answer') return result
    const approved = newlyApproved(before, await read($, featuresAtom))
    const spec = approved && pathOf(approved, 'spec')
    if (approved && spec) {
      $.ui.toast(`${approved.slug} approved: starting /feature-dev:explore-plan (plan_after_approve)`)
      // From a timer, not this hook: $.command.run is refused inside a hook the
      // turn waits on, and from here it queues until the session is idle.
      $.clock.after(1, () => {
        runCommand($, 'feature-dev:explore-plan', spec).catch(err =>
          $.ui.toast(`Could not run /feature-dev:explore-plan: ${String(err)}`),
        )
      })
    }
    return result
  })

  on('ui.render', { component: 'Pane', requestId: PANE_ID }, async ($, e, next) => {
    if (!showPane) return next(e)
    const { Box, Text, Button } = $.ui.resolve(e)
    const error = await read($, errorAtom)
    if (error !== null) {
      return (
        <Box flexDirection="column" paddingX={1} rowGap={1}>
          <Text key="error" color="error" wrap="truncate-end">
            {`Could not list features: ${error}`}
          </Text>
          <Box key="error-actions" flexDirection="row">
            <Button key="retry" label="Retry" variant="primary" onPress={() => refresh($)} />
          </Box>
        </Box>
      )
    }
    const features = await read($, featuresAtom)
    const selectedSlug = await read($, selectedAtom)
    const dismissed = await read($, dismissedAtom)
    const selected = features.find(f => f.slug === selectedSlug)
    const active = features.filter(f => !isDone(f))
    const done = features.filter(isDone)
    if (features.length === 0) {
      return (
        <Box flexDirection="column" paddingX={1}>
          <Text key="empty" dimColor wrap="truncate-end">
            No features yet. Start one with /feature-dev:spec
          </Text>
        </Box>
      )
    }
    const run = (command: string, path: string) => () =>
      runCommand($, command, path).catch(err => $.ui.toast(`Could not run /${command}: ${String(err)}`))
    const confirming = await read($, confirmDeleteAtom)
    const deleteFeature = async (f: Feature) => {
      if (f.status === 'running' || f.status === 'halted') {
        $.ui.toast('Run in progress — finish it, or remove it with /feature-dev:cleanup')
        return
      }
      if (confirming !== f.slug) {
        await update($, confirmDeleteAtom, () => f.slug)
        return
      }
      await update($, confirmDeleteAtom, () => null)
      const root = (await $.session.root()).replace(/\/+$/, '')
      const argv = ['python3', `${$.plugin.root}/scripts/features.py`, 'delete', f.slug, '--root', root]
      if (!isDone(f)) argv.push('--force')
      try {
        const result = await $.process.run(argv, { timeoutMs: LIST_TIMEOUT_MS })
        if (result.exitCode === 0) await refresh($)
        else $.ui.toast(result.stderr.trim() || `features.py exited ${result.exitCode}`)
      } catch (err) {
        $.ui.toast(err instanceof Error ? err.message : String(err))
      }
    }
    const deleteLabel = (f: Feature) =>
      confirming !== f.slug ? 'Delete' : isDone(f) ? 'Press again to delete' : 'Not implemented: press again to force delete'

    // The selected feature's detail and actions, drawn right under its row.
    const actions = (f: Feature) => {
      const spec = pathOf(f, 'spec')
      const plan = pathOf(f, 'plan')
      const continuePath = plan ?? spec
      const detail = [
        f.plan ? `${f.plan.completed.length}/${f.plan.steps} steps` : null,
        f.plan?.halt_reason ? `halted: ${f.plan.halt_reason}` : null,
        f.issue,
        f.reason ?? null,
      ].filter(Boolean).join(' · ')
      return (
        <Box key={`actions:${f.slug}`} flexDirection="column" marginLeft={2} marginBottom={1}>
          {detail ? (
            <Text key="detail" dimColor wrap="truncate-end">
              {detail}
            </Text>
          ) : null}
          <Box key="buttons" flexDirection="row" flexWrap="wrap" columnGap={1}>
            {spec && needsPlan(f) ? (
              <Button key="plan" label="Plan" variant="primary" onPress={run('feature-dev:explore-plan', spec)} />
            ) : null}
            {isContinuable(f) && continuePath ? (
              <Button key="continue" label="Continue" variant="primary" onPress={run('feature-dev:tdd', continuePath)} />
            ) : null}
            {spec ? <Button key="review-spec" label="Review spec" onPress={run('feature-dev:review', spec)} /> : null}
            {plan ? <Button key="review-plan" label="Review plan" onPress={run('feature-dev:review', plan)} /> : null}
            <Button key="dismiss" label="Dismiss" onPress={() => update($, dismissedAtom, d => [...d, f.slug])} />
            <Button key="delete" label={deleteLabel(f)} onPress={() => deleteFeature(f)} />
          </Box>
        </Box>
      )
    }

    const row = (f: Feature) => {
      const [glyph, color] = GLYPHS[f.status] ?? ['?', 'subtle']
      const isSelected = f.slug === selected?.slug
      return (
        <Box key={`feature:${f.slug}`} flexDirection="column">
          <Button
            key={`select:${f.slug}`}
            plain
            onPress={async () => {
              await update($, selectedAtom, () => (isSelected ? null : f.slug))
              await update($, confirmDeleteAtom, () => null)
            }}
          >
            <Text color={color}>{`${glyph} `}</Text>
            <Text
              bold={isSelected}
              dimColor={isDone(f) && !isSelected}
              color={isMarked(f, dismissed) ? 'warning' : undefined}
              wrap="truncate-end"
            >
              {label(f, dismissed)}
            </Text>
          </Button>
          {isSelected ? actions(f) : null}
        </Box>
      )
    }

    return (
      <Box flexDirection="column" paddingX={1}>
        {active.length > 0 ? (
          <Text key="group:active" bold dimColor>
            Active
          </Text>
        ) : null}
        {active.map(row)}
        {done.length > 0 ? (
          <Box key="group:done" marginTop={active.length > 0 ? 1 : 0}>
            <Text bold dimColor>
              Done
            </Text>
          </Box>
        ) : null}
        {done.map(row)}
      </Box>
    )
  })
}
