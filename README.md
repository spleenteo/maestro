---
tags: [maestro, template, orchestrator, claude-code, plugin, satellites, memory]
description: "What Maestro is and every feature it ships: the orchestrator instance, its memory and vault, the agents and skills, the Claude Code plugin with new-instance, maestro-sync, maestro-net, satellites and listen. Read first, then the howto guides."
---

# Maestro

Maestro is a template for a personal orchestrator built on Claude Code: one assistant, with a name and a character you choose, that keeps a memory of what you do, writes into your notes, and coordinates a small team of agents and skills instead of doing everything itself. You create an instance per context of your life (home, a client, a job) and each instance keeps its own identity, memory and notes. A Claude Code plugin ties the instances together and makes project repositories borrow an instance without adding files to them.

## The pieces

- **Instance**: a folder with `CLAUDE.md` (the orchestrator's rules), `private/preferences.md` (its identity and your profile, gitignored), `private/memories.db` (its memory), `bin/` (the CLI tools), and the shipped agents and skills. Created by `/maestro:new-instance`.
- **Vault**: the folder where the orchestrator writes markdown: a daily logbook, "today I learned" notes, longer documents. Any folder on disk, an Obsidian vault included, declared once in preferences.
- **Memory**: a SQLite log of memories, tasks and ideas, written proactively during conversations and read back for reports. Every access goes through `bin/mem`.
- **Plugin**: the `maestro` Claude Code plugin, installed once per machine. It carries the commands that must work in any folder: creating an instance, updating it, talking to other instances, attaching a repo as a satellite, listening to a call.
- **Satellite**: a project repository attached to an instance, its mother. The repo gets the mother's identity, its own memory scope and a folder in the mother's vault, with no file added to the repo.
- **Registry**: `~/.claude/maestro-instances.yaml`, the machine's list of instances and satellites, maintained by the plugin.

## Requirements

Claude Code, git and Python 3 (standard library only). Optional: [Ollama](https://ollama.com) and [uv](https://docs.astral.sh/uv/) for the semantic layer; macOS 26 with [yap](https://github.com/finnvoor/yap) (`brew install yap`) for live call capture, and the Swift toolchain for input-device rotation during a call.

## Install

```bash
claude plugin marketplace add spleenteo/maestro
claude plugin install maestro@maestro
```

The plugin installs at user scope with auto-update off. Then, from any folder:

```
/maestro:new-instance
```

The skill asks for a new or empty destination folder, then interviews you: your language, the project this instance is for, its context, the orchestrator's name and the character that inspires it, your nick, name and role, the people you work with, where the notes live (a folder inside the instance, a folder of your own such as an Obsidian vault, or none for now), and an optional block on how it writes for you (tones, voice, sign-off, translation). It writes `private/preferences.md`, seeds the memory with a first row, writes the first logbook entry and the first TIL, and registers the instance in the registry. Then:

```bash
cd "<destination>" && claude
```

Type `/guide` whenever you're lost: the orchestrator reads its own docs and answers.

## A day with your orchestrator

- "Goodmorning": it greets you in character, runs the task manager's garbage collector when you have one, and reads the plan for the day from tasks and memories.
- "Segna che ho chiamato Anna" / "Remember that the deploy went out": a memory, announced in one line right after the write.
- "Remind me to send the deck by Friday": a task, in your task manager when preferences declare one, in the memory otherwise. An undated, unurgent "I should…" stays an idea until you decide.
- "What do I need to do this week?": the `scheduler` agent (Cal) aggregates tasks, events and routines from the channels you wired.
- "Write a reply to the client": the reply is drafted under the writing register, in the tone preferences set for emails, with your sign-off.
- "Recap of today": the `logbook` skill writes the daily note into your vault, reading the memory and the day's parallel sessions.
- "Add `~/Code/blog` as a sub-app": the `add-external-app` skill links the project so the orchestrator can work in it.
- `/maestro:maestro-sync`: pulls the latest template into the instance, file by file, with your confirmation.

## What ships in an instance

- `CLAUDE.md`: role, session start, routing, delegation, memory behaviour, markdown discipline, writing register. Generic, no owner data.
- `private/preferences.md`: identity, owner profile, file territories, available apps, integrations, warm task channel, communication preferences, writing register values. `preferences.example.md` documents every section.
- `private/memories.db`, seeded from `memories.db.template`; `private/routines.yaml`, seeded from `routines.example.yaml`.
- Agents in `.claude/agents/`, registered in `.claude/roster.yaml`: `librarian` (Olivier: vault research and frontmatter hygiene), `scheduler` (Cal: tasks, events and routines from the channels in `.claude/agents/data/channels.yaml`), `steward` (Della: a weekly backlog review that proposes closures, groupings and moves, never writes), and `hr` (hires and retires the others).
- Skills in `.claude/skills/`: `logbook`, `add-external-app`, `guide`, `writing-register`, `translate`.
- `bin/mem` and `bin/mem-vec` (the memory CLI and its semantic layer, with `bin/mem_schema.py`), `bin/session-digest` (the owner's messages from the day's sessions), `bin/register-check` (the mechanical check of the writing register).
- `howto/`: twelve guides, listed below.

## Features

**Memory.** Three row types: `memory` (a fact), `task` (with status, due date, priority), `idea` (an open question). The orchestrator writes without being asked when work completes, when you tell it something happened, when you list things to do, when an idea emerges; every write is announced in one line. A task is created only on a direct request, a date, or evident urgency; everything else stays an idea. Writes between midnight and 06:00 belong to the previous day. `bin/mem` covers saves, updates, reports (`today`, `todo`, `overdue`, `stats`), search with filters, markers and bulk writes.

**Vault and markdown discipline.** Every file the orchestrator writes carries `tags` and a one-line `description` in its frontmatter, so it can be found by `rg` before anyone reads its body. Three territories (`logbook_path`, `til_path`, `documents_path`) under one `vault_path`; nothing is written outside them without your yes.

**Logbook.** The daily note, written on "recap of today" from the memory, the conversation and the transcripts of the other sessions of the day, in your language and first person.

**Writing register.** Seven prohibitions on every text written for a person (no meta-commentary, no sycophantic concessions, no negative parallelism, no em dash as a pause, no bold as emphasis, no rhythmic triads, no judgment as tone of voice), three domains with a default tone each (communication, documentation, synthesis), your voice and sign-off, and a post-pass on every document, post or README before it goes out. `translate` returns two versions of a draft in your target language when preferences enable it.

**Agents and HR.** Craft agents live in `.claude/agents/` and in the roster; you talk to them through the orchestrator, by alias. HR searches the filesystem, the marketplace and GitHub, proposes, and installs or retires on your approval.

**Scheduler channels and routines.** Cal reads `channels.yaml` (the memory always; task tools, calendars and CRMs when you declare them) and `private/routines.yaml` (recurring commitments) to answer "what do I need to do" and "what did I do".

**Sub-apps.** An external project registered as `apps/<name>` (a symlink) with a pointer skill and an `access` level: `read-only` or `read-write`. The orchestrator works there for small edits and hands you the command for a dedicated session when the work is foundational.

**Warm task channel.** An external task manager as the live layer of tasks (`memories.db` stays the cold one), declared in preferences with the skill that drives it; a lazy garbage collector at session start archives the tasks closed there.

**Semantic layer.** With Ollama and uv, `bin/mem search --semantic` recalls by meaning over the memory and the vault (chunked by section), `similar` and `dupes` find neighbours and duplicates, `embed` keeps the vectors current. Without them, everything degrades to keyword search.

**maestro-net.** `maestro-net recap <instance> "…"` writes a memory into another instance; `maestro-net ask <instance> "…"` asks it a question headless; from a satellite, `maestro-net request "…"` opens a background session in the mother. The registry's `accepts` field says which verbs each instance admits; the channel carries memories and questions, never permissions.

**Satellites.** In a project repo, "make this repo a satellite of home" runs the plugin's `satellite` skill: it registers the repo with its role (type, mandate, method, constraints, vault folder) in the mother and in the registry. From then on, every session opened in the repo gets the mother's identity, its own memory scope (`MEM_SCOPE`) and write access to its vault folder, through the plugin's hooks. The mother answers the satellite's questions by relevance to its mandate.

**Listen.** `/listen` captures a call in progress (system audio plus microphone) through `yap`, keeps a transcript growing on disk, answers questions about what has been said so far, and files a note plus the raw transcript where you confirm at close. Works in an instance, in a satellite and in any folder.

**Updates.** Files distributed by Maestro carry `origin: maestro` and a version. `/maestro:maestro-sync` mirrors the template, shows the changelog delta, and applies the diffs file by file with your confirmation; the only field you may customize on a distributed file is `tools:`.

## The plugin

`plugins/maestro/` holds the plugin, published through `.claude-plugin/marketplace.json`:

- skills: `new-instance`, `maestro-sync`, `maestro-net`, `satellite`, `listen`
- commands on the Bash tool's PATH: `maestro-net`, `maestro-listen`, `maestro-register-keys`
- hooks: a `SessionStart` hook that recognises a satellite repo, and a `PreToolUse` guard that opens its vault folder to the file tools

`/listen` calls `maestro-listen` on every question you ask during a call. To keep permission prompts out of the conversation, allow it once in `~/.claude/settings.json`:

```json
{ "permissions": { "allow": ["Bash(maestro-listen *)"] } }
```

## Going deeper

- [`howto/01-skills.md`](howto/01-skills.md): add, invoke, write, retire skills
- [`howto/02-agents-and-hr.md`](howto/02-agents-and-hr.md): hire, use, retire agents via HR
- [`howto/03-customization.md`](howto/03-customization.md): identity, owner profile, context, communication style
- [`howto/04-memory-and-integrations.md`](howto/04-memory-and-integrations.md): memory db internals, `bin/mem`, external tools
- [`howto/05-backup-and-sync.md`](howto/05-backup-and-sync.md): privacy, `.gitignore`, cloud-drive sync, sub-apps
- [`howto/06-configure-cal.md`](howto/06-configure-cal.md): the `scheduler` agent, data channels, routines
- [`howto/07-warm-task-channel.md`](howto/07-warm-task-channel.md): an external task manager as the warm layer
- [`howto/08-markdown-discipline.md`](howto/08-markdown-discipline.md): frontmatter, tags, YAML safety, wikilinks
- [`howto/09-semantic-memory.md`](howto/09-semantic-memory.md): the semantic layer over the memory and the vault
- [`howto/10-writing-register.md`](howto/10-writing-register.md): the prose register, domains, tones, `bin/register-check`
- [`howto/11-maestro-net.md`](howto/11-maestro-net.md): the channel between instances and the registry
- [`howto/12-satellites.md`](howto/12-satellites.md): project repos attached to an instance

## Development

The repository is the origin of the template: it has no `private/` and works as a plain developer session. Tests run with `python3 -m unittest discover -s tests -t .` (standard library only, no real instance touched); `docs/development-guidelines.md` holds the rules for code, prose and commits; `docs/decisions-log/` records the architectural decisions; `CHANGELOG.md` records every version, in the date-based `vYYYY.MM.DD.N` scheme, with migration notes for instances syncing in.

## License

TBD.

## Contributing

If you build your own orchestrator from this template and find improvements worth backporting, open a PR or an issue.
