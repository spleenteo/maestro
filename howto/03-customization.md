---
tags: [howto, customization, preferences, identity, orchestrator]
description: How to customize your orchestrator — identity, owner profile, context, file territories, integrations, communication style. All through `private/preferences.md`.
---

# How to customize your orchestrator

Everything that makes your orchestrator *yours* lives in **`private/preferences.md`**. This file is the single source of truth: it's loaded at every session start, and any change takes effect on the next session.

The `setup` skill fills in the essentials at first launch. This document explains how to expand, refine, and reset the customization over time.

## The seven sections

Your preferences are organized in seven blocks. Fill what's relevant, leave the rest empty or remove sections you don't need.

### 1. Identity (the orchestrator)

Defines how the orchestrator presents itself:

```markdown
## Identity

- Name: Jarvis
- Inspired by: "a calm butler, patient and discreet"
- Adjectives: paternal, calm, discreet, proactive, gentle
```

**Rename** or **restyle** by editing these fields. The orchestrator reads them at the next session start.

### 2. Owner — basics

Who you are to the orchestrator:

```markdown
## Owner — basics

- Nick: Jane
- Full name: Jane Doe
- Role: Account Manager
- Default language: english
```

Change language here and the orchestrator switches at next session (current session continues in the old language unless you ask).

### 3. Context of operation

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

### 4. People

People who matter in your work:

```markdown
## People

- A. Smith (CEO): escalation for technical or strategic decisions
- B. Jones (GM): primary sparring partner on product/partner strategy
- C. Brown (Lead Dev): technical point for infrastructure and integrations
```

The orchestrator proposes additions when it notices someone recurring in conversation.

### 5. File territories

Where the orchestrator is authorized to write:

```markdown
## File territories

- logbook_path: /Users/you/vault/Work/Diary
- til_path: /Users/you/vault/Work/TIL
- documents_path: /Users/you/vault/Work/Documents
```

Paths can be any filesystem location. Remove a line to disable that territory.

### 6. Integrations

External services:

```markdown
## Integrations

- Basecamp: account 1234567, project 9876543
- MCP servers: slacky, gmail, gcal
- Other: a CRM, a shared inbox tool
```

Integrations declared here are things the orchestrator knows *about*. Actual wiring (MCP setup, OAuth) happens in Claude Code's config, not here.

### 7. Communication preferences

How the orchestrator should talk:

```markdown
## Communication preferences

- Tone with you: direct, terse, no preambles or decorative empathy
- Tone with others (drafting on your behalf): warmer with agency contacts, more measured with enterprise clients
- Things to avoid: bureaucratic phrasing, final summaries, emojis in work messages
- Things to keep doing: flag problems early even when uncomfortable, suggest alternatives before committing
```

This is also where the orchestrator will propose additions over time when it picks up on patterns in how you actually work.

### 8. Notes

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
