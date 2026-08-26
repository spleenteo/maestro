---
origin: maestro
maestro_version: v2026.08.26.1
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

Follow the full markdown discipline in `howto/08-markdown-discipline.md`: quote YAML values containing `: `/`# `/leading special characters, and use `[[Wikilinks]]` when referencing other notes in an Obsidian vault.

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

1. **The memory db** (`private/memories.db`, `log` table, `date = target day`) — complete list of memories, completed tasks, and emerged ideas. It's the one source that already spans every session, because all sessions in the same working directory write to the same file.
2. **The current conversation** — context, anecdotes, asides, reflections not in the db
3. **The other sessions of the target day** (`bin/session-digest`) — the owner may have worked in parallel across several sessions. Their memories are already in the db; the thread of the discussion is only in their transcripts. See step 5 of the procedure.
4. **Only secondarily**: git commits, project-specific sources, calendar, meeting notes

The db is the starting point, not the text of the note. It needs *interpretation*.

## Procedure

1. Read the owner's `logbook_path` and `default_language` from `private/preferences.md`. If `logbook_path` is empty, respond that the logbook is disabled and stop.

2. **Pre-flush the warm task channel** — if `preferences.md` declares a `## Warm task channel` block with `channel != none`, invoke the skill named there and run its `## Garbage Collector` section before going on. Writing the logbook is an end-of-session trigger: the flush moves the tasks closed in the warm layer into `memories.db` dated to the target day, so they reach the note instead of staying behind in the task manager. Pattern: `howto/07-warm-task-channel.md`.

   - Announce in one line (`📦 archived N tasks: …`) only when `N > 0`.
   - Stay silent when the GC is silent (nothing closed, or less than an hour since the last flush).
   - If the channel is unreachable or the GC fails, **don't block the logbook**: carry on and report it as a minor note at the end.
   - No block, or `channel: none`, means skip this step.

3. **Decide which day you are documenting** — the target day is not always `date('now')`. It follows the same early-morning rule that governs every write to `memories.db`.

   - **Invoked in the small hours** (before 06:00 local) **and** no logbook exists yet for the previous day → the target day is the **previous day**. The working session that was lived is one, and it does not split at the change of solar date: it started the evening before and is running into the night. Collecting only the hour or two past midnight would produce a partial note.
   - **Any other case** (from 06:00 on, or a logbook for the previous day already exists) → the target day is today.
   - When in doubt, ask the owner "Am I writing the logbook for <day X>?" before going on.

4. Retrieve the target day's log entries:

   ```bash
   bin/mem today
   ```

   For a target day other than today, or without the CLI:

   ```bash
   sqlite3 -header -column private/memories.db "SELECT id, title, description, tags, type, status FROM log WHERE date = date('now','-1 day') ORDER BY id;"
   ```

   **In the early-morning case, include the entries of the night that follows** (those dated today, up to the moment of the call): they are usually the tail of the same session and belong to the previous day's note.

   ```bash
   sqlite3 -header -column private/memories.db "SELECT id, title, description, tags, type, status FROM log WHERE date IN (date('now','-1 day'), date('now')) ORDER BY date, id;"
   ```

5. **Pick up the threads of the parallel sessions** — the owner may have worked across several sessions the same day (agent view). Their memories are already in the db by construction; what's missing is the thread of each discussion, which lives only in its transcript.

   ```bash
   bin/session-digest                      # today
   bin/session-digest --date yesterday     # when the target day is the previous one
   bin/session-digest --date 2026-08-25    # explicit day
   ```

   It returns, for every session with activity that day, the name the owner gave it and the messages they typed, in chronological order. The assistant's replies stay out (they run to megabytes, and the owner's messages are enough to reconstruct what was discussed).

   How to use it:

   - **Read the digest before grouping by theme**: it carries the threads the db doesn't record, and session names are often the day's themes already.
   - **The db stays the source of facts.** The digest adds context and nuance, and surfaces open threads whose outcome nobody recorded. When something substantial in the digest is missing from the db, save it as a memory before writing the note, so the next search finds it.
   - **The current session shows up in the digest too.** You already have its context in front of you: use the digest to check it says nothing more, not to reread it.
   - **Sessions sharing a title** with overlapping messages are one conversation seen through two transcripts (backgrounded or forked). The script merges them; if a trace survives, treat them as one.
   - If the script is missing or errors out, **don't block the logbook**: compose the note from the db and the current conversation, and say so as a minor note at the end.

6. Group by theme (not by type): multiple entries can merge into a single section if they talk about the same topic.
7. Pick a thread for the H1 if the day has one; otherwise use a neutral title like `# Work log`.
8. Extract tags — from entries, conversational asides, and the parallel sessions — and draft a one-line `description`.
9. Write the note at `<logbook_path>/YYYY-MM-DD-slug.md`, dated to the **target day** (the day being documented, not the day of writing), in the owner's default language.
10. Confirm to the owner: path written + tags chosen + the **target day**, when it differs from today + **how many sessions fed into it**, when more than one.

**If a note for the target day already exists**, do not overwrite. Ask the owner whether to update it (append a new section) or create a second note with a different slug.

## Writing register

The note is prose for a human reader, so it follows the writing register: no meta-commentary on the text itself, no sycophantic concessions, no negative parallelism in any variant ("it's not X, it's Y", "non è X, è Y", and the tailing "Y, not X"), no em dash used as a pause, no bold as rhetorical emphasis (structural labels stay), no rhythmic triads, no judgment as tone of voice.

Prohibition 7 is the one a logbook trips over most, because a daily note invites a closing verdict. "Solid progress on the parser" goes; "the parser now handles empty input, the timeout is still missing" stays. A reflective closing section is welcome when it carries an observation, not when it carries encouragement.

Condensed rules: `CLAUDE.md` → `## Writing register`. Full reference: `howto/10-writing-register.md`.

Before writing the file, pass the finished text through the `writing-register` skill, then write it. Delivery is silent: confirm the path and the tags to the owner, without narrating what the pass changed.

## When to trigger

The owner usually invokes this skill explicitly with phrases like:

- "Recap of today"
- "Wrap up the day"
- "Update the logbook"
- "End of day"
- "Let's take stock"

The skill may also be suggested by the orchestrator when the conversation reaches a natural closing point and the day has produced enough material to summarize — but only as a suggestion, never autonomously.
