import { expect, mock, test } from 'claude-code/testing'

const KEY = 'agenda:/a'
const PANE = {
  plugin: 'agenda',
  component: 'Pane',
  requestId: 'agenda',
  props: {
    title: 'Agenda',
    isFocused: false,
    bodyColumns: 40,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 20 },
    view: {},
  },
} as const
const SURFACES = ['terminal', 'desktop'] as const

const recap = (date: string, updatedAt: number, events: { start: string; title: string }[], tasks: { title: string }[]) => ({
  date,
  offsetMin: 60,
  updatedAt,
  events,
  tasks,
})

/** Starts the mod at `now` over a hand-made store (a Map behind store.get/set), root `/a`. */
async function boot($: any, on: any, now: number, seed: Record<string, unknown> = {}) {
  const store = new Map<string, unknown>(Object.entries(seed))
  const opens: any[] = []
  const clock = mock.clock(on, { now })
  on('store.get', (_: any, e: any) => ({ value: store.get(e.key) }))
  on('store.set', (_: any, e: any) => {
    store.set(e.key, e.value)
    return { value: undefined }
  })
  on('session.root', () => ({ value: '/a' }))
  on('fs.stat', () => ({ value: { kind: 'dir', size: 0, mtimeMs: 0, isLink: false, realPath: '/a' } }))
  on('tool.register', () => ({ value: {} }))
  on('command.register', () => ({ value: { command: 'agenda' } }))
  on('ui.open', (_: any, e: any) => {
    opens.push(e)
    return { value: { isPlaced: true } }
  })
  on('session.start', (_: any, e: any) => ({ cwd: e.cwd }))
  await $.session.start({ cwd: '/a', surface: 'terminal', isInteractive: true })
  return { store, opens, clock }
}

/** Mounts the pane afresh, runs `check` on it, unmounts. */
async function mounted($: any, surface: (typeof SURFACES)[number], check: (ui: any) => Promise<void>) {
  const ui = await $.ui.mount({ ...PANE, surface })
  await check(ui)
  await ui.unmount()
}

const text = async (ui: any, re: RegExp) => ui.find({ type: 'Text', text: re })

test('the next appointment is bold and the past one leaves at the tick', { options: { language: 'it' } }, async ($, on) => {
  const events = [
    { start: '2026-10-29T14:12:00+01:00', title: 'Call' },
    { start: '2026-10-29T18:30:00+01:00', title: 'Karate' },
  ]
  const now = Date.UTC(2026, 9, 29, 13, 10, 30)
  const { clock } = await boot($, on, now, { [KEY]: recap('2026-10-29', now, events, [{ title: 'Pay invoice' }]) })
  for (const surface of SURFACES) {
    await mounted($, surface, async ui => {
      const call = await text(ui, /Call/)
      expect(call?.text).toContain('14:12  Call')
      expect(call?.text).toContain('← prossimo')
      expect(call?.props.weight).toBe('bold')
    })
  }
  await clock.advance(150000)
  for (const surface of SURFACES) {
    await mounted($, surface, async ui => {
      expect(await text(ui, /Call/)).toBeUndefined()
      expect((await text(ui, /Karate/))?.text).toContain('← prossimo')
    })
  }
})

test('yesterday recap fades at the day start', { options: { language: 'it' } }, async ($, on) => {
  const now = Date.UTC(2026, 9, 29, 4, 59)
  const { clock } = await boot($, on, now, { [KEY]: recap('2026-10-28', now - 3600000, [], [{ title: 'Pay invoice' }]) })
  for (const surface of SURFACES) {
    await mounted($, surface, async ui => {
      expect((await text(ui, /mer 28 ott/))?.text).not.toContain('di ieri')
    })
  }
  await clock.advance(60000)
  for (const surface of SURFACES) {
    await mounted($, surface, async ui => {
      const head = await text(ui, /di ieri/)
      expect(head?.text).toContain('mer 28 ott')
      expect(head?.props.dimColor).toBe(true)
      expect((await text(ui, /Pay invoice/))?.props.dimColor).toBe(true)
    })
  }
})

test('a stale view with an event does not highlight it', { options: { language: 'it' } }, async ($, on) => {
  const now = Date.UTC(2026, 9, 29, 13, 10)
  const events = [{ start: '2026-10-28T18:30:00+01:00', title: 'Karate' }]
  await boot($, on, now, { [KEY]: recap('2026-10-28', now - 86400000, events, []) })
  for (const surface of SURFACES) {
    await mounted($, surface, async ui => {
      const row = await text(ui, /Karate/)
      expect(row?.text).not.toContain('← prossimo')
      expect(row?.props.weight).not.toBe('bold')
    })
  }
})

test('dayStart from the settings moves the switch', { options: { dayStart: '04:00', language: 'it' } }, async ($, on) => {
  const now = Date.UTC(2026, 9, 29, 2, 59)
  const { clock } = await boot($, on, now, { [KEY]: recap('2026-10-28', now - 3600000, [], [{ title: 'Pay invoice' }]) })
  for (const surface of SURFACES) {
    await mounted($, surface, async ui => {
      expect((await text(ui, /mer 28 ott/))?.text).not.toContain('di ieri')
    })
  }
  await clock.advance(60000)
  for (const surface of SURFACES) {
    await mounted($, surface, async ui => {
      expect((await text(ui, /di ieri/))?.props.dimColor).toBe(true)
    })
  }
})

test('an empty recap shows the cup', { options: { language: 'it' } }, async ($, on) => {
  const now = Date.UTC(2026, 9, 29, 13, 10)
  await boot($, on, now, { [KEY]: recap('2026-10-29', now, [], []) })
  for (const surface of SURFACES) {
    await mounted($, surface, async ui => {
      expect(await text(ui, /niente in sospeso/)).toBeDefined()
      expect((await text(ui, /aggiornato alle/))?.text).toContain('aggiornato alle 14:10')
    })
  }
})

test('tasks without visible appointments keep the today view', { options: { language: 'it' } }, async ($, on) => {
  const now = Date.UTC(2026, 9, 29, 13, 10)
  const events = [{ start: '2026-10-29T13:00:00+01:00', title: 'Standup' }]
  await boot($, on, now, { [KEY]: recap('2026-10-29', now, events, [{ title: 'Pay invoice' }]) })
  for (const surface of SURFACES) {
    await mounted($, surface, async ui => {
      expect(await text(ui, /APPUNTAMENTI/)).toBeUndefined()
      expect(await text(ui, /Standup/)).toBeUndefined()
      expect(await text(ui, /niente in sospeso/)).toBeUndefined()
      expect((await text(ui, /TASK/))?.text).toContain('TASK · 1')
      expect((await text(ui, /Pay invoice/))?.text).toContain('☐ Pay invoice')
    })
  }
})

test('a newer recap from another session replaces the one in memory, an older one does not', async ($, on) => {
  const now = Date.UTC(2026, 9, 29, 13, 10)
  const { store, opens, clock } = await boot($, on, now, {
    [KEY]: recap('2026-10-29', now - 3600000, [], [{ title: 'Mine' }]),
  })
  store.set(KEY, recap('2026-10-29', now - 3600000 + 1000, [], [{ title: 'From the other session' }]))
  await clock.advance(60000)
  expect(opens.length).toBe(0)
  for (const surface of SURFACES) {
    await mounted($, surface, async ui => {
      expect(await text(ui, /From the other session/)).toBeDefined()
    })
  }
  store.set(KEY, recap('2026-10-29', now - 7200000, [], [{ title: 'Stale write' }]))
  await clock.advance(60000)
  expect(opens.length).toBe(0)
  for (const surface of SURFACES) {
    await mounted($, surface, async ui => {
      expect(await text(ui, /From the other session/)).toBeDefined()
      expect(await text(ui, /Stale write/)).toBeUndefined()
    })
  }
})

test('a recap of a new day written elsewhere opens the pane at the tick', async ($, on) => {
  const now = Date.UTC(2026, 9, 29, 13, 10)
  const { store, opens, clock } = await boot($, on, now)
  expect(opens.length).toBe(0)
  store.set(KEY, recap('2026-10-29', now, [], [{ title: 'Pay invoice' }]))
  await clock.advance(60000)
  expect(opens.some(o => o.id === 'agenda')).toBe(true)
})

test('the English pane marks the next appointment and the stale day', async ($, on) => {
  const now = Date.UTC(2026, 9, 29, 13, 10)
  const events = [{ start: '2026-10-29T18:30:00+01:00', title: 'Karate' }]
  await boot($, on, now, { [KEY]: recap('2026-10-29', now, events, [{ title: 'Pay invoice' }]) })
  for (const surface of SURFACES) {
    await mounted($, surface, async ui => {
      expect((await text(ui, /Karate/))?.text).toContain('← next')
      expect((await text(ui, /APPOINTMENTS/))).toBeDefined()
      expect((await text(ui, /TASKS/))?.text).toContain('TASKS · 1')
    })
  }
})

test('the English pane labels yesterday', async ($, on) => {
  const now = Date.UTC(2026, 9, 29, 13, 10)
  await boot($, on, now, { [KEY]: recap('2026-10-28', now - 86400000, [], [{ title: 'Pay invoice' }]) })
  for (const surface of SURFACES) {
    await mounted($, surface, async ui => {
      expect((await text(ui, /yesterday/))?.text).toContain('Wed 28 Oct')
    })
  }
})
