---
origin: maestro
maestro_version: v2026.11.08.1
tags: [howto, agenda, pane, plugin, scheduler, migration, language]
description: "The agenda pane and its skill: what the pane shows, the two plugin scopes, how it is installed, the language and day-start settings, and the runbook for an instance that ran the agenda from another marketplace. Reference when the pane is missing, in the wrong language, or an instance still carries an older agenda."
---

# 14 — The agenda pane

Claude Code can show a pane beside the conversation. The agenda plugin uses it for one thing: what is left to do today. You ask for the day's plan, the orchestrator collects it and the pane keeps it in view while you work.

## What the pane shows

Today's appointments with their time, then the open tasks planned for today. The `agenda` skill fills it: it asks the `scheduler` agent for the day, maps the answer and saves it through the plugin's `agenda_set` tool. When you create, close, move or cancel a task or an appointment of today, the skill saves the whole list again, without asking `scheduler`, when the list is still in the conversation.

- `/agenda` shows or hides the pane; `/agenda update` refreshes it.
- The pane is empty until the first agenda request of the day. Asking "what is on today" is enough.
- Without the plugin the skill still answers in chat and does not touch a pane.
- `/clear` leaves the pane and `agenda_set` working: the tool finds the agenda's store again on its own, from the instance root, so no new agenda request is needed to save.

## Two plugins, two scopes

- `maestro@maestro`, the plugin with `new-instance`, `maestro-sync` and the other commands, is installed at user scope, once per machine.
- `agenda@maestro` is installed at project scope, in each instance that should have a pane. A satellite or a plain folder has none, because the plugin is not enabled there.

## Installing it

- A new instance: `/maestro:new-instance` installs it at the end of the setup.
- An existing instance: `/maestro:maestro-sync` offers it as the `plugin` item, see [the agenda plugin in howto/05](05-backup-and-sync.md#the-agenda-plugin).
- By hand, from the instance root: `claude plugin install agenda@maestro --scope project`.

The pane loads at the next start of Claude Code. The plugin needs a recent Claude Code, see [Requirements in the README](../README.md#requirements).

## Language and day start

Two options, both set once per machine and shared by every instance:

- `language`: `en` or `it`, the language of the pane's labels. English is the default.
- `dayStart`: the local time a new day begins, `06:00` by default. Before it, the previous day still counts as today.

Claude Code keeps them in your user settings, `~/.claude/settings.json`, under `pluginConfigs` → `agenda@maestro` → `options`. The pane follows your language: the setup writes the value when none is set yet, `it` for Italian in any wording and `en` for every other language. A later install keeps a value already there. To set it by hand on an install, pass `--config language=it`, and only when no value exists, since the option applies to the whole machine.

## The migration runbook

An instance that ran the agenda from another marketplace has an `agenda@<other>` plugin. The sync prints `AGENDA migrate` for it and offers no `plugin` item until the instance moves to `agenda@maestro`. The move is one instance at a time, because an early removal of the old marketplace breaks the old agenda in every instance still waiting.

For each instance, in any order. A sync in an instance still on the old agenda is harmless: it shows only the migrate line and keeps the unmarked skill copy.

1. `claude plugin marketplace update maestro`, so the install finds the current plugin.
2. From the instance root, `claude plugin uninstall agenda@<other> --scope project --keep-data`. The uninstall drops the instance's `agenda@<other>` key by itself and breaks no other instance. `--keep-data` leaves the old data folder alone.
3. `claude plugin install agenda@maestro --scope project`. Add `--config language=<code>` only when `pluginConfigs["agenda@maestro"].options.language` is unset, with `<code>` as in [language and day start](#language-and-day-start). The command's `outcome` tells whether it worked; its message may still say an option is not yet set.
4. If the instance keeps its own copy of `.claude/skills/agenda/SKILL.md`, add `origin: maestro` and `maestro_version: <the content of private/.version>` to its frontmatter, since the sync skips a file without the marker.
5. Run `/maestro:maestro-sync` and take the skill's `update` item through the merge conversation.

The pane starts empty: the plugin keeps its store under its own id, so the old pane's content does not follow. The next agenda request fills it.

After the last instance:

1. From the last instance's root, `claude plugin marketplace remove <other>` once. If it reports `not_configured`, run it again with `--scope project`. A removal before this point uninstalls the old agenda in every instance that has not moved yet.
2. In each instance, remove the `<other>` entry from `extraKnownMarketplaces` in `.claude/settings.json` (and in `.claude/settings.local.json` when it has one) by hand: Claude Code leaves it.
3. Delete the old plugin's store file, `~/.claude/plugins/store/agenda_<other>-*.json`, after checking that it is the only file with that name pattern.
4. Delete the old data folder `~/.claude/plugins/data/agenda-<other>` (kept by `--keep-data`) and the cache folder `~/.claude/plugins/cache/<other>/` (marked `.orphaned_at`); both are safe to delete.
5. Remove the folder that held the old plugin, wherever it lives.

Check each instance as it moves: `claude plugin list --json` shows `agenda@maestro` with `scope: project` and the instance's path, `.claude/settings.json` has `"agenda@maestro": true` and no `agenda@<other>` key in `enabledPlugins`, and `/agenda` opens the pane in a new session. The uninstall keeps the `<other>` entry in `extraKnownMarketplaces` until the cleanup above. After the cleanup, `<other>` appears in neither `.claude/settings.json` nor `.claude/settings.local.json`.

If a step fails, stop before the next instance and undo this instance's steps, newest first:

- After the sync: `maestro-sync rollback <stamp>`.
- After the marker edit: remove the two marker lines (`origin` and `maestro_version`) from the skill copy.
- After the install: `claude plugin uninstall agenda@maestro --scope project`.
- Then reinstall the old agenda: `claude plugin install agenda@<other> --scope project`, possible while the old marketplace is still there.
