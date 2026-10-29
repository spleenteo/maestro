import type { Labels } from './labels'

const isObject = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null

/** How many appointments and tasks a call of agenda_set sent; 0 for what is missing. */
export function rowCounts(input: unknown): { events: number; tasks: number } {
  if (!isObject(input)) return { events: 0, tasks: 0 }
  return {
    events: Array.isArray(input.events) ? input.events.length : 0,
    tasks: Array.isArray(input.tasks) ? input.tasks.length : 0,
  }
}

const plural = (n: number, forms: readonly [string, string]) => `${n} ${n === 1 ? forms[0] : forms[1]}`

/** Draws the one-line transcript row of an agenda_set call; `ui` is the resolved set of Box and Text. */
export function renderToolRow(ui: { Box: any; Text: any }, props: { isRunning: boolean; input: unknown }, labels: Labels) {
  const { Text } = ui
  if (props.isRunning) return <Text dimColor>{`☀ ${labels.rowRunning}`}</Text>
  const { events, tasks } = rowCounts(props.input)
  return (
    <Text>{`☀ ${labels.rowDone} · ${plural(events, labels.appointmentForms)}, ${plural(tasks, labels.taskForms)}`}</Text>
  )
}
