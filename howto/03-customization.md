---
tags: [howto, customization, preferences, identity, orchestrator]
description: How to customize your orchestrator — identity, owner profile, context, file territories, integrations, communication style. All through `private/preferences.md`.
---

# How to customize your orchestrator

Everything that makes your orchestrator *yours* lives in **`private/preferences.md`**. This file is the single source of truth: it's loaded at every session start, and any change takes effect on the next session.

The `setup` skill fills in the essentials at first launch. This document explains how to expand, refine, and reset the customization over time.

## The sections

Your preferences are organized in several blocks. Fill what's relevant, leave the rest empty or remove sections you don't need.

### 1. Project

The top-level scope this orchestrator is for. Shapes what "context" means in the rest of the file and provides the default folder name for the internal vault (if you picked internal mode at setup).

```markdown
## Project

- project_name: Acme partnership
- project_slug: acme-partnership
```

The **slug** is a filesystem-safe version of the name (lowercase, non-alphanumeric replaced by `-`). Setup computes it automatically. You can rename the project later, but if you do and you're in internal mode, remember to rename the vault folder on disk and update the `vault_path` / subfolder keys to match.

### 2. Identity (the orchestrator)

Defines how the orchestrator presents itself:

```markdown
## Identity

- Name: Jarvis
- Inspired by: "a calm butler, patient and discreet"
- Adjectives: paternal, calm, discreet, proactive, gentle
```

**Rename** or **restyle** by editing these fields. The orchestrator reads them at the next session start.

### 3. Owner — basics

Who you are to the orchestrator:

```markdown
## Owner — basics

- Nick: Jane
- Full name: Jane Doe
- Role: Account Manager
- Default language: english
- timezone: Europe/Rome   # optional — omit to fall back to system TZ
```

Change language here and the orchestrator switches at next session (current session continues in the old language unless you ask). The `timezone` key is optional — agents that reason about "today" and "this week" (like Cal) read it, falling back to the system timezone when absent.

### 4. Context of operation

**The section that pays off the most.** The orchestrator is much more useful when it understands your world:

```markdown
## Context of operation

- Setting: work — Account Manager at ACME. I handle partner relationships, solution consulting, and occasional conflict mediation.
- Why you need an assistant: juggling 40+ active partner conversations, tracking commitments, remembering context across weeks.
- Main objectives:
  - Keep every partner conversation warm and on-track
  - Flag risk early (churn signals, missed commitments)
  - Draft diplomatic messages on short notice
- Constraints and rhythms: 9–18 Mon–Fri, no weekends. Mondays are reserved for planning.
```

Expand freely. This is what the orchestrator uses to prioritize and tailor its help.

### 5. People

People who matter in your work:

```markdown
## People

- A. Smith (CEO): escalation for technical or strategic decisions
- B. Jones (GM): primary sparring partner on product/partner strategy
- C. Brown (Lead Dev): technical point for infrastructure and integrations
```

The orchestrator proposes additions when it notices someone recurring in conversation.

### 6. File territories

Where the orchestrator is authorized to write. The library is organized around a **vault root** (`vault_path`) with three subfolder keys that default to subfolders of it:

```markdown
## File territories

- vault_path: /Users/you/vault/Work
- logbook_path: /Users/you/vault/Work/logbook
- til_path: /Users/you/vault/Work/til
- documents_path: /Users/you/vault/Work/documents
```

`vault_path` is the single source of truth for the vault location — every other file (CLAUDE.md, agents, skills) references the key, never the value. Subfolder keys default to subfolders of `vault_path` but can point anywhere if you want a non-standard layout. Remove a subfolder line to disable that territory.

**Internal vs external.** At setup time you chose between three modes:

- **internal** — the orchestrator created `./<project-slug>/` inside the repo as the vault (the slug derived from your project name in Q2), with `logbook/`, `til/`, `documents/` as subfolders. All four keys were written to preferences and the slug was appended to `.gitignore`, so notes stay private.
- **external** — you gave an absolute path to a vault on disk (typical for Obsidian vaults or cloud-synced directories); subfolders defaulted to `<vault_path>/{logbook,til,documents}`.
- **skip** — no territories, no markdown writes until you set at least `vault_path` here.

You can switch modes anytime by editing `vault_path` (and adjusting the three subfolder keys, if you moved them). To migrate from internal to external, move the content from `./<project-slug>/` to your target vault and update `vault_path` here. To migrate from external to internal, do the reverse and point `vault_path` at `<repo>/<project-slug>/` (and add the slug to `.gitignore` if it isn't already).

### 7. Integrations

External services:

```markdown
## Integrations

- Basecamp: account 1234567, project 9876543
- MCP servers: slacky, gmail, gcal
- Other: a CRM, a shared inbox tool
```

Integrations declared here are things the orchestrator knows *about*. Actual wiring (MCP setup, OAuth) happens in Claude Code's config, not here.

### 8. Communication preferences

How the orchestrator should talk:

```markdown
## Communication preferences

- Tone with you: direct, terse, no preambles or decorative empathy
- Tone with others (drafting on your behalf): warmer with agency contacts, more measured with enterprise clients
- Things to avoid: bureaucratic phrasing, final summaries, emojis in work messages
- Things to keep doing: flag problems early even when uncomfortable, suggest alternatives before committing
```

This is also where the orchestrator will propose additions over time when it picks up on patterns in how you actually work.

### 9. Notes

Free-form, for anything that doesn't fit the blocks above.

## Preferences evolution

The orchestrator watches for **durable patterns** in conversation and proposes additions to `preferences.md` proactively (see `CLAUDE.md` → `## Preferences evolution` for the behavioral rules). Three tiers:

1. **Additive** (new person, new durable fact): written immediately, announced with `🧩 added to preferences: <Section> — <one-line>`.
2. **Modification** (changing an existing field): the orchestrator proposes and waits for your confirmation.
3. **Removal or structural change**: always asked first.

The trigger for writing to preferences is **patterns**, not topic transitions. Topic transitions go into the memory db. If the orchestrator starts writing here too often, it's drifting — tell it to slow down.

## Renaming the orchestrator

Edit the `Name` field in the Identity block. Next session the orchestrator introduces itself with the new name.

If you want a full re-setup (new identity, new adjectives, new paths), move the `setup` skill back out of `.disabled/` and flip `setup_completed: false`:

```bash
mv .claude/skills/.disabled/setup .claude/skills/setup
# Then edit private/preferences.md and set setup_completed: false in frontmatter
```

The setup skill will re-trigger on the next launch.

## Changing language

Change `Default language` in the Owner block. Next session, the orchestrator uses the new language.

## How to reset completely

To start over from zero while preserving memory:

1. Back up `private/memories.db` (it's the log you've accumulated).
2. Delete `private/preferences.md`.
3. Restore the `setup` skill: `mv .claude/skills/.disabled/setup .claude/skills/setup`.
4. Restore the templates from git if needed: `git checkout HEAD -- preferences.example.md memories.db.template`.
5. Launch `claude` — setup runs again.

To start over *completely* (fresh memory too), also delete `private/memories.db` before step 3. You'll lose your history.
