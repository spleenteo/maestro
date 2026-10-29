export type AgendaEvent = {
  /** ISO 8601 with the local offset, e.g. 2026-10-29T18:30:00+01:00. */
  start: string
  title: string
}

export type AgendaTask = { title: string }

export type AgendaRecap = {
  /** Local day, YYYY-MM-DD. */
  date: string
  /** Local offset in minutes, taken from the first event start or the environment. */
  offsetMin: number
  /** Instant of the save, epoch milliseconds. */
  updatedAt: number
  /** Sorted by instant. */
  events: AgendaEvent[]
  tasks: AgendaTask[]
}

declare module 'claude-code' {
  interface PluginState {
    agenda: {
      recap: Shaped<AgendaRecap | null>
      storeKey: string
      now: Shaped<number>
    }
  }
}
