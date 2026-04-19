---
name: help
description: Answer the owner's questions about this orchestrator — how it works, what features exist, how to do something specific. Reads CLAUDE.md and the guides in howto/ to give grounded answers. Use when the owner types /help, or says things like "I'm lost", "what can you do", "how do I", "how does this work", "remind me how to...", or similar confusion signals.
---

# Help

This skill is the owner's way in when they're confused or exploring. It answers questions about the orchestrator itself — its features, conventions, how to do something — by reading the project's own documentation and giving a grounded answer. It never invents; if an answer isn't in the docs, it says so.

## Where the answers come from

Priority order when looking for an answer:

1. **`CLAUDE.md`** (repo root) — the orchestrator's definition: role, memory behavior, frontmatter discipline, delegation rules, sub-app validation, etc. First stop for any "how does the orchestrator handle X" question.
2. **`howto/`** — practical guides for extending and customizing:
   - `howto/01-skills.md` — adding, writing, retiring skills
   - `howto/02-agents-and-hr.md` — the HR agent, hiring, retiring, aliases
   - `howto/03-customization.md` — preferences, identity, file territories, reset
   - `howto/04-memory-and-integrations.md` — memory model, queries, extending, integrations
   - `howto/05-backup-and-sync.md` — privacy, sync, symlinks, pointer skills, Claude's own project memory
3. **`private/preferences.md`** (only if relevant to the owner's specific setup) — for questions like "what's my current language" or "which territories do I have configured".
4. **Hub skills** (`.claude/skills/*/SKILL.md`) — when the question is about a specific skill's behavior.

Use `rg` to scan frontmatter and section headings before reading bodies in full. Keep token cost low.

## How to respond

### Step 1 — Detect the topic

When invoked, either the owner asked a specific question (*"how do I hire an agent?"*) or a generic one (*"/help"*, *"I'm lost"*).

- **Specific**: go straight to the relevant doc (typically one of the `howto/` files) and answer from it.
- **Generic**: present the short menu below, in the owner's default language.

### Step 2 — Menu (for generic questions)

Example in English (translate into the owner's language from preferences):

> What would you like help with?
>
> - **How I work** — my role, what I can and can't do on my own
> - **Memory, logbook, TIL** — where things get saved and how to read them back
> - **Skills** — what they are, how to add one
> - **Agents and HR** — how to hire a specialist
> - **Customization** — changing my name, language, what I know about you
> - **File territories** — where I'm allowed to write
> - **Backup and sync** — what's private, what's in git, how to protect your data
> - **Registering an external app** — linking another project so I can work on it
>
> Or ask me something more specific.

Wait for a choice. Then answer from the matching doc.

### Step 3 — Give a grounded answer

- **Short answer first** (2–4 sentences) addressing what the owner asked.
- **Point to the doc** with an exact path (`howto/01-skills.md` or `CLAUDE.md` → "Section name") so the owner can read the full version if they want.
- **Offer a follow-up** — *"Want me to walk you through it?"* or *"Any specific part you'd like me to expand on?"*

### Step 4 — When the answer isn't in the docs

Say so plainly: *"That's not covered in the current docs. Want me to help you figure it out based on the general pattern, or save the question as an idea to document later?"*

If the owner picks "save as idea", insert an entry in the memory db with `type='idea'` tagged `[docs,help,gap,<topic>]` — and announce it per the "announce every write" rule.

## Language

Always respond in the owner's **default language** from `private/preferences.md`. If preferences isn't loaded yet (somehow help is invoked before setup), respond in English and suggest running `/setup` first.

## Rules

- **Never invent.** If the docs don't answer a question, say so. Don't fabricate features, file paths, or behaviors.
- **Short first, deep on demand.** Don't dump a full doc on the owner unless they ask to see it.
- **Cite the source.** Every substantive claim should map to a file path in the repo.
- **Don't write anywhere** except to the memory db for gap-tracking (on explicit owner consent). `help` is a read-only skill.
- **Stay in character** — use the orchestrator's voice and tone (from preferences' Identity + Communication preferences sections).
