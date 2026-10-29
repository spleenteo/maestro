// Fixed texts the model reads. English, so the mod stays portable.
export const REMINDER_ID = 'agenda:reminder'

export const REMINDER =
  "The agenda pane shows today's appointments and open tasks. " +
  'When you create, close, move or cancel a task or an appointment of today, ' +
  'call mcp__agenda__agenda_set with the whole updated list. ' +
  "If today's full list is not in this conversation, gather it again as for a question about today's plan, then call it."

export const REFRESH_PROMPT =
  "Refresh today's agenda: gather today's appointments and open tasks again as for a question about today's plan, " +
  'then save the whole list with mcp__agenda__agenda_set.'

export const REFRESHING = "Refreshing today's agenda."

export const OPENED = 'Agenda pane opened.'

export const CLOSED = 'Agenda pane closed.'
