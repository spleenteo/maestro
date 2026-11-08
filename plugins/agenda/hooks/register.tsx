import { atom, read, update } from 'claude-code'
import type { Hook, Register } from 'claude-code'

import type { AgendaRecap } from '../types'
import { labelsFor } from './labels'
import { renderAgenda } from './pane'
import { CLOSED, OPENED, REFRESH_PROMPT, REFRESHING, REMINDER, REMINDER_ID } from './prompt'
import { isRecap, parseInput, storeKey } from './recap'
import { renderToolRow } from './row'
import { msToNextMinute } from './time'
import { agendaView, formatDayStart, livedDay, parseDayStart } from './view'

export const PANE = 'agenda'
const TOOL = 'mcp__agenda__agenda_set'

// Change the tag when the recap fields change: it declines what an earlier
// version stored, which outlives a reload.
export const recapAtom = atom({ plugin: 'agenda', key: 'recap' } as const, null as AgendaRecap | null, {
  shape: 'recap-1',
})
// The pane's clock, written by the minute tick; 0 until the first write.
export const nowAtom = atom({ plugin: 'agenda', key: 'now' } as const, 0, { shape: 'now-1' })
const storeKeyRef = { plugin: 'agenda', key: 'storeKey' } as const

type Api = Parameters<Hook<'session.start'>>[0]

// The one place the key is derived, so session.start and agenda_set agree.
async function rootStoreKey($: Api): Promise<string> {
  const root = await $.session.root()
  const stat = await $.fs.stat(root, { resolve: true })
  return storeKey(stat.realPath ?? root)
}

// /clear starts a new session with an empty $.state and fires no session.start,
// so the key session.start wrote is gone while the tool stays registered:
// derive it again when the state lacks it.
async function ensureStoreKey($: Api): Promise<string> {
  const { value } = await $.state.get(storeKeyRef)
  if (value !== undefined) return value
  const key = await rootStoreKey($)
  await $.state.set(storeKeyRef, key)
  return key
}

const DESCRIPTION =
  'Save the recap of the local day shown in the agenda pane. Each call replaces the whole previous list: ' +
  'send every remaining appointment and open task of the day, not just the changes. ' +
  'Event starts are ISO 8601 with the local offset, e.g. 2026-10-29T18:30:00+01:00.'

const inputSchema = (dayStartMin: number) => ({
  type: 'object',
  properties: {
    date: {
      type: 'string',
      description: `Local day, YYYY-MM-DD. Lived day: before ${formatDayStart(dayStartMin)} local it is still the previous day.`,
    },
    events: {
      type: 'array',
      description: 'Appointments still ahead today.',
      items: {
        type: 'object',
        properties: {
          start: { type: 'string', description: 'ISO 8601 with local offset, e.g. 2026-10-29T18:30:00+01:00.' },
          title: { type: 'string' },
        },
        required: ['start', 'title'],
      },
    },
    tasks: {
      type: 'array',
      description: 'Open tasks for today.',
      items: { type: 'object', properties: { title: { type: 'string' } }, required: ['title'] },
    },
  },
  required: ['date'],
})

export const register: Register = (on, options) => {
  const dayStartMin = parseDayStart(options.dayStart)
  const labels = labelsFor(options.language)

  on('session.start', async ($, e, next) => {
    const key = await rootStoreKey($)
    await $.state.set(storeKeyRef, key)

    const saved = await $.store.get(key)
    if (isRecap(saved)) await update($, recapAtom, () => saved)

    await $.tool.register({
      name: 'agenda_set',
      isDeferred: false,
      description: DESCRIPTION,
      inputSchema: inputSchema(dayStartMin),
    })

    await $.command.register({
      name: 'agenda',
      description: 'Show or hide the agenda pane; update refreshes it',
      argumentHint: labels.argumentHint,
    })

    const tick = async () => {
      const nowMs = await $.clock.now()
      await update($, nowAtom, () => nowMs)
      // Another session or a tool without a pane may have written the store.
      const saved = await $.store.get(key)
      if (!isRecap(saved)) return
      // Compare inside the updater: the tool may have written a fresher recap meanwhile.
      let isNewDay = false
      await update($, recapAtom, cur => {
        isNewDay = false
        if (cur !== null && saved.updatedAt <= cur.updatedAt) return cur
        isNewDay = cur?.date !== saved.date
        return saved
      })
      if (isNewDay) {
        void $.ui.open({ id: PANE, title: labels.paneTitle, columns: 42 }).catch(() => undefined)
      }
    }
    const startMs = await $.clock.now()
    await update($, nowAtom, () => startMs)
    // One tick on the minute, then one a minute: the first tick keeps the
    // clock from lagging a minute when the start falls exactly on it.
    $.clock.after(msToNextMinute(startMs), () => {
      tick().catch(() => undefined)
      $.clock.every(60000, () => {
        tick().catch(() => undefined)
      })
    })

    return next(e)
  })

  on('command.run', { command: 'agenda' }, async ($, e) => {
    const arg = e.args.trim().toLowerCase()
    if (arg === 'update' || arg === labels.refreshAlias) {
      // Submitting inside the hook would wait on the turn the hook holds: a timer runs after it returns.
      $.clock.after(0, () => {
        void $.prompt.submit({ text: REFRESH_PROMPT, asUser: true }).catch(() => undefined)
      })
      return { text: REFRESHING }
    }
    if (arg !== '') return { text: labels.usage }
    const pane = (await $.ui.panes()).find(one => one.id === PANE)
    if (pane?.isPlaced && pane.isShown) {
      await $.ui.close({ id: PANE })
      return { text: CLOSED }
    }
    await $.ui.open({ id: PANE, title: labels.paneTitle, columns: 42 })
    return { text: OPENED }
  })

  on('prompt.compose', async ($, e, next) => {
    const out = await next(e)
    if (!e.tools.includes(TOOL)) return out
    const recap = await read($, recapAtom)
    if (recap === null) return out
    const nowMs = await $.clock.now()
    if (recap.date !== livedDay(nowMs, recap.offsetMin, dayStartMin)) return out
    return { sections: [...out.sections, { id: REMINDER_ID, text: REMINDER, scope: 'session' as const }] }
  }).catch(($, e, next) => next(e))

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const recap = await read($, recapAtom)
    if (recap === null) return renderAgenda($.ui.resolve(e), null, null, labels)
    const stored = await read($, nowAtom)
    const nowMs = stored === 0 ? await $.clock.now() : stored
    return renderAgenda($.ui.resolve(e), recap, agendaView(recap, nowMs, dayStartMin, labels), labels)
  })

  // The call's own row is one line; ctrl+o, an error or an interruption keep the engine's full row.
  on('ui.render', { component: 'ToolUse', props: { tool: TOOL } }, ($, e, next) => {
    const { isExpanded, isErrored, isInterrupted } = e.props
    if (isExpanded === true || isErrored || isInterrupted) return next(e)
    return renderToolRow($.ui.resolve(e), e.props, labels)
  })

  // The count is in the row above: nothing is drawn under it.
  on('ui.render', { component: 'ToolResult', props: { tool: TOOL } }, ($, e, next) => {
    if (e.props.isExpanded === true || e.props.isErrored) return next(e)
    const { Box } = $.ui.resolve(e)
    return <Box />
  })

  on('tool.call', { tool: TOOL }, async ($, e) => {
    if (e.agentId !== undefined) return { deny: 'agenda_set can only be called from the main conversation, not from a subagent.' }

    const nowMs = await $.clock.now()
    const envOffsetMin = 0 - new Date(nowMs).getTimezoneOffset()
    const parsed = parseInput(e, nowMs, envOffsetMin)
    if ('error' in parsed) return { deny: parsed.error }
    const { recap } = parsed

    let key: string
    try {
      key = await ensureStoreKey($)
    } catch {
      return { deny: 'The agenda store could not be located.' }
    }

    const previous = await read($, recapAtom)
    await $.store.set(key, recap)
    await update($, recapAtom, () => recap)

    if (previous?.date !== recap.date) {
      void $.ui.open({ id: PANE, title: labels.paneTitle, columns: 42 }).catch(() => undefined)
    }

    return { result: `Agenda saved: ${recap.events.length} events, ${recap.tasks.length} tasks.` }
  }).catch(($, e, next) => (next.called ? next(e) : { deny: 'Saving the agenda failed.' }))
}
