---
tags: [howto, tasks, warm-channel, cold-layer, gc, slacky, basecamp, integrations]
description: Configure an optional external task system as the "warm" layer of the orchestrator, with the memory db as the "cold" layer and a lazy garbage collector that archives done tasks at session start.
---

# How to wire an external task channel (warm/cold pattern)

Some owners use a dedicated task manager — Slacky, Basecamp todos, Todoist, Linear, custom — and want the orchestrator to treat that as the source of truth for "things to do" instead of the memory db. This guide explains the pattern: a **warm layer** outside the orchestrator, a **cold layer** in `memories.db`, and a **lazy garbage collector** that bridges them.

It's optional. If you don't declare a warm task channel, the orchestrator keeps using `type='task'` in `memories.db` as documented in [04 — Memory and integrations](04-memory-and-integrations.md).

## The three pieces

| Piece | What it is | Where it lives |
|---|---|---|
| **Warm layer** | The external task system. Tasks are created, scheduled, completed, deleted here. Authoritative for what is *in flight*. | Outside the repo — Slacky (Supabase + React client), Basecamp todos, Todoist, etc. Reached via MCP, CLI, or HTTP. |
| **Cold layer** | `memories.db`, table `log`, `type='memory'`. Authoritative for what *was done*, as an archived flat record. | `private/memories.db`, queried via `bin/mem`. |
| **Garbage collector** | A short routine that runs at session start (and on a few other triggers): reads tasks closed since the last flush, writes them to the cold layer in bulk, deletes them from the warm layer, updates a marker. | Inside a skill named `<channel>-task-manager`, in the section `## Garbage Collector`. |

The pattern decouples *liveness* (warm) from *history* (cold). The warm layer can stay small and current; the cold layer accumulates without slowing the warm UI down.

## Configuration — preferences

To enable a warm task channel, add a block to `private/preferences.md`:

```yaml
## Warm task channel

channel: slacky                    # or basecamp, todoist, none
skill: slacky-task-manager         # the skill that implements the contract
archive_tag: slacky-archive        # tag prepended to every archived memory
marker_name: last-slacky-flush     # marker key in memories.db for the watermark
```

If the block is absent or `channel: none`, the orchestrator does not invoke any GC and treats `memories.db` as the only task store.

The channel name is free-form but conventionally matches a known integration. Suggested values:

- `slacky` — custom Slacky task manager (MCP-based)
- `basecamp` — Basecamp todos (Basecamp CLI / MCP)
- `todoist`, `linear`, etc. — any external system with a programmable interface

## The skill contract

The skill named in `skill:` (e.g. `slacky-task-manager`, `basecamp-task-manager`) must expose, at minimum, a `## Garbage Collector` section that the orchestrator can invoke. The section describes how the skill:

1. Reads the watermark — `bin/mem marker get <marker_name>` (fallback: 7 days ago).
2. Lists tasks closed in the warm layer since that watermark.
3. If non-empty, archives each one into `memories.db` as `type='memory'` with the configured `<archive_tag>` plus per-channel tags (list, section, recurrence flag, parent idea ref).
4. Deletes (or marks archived) the closed tasks in the warm layer, so they don't show again next flush.
5. Updates the watermark — `bin/mem marker set <marker_name> <now-iso>`.
6. Announces in chat in one line: `📦 archived N tasks: <inline ≤3 | count + first 3 if ≥4>`. Silent if N=0.

Beyond GC, the skill typically also exposes read/write operations to the warm layer (list today, create a task, complete one). Those are channel-specific and not part of this guide.

### Archive memory format (recommended)

```yaml
title: "<original task title>"
type: memory
date: <task.completed_at, YYYY-MM-DD>
tags: <archive_tag>, done, <list-kebab>[, <section-kebab>][, recurring][, idea-<id>]
description: list:<List>/<Section> | scheduled:<date> <timeOfDay> | due:<date> | est:<N>min | recurring:<yes|no>[ | ref:idea#<id>][ | notes:<flat>]
```

The `description` field uses a fixed-order pipe-separated format so it's both human-readable and parsable. Keep the order stable across channels — it makes cross-channel retrospection easier later.

## Session-start integration — CLAUDE.md

The session-start routine (`CLAUDE.md` → `## Session start`) includes the GC as a non-blocking step, **conditional** on the warm channel being declared. Pseudocode:

```
if preferences declares warm_task_channel and channel != "none":
    invoke skill <channel>-task-manager, section "Garbage Collector"
    # rules:
    # - guard: skip if now - last_<channel>_flush < 1 hour (idempotency)
    # - cross-week-boundary: if the window crosses an ISO Sunday, compute weekly trend first
    # - non-blocking: if the channel is unreachable, log silently and continue the session
    # - announcement: one line if N > 0, otherwise silent
```

The orchestrator never invents the channel name. If the skill the preferences refer to is missing, the orchestrator skips the GC silently and notes the misconfiguration in the next conversational opportunity.

## End-of-session and manual triggers

In addition to session start, the GC is typically wired to:

- **End-of-session phrases** — "buonanotte", "ok basta", "a domani", invocation of the `logbook` skill. Same flow.
- **Manual override** — "flusha", "scarica i done", "sincronizza i task". Runs immediately, ignoring the 1-hour idempotency guard.

These triggers live inside the `<channel>-task-manager` skill, not in `CLAUDE.md`.

## Optional — weekly trend

If you want the GC to compute a "weekly trend" memory when its flush window crosses an ISO Sunday, add a `## Trend` subsection to the skill describing what metrics to compute (e.g. completion rate, peak time-of-day, late count) and emit a single `type='memory'` row tagged `<channel>-trend, weekly, <YYYY-W##>` before the per-task archive rows.

This is optional. Skip it if you don't need behavioral retrospectives.

## Why use this pattern instead of plain memory tasks

Two reasons:

1. **The warm tool has UI affordances the orchestrator cannot replicate** — daily views, recurring schedules, time-of-day buckets, mobile push, swipe-to-complete. The owner interacts with the warm tool through its native UI; the orchestrator coordinates around it.
2. **The cold layer stays clean** — `memories.db` accumulates `type='memory'` rows with a stable shape, ready for retrospection ("what did I do last week?"). No mixed lifecycle, no half-open `type='task'` rows from years ago.

If you don't have those affordances or don't need them, plain memory tasks are fine.

## Why use `memories.db` instead of pulling history from the warm tool

Because the warm tool is allowed to forget. Slacky deletes done tasks after a window; Basecamp archives todos out of the active project; Todoist hides completed items. The cold layer in `memories.db` is the orchestrator's own copy of what was done — durable, searchable, and under your control.

## Anti-patterns

- **Two writers**: the warm layer and `memories.db` both having `type='task'` rows for the same thing. Pick one. With a warm channel, `memories.db` does not hold open tasks — only their archived form after GC.
- **Eager sync**: trying to mirror the warm layer in real time. The point of the GC is laziness — it runs at session start, not continuously.
- **Silent writes**: archiving without the one-line announcement. The owner must always see what landed.
- **Hardcoding the channel name in `CLAUDE.md`**: the channel name comes from preferences, the orchestrator never hardcodes "Slacky" or "Basecamp" in its top-level instructions.

## Example — Slacky

```yaml
## Warm task channel
channel: slacky
skill: slacky-task-manager
archive_tag: slacky-archive
marker_name: last-slacky-flush
```

The skill `.claude/skills/slacky-task-manager/SKILL.md` wraps the Slacky MCP (`slacky_list_done_since`, `slacky_delete_task`, etc.), implements the GC flow, and optionally adds read/write tools (`slacky_get_today`, `slacky_create_task`).

## Example — Basecamp

```yaml
## Warm task channel
channel: basecamp
skill: basecamp-task-manager
archive_tag: basecamp-archive
marker_name: last-basecamp-flush
```

The skill `.claude/skills/basecamp-task-manager/SKILL.md` wraps the Basecamp CLI (`bc3 todos:list --completed-since=…`, `bc3 todos:archive …`), implements the GC flow, and maps Basecamp concepts:

- A todo's **assignee** maps to a tag.
- A todo's **list** (within a project) maps to the `list` field of the archive description.
- A todo's **parent message** or **card** can be referenced as `ref:` in the description (analog to Slacky's `parent_idea_ref`).
- **Comments** on the todo at completion time are flattened into the `notes:` field of the description (whitespace collapsed, `|` escaped).

The same skill contract holds: the orchestrator at session start calls the GC, the GC reads since the marker, writes to the cold layer in bulk via `bin/mem save --bulk`, updates the marker, and announces.

## Reusing across instances

The pattern is identical across Maestro instances. If you have multiple instances (Pam, Alfred, Claudio, Luigi), each one can declare its own channel:

- Alfred → `slacky` (personal life)
- Pam → `basecamp` (DatoCMS work)
- Claudio → `basecamp` (DSM / Acacia)
- Luigi → another channel or none

Each instance has its own `memories.db`, its own marker, and its own archived rows. The channels never cross.
