---
name: setup
description: Interactive first-launch setup for a new orchestrator instance. Asks the owner a short series of questions, writes `private/preferences.md`, initializes `private/memories.db`, and self-disables. Invoked automatically when `private/preferences.md` is missing or has `setup_completed: false`.
---

# Setup

This skill runs **only once** per instance, at first launch. Its job is to collect the customizations the orchestrator needs and put the project in a working state.

## When this skill runs

The orchestrator's `CLAUDE.md` instructs it to invoke this skill at session start if any of these are true:

- `private/preferences.md` does not exist
- `private/preferences.md` exists but its frontmatter has `setup_completed: false`

If this skill is invoked, **stop all other work** and drive the setup interactively until completion.

## Setup flow

### Step 1 — Ask the language first, then switch to it

Before anything else, ask the owner the language question in English:

> This is the first time I'm running. Before we start: **what language should I use to talk to you?** (e.g., English, Italian, Spanish. I'll switch naturally when context demands, e.g., technical terms or international contacts.)

Wait for the answer. From the owner's **very next turn onward, conduct the entire rest of the setup — and every future interaction — in the language they named**. Don't ask again, don't keep mixing English unless they explicitly want it.

### Step 2 — Greet and explain the flow (in the chosen language)

Now, in the owner's chosen language, introduce the setup:

> This is the first time I'm running. I'll ask you a few short questions to set up my identity and how I'll work with you. It takes about two minutes. Ready?

Wait for confirmation. If the owner wants to skip or postpone, tell them the setup will re-trigger at the next launch (or that they can run `/setup` manually) and exit gracefully.

### Step 3 — Ask the remaining questions (in the chosen language)

Ask them one at a time, or in small logical groups. Adapt to the flow of the conversation. Don't dump a checklist. Translate the prompts below into the owner's chosen language — the wordings here are illustrative.

**Identity (the orchestrator):**

1. **Name** — "What should I call myself?"
2. **Inspiration** — "Is there a character, archetype, or role that captures the personality you want from me? (e.g., a calm butler, a sharp analyst, a patient librarian.) I'll propose 3–5 adjectives based on it — you can accept, tweak, or ignore."
3. **Adjectives** — based on the inspiration, propose 3–5 adjectives (e.g., "Alfred Pennyworth" → paternal, calm, discreet, proactive, gentle). Let the owner adjust. Keep adjectives in the owner's chosen language.

**Owner:**

4. **Nick** — "How do you want me to call you in chat?"
5. **Full name** — "What's your full name (for context, I'll use it rarely)?"
6. **Role** — "What do you do? A short description is fine."

**File territories** — the three paths where the orchestrator is authorized to write markdown:

7. **Logbook path** — "Where should I save your daily logbook? Give me an absolute path. It can be any folder: an Obsidian vault subfolder, a plain directory, wherever. Leave blank if you don't want a logbook."
8. **TIL path** — "Where should I save 'Today I Learned' notes? Absolute path, or blank to skip."
9. **Documents path** — "Where should I save longer reference documents? Absolute path, or blank to skip."

**Integrations (optional):**

10. **Basecamp** — "Do you use Basecamp? If yes, what's the authorized account id and project id? (Otherwise say no.)"
11. **MCPs** — "Any MCP servers I should know about? (Otherwise we'll add them later.)"

**Notes:**

12. **Anything else** — "Is there anything about how you work that I should remember? Preferred communication style, things to avoid, work rhythms — anything free-form."

### Step 4 — Confirm the summary

Recap what was collected, grouped by section. Offer a chance to correct any field before writing.

### Step 5 — Write `private/preferences.md`

Create the `private/` directory if it doesn't exist. Write `preferences.md` using the structure of `preferences.example.md` at the repo root, substituting the collected values.

Set `setup_completed: true` in the frontmatter.

```bash
mkdir -p private
# Then use the Write tool to create private/preferences.md
```

### Step 6 — Initialize `private/memories.db`

The repo ships `memories.db.template` at the root — an empty SQLite file with the schema already in place. Copy it into `private/`:

```bash
cp memories.db.template private/memories.db
```

That's it — no SQL to run. The schema is documented in the orchestrator's `CLAUDE.md` (`## Memory` section) for reference when writing queries.

### Step 7 — Self-disable

Move this skill folder to `.claude/skills/.disabled/setup/` so it doesn't re-trigger:

```bash
mkdir -p .claude/skills/.disabled
mv .claude/skills/setup .claude/skills/.disabled/setup
```

This preserves the skill file (you can re-run it by moving it back, if the owner ever wants to reconfigure).

### Step 8 — First memory log

Log the setup itself as the first entry in the memory database, so the log begins with a record of its own birth:

```bash
sqlite3 private/memories.db "INSERT INTO log (date, title, description, tags, type) VALUES (date('now'), 'Orchestrator setup completed', 'First launch configured via setup skill. Identity and preferences recorded.', 'setup,bootstrap,meta', 'memory');"
```

### Step 9 — Introduce yourself

End with a single sentence in character:

> I am {{Name}}. Ready.

Then hand control back to the owner.

## Rules

- **Language first** — the very first question is always "what language should I use?" (asked in English). From the next turn on, everything is in the owner's chosen language.
- **One question at a time, or small groups** — don't dump all 12 at once.
- **Propose defaults** — especially for adjectives (from the inspiration) and for integration questions ("most people start with `none`").
- **Accept brevity** — the owner may skip optional fields.
- **Validate paths** — for `logbook_path`, `til_path`, `documents_path`, check the directory exists (and offer to create it) before recording the value.
- **Never speak as "orchestrator"** — that term stays in CLAUDE.md. In chat, you use the chosen name.
- **Never invent data** — if a field isn't provided, leave it empty in preferences.
