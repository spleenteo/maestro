import { expect, mock, test } from 'claude-code/testing'

const TOOL = 'mcp__agenda__agenda_set'
const NOW = Date.UTC(2026, 9, 29, 13, 10)

const list = (title: string) => ({
  date: '2026-10-29',
  events: [{ start: '2026-10-29T18:30:00+01:00', title }],
  tasks: [{ title: 'Pay invoice' }],
})

async function boot($: any, on: any, root: string, real: string, seed: Record<string, unknown> = {}, failSet = false) {
  const writes: { key: string; value: unknown }[] = []
  let opened = 0
  mock.clock(on, { now: NOW })
  const mem = new Map<string, unknown>(Object.entries(seed))
  on('store.get', (_: any, e: any) => ({ value: mem.get(e.key) }))
  on('store.set', (_: any, e: any) => {
    if (failSet) throw new Error('disk full')
    writes.push({ key: e.key, value: e.value })
    mem.set(e.key, e.value)
    return { value: undefined }
  })
  on('session.root', () => ({ value: root }))
  on('fs.stat', () => ({ value: { kind: 'dir', size: 0, mtimeMs: 0, isLink: true, realPath: real } }))
  on('tool.register', () => ({ value: {} }))
  on('command.register', () => ({ value: { command: 'agenda' } }))
  on('ui.open', () => {
    opened += 1
    return { value: { isPlaced: true } }
  })
  on('session.start', (_: any, e: any) => ({ cwd: e.cwd }))
  await $.session.start({ cwd: root, surface: 'terminal', isInteractive: true })
  return { writes, opened: () => opened }
}

test('two calls in a row leave only the second list', async ($, on) => {
  const w = await boot($, on, '/a', '/real/a')
  await $.tool.call({ tool: TOOL, ...list('Karate') })
  await $.tool.call({ tool: TOOL, ...list('Dentist') })
  const last = w.writes[w.writes.length - 1]
  expect(last?.key).toBe('agenda:/real/a')
  expect((last?.value as any).events).toEqual([{ start: '2026-10-29T18:30:00+01:00', title: 'Dentist' }])
  expect(w.writes.length).toBe(2)
})

test('the write goes under the real root and leaves another root alone', async ($, on) => {
  const other = { date: '2026-10-29', offsetMin: 60, updatedAt: 1, events: [], tasks: [] }
  const w = await boot($, on, '/a', '/real/a', { 'agenda:/real/b': other })
  await $.tool.call({ tool: TOOL, ...list('Karate') })
  expect(w.writes.map(x => x.key)).toEqual(['agenda:/real/a'])
})

test('a subagent call is refused and the store does not change', async ($, on) => {
  const w = await boot($, on, '/a', '/real/a')
  const r = await $.tool.call({ tool: TOOL, agentId: 'a1', ...list('Karate') })
  expect(r.deny ?? r.text).toBeDefined()
  expect(w.writes.length).toBe(0)
})

test('a stored recap returns to the atom after session.start', async ($, on) => {
  const saved = { date: '2026-10-29', offsetMin: 60, updatedAt: 1, events: [], tasks: [{ title: 'Old' }] }
  const atomWrites: any[] = []
  on('state.set', { plugin: 'agenda', key: 'recap' }, (_: any, e: any, next: any) => {
    atomWrites.push(e.value)
    return next(e)
  })
  await boot($, on, '/a', '/real/a', { 'agenda:/real/a': saved })
  expect(atomWrites.length).toBe(1)
  expect(atomWrites[0].value ?? atomWrites[0]).toEqual(saved)
})

test('the pane opens on the first write of the day and not on the second', async ($, on) => {
  const w = await boot($, on, '/a', '/real/a')
  await $.tool.call({ tool: TOOL, ...list('Karate') })
  expect(w.opened()).toBe(1)
  await $.tool.call({ tool: TOOL, ...list('Dentist') })
  expect(w.opened()).toBe(1)
})

test('a failing store.set denies the call and leaves the atom unchanged', async ($, on) => {
  const atomWrites: any[] = []
  on('state.set', { plugin: 'agenda', key: 'recap' }, (_: any, e: any, next: any) => {
    atomWrites.push(e.value)
    return next(e)
  })
  await boot($, on, '/a', '/real/a', {}, true)
  const r = await $.tool.call({ tool: TOOL, ...list('Karate') })
  expect(r.deny ?? r.text).toBeDefined()
  expect(atomWrites.length).toBe(0)
})

async function bootNoPane($: any, on: any, open: () => unknown) {
  const mem = new Map<string, unknown>()
  let sets = 0
  mock.clock(on, { now: NOW })
  on('store.get', (_: any, e: any) => ({ value: mem.get(e.key) }))
  on('store.set', (_: any, e: any) => {
    sets += 1
    mem.set(e.key, e.value)
    return { value: undefined }
  })
  on('session.root', () => ({ value: '/a' }))
  on('fs.stat', () => ({ value: { kind: 'dir', size: 0, mtimeMs: 0, isLink: false, realPath: '/a' } }))
  on('tool.register', () => ({ value: {} }))
  on('command.register', () => ({ value: { command: 'agenda' } }))
  on('ui.open', open)
  on('session.start', (_: any, e: any) => ({ cwd: e.cwd }))
  await $.session.start({ cwd: '/a', surface: null, isInteractive: false })
  return { sets: () => sets }
}

test('without a surface the tool still saves and answers', async ($, on) => {
  const w = await bootNoPane($, on, () => ({ value: { isPlaced: false, reason: 'no-surface' } }))
  const r = await $.tool.call({ tool: TOOL, ...list('Karate') })
  expect(r.deny).toBeUndefined()
  expect(String(r.result ?? r.text)).toContain('Agenda saved')
  expect(w.sets()).toBe(1)
})

test('a throwing ui.open does not touch the tool answer', async ($, on) => {
  const w = await bootNoPane($, on, () => {
    throw new Error('no ui')
  })
  const r = await $.tool.call({ tool: TOOL, ...list('Karate') })
  expect(r.deny).toBeUndefined()
  expect(String(r.result ?? r.text)).toContain('Agenda saved')
  expect(w.sets()).toBe(1)
})

// /clear empties $.state and fires no session.start while the tool stays registered:
// the next test is that state, a call with no key written.
test('after a /clear (no key, no session.start) the write derives the key again', async ($, on) => {
  const writes: string[] = []
  mock.clock(on, { now: NOW })
  on('store.get', () => ({ value: undefined }))
  on('store.set', (_: any, e: any) => {
    writes.push(e.key)
    return { value: undefined }
  })
  on('session.root', () => ({ value: '/a' }))
  on('fs.stat', () => ({ value: { kind: 'dir', size: 0, mtimeMs: 0, isLink: true, realPath: '/real/a' } }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  const r = await $.tool.call({ tool: TOOL, ...list('Karate') })
  expect(r.deny).toBeUndefined()
  expect(writes).toEqual(['agenda:/real/a'])
})

test('an unlocatable store is a clear refusal, not a crash', async ($, on) => {
  mock.clock(on, { now: NOW })
  on('session.root', () => {
    throw new Error('no root')
  })
  const r = await $.tool.call({ tool: TOOL, ...list('Karate') })
  expect(String(r.deny)).toContain('could not be located')
})

test('a failing fs.stat is a clear refusal too', async ($, on) => {
  mock.clock(on, { now: NOW })
  on('session.root', () => ({ value: '/a' }))
  on('fs.stat', () => {
    throw new Error('gone')
  })
  const r = await $.tool.call({ tool: TOOL, ...list('Karate') })
  expect(String(r.deny)).toContain('could not be located')
})
