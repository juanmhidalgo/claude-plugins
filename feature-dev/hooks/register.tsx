// Feature sidebar: a `Features` pane listing the features of this repository,
// active ones first, then a Done group. The list comes from
// `scripts/features.py list --json`, run through `$.process.run`; the mod reads
// no file itself (AC-20), so the script owns the layout and the state machine.
//
// Draws only where the engine raises `Pane`. Under `claude -p`, VS Code,
// --safe-mode or disableAllHooks nothing here runs.
import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Feature } from '../types'

const PANE_ID = 'features'
const PANE_TITLE = 'Features'
const LIST_TIMEOUT_MS = 30_000

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
  if (options.review_band === false) return

  on('session.start', async ($, e, next) => {
    const result = await next(e)
    if (e.isInteractive) {
      // List first; an empty repository gets no pane at all (AC-22).
      await refresh($)
      // A failed list opens the pane too, so the person sees the error and Retry.
      if ((await read($, featuresAtom)).length > 0 || (await read($, errorAtom)) !== null) {
        const opened = await $.ui.open({ id: PANE_ID, title: PANE_TITLE })
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
            const opened = await $.ui.open({ id: PANE_ID, focus: true })
            if (opened.isPlaced) await update($, paneOpenAtom, () => true)
          }}
        />
      </Box>
    )
  })

  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    if (e.agentId === undefined) await refresh($)
    return result
  })

  on('ui.render', { component: 'Pane', requestId: PANE_ID }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const { Button } = $.ui.resolve(e)
    const error = await read($, errorAtom)
    if (error !== null) {
      const { Button } = $.ui.resolve(e)
      return (
        <Box flexDirection="column">
          <Text key="error" wrap="truncate-end">
            {`Could not list features: ${error}`}
          </Text>
          <Button key="retry" label="Retry" onPress={() => refresh($)} />
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
        <Box flexDirection="column">
          <Text key="empty" wrap="truncate-end">
            No features yet. Start one with /feature-dev:spec
          </Text>
        </Box>
      )
    }
    const row = (f: Feature) => (
      <Box key={`feature:${f.slug}`} flexDirection="row">
        <Button key={`select:${f.slug}`} label="▸" onPress={async () => {
            await update($, selectedAtom, () => f.slug)
            await update($, confirmDeleteAtom, () => null)
          }}
        />
        <Text wrap="truncate-end">{label(f, dismissed)}</Text>
      </Box>
    )
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
    const deleteLabel = !selected || confirming !== selected.slug
      ? 'Delete'
      : isDone(selected)
        ? 'Press again to delete'
        : 'Not implemented: press again to force delete'
    const spec = selected && pathOf(selected, 'spec')
    const plan = selected && pathOf(selected, 'plan')
    const continuePath = selected && (plan ?? spec)
    return (
      <Box flexDirection="column">
        {active.map(row)}
        {done.length > 0 ? (
          <Text key="group:done" bold>
            Done
          </Text>
        ) : null}
        {done.map(row)}
        {selected ? (
          <Box key="actions" flexDirection="row">
            {spec ? <Button key="review-spec" label="Review spec" onPress={run('feature-dev:review', spec)} /> : null}
            {plan ? <Button key="review-plan" label="Review plan" onPress={run('feature-dev:review', plan)} /> : null}
            {isContinuable(selected) && continuePath ? (
              <Button key="continue" label="Continue" onPress={run('feature-dev:tdd', continuePath)} />
            ) : null}
            <Button key="dismiss" label="Dismiss" onPress={() => update($, dismissedAtom, d => [...d, selected.slug])} />
            <Button key="delete" label={deleteLabel} onPress={() => deleteFeature(selected)} />
          </Box>
        ) : null}
      </Box>
    )
  })
}
