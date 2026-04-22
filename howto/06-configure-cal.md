---
tags: [howto, cal, scheduler, channels, routines, configuration, agents]
description: How to configure the `scheduler` agent (alias Cal) — adding data channels (task trackers, calendars), writing routines, and understanding the seven `question_types`.
---

# Configure Cal — channels, routines, question types

Cal is the `scheduler` craft agent. Its job: aggregate tasks, events, and completed work from multiple data channels and return structured, sourced lists to the orchestrator when you ask things like *"what do I have today?"* or *"what did I do this week?"*. Cal never talks to you directly — output always flows through the orchestrator.

Out of the box Cal reads only one channel: `memories_db` (your orchestrator's memory log). Everything else — Basecamp, Google Calendar, other task trackers — is configuration you add. This doc is the map.

## Where everything lives

| File | Role | Gitignored |
|------|------|:---:|
| `.claude/agents/data/channels.yaml` | Channels + `question_types`. Read by Cal at every invocation. Shared, versioned. | no |
| `private/routines.yaml` | Your recurring routines. Seeded from `routines.example.yaml` at setup. Edit freely. | **yes** |
| `private/preferences.md` | Owner profile, including `timezone` (optional; Cal falls back to system TZ). | **yes** |
| Tool-specific configs | Where the tool expects them. Example: `.basecamp/config.json` if you use the Basecamp CLI. | varies |

Cal reads `channels.yaml` on every invocation, so changes take effect without touching the agent prompt. No restart needed.

## The grammar: `question_types`

Cal classifies every request into one of seven `question_types`. Each type declares which channels to query, how to group the output, and whether to include routines. The matrix ships all seven routed through `memories_db` only:

| `question_type` | Covers | Grouping | Includes routines? |
|---|---|---|:---:|
| `prospective_today` | "what do I have today?" | by_area | yes |
| `prospective_week` | "what's on this week?" | by_area | yes |
| `retrospective_today` | "what did I do today?" | chronological | no |
| `retrospective_week` | "what did I do this week?" | by_area | no |
| `daily_report` | formal daily report (orchestrator persists) | chronological | no |
| `weekly_plan` | formal weekly plan (orchestrator persists) | by_area | yes |
| `ad_hoc` | specific questions — Cal decides which channels to query | none | on_demand |

When you add a channel, you also add its name under the `channels:` list of every `question_type` that should use it. A channel is only queried for a given question type if it appears in that type's list.

## Adding a channel

A channel declares three things: **purpose** (free-text, so you remember why it's there), **access** (how Cal reaches it), and **item_types** (what shape the returned data has). Access has four flavors:

### `access.tool` — direct CLI / local command

For channels backed by a local tool on your machine — like SQLite, a local JSON store, or a shell command. The `memories_db` channel uses this flavor:

```yaml
memories_db:
  purpose: >
    The orchestrator's memory log — tasks, memories, and ideas.
  access:
    tool: sqlite3
    path: private/memories.db
    table: log
  item_types:
    - name: task
      states: [todo, in_progress, done, cancelled]
      fields: [title, description, tags, due_date, completed_date, priority]
  temporal_field: date
```

### `access.skill` — delegate to a Claude Code skill

For channels where a dedicated skill already wraps the API — like a `basecamp` skill or a custom CLI wrapper. Cal invokes the skill by name and passes the declared config refs:

```yaml
<your_channel_name>:
  purpose: >
    <what this channel gives you and why it matters>
  access:
    skill: basecamp                  # the skill you have installed
    config_refs:                     # IDs read from the skill's own config file
      - bucket_id
      - card_table_id
      - owner_user_id
  item_types:
    - name: card
      fields: [title, assignees, content, due_on]
      assignable: true
    - name: step
      parent: card
      fields: [title, due_on, status, assignee]
  temporal_field: due_on
  notes: >
    Filter by assignees containing <owner_user_id>.
```

**Why `config_refs` and not raw IDs?** Cal never stores IDs in `channels.yaml` or in the agent prompt. The tool's own config (e.g. `.basecamp/config.json`) is the single source of truth for IDs. This keeps the YAML portable and keeps secrets/IDs where they belong.

### `access.mcp` — delegate to an MCP server

For channels served by an MCP — like Google Calendar, Gmail, a calendar MCP of your choice. Declare the MCP tool name and whatever arguments the MCP needs:

```yaml
calendar_events:
  purpose: >
    Calendar events (meetings, calls, blocks).
  access:
    mcp: mcp__your_provider__list_events
    calendar: primary
    exclude_types: [outOfOffice, workingLocation, birthday]
  item_types:
    - name: event
      fields: [summary, start, end, attendees, location, description]
  temporal_field: start
```

Timezone for these events is resolved at runtime from your `preferences.md` `timezone` key (fallback: system TZ). You don't need to set it here.

### Mix and match

A matrix instance can have any combination of channels across the three access flavors. The owner-authoritative pattern is:

1. Install the tool/skill/MCP.
2. Declare the channel in `channels.yaml` pointing at it.
3. Add the channel's name to the `question_types` that should read from it.

That's it — next time you ask Cal something, the new channel is part of the pipeline.

## Soft failure

If a declared channel's backing tool is unavailable (SQLite file missing, Basecamp CLI not installed, MCP disconnected), Cal doesn't crash the invocation. It skips the channel and adds a line to the output's `## Notes` section saying which channel was skipped and why. This is by design: one broken integration shouldn't black out the other four.

## Routines

Routines are recurring items you keep outside your task tracker — think "review invoices at month end", "weekly retro on Friday afternoon", "check X every 15th". They live in `private/routines.yaml`, seeded at setup from `routines.example.yaml`. Cal reads them only when the matched `question_type` has `include_routines: true` (e.g. `prospective_today`, `prospective_week`, `weekly_plan`).

A routine is one YAML item under `routines:`:

```yaml
routines:
  - title: "Weekly retro — review the week, plan the next"
    frequency: weekly
    day_of_week: fri
    active: true
    tags: [retro, planning, self]
    notes: "30min on Friday afternoon."
```

Fields:

- **title** (required) — short, recognizable.
- **frequency** (required) — `daily` / `weekly` / `monthly` / `quarterly` / `yearly`.
- **day_of_week** — for `weekly`. `mon|tue|wed|thu|fri|sat|sun`.
- **day_of_month** — for `monthly`. `1`–`31` or `last`.
- **month_of_year** — for `yearly`. `1`–`12`.
- **active** (required) — `true` or `false`. `false` routines are ignored by Cal.
- **tags** — same multi-dimensional style as memory tags.
- **notes** — one-line context for future-you.

Routines are inert when the template ships. Edit `private/routines.yaml` to activate them. Add as many as you need.

## Timezone

Cal resolves time windows ("today", "this week") using:

1. `timezone` key in `private/preferences.md` if present (IANA name — e.g. `Europe/Rome`, `America/New_York`, `Asia/Tokyo`).
2. System timezone via `date +%Z` as fallback.

No question about this in setup — it's an advanced preference. Add the key to `preferences.md` only if you want to override the system TZ.

## Common workflows

**Add Basecamp support**

1. Install a `basecamp` skill (your own wrapper, or one from the community).
2. Configure its credentials/IDs file (e.g. `.basecamp/config.json`) per the skill's README.
3. Open `.claude/agents/data/channels.yaml` and uncomment/adapt the `card_table_watch` example (rename to something meaningful). Point `access.skill` at your skill's name. List the config keys your skill exposes under `config_refs`.
4. Add the channel's name to the `channels:` lists of the `question_types` that should use it (usually `prospective_*`, `retrospective_*`, `daily_report`, `weekly_plan`).
5. Ask Cal a question through the orchestrator. If the skill is missing or broken, the `## Notes` section will tell you.

**Add a calendar via MCP**

1. Configure the calendar MCP in Claude Code (see MCP provider docs).
2. Uncomment/adapt the `calendar_events` example in `channels.yaml`. Set `access.mcp` to the MCP tool name.
3. Add the channel to the `question_types` that should include events (typically all prospectives and retrospectives).
4. Optionally set `timezone` in `preferences.md` if your calendar uses a TZ other than the system's.

**Add a recurring routine**

1. Open `private/routines.yaml`.
2. Add an item under `routines:` with `active: true` and the right frequency fields.
3. Next time you ask Cal "what's on today?" or "what's on this week?", the routine will surface in the `## Routines for today/this week` section.

## Debugging

- **Cal returned empty output** — check that the relevant `question_type` has `channels:` listed and not commented out. Every channel you expect to be queried must be in that list.
- **Cal skipped a channel** — look at the `## Notes` section of its output. It'll name the channel and the reason (tool missing, config unreadable, query error).
- **Cal returned the wrong time window** — verify `timezone` in `preferences.md` (if set) matches where you actually are. Otherwise check the system TZ.
- **Routines not showing up** — routines are surfaced only for `question_types` with `include_routines: true`. Retrospectives never include routines, by design.

---

Cal's configuration is meant to grow with you. Start with `memories_db`, add channels as you integrate tools, and keep the routines file honest (retire routines you no longer need). The agent prompt doesn't need updating — the YAML is the source of truth.
