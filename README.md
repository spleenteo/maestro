# Spleenteo Orchestrator

A bootstrap template to scaffold your own personal orchestrator — a Claude Code project that acts as a single interface to a team of agents and skills.

The pattern is proven on two instances: **Alfred** (personal life orchestrator) and **Pam** (DatoCMS work orchestrator). This repo distills the pattern into a reusable, owner-agnostic template, written in English, configurable through an interactive first-launch setup.

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
- No Obsidian lock-in — it's filesystem-agnostic
- No domain-specific skills (finance, music, CRM, etc.) — you add those over time
- No slacky, no calendar, no email — you configure integrations via preferences

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

Either way, the `setup` skill asks you a short set of questions:

1. **Name of your orchestrator** — what it should call itself
2. **Inspiration** — a character or archetype (real or fictional) that captures the personality you want; the skill proposes 3–5 adjectives based on it, which you accept or tweak
3. **Your nick** — how the orchestrator should refer to you
4. **Your full name and role** — for context
5. **Default language** — how the orchestrator talks to you by default
6. **File territories** — three absolute paths for `logbook`, `til`, `documents` (you can skip any; they can live anywhere, not necessarily in Obsidian)
7. **Integrations** (optional) — Basecamp account/project, MCPs

The setup writes `private/preferences.md` and initializes `private/memories.db`. Then it self-disables (moves to `.claude/skills/.disabled/setup/`) so it doesn't rerun. You're operational.

## The orchestrator pattern

Every instance built from this template has:

- **`CLAUDE.md`** — the brain. Defines the orchestrator role, routing, delegation, memory behavior, frontmatter discipline. Generic, not owner-specific.
- **`private/preferences.md`** — identity + owner profile + customizations, loaded at every session start. Gitignored.
- **`private/memories.db`** — SQLite log of memories, tasks, ideas. Gitignored.
- **`.claude/roster.yaml`** — registry of active craft agents (empty at install).
- **`.claude/agents/hr.md`** — the HR agent, recruiter and manager of craft agents.
- **`.claude/skills/setup/`** — first-launch configuration (self-disables).
- **`.claude/skills/logbook/`** — writes a daily logbook note in your configured `logbook_path`.
- **`.gitignore`** — covers `private/`, `workspace/`, and local settings.

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

## Status

- Alfred (personal) — built, operational
- Pam (DatoCMS) — built, operational
- Template (this repo) — initial release, version 0.1.0

## License

TBD.

## Contributing

If you build your own orchestrator from this template and find improvements worth backporting, open a PR or issue. The pattern is meant to evolve.
