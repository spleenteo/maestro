/** Every visible string of the pane, in one table per language. */
export type Labels = {
  readonly days: readonly string[]
  readonly months: readonly string[]
  readonly appointments: string
  readonly tasks: string
  readonly updatedAt: string
  readonly empty: string
  readonly next: string
  readonly yesterday: string
  readonly older: string
  readonly nothingLeft: string
  readonly paneTitle: string
  readonly rowRunning: string
  readonly rowDone: string
  readonly appointmentForms: readonly [string, string]
  readonly taskForms: readonly [string, string]
  /** Second word of `/agenda` that refreshes the pane; `update` always works. */
  readonly refreshAlias: string
  readonly argumentHint: string
  readonly usage: string
}

export const LABELS_EN: Labels = {
  days: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
  months: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
  appointments: 'APPOINTMENTS',
  tasks: 'TASKS',
  updatedAt: 'updated at',
  empty: 'No agenda yet',
  next: '← next',
  yesterday: 'yesterday',
  older: 'out of date',
  nothingLeft: 'nothing left',
  paneTitle: 'Agenda',
  rowRunning: 'Updating the agenda…',
  rowDone: 'Agenda updated',
  appointmentForms: ['appointment', 'appointments'],
  taskForms: ['task', 'tasks'],
  refreshAlias: 'update',
  argumentHint: '[update]',
  usage: 'Use /agenda to show or hide the pane, /agenda update to refresh it.',
}

export const LABELS_IT: Labels = {
  days: ['dom', 'lun', 'mar', 'mer', 'gio', 'ven', 'sab'],
  months: ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic'],
  appointments: 'APPUNTAMENTI',
  tasks: 'TASK',
  updatedAt: 'aggiornato alle',
  empty: 'Nessuna agenda per ora',
  next: '← prossimo',
  yesterday: 'di ieri',
  older: 'non aggiornata',
  nothingLeft: 'niente in sospeso',
  paneTitle: 'Agenda',
  rowRunning: "Aggiorno l'agenda…",
  rowDone: 'Agenda aggiornata',
  appointmentForms: ['appuntamento', 'appuntamenti'],
  taskForms: ['task', 'task'],
  refreshAlias: 'aggiorna',
  argumentHint: '[update|aggiorna]',
  usage: 'Use /agenda to show or hide the pane, /agenda update or /agenda aggiorna to refresh it.',
}

/** The table of the `language` setting; English for anything but `it`. */
export function labelsFor(language: unknown): Labels {
  return language === 'it' ? LABELS_IT : LABELS_EN
}
