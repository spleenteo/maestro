import type { AgendaEvent, AgendaRecap, AgendaTask } from '../types'
import type { Labels } from './labels'
import { localParts } from './time'

export type AgendaView =
  | { kind: 'today'; events: AgendaEvent[]; tasks: AgendaTask[] }
  | { kind: 'empty' }
  | { kind: 'stale'; label: string }

const DEFAULT_DAY_START = 360

/** Minutes after midnight from an `HH:MM` setting; 360 (06:00) when invalid. */
export function parseDayStart(value: unknown): number {
  const m = typeof value === 'string' ? /^(\d{2}):(\d{2})$/.exec(value) : null
  if (!m) return DEFAULT_DAY_START
  const h = Number(m[1])
  const min = Number(m[2])
  return h > 23 || min > 59 ? DEFAULT_DAY_START : h * 60 + min
}

/** Local date (YYYY-MM-DD) of the lived day, which starts at `dayStartMin`. */
export function livedDay(nowMs: number, offsetMin: number, dayStartMin: number): string {
  return localParts(nowMs - dayStartMin * 60000, offsetMin).date
}

/** What the pane shows for a recap at a given instant. */
export function agendaView(recap: AgendaRecap, nowMs: number, dayStartMin: number, labels: Labels): AgendaView {
  const lived = livedDay(nowMs, recap.offsetMin, dayStartMin)
  if (lived > recap.date) {
    const [y = 0, m = 1, d = 1] = recap.date.split('-').map(Number)
    const next = localParts(Date.UTC(y, m - 1, d + 1), 0).date
    return { kind: 'stale', label: lived === next ? labels.yesterday : labels.older }
  }
  const events = recap.events.filter(e => nowMs < Date.parse(e.start) + 60000)
  if (events.length === 0 && recap.tasks.length === 0) return { kind: 'empty' }
  return { kind: 'today', events, tasks: recap.tasks }
}

/** `HH:MM` from minutes after midnight; the inverse of `parseDayStart`. */
export function formatDayStart(min: number): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(Math.floor(min / 60))}:${pad(min % 60)}`
}
