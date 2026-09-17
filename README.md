---
tags: [maestro, template, orchestrator, bootstrap, claude-code]
description: Bootstrap template for a personal Claude Code orchestrator, a single interface to a team of agents and skills, configured via interactive first-launch setup.
---

# Maestro

A bootstrap template to scaffold your own personal orchestrator: a Claude Code project that acts as a single interface to a team of agents and skills.

Like a conductor, *maestro* doesn't play the instruments. It coordinates the ones that do. The template is a reusable, owner-agnostic pattern. It is written in English and configured through an interactive first-launch setup.

## What you get

After running `/maestro:new-instance`, you have an orchestrator that:

- Introduces itself with the name and personality you chose
- Reads your profile (role, nick, default language) at every session
- Writes into a vault you declare (`vault_path`) with three note territories as subfolders by default: daily logbook, TIL notes, longer documents. Any filesystem path; Obsidian vault folders welcome but not required.
- Keeps a memory database of what was done, what's to do, and ideas that emerged, as a log of your collaboration
- Can hire craft agents through an HR agent that searches the filesystem, marketplaces, and GitHub for matches
- Applies a frontmatter discipline so the files it writes are searchable by description and tags before anyone reads their body

## What it doesn't do

- No personal data and no hardcoded names
- No domain-specific skills (finance, music, CRM, etc.). You add those over time
- No task-manager, calendar, or email integrations. You configure what you need via preferences

## Install

You need a working installation of [Claude Code](https://claude.com/claude-code) and the `maestro` plugin, which ships `new-instance` (creates an instance), `maestro-net` (cross-talk between instances, see [`howto/11-maestro-net.md`](howto/11-maestro-net.md)) and `listen` (live capture of a call, from any session):

```bash
claude plugin marketplace add spleenteo/maestro
claude plugin install maestro@maestro
```

User scope, auto-update off.

`/listen` calls the `maestro-listen` command on every question you ask during a call. To keep permission prompts out of the conversation, allow it once in `~/.claude/settings.json`:

```json
{ "permissions": { "allow": ["Bash(maestro-listen *)"] } }
```

From any folder, run:

```
/maestro:new-instance
```

`new-instance` asks for a new or empty destination folder, takes the template at the plugin's commit, and interviews you with a short set of questions, starting with your preferred language. From that point on the whole interview runs in that language. In order:

1. **Default language**: how the orchestrator talks to you by default (asked in English)
2. **Project name**: the top-level scope this orchestrator is for (e.g. "Personal life", "Acme startup", "Novel draft"); a slug of it becomes the default vault folder name later
3. **Project context and expectations**: a few lines about what this context looks like day to day and what you expect from an AI assistant
4. **Name of your orchestrator**: what it should call itself
5. **Inspiration**: a character or archetype (real or fictional) that captures the personality you want; the skill proposes 3–5 adjectives based on it, which you accept or tweak
6. **Your nick**: how the orchestrator should refer to you
7. **Your full name**: for context
8. **Your role**: what you do
9. **People you work with** (optional): team, collaborators, family, clients, whoever's relevant
10. **File territories**: where markdown notes should live. `new-instance` writes four keys to preferences: `vault_path` (the root) plus `logbook_path`, `til_path`, `documents_path` as subfolders by default. Three options: internal (vault is `./<project-slug>/` inside the repo, with the slug derived from Q2, gitignored), external (you give an absolute path to a vault on disk, e.g. an Obsidian vault: subfolders default to `<vault_path>/{logbook,til,documents}`), or skip (no territories for now)

After the questions and a quick summary, `finalize.sh` (shipped inside the plugin) handles the mechanical work in one atomic step: writes `private/preferences.md`, copies `memories.db.template` into `private/memories.db`, copies `routines.example.yaml` into `private/routines.yaml`, inserts the first memory log row, and removes the three root templates. The first logbook entry and the first TIL are written just before that: creative content the orchestrator composes in your language. `new-instance` then registers the instance in `~/.claude/maestro-instances.yaml`, so `maestro-net` can reach it.

`cd` into the new folder and start working with your orchestrator:

```bash
cd "<destination>" && claude
```

Any time you feel lost later, type `/guide`, and the orchestrator will read its own docs and answer. (`/help` is a Claude Code built-in command and won't reach this skill.)

## The orchestrator pattern

Every instance built from this template has:

- **`CLAUDE.md`**: defines the orchestrator role, routing, delegation, memory behavior, frontmatter discipline. Generic, with no owner-specific content.
- **`private/preferences.md`**: identity + owner profile + customizations, loaded at every session start. Gitignored.
- **`private/memories.db`**: SQLite log of memories, tasks, ideas. Gitignored.
- **`memories.db.template`**: empty SQLite seed with the schema, copied into `private/` by `new-instance`.
- **`.claude/roster.yaml`**: registry of active craft agents (ships with `librarian` and `scheduler` enrolled).
- **`.claude/agents/`**: the shipped craft agents `hr` (recruiter and manager of the roster), `librarian` (vault research and frontmatter hygiene), `scheduler` (cold data layer for prospective/retrospective questions).
- **`.claude/skills/`**: the hub skills `logbook` (daily note in your configured `logbook_path`), `add-external-app` (registers a sub-app), `guide` (answers questions about the orchestrator), `writing-register` (the prose register in full: loaded before writing an email, a message or a document, and run as the post-pass on the finished text).
- **`bin/mem`**: CLI wrapper for `memories.db` (escape-safe writes, relative dates, reports), backed by `bin/mem-vec` for the optional semantic layer.
- **`bin/session-digest`**: pulls the owner's messages from the day's parallel sessions, for the `logbook` skill.
- **`bin/register-check`**: mechanical check of the writing register prohibitions that carry a syntactic signature.
- **`.claude-plugin/marketplace.json`** and **`plugins/`**: the `maestro` Claude Code plugin, installed separately (see Install above) rather than through `/maestro:maestro-sync`, because it's meant to be visible from every session on the machine, not carried per instance. Currently `plugins/maestro/skills/new-instance` (creates a new instance), `plugins/maestro/skills/maestro-sync` (pulls template updates into an instance), `plugins/maestro/skills/maestro-net` (the cross-talk channel between several Maestro instances, see [`howto/11-maestro-net.md`](howto/11-maestro-net.md)), `plugins/maestro/skills/satellite` with the plugin's hooks (a project repo borrows an instance's identity and memory without files of its own, see [`howto/12-satellites.md`](howto/12-satellites.md)), and `plugins/maestro/skills/listen` with the `maestro-listen` command (live capture of a call in any session: at close it proposes where to file the note, from the vault of an instance or a satellite, and writes only where you confirm).
- **`.gitignore`**: covers `private/`, workspace artifacts, and local settings.

Everything else you add as you use the orchestrator:

- To add a sub-app, invoke the `add-external-app` skill. It creates the symlink in `apps/<name>/`, generates a pointer skill, and updates the "Available apps" section in `private/preferences.md`.
- For a recurring task handled by a specialist, ask your orchestrator. It invokes HR, which proposes an agent and, once you approve, installs it into `.claude/agents/` and the roster.
- A skill your instance needs goes straight into `.claude/skills/`. No ceremony.

## Philosophy

Three principles guide the pattern:

1. **Single interface**: the owner talks only to the orchestrator. No agent speaks directly to the owner. Output from agents is always filtered or synthesized by the orchestrator.
2. **Delegate when it fits, not always**: the orchestrator answers directly to conversational requests. Delegation is reserved for clear matches with registered agents.
3. **Proactive on recurring patterns**: if the same kind of request keeps coming up without a dedicated agent, the orchestrator suggests hiring one. The owner decides.

These live in `CLAUDE.md` under "Role: orchestrator" and carry through every instance.

## Going deeper

After setup, the `howto/` folder has eleven guides:

- [`howto/01-skills.md`](howto/01-skills.md): add, invoke, write, retire skills
- [`howto/02-agents-and-hr.md`](howto/02-agents-and-hr.md): hire, use, retire agents via HR
- [`howto/03-customization.md`](howto/03-customization.md): customize identity, owner profile, context, communication style
- [`howto/04-memory-and-integrations.md`](howto/04-memory-and-integrations.md): memory db internals and how to integrate external tools (Basecamp, Google Calendar, reminders)
- [`howto/05-backup-and-sync.md`](howto/05-backup-and-sync.md): privacy, `.gitignore`, cloud-drive sync, symlinks to external apps/skills/agents
- [`howto/06-configure-cal.md`](howto/06-configure-cal.md): configure the `scheduler` agent (data channels, routines, question types)
- [`howto/07-warm-task-channel.md`](howto/07-warm-task-channel.md): wire an external task manager as the warm layer, with `memories.db` as the cold layer
- [`howto/08-markdown-discipline.md`](howto/08-markdown-discipline.md): frontmatter, tags, descriptions, YAML safety, wikilinks
- [`howto/09-memoria-semantica.md`](howto/09-memoria-semantica.md): the optional semantic layer over `memories.db` and the vault
- [`howto/10-writing-register.md`](howto/10-writing-register.md): the seven prose prohibitions, the three kinds of text and their tones, the per-instance values, the post-pass, and `bin/register-check`
- [`howto/11-maestro-net.md`](howto/11-maestro-net.md): cross-talk between several Maestro instances (`recap`, `ask`, a satellite's `request`, the instance registry)

## Status

Actively evolving. Versions follow the date-based `vYYYY.MM.DD.N` scheme. See [`CHANGELOG.md`](CHANGELOG.md) for the full history and migration notes. Instances pull updates with `/maestro:maestro-sync`, from the plugin.

## License

TBD.

## Contributing

If you build your own orchestrator from this template and find improvements worth backporting, open a PR or issue.
