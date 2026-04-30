---
origin: maestro
maestro_version: v2026.04.30.1
name: logbook
description: Daily logbook of sessions with the orchestrator. Use when the owner asks for "recap of today", "wrap up", "end of day", or whenever it's time to synthesize in writing what was done and what was learned. Writes to the `logbook_path` declared in preferences.
---

# Logbook

This skill writes the **daily logbook**: one note per day that synthesizes what was done during the collaboration between the owner and the orchestrator.

It is **not** the owner's personal diary — it's the shared working log.

## Where to write

The path comes from `private/preferences.md`, field `logbook_path`. If that field is empty, respond to the owner that the logbook is disabled for this instance and offer to enable it by adding a path to preferences.

If the configured folder doesn't exist yet, create it on first write.

## Note conventions

### Filename

`YYYY-MM-DD-slug-kebab-case.md` — zero padding on month and day. The `slug` summarizes the day's dominant theme in 2–4 words. If the day has no dominant theme, something like `work-log` is fine.

### Frontmatter (mandatory)

```yaml
---
tags: [tag1, tag2, tag3, ...]
description: one-line summary of what the day covered — used to decide relevance in future queries
---
```

**Tags** are the retrieval index. A daily logbook is multi-theme, so tags are the primary search lever. Rules:

- Flow-form list `[a, b, c]` — compact and readable
- Cover **all axes** touched during the day: people, areas, objects/artifacts, actions/types
- Lowercase, multi-word separated by `-` (`team-review`, not `team_review` or `TeamReview`)
- 8 to 20 tags is right for a normal working day

**Description** is the one-line summary — same pattern as skill descriptions. It enables the orchestrator (or the owner) to know what a past note was about without opening it.

### Body

1. **First body line** (after frontmatter): the date in the owner's **default language** (from preferences). For example, in Italian: `## 19 Aprile 2026`. In English: `## 19 April 2026`.
2. **H1 evocative title**: a short title capturing the day's mood or theme. Not bureaucratic. Example in Italian: `# Una giornata di manutenzione e scoperte`. In English: `# A day of partner escalations and a quiet MCP fix`.
3. **Opening paragraph**: 1–3 sentences that frame the tone of the day.
4. **Thematic sections**: `### Section title` for each block of work or discovery. One section = one theme. Don't mix.
5. **Optional closing**: if a cross-cutting lesson or reflection emerges, put it at the end as its own section.

## Tone and voice

- **Voice**: the owner's first person. Even though the work was done together with the orchestrator, the logbook is the owner's synthesis of what they wanted to do and what they are learning.
- **Tone**: narrative, reflective, concrete. Not bureaucratic, not a task list. Each section tries to tell **what happened**, say **why it's interesting**, and sometimes close with a **lesson** or observation in one sentence.
- **Language**: the owner's default language from preferences. Mix naturally with technical or work-specific English terms where that reflects how the owner actually speaks.
- **Avoid**:
  - Long bullet lists (prefer prose)
  - Promotional tone ("amazing!", "incredible!")
  - References to "we", "the orchestrator and I", "we did" — stay in first-person singular
  - Paraphrasing the memory db logs verbatim — the logbook is a *synthesis*, not a dump

## Sources for composing the note

Build the content from, in order:

1. **The memory db** (`private/memories.db`, `log` table, `date = today`) — complete list of memories, completed tasks, and emerged ideas
2. **The current conversation** — context, anecdotes, asides, reflections not in the db
3. **Only secondarily**: git commits, project-specific sources, calendar, meeting notes

The db is the starting point, not the text of the note. It needs *interpretation*.

## Procedure

1. Read the owner's `logbook_path` and `default_language` from `private/preferences.md`. If `logbook_path` is empty, respond that the logbook is disabled and stop.
2. Retrieve today's log entries:

   ```bash
   sqlite3 -header -column private/memories.db "SELECT id, title, description, tags, type, status FROM log WHERE date = date('now') ORDER BY id;"
   ```

3. Group by theme (not by type): multiple entries can merge into a single section if they talk about the same topic.
4. Pick a thread for the H1 if the day has one; otherwise use a neutral title like `# Work log`.
5. Extract tags — from entries plus conversational asides — and draft a one-line `description`.
6. Write the note at `<logbook_path>/YYYY-MM-DD-slug.md` in the owner's default language.
7. Confirm to the owner: path written + tags chosen.

**If a note for today already exists**, do not overwrite. Ask the owner whether to update it (append a new section) or create a second note with a different slug.

## When to trigger

The owner usually invokes this skill explicitly with phrases like:

- "Recap of today"
- "Wrap up the day"
- "Update the logbook"
- "End of day"
- "Let's take stock"

The skill may also be suggested by the orchestrator when the conversation reaches a natural closing point and the day has produced enough material to summarize — but only as a suggestion, never autonomously.
