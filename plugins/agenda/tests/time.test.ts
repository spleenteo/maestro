import { expect, test } from 'claude-code/testing'
import { LABELS_EN, LABELS_IT } from '../hooks/labels'
import { dayLabel, localParts, parseOffset } from '../hooks/time'
import { parseInput } from '../hooks/recap'

test('localParts gives the local date and time', async () => {
  expect(localParts(Date.UTC(2026, 9, 29, 13, 10), 60)).toEqual({ date: '2026-10-29', time: '14:10' })
})

test('localParts rolls over midnight in summer time', async () => {
  expect(localParts(Date.UTC(2026, 9, 24, 22, 30), 120)).toEqual({ date: '2026-10-25', time: '00:30' })
})

test('dayLabel names weekday and month', async () => {
  expect(dayLabel('2026-10-29', LABELS_IT)).toBe('gio 29 ott')
  expect(dayLabel('2026-10-25', LABELS_IT)).toBe('dom 25 ott')
  expect(dayLabel('2026-10-29', LABELS_EN)).toBe('Thu 29 Oct')
})

test('parseOffset reads offsets and Z', async () => {
  expect(parseOffset('2026-10-29T18:30:00+01:00')).toBe(60)
  expect(parseOffset('2026-10-29T18:30:00-03:30')).toBe(-210)
  expect(parseOffset('2026-10-29T17:30:00Z')).toBe(0)
  expect(parseOffset('2026-10-29T18:30:00')).toBeUndefined()
})

test('parseInput sorts events and takes the offset from the first start', async () => {
  const r = parseInput(
    {
      date: '2026-10-29',
      events: [
        { start: '2026-10-29T18:30:00+01:00', title: 'Karate' },
        { start: '2026-10-29T09:00:00+01:00', title: 'Call' },
      ],
      tasks: [{ title: 'Pay' }],
    },
    1000,
    0,
  )
  if (!('recap' in r)) throw new Error('expected a recap')
  expect(r.recap.events.map(e => e.title)).toEqual(['Call', 'Karate'])
  expect(r.recap.offsetMin).toBe(60)
})

test('parseInput falls back to the environment offset and rejects bad input', async () => {
  const empty = parseInput({ date: '2026-10-29', events: [], tasks: [] }, 1000, 120)
  if (!('recap' in empty)) throw new Error('expected a recap')
  expect(empty.recap.offsetMin).toBe(120)
  expect('error' in parseInput({ date: '2026-10-29' }, 1000)).toBe(true)
  expect('error' in parseInput({ date: '29/10', events: [] }, 1000, 0)).toBe(true)
  expect('error' in parseInput({ date: '2026-10-29', events: [{ start: '2026-10-29T18:30:00', title: 'x' }] }, 1000, 0)).toBe(true)
  expect('error' in parseInput({ date: '2026-10-29', events: [{ start: '2026-10-29T18:30:00Z', title: ' ' }] }, 1000, 0)).toBe(true)
})

test('parseInput rejects an impossible date and an impossible start', async () => {
  expect('error' in parseInput({ date: '2026-99-99', events: [] }, 1000, 0)).toBe(true)
  expect('error' in parseInput({ date: '2026-02-30', events: [] }, 1000, 0)).toBe(true)
  expect('error' in parseInput({ date: '2026-10-29', events: [{ start: '2026-13-45T99:99:00+01:00', title: 'x' }] }, 1000, 0)).toBe(true)
})
