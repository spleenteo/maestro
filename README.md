# Spleenteo Orchestrator

A bootstrap template to scaffold your own personal orchestrator — a Claude Code project that acts as a single interface to a team of agents and skills.

The template distills a reusable pattern, written in English and owner-agnostic, configured through an interactive first-launch setup.

## What you get

After cloning and running setup, you have an orchestrator that:

- Introduces itself with the **name and personality** you chose
- Reads your **profile** (role, nick, default language) at every session
- Writes to **three file territories** you declare (daily logbook, TIL notes, longer documents) — any filesystem path, Obsidian vault folders welcome but not required
- Keeps a **memory database** of what was done, what's to do, and ideas that emerged — as a log of your collaboration
- Can **hire craft agents** through an HR agent that searches the filesystem, marketplaces, and GitHub for matches
- Applies a **frontmatter discipline** so the files it writes are searchable by description and tags before anyone reads their body

## What it doesn't do

- No personal data, no hardcoded names, no integrations out of the box
- No vault-specific lock-in — it's filesystem-agnostic
- No domain-specific skills (finance, music, CRM, etc.) — you add those over time
- No task-manager, calendar, or email integrations — you configure what you need via preferences

## Install

You need a working installation of [Claude Code](https://claude.com/claude-code).

```bash
git clone https://github.com/<your-fork>/spleenteo-orchestrator.git my-orchestrator
cd my-orchestrator
claude
```

On first launch, the orchestrator should notice that `private/preferences.md` doesn't exist and trigger the `setup` skill automatically. If it doesn't (Claude Code sometimes waits for an explicit signal), just type:

```
/setup
```

Either way, the `setup` skill asks you a short set of questions, starting with your preferred language — from that point on the whole setup runs in that language. In order:

1. **Default language** — how the orchestrator talks to you by default (asked in English)
2. **Name of your orchestrator** — what it should call itself
3. **Inspiration** — a character or archetype (real or fictional) that captures the personality you want; the skill proposes 3–5 adjectives based on it, which you accept or tweak
4. **Your nick** — how the orchestrator should refer to you
5. **Your full name and role** — for context
6. **File territories** — where markdown notes should live. Three options: **internal** (notes in `./myVault/{logbook,til,documents}/` inside the repo, gitignored), **external** (absolute paths to folders outside the repo, e.g. an Obsidian vault), or **skip** (no territories for now)
7. **Integrations** (optional) — Basecamp, MCPs, or any other external service you want the orchestrator to be aware of

The setup writes `private/preferences.md`, copies `memories.db.template` into `private/memories.db`, deletes the two template files at the repo root (`preferences.example.md` and `memories.db.template` — they've done their job and would only cause confusion; they remain in git history if ever needed), and self-disables (moves itself to `.claude/skills/.disabled/setup/`) so it doesn't rerun. You're operational.

## The orchestrator pattern

Every instance built from this template has:

- **`CLAUDE.md`** — the brain. Defines the orchestrator role, routing, delegation, memory behavior, frontmatter discipline. Generic, not owner-specific.
- **`private/preferences.md`** — identity + owner profile + customizations, loaded at every session start. Gitignored.
- **`private/memories.db`** — SQLite log of memories, tasks, ideas. Gitignored.
- **`memories.db.template`** — empty SQLite seed with the schema, copied into `private/` by the setup skill.
- **`.claude/roster.yaml`** — registry of active craft agents (empty at install).
- **`.claude/agents/hr.md`** — the HR agent, recruiter and manager of craft agents.
- **`.claude/skills/setup/`** — first-launch configuration (self-disables).
- **`.claude/skills/logbook/`** — writes a daily logbook note in your configured `logbook_path`.
- **`.gitignore`** — covers `private/`, workspace artifacts, and local settings.

Everything else grows organically as you use the orchestrator:

- Add a sub-app? Symlink it into `apps/<name>/` and add a row in `CLAUDE.md`'s "Available apps" table.
- Need a recurring task handled by a specialist? Ask your orchestrator; it invokes HR, which proposes an agent, and if you approve, installs it into `.claude/agents/` and the roster.
- Want a skill your instance needs? Drop it in `.claude/skills/` — no ceremony.

## Philosophy

Three principles guide the pattern:

1. **Single interface** — the owner talks only to the orchestrator. No agent speaks directly to the owner. Output from agents is always filtered or synthesized by the orchestrator.
2. **Delegate when it fits, not always** — the orchestrator answers directly to conversational requests. Delegation is reserved for clear matches with registered agents.
3. **Proactive on recurring patterns** — if the same kind of request keeps coming up without a dedicated agent, the orchestrator suggests hiring one. The owner decides.

These live in `CLAUDE.md` under "Role: orchestrator" and carry through every instance.

## Going deeper

After setup, the `howto/` folder has four practical guides:

- [`howto/01-skills.md`](howto/01-skills.md) — add, invoke, write, retire skills
- [`howto/02-agents-and-hr.md`](howto/02-agents-and-hr.md) — hire, use, retire agents via HR
- [`howto/03-customization.md`](howto/03-customization.md) — customize identity, owner profile, context, communication style
- [`howto/04-memory-and-integrations.md`](howto/04-memory-and-integrations.md) — memory db internals and how to integrate external tools (Basecamp, Google Calendar, reminders)
- [`howto/05-backup-and-sync.md`](howto/05-backup-and-sync.md) — privacy, `.gitignore`, cloud-drive sync, symlinks to external apps/skills/agents

## Status

Initial release — version 0.1.0.

## License

TBD.

## Contributing

If you build your own orchestrator from this template and find improvements worth backporting, open a PR or issue. The pattern is meant to evolve.
