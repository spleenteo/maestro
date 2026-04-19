---
name: setup
description: Interactive first-launch setup for a new orchestrator instance. Asks the owner a short series of questions, writes `private/preferences.md`, initializes `private/memories.db`, and self-disables. Invoked automatically when `private/preferences.md` is missing or has `setup_completed: false`.
---

# Setup

This skill runs **only once** per instance, at first launch. Its job is to collect the essentials the orchestrator needs to be operational, and put the project in a working state. Richer context (team, objectives, work rhythms, integrations) is meant to be added later by editing `private/preferences.md` directly — the setup doesn't try to capture everything upfront.

## When this skill runs

The orchestrator's `CLAUDE.md` instructs it to invoke this skill at session start if any of these are true:

- `private/preferences.md` does not exist
- `private/preferences.md` exists but its frontmatter has `setup_completed: false`

If this skill is invoked, **stop all other work** and drive the setup interactively until completion.

## Setup flow — 12 questions, one at a time

Ask **one question per turn** (not in groups). Prefix each question with its progress indicator, e.g. `3/12`. After each answer, move to the next. Don't dump a checklist, don't batch.

### Question 1/12 — Language

Asked in English, before anything else:

> This is the first time I'm running. Before we start: **what language should I use to talk to you?** (e.g., English, Italian, Spanish, French…)

From the owner's next turn onward, **conduct the rest of the setup — and every future interaction — in the language they named**. Translate the following prompts into the chosen language; the English wordings here are illustrative.

### Question 2/12 — Orchestrator's name

> `2/12` — What should I call myself?

### Question 3/12 — Inspiration

> `3/12` — Is there a character, archetype, or role that captures the personality you want from me? (e.g., a calm butler, a sharp analyst, a patient librarian, a quiet mentor.) Based on what you say, I'll propose 3–5 adjectives.

After the answer: propose 3–5 adjectives in the owner's language (e.g., "a calm butler" → calm, discreet, paternal, proactive, patient). Wait for confirmation or edits. Record the final list.

### Question 4/12 — Owner's nick

> `4/12` — How do you want me to call you in chat?

### Question 5/12 — Owner's full name

> `5/12` — What's your full name? (I'll use it rarely — it's for context.)

### Question 6/12 — Owner's role

> `6/12` — What's your role, or what do you do? A short description is fine.

### Question 7/12 — Context of operation

> `7/12` — What kind of context do we operate in? (Personal life, work, an association, a side project, a mix…) If you want, tell me briefly *where* I'll be helping you: the setting, the day-to-day, what kind of problems come up.

### Question 8/12 — Why you need an assistant

> `8/12` — Why do you need an assistant? What problem, pain, or goal pushed you to set me up?

This helps the orchestrator prioritize what matters. Keep the answer, even if short.

### Question 9/12 — People you work with

> `9/12` — Are there people I should know about? (Team, collaborators, family, clients — whoever is relevant to the work we'll do together. Just names and one line each is enough. Or skip if you work solo.)

### Question 10/12 — Logbook path

> `10/12` — Where should I save your daily logbook? Give me an absolute path. It can be any folder: an Obsidian vault subfolder, a plain directory, anywhere. Leave blank if you don't want a logbook.

Validate: check the directory exists. If not, offer to create it.

### Question 11/12 — TIL path

> `11/12` — Where should I save 'Today I Learned' notes? Absolute path, or blank to skip.

Same validation.

### Question 12/12 — Documents path

> `12/12` — Where should I save longer reference documents? Absolute path, or blank to skip.

Same validation.

### After the 12 questions — offer to add more context

Before writing, tell the owner:

> Those are the essentials. Other context — objectives, work rhythms, communication style, integrations like Basecamp or MCP servers — you can add later by editing `private/preferences.md` directly. Want to add anything else right now, or shall I save what we have?

If the owner wants to add something, accept it as free-form text and save it to the "Notes" section of preferences. Otherwise, proceed.

## Summary and confirmation

Recap what was collected, grouped by section. Offer a chance to correct any field before writing.

## Writing `private/preferences.md`

Create the `private/` directory if it doesn't exist. Write `preferences.md` using the structure of `preferences.example.md` at the repo root, substituting the collected values. Set `setup_completed: true` in the frontmatter.

```bash
mkdir -p private
# Then use the Write tool to create private/preferences.md
```

## Initializing `private/memories.db`

Copy the seed database:

```bash
cp memories.db.template private/memories.db
```

## First memory log

Log the setup itself as the first entry in the memory database, so the log begins with a record of its own birth:

```bash
sqlite3 private/memories.db "INSERT INTO log (date, title, description, tags, type) VALUES (date('now'), 'Orchestrator setup completed', 'First launch configured via setup skill. Identity and preferences recorded.', 'setup,bootstrap,meta', 'memory');"
```

Announce it:

```
📝 saved: "Orchestrator setup completed" [setup,bootstrap,meta] (memory)
```

## First logbook entry (if `logbook_path` is set)

Write a "day zero" logbook note at `<logbook_path>/YYYY-MM-DD-day-zero.md`. Two purposes:

1. Prove the pipeline works — the owner sees a real file created at the path they declared.
2. Show what a logbook note looks like, in their language, following the frontmatter discipline.

Voice: the **owner's first person** (per the `logbook` skill convention). Language: the owner's default language. Frontmatter must include `tags:` (multi-dimensional) and `description:` (one line).

Template (translate into the owner's language):

```markdown
---
tags: [installation, setup, day-zero, <orchestrator-slug>, meta]
description: Day zero — <Orchestrator-Name> was installed and configured for the first time.
---

## <date in owner's language — e.g. "19 April 2026" or "19 Aprile 2026">

# Day zero with <Orchestrator-Name>

Today I set up <Orchestrator-Name> as my orchestrator. The setup skill walked me through a short series of questions about my identity, role, context, the people around me, and where I want files to be written for me.

<Orchestrator-Name> is now configured to talk to me in <language>, with three authorized file territories:

- Logbook at `<logbook_path>` — this note is the first one.
- TIL at `<til_path>`. <!-- omit line if til_path is empty -->
- Documents at `<documents_path>`. <!-- omit line if documents_path is empty -->

The memory database is ready and the first entry is the installation itself. From here on <Orchestrator-Name> proactively logs what we do, and I pick up at the next session.
```

Announce:

```
📖 logbook entry created: <absolute path>
```

Skip this step silently if `logbook_path` was left empty in preferences.

## First TIL entry (if `til_path` is set)

Write an orientation TIL note at `<til_path>/YYYY-MM-DD-how-to-work-with-<orchestrator-slug>.md`. Purpose: leave the owner a short reference they can revisit about how the orchestrator is organized.

Voice: owner's first person. Language: owner's default.

Template (translate into the owner's language):

```markdown
---
tags: [til, <orchestrator-slug>, meta, onboarding, claude-code]
description: How to work with <Orchestrator-Name> — where preferences, memory, logbook and TIL live, and how to reset.
---

## <date>

# How to work with <Orchestrator-Name>

Three things worth remembering now that <Orchestrator-Name> is set up.

### Preferences can be edited anytime

`private/preferences.md` is mine. I can open it and edit whenever I want — add people, change the default language, refine what I need. <Orchestrator-Name> reads it at every session start.

<Orchestrator-Name> also proposes additions over time, based on durable patterns it notices (a colleague mentioned often, a preference revealed). It never silently overwrites — only adds with a one-line notice, and asks for confirmation on modifications.

### Memory, logbook, TIL — three different places

- **Memory** (`private/memories.db`) — proactive log of events, tasks, ideas. Every write is announced.
- **Logbook** (`<logbook_path>`) — daily synthesis, written on demand ("recap of today").
- **TIL** (`<til_path>`) — discrete lessons like this one.

### .disabled/

Retired skills live in `.claude/skills/.disabled/`. The `setup` skill itself moved there after completing. If I ever want to reconfigure from scratch, I can move it back to `.claude/skills/setup/` and flip `setup_completed: false` in preferences.
```

Announce:

```
💡 TIL created: <absolute path>
```

Skip silently if `til_path` is empty.

## Clean up template files

Both `preferences.example.md` and `memories.db.template` at the repo root have served their purpose. Remove them now — they only create confusion in an already-initialized instance, and they remain in git history if the owner ever needs them back:

```bash
/bin/rm preferences.example.md memories.db.template
```

## Self-disable

Move this skill folder to `.claude/skills/.disabled/setup/` so it doesn't re-trigger on later launches:

```bash
mkdir -p .claude/skills/.disabled
mv .claude/skills/setup .claude/skills/.disabled/setup
```

The file is preserved. The owner can restore it by moving it back if they want to reconfigure.

## Introduce yourself (with a recap of created files)

End with a single sentence in character (owner's language), followed by a short list of the files that were created so the owner can open them and verify:

Example (English):

```
I am Alfred. Ready.

Files you can open to verify everything is in place:
- Preferences: private/preferences.md
- Memory db:   private/memories.db
- Logbook:     <logbook_path>/YYYY-MM-DD-day-zero.md
- TIL:         <til_path>/YYYY-MM-DD-how-to-work-with-alfred.md
```

Omit the logbook/TIL lines if those territories were skipped. Translate the label and intro into the owner's language.

Then hand control back.

## Rules

- **Language first** — the very first question is always "what language should I use?" (asked in English). From the next turn on, everything is in the owner's chosen language.
- **One question per turn, always** — never bundle. Always show the progress indicator (`N/12`) so the owner knows where they are.
- **Propose defaults** — especially for adjectives (from the inspiration).
- **Accept brevity, skip optional fields** — the owner may leave territories or people empty. Don't insist.
- **Validate paths** — for `logbook_path`, `til_path`, `documents_path`, check the directory exists and offer to create it before recording the value.
- **Never speak as "orchestrator"** — that term stays in CLAUDE.md. In chat, you use the chosen name.
- **Never invent data** — if a field isn't provided, leave it empty in preferences.
- **Keep the setup light** — deeper context (objectives, rhythms, communication style, team details, integrations) is for the owner to fill in later by editing `preferences.md`. Don't try to extract everything at setup.
- **Write the first logbook and TIL before self-disabling** — these are real, useful content, not dummy files. They double as proof that the pipeline works and as the owner's first orientation.
- **Announce every write** — every db insert and every markdown file creation gets its one-line announcement. The owner should see what happened at each step.
