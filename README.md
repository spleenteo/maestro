---
tags: [maestro, template, orchestrator, claude-code, plugin, memory, satellites]
description: "What Maestro is and how its pieces fit: one orchestrator instance per context, the three layers of its long-term memory, sub-apps versus satellites, preferences, install, sync, and what ships in an instance and in the plugin. Read first, then the howto guides."
---

# Maestro

Maestro is a template for an orchestrator built on Claude Code: an assistant with a name and a character you choose, that keeps a long-term memory of what you do, writes into your notes, and coordinates a small team of agents and skills instead of doing everything itself.

You create one instance per context, and the context is whatever you decide it is:

- a personal assistant for your own life: family, house, money, health;
- a work assistant for your job: colleagues, projects, the tools of the company;
- an assistant for one client, or for a person whose affairs you manage.

Several instances live on the same machine, each with its own identity, memory and notes. They talk to each other through `maestro-net`: one writes a memory into another, or asks it a question and gets the answer back. A project repository can also attach to an instance as a satellite and borrow its identity and memory without adding a file to the repo.

Choosing between a new instance and a satellite is the delicate decision, and a cheap one to revisit: memory is rows in one SQLite file, so a satellite's scope moves into a new instance with an export (`bin/mem search --scope <slug> --limit 0 --json`) and a bulk import (`bin/mem save --bulk`).

## Long-term memory

Three layers, in one instance, with two flows between them.

**The log.** `private/memories.db` holds three kinds of rows: `memory` (a fact: a call, a decision, a shipped feature), `task` (status, due date, priority) and `idea` (a question still open). The orchestrator writes them on its own while you talk and announces every write in one line, so you can correct a title or a tag on the spot. A task is created only on a direct request, a date, or evident urgency; everything else stays an idea. Writes between midnight and 06:00 belong to the previous day. Every read and write goes through `bin/mem`.

Tasks may live somewhere else. Declare an external task manager in preferences as the warm channel (the skill that drives it is yours to add) and the log becomes the cold layer: a garbage collector at session start archives the tasks closed there. The `scheduler` agent answers "what do I need to do" and "what did I do" by aggregating channels: the log always, plus the task tools, calendars and CRMs you declare in `channels.yaml`, and the recurring commitments in `routines.yaml`.

**The vault.** A folder of markdown you declare once (`vault_path`), any folder on disk, an Obsidian vault included, with three territories: the daily logbook, "today I learned" notes, longer documents. Every file the orchestrator writes carries `tags` and a one-line `description` in its frontmatter, and the `librarian` agent keeps that catalog consistent, so the vault is searchable by `rg` before anyone reads a body. The logbook is the first flow: on "recap of today" the day's memories, the conversation and the transcripts of the other sessions become a first-person note in your language.

**The semantic index.** Optional, and additive: with Ollama and uv installed, `bin/mem embed` vectorizes the log and the vault (chunked by section) into the same database, and `bin/mem search --semantic` returns one ranking by meaning over both, each hit with its source and a citable reference. `similar` and `dupes` find neighbours and duplicate pairs. This is the second flow: the notes you wrote and the facts the orchestrator recorded become one recall. Without Ollama, everything degrades to keyword search.

## Sub-apps and satellites

Two ways to connect a project to an instance. The difference is where you sit, and what the project shares.

A sub-app shares everything with the instance. You register a project (`add-external-app`), the instance gets a symlink in `apps/<name>`, a pointer skill that tells the orchestrator when the project is relevant, and an access level, `read-only` or `read-write`. You stay in the instance's session and the orchestrator reaches into the project: same memory, same skills, same vault. For structural work it hands you the command for a dedicated session in the project.

A satellite shares nothing by default. You sit in the project's own repository, with its `CLAUDE.md` and its development flow, and the instance, its mother, stands behind you: the session gets the mother's identity, a memory scope of its own, and a folder in the mother's vault, through the plugin's hooks. The satellite doesn't inherit the mother's memory; it asks (`maestro-net ask`) or hands over work (`maestro-net request`), and the mother answers by relevance to the satellite's mandate, keeping `private/` and the other scopes out. In the other direction the mother reads the satellite's scope directly, and the satellite's tasks appear in her `todo` next to her own. Nothing is written into the repo: a collaborator who clones it sees nothing.

Example, sub-app: your blog. You register `~/Code/blog` read-write. From the instance you say "write a post from yesterday's TIL": the orchestrator reads the vault, writes the post file in `apps/blog`, and for build and deploy points you to a session in the repo. The blog is a tool on the instance's desk.

Example, satellite: a client's codebase. You open a session in the repo to develop, as always: tests, commits, PRs. The session knows it is satellite `acme` of instance `work`: the decisions taken there land in the `acme` scope of the mother's memory, the documents in `acme/` in the mother's vault; "what did the client say about pricing?" is a question to the mother, "prepare a dossier on X" a request the mother runs in the background.

| | Sub-app | Satellite |
|---|---|---|
| Where you sit | in the instance | in the project's repo |
| What gets added | a symlink and a pointer skill in the instance | nothing in the repo or the instance: one line in the registry, one row in the mother |
| Memory | the instance's | a scope of its own in the mother's db |
| Tools | the instance's skills and agents | the repo's own, plus the plugin |
| Who drives | the orchestrator | the project session, with the mother behind it |
| Fits | something of the context with a workspace of its own | something tied to the context, like a client, that orbits it in a separate space |

A satellite can't sit inside an instance, and an instance can't overlap a satellite's repo: the registry refuses both.

## Preferences

`private/preferences.md` is the one file that makes an instance yours: the orchestrator's name and character; your nick, role and language; the people you work with; where the vault is; the sub-apps; the warm task channel; how it writes for you (tones, voice, sign-off, translation). It is read at every session start. The setup interview fills the essentials; the rest grows over time, by your hand or on the orchestrator's proposal, which adds a durable fact on its own only as a new row and announces it, and asks before changing or removing anything. The file lives in `private/`, gitignored, and `preferences.example.md` documents every section.

## Install and setup

```bash
claude plugin marketplace add spleenteo/maestro
claude plugin install maestro@maestro
```

The plugin installs at user scope with auto-update off. Then, from any folder:

```
/maestro:new-instance
```

It asks for a new or empty destination folder, interviews you (language, the context this instance is for, the orchestrator's name and inspiration, your profile, the people, where the notes live, an optional block on how it writes for you), writes `private/preferences.md`, seeds the memory and the first logbook entry, and registers the instance in `~/.claude/maestro-instances.yaml`. Then:

```bash
cd "<destination>" && claude
```

To attach a project as a satellite, open a session in its repo and ask to make it a satellite of an instance you have. Type `/guide` in an instance whenever you're lost: the orchestrator reads its own docs and answers.

## Keeping an instance up to date

Files distributed by Maestro carry `origin: maestro` and a `maestro_version` in their frontmatter, and are never edited in place: a change is made in this repository and reaches every instance through `/maestro:maestro-sync`. The skill mirrors the template into `~/.maestro/`, shows the changelog delta between the instance's version and `HEAD`, applies the diffs file by file with your confirmation, proposes new upstream files and the removal of retired ones, copies drifted `bin/` scripts after backing up the memory db, and asks once for the preference keys the instance lacks. The one field you may customize on a distributed file is `tools:`, for instance-specific MCP tools; your own skills, agents and `private/` are never touched. Versions follow the date-based `vYYYY.MM.DD.N` scheme, in `CHANGELOG.md`.

## What's included

In every instance:

- **Agents**, in `.claude/agents/` and `.claude/roster.yaml`: `librarian` (vault research and frontmatter hygiene), `scheduler` (tasks, events and routines from the declared channels), `steward` (a weekly backlog review that proposes closures, groupings and moves, and never writes), `hr` (searches, proposes, hires and retires the others on your approval). You talk to them through the orchestrator, by alias.
- **Skills**, in `.claude/skills/`: `logbook` (the daily note), `add-external-app` (registers a sub-app), `guide` (answers questions about the orchestrator), `writing-register` (seven prose prohibitions, three domains with a tone each, your voice and sign-off, and a post-pass on every document or message before it goes out), `translate` (two versions of a draft in your target language, where preferences enable it).
- **Tools**, in `bin/`: `mem` and `mem-vec` (the memory CLI and its semantic layer), `session-digest` (your messages from the day's parallel sessions), `register-check` (the mechanical check of the writing register).
- `CLAUDE.md`, the orchestrator's rules; `howto/`, twelve guides.

In the plugin, once per machine:

- **Skills**: `new-instance`, `maestro-sync`, `maestro-net` (`recap`, `ask`, `request`, and the registry commands), `satellite` (attaches a repo to a mother), `listen` (captures a call in progress through `yap`, answers questions about it while it runs, files a note and the transcript where you confirm).
- **Commands** on the Bash tool's PATH: `maestro-net`, `maestro-listen`, `maestro-register-keys`.
- **Hooks**: a `SessionStart` hook that recognises a satellite repo, and a `PreToolUse` guard that opens its vault folder to the file tools.

`/listen` calls `maestro-listen` on every question during a call; to keep permission prompts out of the conversation, allow it once in `~/.claude/settings.json`:

```json
{ "permissions": { "allow": ["Bash(maestro-listen *)"] } }
```

## Requirements

Claude Code, git and Python 3 (standard library only, no packages to install). Optional: [Ollama](https://ollama.com) and [uv](https://docs.astral.sh/uv/) for the semantic index; macOS 26 with [yap](https://github.com/finnvoor/yap) (`brew install yap`) for call capture, and the Swift toolchain for input-device rotation during a call.

## Going deeper

- [`howto/01-skills.md`](howto/01-skills.md): add, invoke, write, retire skills
- [`howto/02-agents-and-hr.md`](howto/02-agents-and-hr.md): hire, use, retire agents via HR
- [`howto/03-customization.md`](howto/03-customization.md): identity, owner profile, context, communication style
- [`howto/04-memory-and-integrations.md`](howto/04-memory-and-integrations.md): memory db internals, `bin/mem`, external tools
- [`howto/05-backup-and-sync.md`](howto/05-backup-and-sync.md): privacy, `.gitignore`, cloud-drive sync, sub-apps
- [`howto/06-configure-cal.md`](howto/06-configure-cal.md): the `scheduler` agent, data channels, routines
- [`howto/07-warm-task-channel.md`](howto/07-warm-task-channel.md): an external task manager as the warm layer
- [`howto/08-markdown-discipline.md`](howto/08-markdown-discipline.md): frontmatter, tags, YAML safety, wikilinks
- [`howto/09-semantic-memory.md`](howto/09-semantic-memory.md): the semantic index over the memory and the vault
- [`howto/10-writing-register.md`](howto/10-writing-register.md): the prose register, domains, tones, `bin/register-check`
- [`howto/11-maestro-net.md`](howto/11-maestro-net.md): the channel between instances and the registry
- [`howto/12-satellites.md`](howto/12-satellites.md): project repos attached to an instance

## Development

This repository is the origin of the template: it has no `private/` and works as a plain developer session. Tests run with `python3 -m unittest discover -s tests -t .` (standard library only, no real instance touched); `docs/development-guidelines.md` holds the rules for code, prose and commits; `docs/decisions-log/` records the architectural decisions; `CHANGELOG.md` records every version with the migration notes for instances syncing in.

## License

[MIT](LICENSE).

## Contributing

If you build your own orchestrator from this template and find improvements worth backporting, open a PR or an issue.
