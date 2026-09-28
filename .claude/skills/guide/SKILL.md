---
origin: maestro
maestro_version: v2026.09.28.1
name: guide
description: Answer the owner's questions about this orchestrator — how it works, what features exist, how to do something specific. Reads CLAUDE.md and the guides in howto/ to give grounded answers. Use when the owner types /guide, or says things like "I'm lost", "what can you do", "how do I", "how does this work", "remind me how to...", or similar confusion signals. Note: /help is a Claude Code built-in command and won't reach this skill — only /guide does.
---

# Guide

The owner's way in when they're confused or exploring. It answers questions about the orchestrator itself, its features and conventions, by reading the project's own documentation. It never invents: when an answer isn't in the docs, it says so.

The skill is named `guide` because `/help` is a Claude Code built-in and never reaches a project skill.

## Where the answers come from

Priority order:

1. `CLAUDE.md` (repo root): the orchestrator's definition, first stop for any "how does the orchestrator handle X" question.
2. `howto/`, one guide per topic (`howto/README.md` is the index):
   - `01-skills.md`: adding, writing, retiring skills
   - `02-agents-and-hr.md`: the HR agent, hiring, retiring, aliases
   - `03-customization.md`: preferences, identity, file territories, reset
   - `04-memory-and-integrations.md`: memory model, `bin/mem`, extending, integrations
   - `05-backup-and-sync.md`: privacy, sync, symlinks, pointer skills, sub-apps
   - `06-configure-cal.md`: the `scheduler` agent, data channels, routines
   - `07-warm-task-channel.md`: an external task manager as the warm layer, the garbage collector
   - `08-markdown-discipline.md`: frontmatter, tags, YAML safety, wikilinks
   - `09-semantic-memory.md`: the optional semantic layer over the memory and the vault
   - `10-writing-register.md`: the prose register, domains, tones, `bin/register-check`
   - `11-maestro-net.md`: the channel between instances
   - `12-satellites.md`: project repos attached to an instance
3. `private/preferences.md`, only for questions about the owner's own setup ("what's my current language", "which territories do I have").
4. The hub skills (`.claude/skills/*/SKILL.md`), when the question is about one skill's behaviour.

Use `rg` on frontmatter and section headings before reading bodies in full.

## How to respond

1. Detect the topic. A specific question ("how do I hire an agent?") goes straight to the relevant guide. A generic one (`/guide`, "I'm lost") gets the menu below, in the owner's default language, then waits for a choice.
2. Answer short first: two to four sentences on what the owner asked, then the exact path (`howto/01-skills.md`, or `CLAUDE.md` → section name) for the full version, then one offer to go deeper.
3. When the answer isn't in the docs, say so plainly and offer two ways out: reason from the general pattern, or save the question as an idea to document later. On "save as idea", write it with `bin/mem idea "…" -t docs,guide,gap,<topic>` and announce the write.

Menu for a generic question (translate into the owner's language):

> What would you like help with?
>
> - How I work: my role, what I can and can't do on my own
> - Memory, logbook, TIL: where things get saved and how to read them back
> - Skills and agents: what they are, how to add one, how HR hires
> - Customization: my name, language, what I know about you
> - File territories and markdown: where I write and how files are tagged
> - Tasks: the memory db, an external task manager, Cal's questions
> - Writing register: how I write emails, documents and reports for you
> - Other instances and satellites: maestro-net, project repos attached to me
> - Backup, sync and sub-apps: what's private, what's in git, linking another project
>
> Or ask me something more specific.

## Rules

- Never invent a feature, a path or a behaviour.
- Short first, deep on demand: no full document dumped on the owner unless asked.
- Cite the source: every substantive claim maps to a file path in the repo.
- Read-only, except the idea written on the owner's explicit consent.
- Respond in the owner's default language from `private/preferences.md`; when this folder isn't a configured instance, respond in English and point to `/maestro:new-instance`.
- Stay in character: the orchestrator's voice from preferences.
