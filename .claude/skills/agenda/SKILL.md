---
origin: maestro
maestro_version: v2026.10.01.3
name: agenda
description: "Today's plan, in any language: use for any question, in any language, about today's plan or what is left to do today, and to refresh today's agenda. The single entry point for that question: asks the scheduler agent for today's tasks and appointments and saves them to the agenda pane with mcp__agenda__agenda_set. Not for other days."
user-invocable: false
tags: [agenda, today, tasks, appointments, pane, scheduler]
---

# Agenda

Answers "what is on today" and keeps the agenda pane in step with the answer.

## Steps

1. Pane check. When `mcp__agenda__agenda_set` is not among the session's tools, take the local date from `date '+%F'`, ask `scheduler` with the request of the scheduler step below, answer in chat as the reply step below says, and stop. Only when `private/preferences.md` exists in the working directory, add one line saying the pane needs the `agenda` plugin (`claude plugin install agenda@maestro --scope project`, run from the instance root). Elsewhere, add no hint.
2. Lived day. The hour the day starts at is in the description of the `date` field of `mcp__agenda__agenda_set`. `date '+%F %H:%M %z'` gives local date, time and offset. If the local time is earlier than that hour, the day is the previous one (`date -v-1d +%F` on macOS, `date -d yesterday +%F` elsewhere). If no hour is found there, use the local date from `date`.
3. Call the `scheduler` agent with the Agent tool and this request, with the lived day filled in:

   > prospective_today for <lived day>. Return two blocks. `APPOINTMENTS`: that day's appointments that have a time, one per line as `HH:MM title`. `TASKS`: open tasks planned for that day, one title per line. Leave out reminders of future deadlines not planned for that day, done items, routines and notes. Plain titles, no source tags, flags or areas.

4. Map the answer as is. Drop any trailing `[source]` tag or `⚠️` note from a line. Each `APPOINTMENTS` line becomes `{ start, title }` with `start` = `<day>T<HH:MM>:00<offset>`, the offset from the lived day step (`date` gives `+0100`; write it `+01:00`). Each `TASKS` line becomes `{ title }`. An empty block becomes `[]`. Send every appointment that has a time: the pane hides the past ones.
5. Call `mcp__agenda__agenda_set` with `{ date, events, tasks }`.
6. Reply in chat, in the language of the conversation. To a question about today's plan: short, appointments with their time, then tasks. To a refresh request: one short sentence saying the agenda is updated, since the pane shows it.

## Keeping the pane current

Only when `mcp__agenda__agenda_set` is available; otherwise do nothing here. When a task or an appointment of today is created, closed, moved or cancelled, call `mcp__agenda__agenda_set` again with the whole list, updated with the change, without `scheduler`. If the list is not in the conversation, run the steps above from the start. Either way, confirm the change in one short sentence, without repeating the list.

## Never

- Read sources yourself or interpret a task manager's fields: `scheduler` does that.
- Call the tool from a subagent: it refuses them, so this skill runs in the main conversation.
