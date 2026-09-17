---
tags: [howto, index, orchestrator, documentation]
description: Index of how-to guides for working with your orchestrator beyond the first setup. Read these when you want to extend or customize deeper than the default behavior.
---

# How-to guides

Practical guides for extending and customizing your orchestrator after setup. Read in order if you're new, or jump straight to the topic you need.

| Guide | Topic |
|---|---|
| [01 — Skills](01-skills.md) | Add, invoke, write, and retire skills |
| [02 — Agents and HR](02-agents-and-hr.md) | Hire, use, and retire craft agents via the HR agent |
| [03 — Customization](03-customization.md) | Customize identity, owner profile, context, territories, integrations, communication style |
| [04 — Memory and integrations](04-memory-and-integrations.md) | How the memory db works, how to query and extend it, how to integrate external tools (Basecamp, Google Calendar, reminders) |
| [05 — Backup and sync](05-backup-and-sync.md) | What to keep out of git, how to sync across machines via a cloud drive, how to use symlinks for external apps, skills, and agents |
| [06 — Configure Cal](06-configure-cal.md) | Configure the `scheduler` agent (Cal): add data channels (task trackers, calendars), write routines, understand the seven `question_types` |
| [07 — Warm task channel](07-warm-task-channel.md) | Wire an external task manager (Acme, Basecamp todos, etc.) as the warm layer, with `memories.db` as cold layer and a lazy GC at session start |
| [08 — Markdown discipline](08-markdown-discipline.md) | Frontmatter, YAML safety, wikilinks and search-from-frontmatter rules for every markdown file |
| [09 — Semantic memory](09-memoria-semantica.md) | Optional semantic layer over `memories.db` and the vault: setup, commands, scope rules |
| [10 — Writing register](10-writing-register.md) | The seven prose prohibitions, the kinds of text and their tones, the per-instance values, the post-pass and `bin/register-check` |
| [11 — maestro-net](11-maestro-net.md) | The channel between several instances: `recap`, `ask`, the machine registry |
| [12 — Satellites](12-satellites.md) | Attach a project repo to an instance: the `satellite` skill, session hooks, vault folder, removal |

Each guide stands on its own. Frontmatter on each file includes tags and a one-line description — consistent with the orchestrator's own frontmatter discipline.
