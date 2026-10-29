import type { AgendaRecap } from '../types'
import type { Labels } from './labels'
import { dayLabel, localParts, wallTime } from './time'
import type { AgendaView } from './view'

const CUP = ['   ( (', '    ) )', '  ........', '  |      |]', '  \\      /', "   `----'"]

/** Draws the agenda pane; `ui` is the resolved set of Box and Text. */
export function renderAgenda(ui: { Box: any; Text: any }, recap: AgendaRecap | null, view: AgendaView | null, labels: Labels) {
  const { Box, Text } = ui
  if (recap === null || view === null) return <Text dimColor>{labels.empty}</Text>

  const stale = view.kind === 'stale'
  const dim = stale
  const heading = `☀ ${dayLabel(recap.date, labels)}${stale ? ` · ${view.label}` : ''}`
  const events = view.kind === 'today' ? view.events : stale ? recap.events : []
  const tasks = view.kind === 'today' ? view.tasks : stale ? recap.tasks : []
  const highlight = view.kind === 'today'

  return (
    <Box flexDirection="column">
      <Text dimColor={dim}>{heading}</Text>
      <Text dimColor>
        {labels.updatedAt} {localParts(recap.updatedAt, recap.offsetMin).time}
      </Text>
      <Text> </Text>
      {view.kind === 'empty' && (
        <Box flexDirection="column">
          {CUP.map(line => (
            <Text>{line}</Text>
          ))}
          <Text> </Text>
          <Text>{labels.nothingLeft}</Text>
        </Box>
      )}
      {events.length > 0 && (
        <Box flexDirection="column">
          <Text dimColor={dim}>{labels.appointments}</Text>
          {events.map((event, i) =>
            highlight && i === 0 ? (
              <Text weight="bold">{`${wallTime(event.start)}  ${event.title}  ${labels.next}`}</Text>
            ) : (
              <Text dimColor={dim}>{`${wallTime(event.start)}  ${event.title}`}</Text>
            ),
          )}
          {tasks.length > 0 && <Text> </Text>}
        </Box>
      )}
      {tasks.length > 0 && (
        <Box flexDirection="column">
          <Text dimColor={dim}>{`${labels.tasks} · ${tasks.length}`}</Text>
          {tasks.map(task => (
            <Text dimColor={dim}>{`☐ ${task.title}`}</Text>
          ))}
        </Box>
      )}
    </Box>
  )
}
