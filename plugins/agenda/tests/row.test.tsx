import { expect, test } from 'claude-code/testing'

const TOOL = 'mcp__agenda__agenda_set'
const SURFACES = ['terminal', 'desktop'] as const

/** The engine's own rows, answered before the mod's hooks are asked. */
function base(on: any) {
  on('ui.render', { component: 'ToolUse' }, ($h: any, e: any) => {
    const { Text } = $h.ui.resolve(e)
    return <Text>ENGINE ROW</Text>
  })
  on('ui.render', { component: 'ToolResult' }, ($h: any, e: any) => {
    const { Text } = $h.ui.resolve(e)
    return <Text>ENGINE RESULT</Text>
  })
}

const rows = (n: number) => Array.from({ length: n }, (_, i) => ({ title: 'T' + i }))
const events = (n: number) => Array.from({ length: n }, (_, i) => ({ start: `2026-10-29T1${i}:00:00+01:00`, title: 'E' + i }))

const use = (surface: (typeof SURFACES)[number], over: Record<string, unknown>) =>
  ({
    plugin: 'agenda',
    surface,
    component: 'ToolUse',
    requestId: 'tu1',
    props: {
      tool_use_id: 'tu1',
      tool: TOOL,
      input: { date: '2026-10-29' },
      isRunning: false,
      isErrored: false,
      isInterrupted: false,
      isExpanded: false,
      output: 'Agenda saved: 0 events, 0 tasks.',
      ...over,
    },
  }) as const

const result = (surface: (typeof SURFACES)[number], over: Record<string, unknown>) =>
  ({
    plugin: 'agenda',
    surface,
    component: 'ToolResult',
    requestId: 'tu1',
    props: {
      tool_use_id: 'tu1',
      tool: TOOL,
      output: 'Agenda saved: 2 events, 9 tasks.',
      isErrored: false,
      isExpanded: false,
      ...over,
    },
  }) as const

test('a running call is one dim line', { options: { language: 'it' } }, async ($, on) => {
  base(on)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount(use(surface, { isRunning: true, output: undefined }))
    const texts = await ui.findAll({ type: 'Text' })
    expect(texts).toHaveLength(1)
    expect(texts[0]?.text).toBe("☀ Aggiorno l'agenda…")
    await ui.unmount()
  }
})

test('a finished call says how many appointments and tasks', { options: { language: 'it' } }, async ($, on) => {
  base(on)
  const cases: [unknown, string][] = [
    [{ date: '2026-10-29', events: events(2), tasks: rows(9) }, '☀ Agenda aggiornata · 2 appuntamenti, 9 task'],
    [{ date: '2026-10-29', events: events(1), tasks: rows(1) }, '☀ Agenda aggiornata · 1 appuntamento, 1 task'],
    [{ date: '2026-10-29' }, '☀ Agenda aggiornata · 0 appuntamenti, 0 task'],
  ]
  for (const surface of SURFACES) {
    for (const [input, text] of cases) {
      const ui = await $.ui.mount(use(surface, { input }))
      expect((await ui.findAll({ type: 'Text' })).map(t => t.text)).toEqual([text])
      await ui.unmount()
    }
  }
})

test('a malformed input counts as nothing', { options: { language: 'it' } }, async ($, on) => {
  base(on)
  for (const surface of SURFACES) {
    for (const input of [{ events: 'x', tasks: null }, null, 'text']) {
      const ui = await $.ui.mount(use(surface, { input }))
      expect((await ui.findAll({ type: 'Text' })).map(t => t.text)).toEqual(['☀ Agenda aggiornata · 0 appuntamenti, 0 task'])
      await ui.unmount()
    }
  }
})

test('under the default options the row is English', async ($, on) => {
  base(on)
  const cases: [unknown, string][] = [
    [{ date: '2026-10-29', events: events(2), tasks: rows(9) }, '☀ Agenda updated · 2 appointments, 9 tasks'],
    [{ date: '2026-10-29', events: events(1), tasks: rows(1) }, '☀ Agenda updated · 1 appointment, 1 task'],
  ]
  for (const surface of SURFACES) {
    for (const [input, text] of cases) {
      const ui = await $.ui.mount(use(surface, { input }))
      expect((await ui.findAll({ type: 'Text' })).map(t => t.text)).toEqual([text])
      await ui.unmount()
    }
    const running = await $.ui.mount(use(surface, { isRunning: true, output: undefined }))
    expect((await running.findAll({ type: 'Text' })).map(t => t.text)).toEqual(['☀ Updating the agenda…'])
    await running.unmount()
  }
})

test('expanded, errored or interrupted calls keep the engine row', async ($, on) => {
  base(on)
  for (const surface of SURFACES) {
    for (const over of [{ isExpanded: true }, { isErrored: true }, { isInterrupted: true }]) {
      const ui = await $.ui.mount(use(surface, over))
      expect((await ui.find({ type: 'Text' }))?.text).toBe('ENGINE ROW')
      await ui.unmount()
    }
  }
})

test('the row of another tool is the engine row', async ($, on) => {
  base(on)
  for (const surface of SURFACES) {
    const ui = await $.ui.mount(use(surface, { tool: 'Read' }))
    expect((await ui.find({ type: 'Text' }))?.text).toBe('ENGINE ROW')
    await ui.unmount()
  }
})

test('the result under the row draws nothing unless expanded or errored', async ($, on) => {
  base(on)
  for (const surface of SURFACES) {
    const quiet = await $.ui.mount(result(surface, {}))
    expect(await quiet.find({ type: 'Text' })).toBeUndefined()
    await quiet.unmount()
    for (const over of [{ isExpanded: true }, { isErrored: true }, { tool: 'Read' }]) {
      const ui = await $.ui.mount(result(surface, over))
      expect((await ui.find({ type: 'Text' }))?.text).toBe('ENGINE RESULT')
      await ui.unmount()
    }
  }
})
