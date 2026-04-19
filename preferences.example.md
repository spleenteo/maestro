---
setup_completed: false
---

# Preferences

This file is the single source of truth for the orchestrator's identity and the owner's profile. It's loaded at every session start.

**Do not commit this file** once filled — it lives in `private/` which is gitignored.

## Identity (the orchestrator)

- **Name**: <what the orchestrator calls itself — e.g. Alfred, Pam, Jarvis>
- **Inspired by**: <character or archetype that informs the personality — e.g. Alfred Pennyworth, a precise librarian, a quiet mentor>
- **Adjectives**: <3–5 traits — e.g. paternal, calm, discreet, proactive, gentle>

## Owner

- **Nick**: <how the orchestrator should call you in chat>
- **Full name**: <your full name, for context — the orchestrator uses this rarely>
- **Role**: <what you do, short description>
- **Default language**: <language of daily conversation — e.g. italian, english, spanish; the orchestrator switches only when context demands>

## File territories

Absolute paths where the orchestrator is authorized to write markdown files. Any or all may be set; leave a field empty (or remove the line) if you don't want that territory.

- **logbook_path**: <absolute path for daily logbook notes>
- **til_path**: <absolute path for "Today I Learned" notes>
- **documents_path**: <absolute path for longer reference documents>

These can point anywhere — Obsidian vault folders, plain filesystem directories, cloud-synced folders. The orchestrator doesn't care about the tech; it just respects these boundaries.

## Integrations

Optional. Declare only what applies.

- **Basecamp**: authorized account id, project id (or `none`)
- **MCPs**: list of MCP servers your orchestrator is wired to
- **Other**: any other external service or context worth knowing at session start

## Notes

Free-form section for anything the orchestrator should remember about you that doesn't fit the blocks above — preferred communication style, things to avoid, pet peeves, work rhythms.
