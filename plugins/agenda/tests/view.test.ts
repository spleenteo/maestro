import { expect, test } from 'claude-code/testing'
import type { AgendaRecap } from '../types'
import { LABELS_EN, LABELS_IT } from '../hooks/labels'
import { msToNextMinute } from '../hooks/time'
import { agendaView, parseDayStart } from '../hooks/view'

const recap = (date: string, events: [string, string][] = [], tasks: string[] = []): AgendaRecap => ({
  date,
  offsetMin: 60,
  updatedAt: 0,
  events: events.map(([start, title]) => ({ start, title })),
  tasks: tasks.map(title => ({ title })),
})

test('parseDayStart reads HH:MM and falls back to 06:00', async () => {
  expect(parseDayStart('06:00')).toBe(360)
  expect(parseDayStart('04:30')).toBe(270)
  expect(parseDayStart('25:00')).toBe(360)
  expect(parseDayStart('6')).toBe(360)
  expect(parseDayStart(undefined)).toBe(360)
})

test('msToNextMinute aligns to the minute', async () => {
  expect(msToNextMinute(Date.UTC(2026, 9, 29, 13, 10, 30))).toBe(30000)
  expect(msToNextMinute(Date.UTC(2026, 9, 29, 13, 10))).toBe(60000)
})

test('yesterday recap turns stale at the day start', async () => {
  const r = recap('2026-10-28', [], ['Pay'])
  expect(agendaView(r, Date.UTC(2026, 9, 29, 4, 59), 360, LABELS_EN).kind).toBe('today')
  expect(agendaView(r, Date.UTC(2026, 9, 29, 5, 0), 360, LABELS_IT)).toEqual({ kind: 'stale', label: 'di ieri' })
  expect(agendaView(r, Date.UTC(2026, 9, 29, 2, 59), 240, LABELS_EN).kind).toBe('today')
  expect(agendaView(r, Date.UTC(2026, 9, 29, 3, 0), 240, LABELS_IT)).toEqual({ kind: 'stale', label: 'di ieri' })
})

test('an older recap is labelled non aggiornata', async () => {
  const r = recap('2026-10-27', [], ['Pay'])
  expect(agendaView(r, Date.UTC(2026, 9, 29, 9, 0), 360, LABELS_IT)).toEqual({ kind: 'stale', label: 'non aggiornata' })
})

test('the stale label is English with the English table', async () => {
  const r = recap('2026-10-28', [], ['Pay'])
  expect(agendaView(r, Date.UTC(2026, 9, 29, 5, 0), 360, LABELS_EN)).toEqual({ kind: 'stale', label: 'yesterday' })
})

test('events disappear after their starting minute', async () => {
  const r = recap('2026-10-29', [['2026-10-29T14:12:00+01:00', 'Call'], ['2026-10-29T18:30:00+01:00', 'Karate']])
  const titles = (ms: number) => {
    const v = agendaView(r, ms, 360, LABELS_EN)
    if (v.kind !== 'today') throw new Error('expected today')
    return v.events.map(e => e.title)
  }
  expect(titles(Date.UTC(2026, 9, 29, 13, 12))).toEqual(['Call', 'Karate'])
  expect(titles(Date.UTC(2026, 9, 29, 13, 13))).toEqual(['Karate'])
})

test('a recap with nothing left is empty', async () => {
  expect(agendaView(recap('2026-10-29'), Date.UTC(2026, 9, 29, 13, 10), 360, LABELS_EN)).toEqual({ kind: 'empty' })
  const past = recap('2026-10-29', [['2026-10-29T13:00:00+01:00', 'Lunch']])
  expect(agendaView(past, Date.UTC(2026, 9, 29, 13, 10), 360, LABELS_EN)).toEqual({ kind: 'empty' })
})
