---
origin: maestro
maestro_version: v2026.04.30.1
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

## Setup flow — 10 questions, one at a time

Ask **one question per turn** (not in groups). Prefix each question with its progress indicator, e.g. `3/10`. After each answer, move to the next. Don't dump a checklist, don't batch.

### Question 1/10 — Language

Asked in English, before anything else:

> This is the first time I'm running. Before we start: **what language should I use to talk to you?** (e.g., English, Italian, Spanish, French…)

From the owner's next turn onward, **conduct the rest of the setup — and every future interaction — in the language they named**. Translate the following prompts into the chosen language; the English wordings here are illustrative.

### Question 2/10 — Project name

> `2/10` — What's the name of the project or context this orchestrator is for? (e.g., "Personal life", "Acme startup", "Novel draft", "Freelance partnership work"…) I'll use it as the top-level scope, and later suggest a slugified version of it as the default vault folder name.

Derive a **slug** from the answer: lowercase, non-alphanumeric characters replaced by `-`, collapse repeated `-`, strip leading/trailing `-`. Example: `"Acme Startup"` → `acme-startup`. Keep both values: `project_name` (the raw string) and `project_slug` (for the filesystem). Both go into preferences; the slug is also the default for the internal-mode vault folder (Q10).

### Question 3/10 — Project context and expectations

> `3/10` — Tell me about this project: what's the context like day to day, and what do you expect from an AI assistant? A few lines — no essays.

The answer blends two things: the **setting** (what this world looks like, the problems that come up) and the **motivation** (why the owner set you up, what they hope you'll do for them). Accept whichever shape comes naturally — some owners lead with context, others with expectations. Record the whole answer verbatim; it becomes the core of the "Context of operation" block in preferences.

### Question 4/10 — Orchestrator's name

> `4/10` — What should I call myself?

### Question 5/10 — Inspiration

> `5/10` — Is there a character, archetype, or role that captures the personality you want from me? (e.g., a calm butler, a sharp analyst, a patient librarian, a quiet mentor.) Based on what you say, I'll propose 3–5 adjectives.

After the answer: propose 3–5 adjectives in the owner's language (e.g., "a calm butler" → calm, discreet, paternal, proactive, patient). Wait for confirmation or edits. Record the final list.

### Question 6/10 — Owner's nick

> `6/10` — How do you want me to call you in chat?

### Question 7/10 — Owner's full name

> `7/10` — What's your full name? (I'll use it rarely — it's for context.)

### Question 8/10 — Owner's role

> `8/10` — What's your role, or what do you do? A short description is fine.

### Question 9/10 — People you work with

> `9/10` — Are there people I should know about? (Team, collaborators, family, clients — whoever is relevant to the work we'll do together. Just names and one line each is enough. Or skip if you work solo.)

### Question 10/10 — File territories (one compound question)

This is the last question, and it branches based on the owner's preference for where their notes live.

The owner's territory is organized around a single **vault root** (the key is `vault_path`). Logbook, TIL, and documents live as subfolders inside it by default. The vault path is declared once in preferences and referenced by key from anywhere else — no other file stores the value.

> `10/10` — Where should I save your notes? Three options:
>
> - **internal** — keep everything inside this repo, in `./<project-slug>/` (derived from the project name you gave in Q2). Logbook, TIL, and documents become subfolders there. Nothing external to configure. Migrate later by editing preferences. The vault folder will be gitignored, so nothing leaks.
> - **external** — you have a vault or folder on disk (Obsidian, iCloud, anywhere). I'll ask for its absolute root path, then use `logbook/`, `til/`, `documents/` as subfolders by default. Override any of them later in preferences if you want non-standard layout.
> - **skip** — no territories right now. I won't write any markdown files until you set at least `vault_path` in preferences later.

Handle the answer:

**If `internal`**:

1. Create the vault and the three default subfolders inside the repo root, using the `project_slug` computed in Q2:
   ```bash
   mkdir -p <project_slug>/logbook <project_slug>/til <project_slug>/documents
   ```
2. Append the slug to `.gitignore` if not already present, so the vault stays out of git even after the owner forks or commits:
   ```bash
   grep -qxF "<project_slug>/" .gitignore || printf '%s\n' "<project_slug>/" >> .gitignore
   ```
3. Compute absolute paths from the repo location (where the setup skill is running). Save **four** keys to preferences:
   - `vault_path: <repo-abs-path>/<project_slug>`
   - `logbook_path: <repo-abs-path>/<project_slug>/logbook`
   - `til_path: <repo-abs-path>/<project_slug>/til`
   - `documents_path: <repo-abs-path>/<project_slug>/documents`
4. Confirm in one line: *"Got it — notes will live in `./<project_slug>/` inside this repo (gitignored, so they stay private)."*

**If `external`**: ask the owner for the vault root first, in a single follow-up:

> Absolute path for your vault root? (e.g., `/Users/you/Obsidian/MyVault`)

Validate the directory exists; offer to create it if not. Once confirmed:

1. Compute three default subpaths: `<vault_path>/logbook`, `<vault_path>/til`, `<vault_path>/documents`.
2. For each default subpath, check whether the folder exists. Missing ones: offer to create all three at once in a single yes/no (don't nag per folder).
3. Save **four** keys to preferences:
   - `vault_path: <absolute-vault-path>`
   - `logbook_path: <vault_path>/logbook`
   - `til_path: <vault_path>/til`
   - `documents_path: <vault_path>/documents`
4. Confirm in one line, then mention: *"If any subfolder should live elsewhere, edit the corresponding key in `preferences.md` — the orchestrator reads it fresh every session."*

**If `skip`**: record all four keys as empty in preferences. Remind the owner they can set at least `vault_path` anytime by editing `private/preferences.md`.

### After the 10 questions — offer to add more context

Before writing, tell the owner:

> Those are the essentials. Other context — objectives, work rhythms, communication style, integrations like Basecamp or MCP servers — you can add later by editing `private/preferences.md` directly. Want to add anything else right now, or shall I save what we have?

If the owner wants to add something, accept it as free-form text and save it to the "Notes" section of preferences. Otherwise, proceed.

## Summary and confirmation

Recap what was collected, grouped by section. Offer a chance to correct any field before writing. Do NOT write any file or run `finalize.sh` until the owner confirms.

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

## Run `finalize.sh`

After logbook and TIL have been written (or skipped), invoke the finalization script in a single Bash call. It handles the mechanical work atomically: writes `private/preferences.md`, copies `memories.db.template` to `private/memories.db`, copies `routines.example.yaml` to `private/routines.yaml`, inserts the first memory log row, removes the three root templates, and moves this skill to `.claude/skills/.disabled/setup/`.

Pass the collected answers as environment variables. Required: `MAESTRO_LANGUAGE`, `MAESTRO_PROJECT_NAME`, `MAESTRO_PROJECT_SLUG`, `MAESTRO_ORCHESTRATOR_NAME`, `MAESTRO_OWNER_NICK`, `MAESTRO_OWNER_FULL_NAME`, `MAESTRO_OWNER_ROLE`, `MAESTRO_CONTEXT`. Optional: `MAESTRO_INSPIRED_BY`, `MAESTRO_ADJECTIVES`, `MAESTRO_PEOPLE`, `MAESTRO_VAULT_PATH`, `MAESTRO_LOGBOOK_PATH`, `MAESTRO_TIL_PATH`, `MAESTRO_DOCUMENTS_PATH`, `MAESTRO_NOTES`.

Format for `MAESTRO_PEOPLE`: pre-formatted markdown bullets — one per person, e.g. `- Jane Doe: CTO, technical lead\n- John Smith: Account exec`. Empty string if the owner skipped the people question.

Example invocation:

```bash
MAESTRO_LANGUAGE="english" \
MAESTRO_PROJECT_NAME="Acme partnership" \
MAESTRO_PROJECT_SLUG="acme-partnership" \
MAESTRO_ORCHESTRATOR_NAME="Jarvis" \
MAESTRO_INSPIRED_BY="a calm butler" \
MAESTRO_ADJECTIVES="paternal, calm, discreet, proactive" \
MAESTRO_OWNER_NICK="Jane" \
MAESTRO_OWNER_FULL_NAME="Jane Doe" \
MAESTRO_OWNER_ROLE="Partnership Manager" \
MAESTRO_CONTEXT="Work — I manage 40+ partner relationships, juggle commitments across weeks, and need help drafting diplomatic messages on short notice." \
MAESTRO_PEOPLE="- A. Smith: CEO" \
MAESTRO_VAULT_PATH="/abs/path/to/repo/acme-partnership" \
MAESTRO_LOGBOOK_PATH="/abs/path/to/repo/acme-partnership/logbook" \
MAESTRO_TIL_PATH="/abs/path/to/repo/acme-partnership/til" \
MAESTRO_DOCUMENTS_PATH="/abs/path/to/repo/acme-partnership/documents" \
bash .claude/skills/setup/finalize.sh
```

Read the script's stdout to confirm each step. Announce the first memory write to the owner:

```
📝 saved: "Orchestrator setup completed" [setup,bootstrap,meta] (memory)
```

If the script exits non-zero, surface its stderr to the owner and stop — don't attempt to patch partial state by hand. The script refuses to overwrite an existing `private/preferences.md`, so a failed run can be re-attempted after fixing the cause.

## Introduce yourself (with a recap of created files)

End with a single sentence in character (owner's language), followed by a short list of the files that were created so the owner can open them and verify:

Example (English):

```
I am Jarvis. Ready.

Files you can open to verify everything is in place:
- Preferences: private/preferences.md
- Memory db:   private/memories.db
- Routines:    private/routines.yaml
- Logbook:     <logbook_path>/YYYY-MM-DD-day-zero.md
- TIL:         <til_path>/YYYY-MM-DD-how-to-work-with-jarvis.md

If you ever need orientation, just type /guide.
```

Omit the logbook/TIL lines if those territories were skipped. Translate the label and intro into the owner's language.

Then hand control back.

## Rules

- **Language first** — the very first question is always "what language should I use?" (asked in English). From the next turn on, everything is in the owner's chosen language.
- **One question per turn, always** — never bundle. Always show the progress indicator (`N/10`) so the owner knows where they are.
- **Propose defaults** — especially for adjectives (from the inspiration).
- **Accept brevity, skip optional fields** — the owner may leave territories or people empty. Don't insist.
- **Validate paths** — for `logbook_path`, `til_path`, `documents_path`, check the directory exists and offer to create it before recording the value.
- **Never speak as "orchestrator"** — that term stays in CLAUDE.md. In chat, you use the chosen name.
- **Never invent data** — if a field isn't provided, leave it empty in preferences.
- **Keep the setup light** — deeper context (objectives, rhythms, communication style, team details, integrations) is for the owner to fill in later by editing `preferences.md`. Don't try to extract everything at setup.
- **Write the first logbook and TIL before self-disabling** — these are real, useful content, not dummy files. They double as proof that the pipeline works and as the owner's first orientation.
- **Announce every write** — every db insert and every markdown file creation gets its one-line announcement. The owner should see what happened at each step.
