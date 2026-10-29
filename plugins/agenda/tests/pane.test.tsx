import { expect, mock, test } from 'claude-code/testing'

import { CLOSED, OPENED } from '../hooks/prompt'

const NOW = Date.UTC(2026, 9, 29, 13, 10)
const RECAP = {
  date: '2026-10-29',
  offsetMin: 60,
  updatedAt: NOW,
  events: [{ start: '2026-10-29T18:30:00+01:00', title: 'Karate' }],
  tasks: [{ title: 'Pay invoice' }, { title: 'Call Anna' }],
}
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

async function boot($: any, on: any, panes: any[]) {
  const calls: string[] = []
  mock.clock(on, { now: NOW })
  on('store.get', () => ({ value: RECAP }))
  on('session.root', () => ({ value: '/a' }))
  on('fs.stat', () => ({ value: { kind: 'dir', size: 0, mtimeMs: 0, isLink: false, realPath: '/a' } }))
  on('tool.register', () => ({ value: {} }))
  on('command.register', () => ({ value: { command: 'agenda' } }))
  on('ui.panes', () => ({ value: panes }))
  on('ui.open', () => {
    calls.push('open')
    return { value: { isPlaced: true } }
  })
  on('ui.close', () => {
    calls.push('close')
    return { value: undefined }
  })
  on('session.start', (_: any, e: any) => ({ cwd: e.cwd }))
  await $.session.start({ cwd: '/a', surface: 'terminal', isInteractive: true })
  return calls
}

test('the pane shows the recap, on terminal and desktop', { options: { language: 'it' } }, async ($, on) => {
  await boot($, on, [])
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect((await ui.find({ type: 'Text', text: /gio 29 ott/ }))?.text).toContain('gio 29 ott')
    expect((await ui.find({ type: 'Text', text: /aggiornato alle/ }))?.text).toContain('aggiornato alle 14:10')
    expect((await ui.find({ type: 'Text', text: /Karate/ }))?.text).toContain('18:30  Karate')
    expect((await ui.find({ type: 'Text', text: /TASK/ }))?.text).toContain('TASK · 2')
    await ui.unmount()
  }
})

test('without a recap the pane says so', { options: { language: 'it' } }, async ($, on) => {
  on('state.get', () => ({ value: { value: null, version: 1 } }))
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text' }))?.text).toBe('Nessuna agenda per ora')
  await ui.unmount()
})

test('under the default options the pane is English', async ($, on) => {
  await boot($, on, [])
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect((await ui.find({ type: 'Text', text: /Thu 29 Oct/ }))?.text).toContain('Thu 29 Oct')
    expect((await ui.find({ type: 'Text', text: /updated at/ }))?.text).toContain('updated at 14:10')
    await ui.unmount()
  }
})

test('without a recap the English pane says so', async ($, on) => {
  on('state.get', () => ({ value: { value: null, version: 1 } }))
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect((await ui.find({ type: 'Text' }))?.text).toBe('No agenda yet')
  await ui.unmount()
})

const pane = (isPlaced: boolean, isShown: boolean) => [{ id: 'agenda', title: 'Agenda', isPlaced, isShown }]

async function run($: any, on: any, panes: any[]) {
  const calls = await boot($, on, panes)
  const out = await $.command.run({ command: 'agenda', args: '', origin: 'user', presentation: 'text' })
  return { calls, text: out.text }
}

test('/agenda closes a placed and shown pane', async ($, on) => {
  const { calls, text } = await run($, on, pane(true, true))
  expect(calls).toEqual(['close'])
  expect(text).toBe(CLOSED)
})

test('/agenda opens a placed pane that is not shown', async ($, on) => {
  const { calls, text } = await run($, on, pane(true, false))
  expect(calls).toEqual(['open'])
  expect(text).toBe(OPENED)
})

test('/agenda opens a pane that is not placed', async ($, on) => {
  const { calls, text } = await run($, on, pane(false, false))
  expect(calls).toEqual(['open'])
  expect(text).toBe(OPENED)
})
