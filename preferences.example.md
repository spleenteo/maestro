---
setup_completed: false
---

# Preferences

This file is the **single source of truth** for the orchestrator's identity and the owner's profile. It's loaded at **every session start**, so anything you want the orchestrator to know about you and your world should live here.

The `setup` skill fills in the **essentials** at first launch (identity, nick, role, context, file territories). Everything else — team details, objectives, integrations, communication preferences, work rhythms — is meant to be **added and expanded over time**. The more context the orchestrator has, the better it can help you: be generous here, it pays off.

**Do not commit this file** once filled — it lives in `private/` which is gitignored.

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

*This section is important.* The orchestrator is far more helpful when it understands the world you move in. Setup captures a free-form paragraph here; expand over time with structure as it becomes useful.

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

Subfolder keys default to subfolders of `vault_path` but can point anywhere on disk — any of them may live outside the vault if you want a non-standard layout. Leave a key empty (or remove the line) for territories you don't want.

Paths can target anything — Obsidian vaults, plain filesystem folders, cloud-synced folders. The orchestrator respects the boundaries regardless of the tech.

**Don't want external folders?** The setup skill's "internal" mode sets `vault_path` to `./<project_slug>/` inside the repo (derived from your project name and appended to `.gitignore` automatically). No leaks, no external config.

---

## Integrations

Declare only what applies. Optional at setup time, add as you go.

- **Basecamp**: <authorized account id + project id, or "none">
- **MCP servers**: <list of MCPs your orchestrator is wired to>
- **Other services**: <calendar, email, CRM, task manager, etc. — whatever the orchestrator should know about>

---

## Communication preferences

How the orchestrator should talk *to you* and about *others*. Expand when you notice the orchestrator drifting from how you actually work.

- **Tone with you**: <direct/terse, warm/conversational, formal, playful — whatever fits>
- **Tone with others (when writing on your behalf)**: <e.g. "warmer with agency contacts, more measured with enterprise clients">
- **Things to avoid**: <pet peeves, filler phrases, bureaucratic wording, any habits that annoy you>
- **Things to keep doing**: <patterns you've validated — e.g. "flag problems early even if uncomfortable">

---

## Notes

Free-form section for anything else the orchestrator should remember that doesn't fit the blocks above. Idiosyncrasies, context that only matters sometimes, reminders the owner wants to see at session start.

---

## How to expand this file

When the orchestrator proposes to add new context (a team member, a new objective, a changed preference), it will ask you — don't expect it to edit silently. You can also add things yourself directly: just keep the structure above recognizable, and the orchestrator will pick up the new info at the next session start.

If you want a section the template doesn't cover, add it. This file is yours.
