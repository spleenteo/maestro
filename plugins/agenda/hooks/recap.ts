import type { AgendaEvent, AgendaRecap, AgendaTask } from '../types'
import { localParts, parseOffset } from './time'

export const storeKey = (realRoot: string): string => `agenda:${realRoot}`

const isObject = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null

export function isRecap(value: unknown): value is AgendaRecap {
  if (!isObject(value)) return false
  const { date, offsetMin, updatedAt, events, tasks } = value
  return (
    typeof date === 'string' &&
    typeof offsetMin === 'number' &&
    typeof updatedAt === 'number' &&
    Array.isArray(events) &&
    events.every(ev => isObject(ev) && typeof ev.start === 'string' && typeof ev.title === 'string') &&
    Array.isArray(tasks) &&
    tasks.every(t => isObject(t) && typeof t.title === 'string')
  )
}

/**
 * Validates the tool input. The offset comes from the first event start,
 * else from `envOffsetMin` (the caller's environment offset).
 */
export function parseInput(
  input: unknown,
  nowMs: number,
  envOffsetMin?: number,
): { recap: AgendaRecap } | { error: string } {
  if (!isObject(input)) return { error: 'Input must be an object.' }
  const { date, events: rawEvents = [], tasks: rawTasks = [] } = input
  if (
    typeof date !== 'string' ||
    !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
    localParts(Date.parse(date + 'T00:00:00Z'), 0).date !== date
  ) {
    return { error: 'date must be YYYY-MM-DD.' }
  }
  if (!Array.isArray(rawEvents) || !Array.isArray(rawTasks)) {
    return { error: 'events and tasks must be arrays.' }
  }
  const events: AgendaEvent[] = []
  for (const ev of rawEvents) {
    if (!isObject(ev) || typeof ev.start !== 'string' || typeof ev.title !== 'string') {
      return { error: 'Each event needs a start and a title.' }
    }
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(ev.start) || parseOffset(ev.start) === undefined || Number.isNaN(Date.parse(ev.start))) {
      return { error: `Event start "${ev.start}" must be ISO 8601 with an offset, e.g. 2026-10-29T18:30:00+01:00.` }
    }
    if (ev.title.trim() === '') return { error: 'Event title must not be empty.' }
    events.push({ start: ev.start, title: ev.title })
  }
  const tasks: AgendaTask[] = []
  for (const t of rawTasks) {
    if (!isObject(t) || typeof t.title !== 'string' || t.title.trim() === '') {
      return { error: 'Each task needs a non-empty title.' }
    }
    tasks.push({ title: t.title })
  }
  // offsetMin comes from the first event in input order, before sorting.
  const first = events[0]
  const offsetMin = first ? parseOffset(first.start) : envOffsetMin
  if (offsetMin === undefined) return { error: 'No local offset available: pass at least one event.' }
  events.sort((a, b) => Date.parse(a.start) - Date.parse(b.start))
  return { recap: { date, offsetMin, updatedAt: nowMs, events, tasks } }
}
