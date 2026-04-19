---
tags: [howto, memory, integrations, mcp, sqlite, basecamp, calendar, tasks]
description: How the memory db works, how to query and extend it, and how to integrate external tools (Basecamp, reminders, Google Calendar) without losing the orchestrator's single source of truth.
---

# How to interact with memory and integrations

Memory is the engine of the orchestrator — the log that accumulates events, tasks, and ideas across all your sessions. This document covers how it works, how to query it, how to extend it, and how to integrate external tools without fragmenting the source of truth.

## Model

One SQLite database, one table:

```
private/memories.db
└── log
```

The `log` table has rows of **three types**:

| Type | Purpose | Lifecycle |
|---|---|---|
| `memory` | Events, completed work, things that happened | No lifecycle — it's a fact, `status` stays NULL |
| `task` | Things to do, commitments | `todo` → `in_progress` → `done` (or `cancelled`) |
| `idea` | Things to park for later | `open` → `done` (when realized) or `dismissed` |

Columns: `id`, `date`, `title`, `description`, `tags`, `type`, `status`, `due_date`, `completed_date`, `priority`. The full schema is in `CLAUDE.md` → `## Memory` → "Schema (reference)".

## Proactive writes

The orchestrator writes to `log` on its own initiative when it detects signals (see `CLAUDE.md` → `## Memory` → "Proactive triggers"). Examples:

- You close a topic with "ok", "thanks", "done" → candidate `memory` entry
- You say "I need to...", "remind me..." → `task`
- You say "we could...", "someday I'd like..." → `idea`
- Work is completed in the session → `memory`

**Every write is announced**, always. Format:

```
📝 saved: "<title>" [tag1,tag2] (<type>)
✏️ updated #<id>: <what changed>
```

If you don't see the announcement, nothing was written. If you see one and it's wrong, tell the orchestrator to correct it in place.

## Tags — the retrieval index

Tags are how you find things later. The convention is **multi-dimensional**: one row should have tags across all relevant axes (people, areas, objects, actions). Example:

> **Title**: "Fixed waivers bug in production"
> **Tags**: `waivers,production,bug,fix,api,faber,datocms`

Now you can retrieve this entry by searching for `waivers`, `bug`, `faber`, or `datocms` — any angle works.

Rules:

- Lowercase, multi-word separated by `-` (`partner-program`, not `PartnerProgram`)
- 3–8 tags per row is typical, 1 is too few, 15+ is noise
- Stable vocabulary: prefer existing tags over inventing new ones, the orchestrator can query with `rg`-like patterns on tags

## Querying

Common queries (all documented in `CLAUDE.md` → `## Memory` → "Reports"):

- **Today** — `WHERE date = date('now')`
- **This week** — `WHERE date >= date('now','-7 days')`
- **Open tasks** — `WHERE type = 'task' AND status IN ('todo','in_progress') ORDER BY priority, due_date`
- **Open ideas** — `WHERE type = 'idea' AND status = 'open'`
- **Everything tagged X** — `WHERE tags LIKE '%<keyword>%'`
- **Cross-type by person** — `WHERE tags LIKE '%<name>%'`

Just ask the orchestrator in natural language: *"what did I do yesterday?"*, *"open tasks for the partner program"*, *"show me everything about the waivers feature"*.

## Extending the db

The single-table model is deliberately simple. Two ways to extend:

### Option A — add columns to `log`

If your orchestrator's domain needs a field consistently (e.g., `project_id` for cross-referencing with an external system), add a column:

```bash
sqlite3 private/memories.db "ALTER TABLE log ADD COLUMN project_id TEXT;"
```

Update `CLAUDE.md` → `## Memory` → "Schema (reference)" to document the new column. That's it.

### Option B — add a new table for a distinct use case

If your domain has data with a genuinely different shape (e.g., time entries, invoices, meeting recordings), add a new table:

```bash
sqlite3 private/memories.db "CREATE TABLE meetings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  duration_min INTEGER,
  attendees TEXT,  -- comma-separated
  subject TEXT NOT NULL,
  transcript_path TEXT,
  tags TEXT
);"
```

Same file, same db, new table. Document it in CLAUDE.md so the orchestrator knows it exists and the announcement rule applies to its writes too.

## Integrating external tools

The memory db is the **orchestrator's own log**. It's not a replacement for dedicated tools — it's the index that ties them together. The right pattern: keep each external tool authoritative for its domain, use memory as a reference.

### Basecamp todos / messages

Basecamp is authoritative for project todos and team communication. Your memory db should:

- Log events when you interact with Basecamp ("wrote message X", "closed todo Y")
- Not try to mirror Basecamp's data

Keep the Basecamp account/project in preferences (see `03-customization.md` → Integrations) and let the orchestrator invoke the Basecamp CLI (`bc3` or similar) when needed. Memory captures that something happened, Basecamp stores the content.

### Google Calendar

Calendar is authoritative for events and commitments with time. The orchestrator can read the calendar via an MCP server (e.g., `google-calendar`) and:

- Reference calendar events in memory entries: "Met with <Name> (calendar id: abc123)"
- Propose memory entries after a meeting: "I see you had a 1-hour call with <Name> at 11:00. Want me to log what emerged?"
- Not duplicate calendar events as memory rows — that's noise.

### External task managers (Things, Todoist, Linear, custom Slacky)

If you already use a task manager, you have a choice:

- **Lightweight memory**: keep `type='task'` entries only for things said in conversation, and let the external tool own the real task list
- **Unified view**: have the orchestrator query both and present them together (memory tasks + external tasks), but never sync — syncing causes drift and conflicts

The `CLAUDE.md` default is lightweight: memory `task` entries are **conversational commitments**, quick things said in chat. The source of truth for structured, recurring tasks is your external tool.

### Reminders (macOS / iOS)

Use Reminders when something needs to ping you at a specific time — memory doesn't do notifications. Log in memory that the reminder was created, let Reminders actually remind you.

## MCP servers

MCP (Model Context Protocol) servers give the orchestrator live tools for external systems. Configure them in `.mcp.json` at the repo root (or per-project) and declare them in preferences so the orchestrator knows they exist.

Common ones worth integrating:

- `google-calendar` — read events, suggest times, respond to invites
- `google-drive` / `gmail` — search and draft
- `slack` — post and search messages
- `basecamp` — todos, messages, cards
- `linear` / `jira` — issue tracking
- Custom MCPs for domain-specific systems

When an MCP is wired, you can ask the orchestrator things like *"do I have free time Tuesday afternoon?"* and it'll actually check the calendar.

## When to NOT put something in memory

Three cases:

1. **It's a durable pattern about you or your world** — goes in `preferences.md`, not memory. See `CLAUDE.md` → `## Preferences evolution`.
2. **It's transient session state** — doesn't belong anywhere persistent.
3. **It's the content authoritative in another tool** — keep it there, reference it.

The rule of thumb: memory is a **log**, not a database. Append, don't replace. Tag generously. Trust external tools for their domains.

## Querying memory programmatically

If you want to build skills or reports that analyze memory, the db is standard SQLite. Any client works (`sqlite3`, Python's `sqlite3` module, DB Browser for SQLite, etc.). Stay outside of the `private/` folder when building a script — the db path is `private/memories.db`, but scripts themselves should live in `.claude/skills/<name>/` or `workspace/`.

Example: a skill that exports this week's memories to a Markdown digest can live at `.claude/skills/weekly-digest/` and read memory directly.
