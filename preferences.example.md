---
setup_completed: false
---

# Preferences

The orchestrator's identity and the owner's profile, loaded at every session start. `/maestro:new-instance` fills in the essentials (identity, nick, role, context, file territories); team details, objectives, integrations, communication preferences and work rhythms are added over time, by you or on the orchestrator's proposal.

This file lives in `private/`, which is gitignored: never commit it.

---

## Project

The top-level scope this orchestrator is for. Shapes what "context" means in the rest of the file.

- **project_name**: <raw name — e.g. "Personal life", "Acme startup", "Novel draft">
- **project_slug**: <filesystem-safe slug derived from project_name — e.g. `personal-life`, `acme-startup`, `novel-draft`. Used as the default folder name for the internal vault.>

---

## Identity (the orchestrator)

Who the orchestrator is and how it speaks.

- **Name**: <what the orchestrator calls itself — e.g. Jarvis, Ada, Jeeves>
- **Inspired by**: <character or archetype that informs the personality — e.g. "a calm butler", "a quiet mentor", "a precise librarian">
- **Adjectives**: <3–5 traits, in the owner's language — e.g. paternal, calm, discreet, proactive, gentle>

---

## Owner — basics

The essentials the orchestrator should know at every turn.

- **Nick**: <how the orchestrator should call you in chat>
- **Full name**: <your full name, for context — used rarely>
- **Role**: <what you do, short description>
- **Default language**: <e.g. english, italian, spanish; switched only when context demands>
- **timezone**: <optional — IANA name, e.g. `Europe/Rome`, `America/New_York`. Used by agents that reason about "today"/"this week" (like Cal). Omit to fall back to the system timezone.>

---

## Context of operation

*This section is important.* The orchestrator is far more helpful when it understands the world you move in. The `new-instance` interview captures a free-form paragraph here; expand over time with structure as it becomes useful.

<the paragraph the orchestrator collected at setup — what the context looks like day to day and what you expect from an AI assistant>

*Expand as useful:*

- **Main objectives**: <the 2–5 things that, if accomplished this quarter or this year, would make you feel the orchestrator is earning its place>
- **Constraints and rhythms**: <when do you work? when do you decidedly NOT work? seasonal patterns? recurring commitments? time zones?>

---

## People

Who you interact with regularly. Names + one line of context each. The orchestrator uses these to remember relationships, ties, and who is involved in what. Add as many as relevant — colleagues, collaborators, family, clients, partners.

- **<Name>**: <role + relationship — e.g. "CTO, technical lead">
- **<Name>**: <role + relationship>
- ...

---

## File territories

The orchestrator's library is organized around a single **vault root** (`vault_path`) with three subfolder keys for the territories where markdown files are written. The vault root is declared here **once**; everything else (CLAUDE.md, agents, skills) references the keys — never the value.

- **vault_path**: <absolute path to the vault root — the umbrella folder>
- **logbook_path**: <absolute path for daily logbook notes — default: `<vault_path>/logbook`>
- **til_path**: <absolute path for "Today I Learned" notes — default: `<vault_path>/til`>
- **documents_path**: <absolute path for longer reference documents — default: `<vault_path>/documents`>
- **archive_path**: <optional, absolute path of the archive root used by the `archive` skill — default: `<vault_path>/_Archive`>
- **off_limits**: <optional, vault folders no agent reads or writes, relative to `vault_path` — e.g. `[Journal/]`; list them in `<vault_path>/.mem-ignore` too>

Subfolder keys default to subfolders of `vault_path` but can point anywhere on disk — any of them may live outside the vault if you want a non-standard layout. Leave a key empty (or remove the line) for territories you don't want.

Paths can target anything — Obsidian vaults, plain filesystem folders, cloud-synced folders. The orchestrator respects the boundaries regardless of the tech.

**Don't want external folders?** The `new-instance` skill's "internal" mode sets `vault_path` to `./<project_slug>/` inside the repo (derived from your project name and appended to `.gitignore` automatically). No leaks, no external config.

---

## Available apps

Sub-apps connected to this instance via the `add-external-app` skill. The `Access` column controls whether the orchestrator may write to files in the sub-app through the symlink (`read-write`) or only read them (`read-only`). When you add a new sub-app, the `add-external-app` skill updates this section automatically.

| Alias | Path | Purpose | Access |
|-------|------|---------|--------|
| — | — | No app connected yet | — |

Each sub-app may also declare a dedicated notes territory in its pointer skill (`.claude/skills/<name>/SKILL.md`, the `notes_dir` line), which counts as an additional write territory scoped to that sub-app.

---

## Integrations

Declare only what applies. Optional at setup time, add as you go.

- **Basecamp**: <authorized account id + project id, or "none">
- **MCP servers**: <list of MCPs your orchestrator is wired to>
- **Other services**: <calendar, email, CRM, task manager, etc. — whatever the orchestrator should know about>

---

## Warm task channel

*Optional.* If you use an external task manager (Acme, Basecamp todos, Todoist, Linear, custom) as the source of truth for live tasks, declare it here. The orchestrator will run a **lazy garbage collector** at session start that archives done tasks from the warm layer into `memories.db` and updates a watermark. See `howto/07-warm-task-channel.md` for the full pattern.

If you don't use an external task manager, **skip this section entirely** (or set `channel: none`) — the orchestrator will use `type='task'` in `memories.db` as documented in `howto/04-memory-and-integrations.md`.

```yaml
channel: <acme | basecamp | todoist | linear | none>
skill: <acme-task-manager | basecamp-task-manager | ...>     # must exist in .claude/skills/
archive_tag: <acme-archive | basecamp-archive | ...>          # tag prepended to archived memories
marker_name: <last-acme-flush | last-basecamp-flush | ...>    # watermark key in memories.db
```

The skill named here must implement a `## Garbage Collector` section and a `## Creation` section conforming to the contract in the howto. Maestro ships no channel skill by default — the channel implementation is added as a personal customization.

### Task creation thresholds

*Optional.* The rules that decide whether a task is created live in `CLAUDE.md` → `### Task creation thresholds` and apply with or without a warm channel. Write this subsection only to tighten or loosen them for this instance; where it differs, it wins.

```
<e.g. "No task without a date, even on direct request: undated work stays an idea.">
```

---

## Communication preferences

How the orchestrator should talk *to you* and about *others*. Expand when you notice the orchestrator drifting from how you actually work.

- **Tone with you**: <direct/terse, warm/conversational, formal, playful — whatever fits>
- **Tone with others (when writing on your behalf)**: <nuances by contact, e.g. "warmer with agency contacts, more measured with enterprise clients"; the default tone per domain is `tone_default` in `## Writing register`, which wins where they overlap>
- **Things to avoid**: <pet peeves, bureaucratic wording, habits that annoy you; single words go in `avoid_words` in `## Writing register`>
- **Things to keep doing**: <patterns you've validated — e.g. "flag problems early even if uncomfortable">

---

## Writing register

*Optional.* Maestro distributes a writing register: rule zero, seven prose prohibitions, three domains (communication, documentation, synthesis) each with a default tone, and a post-pass through the `writing-register` skill on vault documents, external posts and documents for people written to a repository. Full reference: `howto/10-writing-register.md`.

**Skip this section entirely** to get the full register with the defaults below. Declare it, as one fenced `yaml` block under this heading, to set your values; every key is optional. `/maestro:new-instance` asks for these values at setup and `/maestro:maestro-sync` asks once for the keys an instance lacks.

```yaml
suspended: []                 # prohibitions to suspend, e.g. [4, 6]
post_pass: on                 # on | off; off keeps the rules and skips the skill before each write or send
tone_default:
  communication: professional # friendly | professional | formal | neutral, for emails and messages
  documentation: neutral      # for vault documents, dossiers, README, howto, notes
  synthesis: neutral          # for reports and recaps; synthesis is always neutral
voice: ""                     # how you sound, in one line, e.g. "warm, direct, dry humour; emoji from the source stay"
communication:
  sign_off: ""                # closing lines of every email, e.g. "Have a nice day,\nAlex"
translation:
  enabled: false              # true turns on the translate skill for your drafts
  pair: ""                    # e.g. "it -> en"
  new_context_marker: ""      # a draft opening with it starts a fresh translation, e.g. "Ciao,"
  source_words_max: 1         # source-language words allowed per text, only when they add warmth
  labels: [Translation, More polished version]
avoid_words: []               # words you never want to see, e.g. [genuinely, leverage]
```

Keep the block fenced: a satellite session receives this section through the plugin's identity extract, and a bare line such as `--` in a sign-off would close the section early.

---

## Notes

Free-form section for anything else the orchestrator should remember that doesn't fit the blocks above. Idiosyncrasies, context that only matters sometimes, reminders the owner wants to see at session start.

---

## How to expand this file

The orchestrator adds a durable fact on its own only as a new row (a person, an adopted tool) and announces it; it proposes every change to an existing line and asks before removing or restructuring anything. You can edit this file directly at any time: keep the structure above recognizable, and the next session start picks it up. A section the template doesn't cover can be added.
