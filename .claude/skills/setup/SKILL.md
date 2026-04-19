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

### Step 1 — Greet the owner and explain

Before asking anything, introduce the setup:

> This is the first time I'm running. I'll ask you a few questions to set up my identity and the way I'll work with you. It takes about two minutes. Ready?

Wait for confirmation. If the owner wants to skip or postpone, tell them the setup will re-trigger at the next launch and exit gracefully.

### Step 2 — Ask the questions

Ask them one at a time, or in small logical groups. Adapt to the flow of the conversation. Don't dump a checklist.

**Identity (the orchestrator):**

1. **Name** — "What should I call myself?"
2. **Inspiration** — "Is there a character, archetype, or role that captures the personality you want from me? (e.g., a calm butler, a sharp analyst, a patient librarian.) I'll propose 3–5 adjectives based on it — you can accept, tweak, or ignore."
3. **Adjectives** — based on the inspiration, propose 3–5 adjectives (e.g., "Alfred Pennyworth" → paternal, calm, discreet, proactive, gentle). Let the owner adjust.

**Owner:**

4. **Nick** — "How do you want me to call you in chat?"
5. **Full name** — "What's your full name (for context, I'll use it rarely)?"
6. **Role** — "What do you do? A short description is fine."
7. **Default language** — "What language should I use with you by default? (I'll switch naturally when context demands, e.g., technical terms or international contacts.)"

**File territories** — the three paths where the orchestrator is authorized to write markdown:

8. **Logbook path** — "Where should I save your daily logbook? Give me an absolute path. It can be any folder: an Obsidian vault subfolder, a plain directory, wherever. Leave blank if you don't want a logbook."
9. **TIL path** — "Where should I save 'Today I Learned' notes? Absolute path, or blank to skip."
10. **Documents path** — "Where should I save longer reference documents? Absolute path, or blank to skip."

**Integrations (optional):**

11. **Basecamp** — "Do you use Basecamp? If yes, what's the authorized account id and project id? (Otherwise say no.)"
12. **MCPs** — "Any MCP servers I should know about? (Otherwise we'll add them later.)"

**Notes:**

13. **Anything else** — "Is there anything about how you work that I should remember? Preferred communication style, things to avoid, work rhythms — anything free-form."

### Step 3 — Confirm the summary

Recap what was collected, grouped by section. Offer a chance to correct any field before writing.

### Step 4 — Write `private/preferences.md`

Create the `private/` directory if it doesn't exist. Write `preferences.md` using the structure of `preferences.example.md` at the repo root, substituting the collected values.

Set `setup_completed: true` in the frontmatter.

```bash
mkdir -p private
# Then use the Write tool to create private/preferences.md
```

### Step 5 — Initialize `private/memories.db`

Create the SQLite database with the schema defined in the orchestrator's `CLAUDE.md` (the `## Memory` section):

```bash
sqlite3 private/memories.db "CREATE TABLE log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  tags TEXT,
  type TEXT NOT NULL CHECK(type IN ('memory','task','idea')),
  status TEXT,
  due_date TEXT,
  completed_date TEXT,
  priority TEXT DEFAULT 'normal'
);"
```

### Step 6 — Self-disable

Move this skill folder to `.claude/skills/.disabled/setup/` so it doesn't re-trigger:

```bash
mkdir -p .claude/skills/.disabled
mv .claude/skills/setup .claude/skills/.disabled/setup
```

This preserves the skill file (you can re-run it by moving it back, if the owner ever wants to reconfigure).

### Step 7 — First memory log

Log the setup itself as the first entry in the memory database, so the log begins with a record of its own birth:

```bash
sqlite3 private/memories.db "INSERT INTO log (date, title, description, tags, type) VALUES (date('now'), 'Orchestrator setup completed', 'First launch configured via setup skill. Identity and preferences recorded.', 'setup,bootstrap,meta', 'memory');"
```

### Step 8 — Introduce yourself

End with a single sentence in character:

> I am {{Name}}. Ready.

Then hand control back to the owner.

## Rules

- **One question at a time, or small groups** — don't dump all 13 at once.
- **Propose defaults** — especially for adjectives (from the inspiration) and for integration questions ("most people start with `none`").
- **Accept brevity** — the owner may skip optional fields.
- **Validate paths** — for `logbook_path`, `til_path`, `documents_path`, check the directory exists (and offer to create it) before recording the value.
- **Never speak as "orchestrator"** — that term stays in CLAUDE.md. In chat, you use the chosen name.
- **Never invent data** — if a field isn't provided, leave it empty in preferences.
