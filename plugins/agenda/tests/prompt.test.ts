import { expect, mock, test } from 'claude-code/testing'

import { LABELS_EN, LABELS_IT } from '../hooks/labels'
import { REFRESH_PROMPT, REFRESHING, REMINDER } from '../hooks/prompt'

const TOOL = 'mcp__agenda__agenda_set'
const NOW = Date.UTC(2026, 9, 29, 13, 10) // Thursday 14:10 at +01:00
const INTRO = { id: 'intro', text: 'Base.', scope: 'shared' }

/** Starts the mod at `now` over a hand-made store (a Map behind store.get/set), root `/a`. */
async function boot($: any, on: any, now: number, seed: Record<string, unknown> = {}, submit?: (e: any) => void) {
  const store = new Map<string, unknown>(Object.entries(seed))
  const registered: any[] = []
  const commands: any[] = []
  const opens: any[] = []
  const closes: any[] = []
  const clock = mock.clock(on, { now })
  on('prompt.compose', () => ({ sections: [INTRO] }))
  if (submit) {
    on('prompt.submit', (_: any, e: any) => {
      submit(e)
      return { text: e.text }
    })
  }
  on('store.get', (_: any, e: any) => ({ value: store.get(e.key) }))
  on('store.set', (_: any, e: any) => {
    store.set(e.key, e.value)
    return { value: undefined }
  })
  on('session.root', () => ({ value: '/a' }))
  on('fs.stat', () => ({ value: { kind: 'dir', size: 0, mtimeMs: 0, isLink: false, realPath: '/a' } }))
  on('tool.register', (_: any, e: any) => {
    registered.push(e)
    return { value: {} }
  })
  on('command.register', (_: any, e: any) => {
    commands.push(e)
    return { value: { command: 'agenda' } }
  })
  on('ui.open', (_: any, e: any) => {
    opens.push(e)
    return { value: { isPlaced: true } }
  })
  on('ui.close', (_: any, e: any) => {
    closes.push(e)
    return { value: undefined }
  })
  on('ui.panes', () => ({ value: [] }))
  on('session.start', (_: any, e: any) => ({ cwd: e.cwd }))
  await $.session.start({ cwd: '/a', surface: 'terminal', isInteractive: true })
  return { store, registered, commands, clock, opens, closes }
}

const compose = ($: any, tools: string[]) =>
  $.prompt.compose({ model: 'm', promptModel: 'm', surfaces: ['terminal'], tools, outputStyle: null, traits: [] })

const call = (events: { start: string; title: string }[], tasks: { title: string }[]) => ({
  tool: TOOL as typeof TOOL,
  date: '2026-10-29',
  events,
  tasks,
})

test('an empty store leaves the prompt as it was', async ($, on) => {
  await boot($, on, NOW)
  const r = await compose($, [TOOL])
  expect(r.sections).toEqual([INTRO])
})

test('a recap of the lived day adds one fixed line at the end', async ($, on) => {
  await boot($, on, NOW)
  await $.tool.call(call([{ start: '2026-10-29T18:30:00+01:00', title: 'Karate' }], [{ title: 'Pay invoice' }]))
  const first = await compose($, [TOOL])
  expect(first.sections[0]).toEqual(INTRO)
  expect(first.sections[first.sections.length - 1]).toEqual({ id: 'agenda:reminder', text: REMINDER, scope: 'session' })
  await $.tool.call(call([], [{ title: 'A' }, { title: 'B' }]))
  expect(await compose($, [TOOL])).toEqual(first)
})

test('a request without the tool carries no line', async ($, on) => {
  await boot($, on, NOW)
  await $.tool.call(call([], [{ title: 'Pay invoice' }]))
  const r = await compose($, ['Read'])
  expect(r.sections).toEqual([INTRO])
})

test('the line goes away when the lived day passes dayStart', async ($, on) => {
  const now = Date.UTC(2026, 9, 29, 4, 59) // 05:59 local
  const seed = {
    'agenda:/a': { date: '2026-10-28', offsetMin: 60, updatedAt: now - 3600000, events: [], tasks: [{ title: 'Pay invoice' }] },
  }
  const { clock } = await boot($, on, now, seed)
  expect((await compose($, [TOOL])).sections.map((s: any) => s.id)).toEqual(['intro', 'agenda:reminder'])
  await clock.advance(60000)
  expect((await compose($, [TOOL])).sections).toEqual([INTRO])
})

test('the reminder names the tool and carries no digits', () => {
  expect(REMINDER).toContain(TOOL)
  expect(/\d/.test(REMINDER)).toBe(false)
})

test('the tool schema says when the lived day starts', async ($, on) => {
  const { registered } = await boot($, on, NOW)
  expect(registered.find(r => r.name === 'agenda_set').inputSchema.properties.date.description).toContain('before 06:00 local')
})

test('the tool schema follows the dayStart option', { options: { dayStart: '04:30' } }, async ($, on) => {
  const { registered } = await boot($, on, NOW)
  expect(registered.find(r => r.name === 'agenda_set').inputSchema.properties.date.description).toContain('before 04:30 local')
})

const run = ($: any, args: string) =>
  $.command.run({ command: 'agenda', args, origin: 'user', presentation: 'text' })

function submitSpy() {
  let seen: any
  let resolve!: (e: any) => void
  const got = new Promise<any>(r => (resolve = r))
  return { got, fn: (e: any) => ((seen = e), resolve(e)), seen: () => seen }
}

for (const args of ['update', 'aggiorna', ' Update ']) {
  test(`/agenda ${JSON.stringify(args)} answers at once and submits the refresh as the user`, { options: { language: 'it' } }, async ($, on) => {
    const spy = submitSpy()
    const { opens, closes, clock } = await boot($, on, NOW, {}, spy.fn)
    const r = await run($, args)
    expect(r.text).toBe(REFRESHING)
    await clock.advance(1)
    const e = await spy.got
    expect(e.text).toBe(REFRESH_PROMPT)
    expect(e.origin?.asUser ?? e.asUser).toBe(true)
    expect(opens).toEqual([])
    expect(closes).toEqual([])
  })
}

test('a failing prompt.submit leaves the answer alone', async ($, on) => {
  const spy = submitSpy()
  const { clock } = await boot($, on, NOW, {}, e => {
    spy.fn(e)
    throw new Error('busy')
  })
  const r = await run($, 'update')
  await clock.advance(1)
  await spy.got
  expect(r.text).toBe(REFRESHING)
})

test('an unknown argument answers the usage and leaves the pane alone', { options: { language: 'it' } }, async ($, on) => {
  const { opens, closes } = await boot($, on, NOW)
  const r = await run($, 'boh')
  expect(r.text).toBe(LABELS_IT.usage)
  expect(opens).toEqual([])
  expect(closes).toEqual([])
})

test('under the default options update refreshes', async ($, on) => {
  const spy = submitSpy()
  const { clock } = await boot($, on, NOW, {}, spy.fn)
  const r = await run($, 'update')
  expect(r.text).toBe(REFRESHING)
  await clock.advance(1)
  expect((await spy.got).text).toBe(REFRESH_PROMPT)
})

test('under the default options aggiorna and unknown arguments answer the English usage', async ($, on) => {
  const { opens, closes } = await boot($, on, NOW)
  for (const args of ['aggiorna', 'boh']) {
    expect((await run($, args)).text).toBe(LABELS_EN.usage)
  }
  expect(opens).toEqual([])
  expect(closes).toEqual([])
})

test('the argument hint offers only update under the default options', async ($, on) => {
  const { commands } = await boot($, on, NOW)
  expect(commands.map(c => c.argumentHint)).toEqual(['[update]'])
})

test('the argument hint offers both words in Italian', { options: { language: 'it' } }, async ($, on) => {
  const { commands } = await boot($, on, NOW)
  expect(commands.map(c => c.argumentHint)).toEqual(['[update|aggiorna]'])
})
