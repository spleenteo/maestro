---
work: agenda-port
status: active
superseded_by: null
tags: [decision, agenda, plugin, maestro-sync, new-instance, scope, rollback]
description: "The agenda is its own plugin, agenda@maestro, installed at project scope in each instance beside maestro at user scope; maestro-sync's plugin kind installs or updates it outside rollback. Read before changing where a plugin installs or what sync writes outside the instance."
---

# The agenda plugin installs at project scope in each instance

**Date**: 2026-10-29 · **Work**: `agenda-port` · **Status**: active

## Context

The agenda becomes its own plugin, `agenda@maestro`, served by the same marketplace as `maestro`. The `maestro` plugin sits at user scope, and `2026-09-13-plugin-user-scope.md` ruled out project scope for it. The agenda has the opposite need: its pane belongs to an instance, and a session in a satellite or in a plain folder has no use for it. Existing instances must be able to receive it, and until now no item kind wrote outside the instance.

## Decision

`agenda@maestro` installs at project scope in each instance, beside `maestro@maestro` at user scope. `/maestro:new-instance` installs it at setup. For an existing instance, `maestro-sync` gains a `plugin` item kind with two states: `missing` (no agenda installed for the instance) and `behind` (the installed commit differs from `plugins/agenda` in the mirror). The owner approves the item like any other, and a decline is remembered in `private/maestro-sync.declined`.

The `plugin` kind is the only item kind that writes outside the instance. On apply, the sync refreshes the `maestro` marketplace copy with `claude plugin marketplace update maestro`, then runs `claude plugin install` or `claude plugin update` from the instance root. Claude Code records the install under `~/.claude/plugins/` and adds the key to the instance's `.claude/settings.json`. This extends `2026-09-28-maestro-sync-as-a-command.md`: the declined file joins what the sync writes under `private/`, and the plugin item is the first item kind to write outside the instance.

The item stays outside rollback. On an install, apply copies `.claude/settings.json` (when present) into the backup set for reference and lists no backup entry for it, so a rollback never restores it. Rollback prints the uninstall command instead, `claude plugin uninstall agenda@maestro --scope project` run from the instance root.

The agenda's language is one value per machine. Claude Code keeps a plugin's `userConfig` in the user-level settings (`pluginConfigs`, keyed by plugin id), never in the project, so a later install must not overwrite an existing value. This was observed during the first slice of the work.

An instance that runs an agenda from another marketplace, shown by an `agenda@<other>` key in `.claude/settings.json` or `.claude/settings.local.json`, or by an installed `agenda@<other>` row, gets no install item. The plan prints one line saying to migrate with the runbook first. That block holds only while no `agenda@maestro` install exists for the instance: once it does, a `behind` update is still offered. That update uses the scope of the installed row, `project` or `local`. An installed version that is not a commit gives a warning and no item.

## Alternatives discarded

- **The agenda at user scope**: the pane would load in every session on the machine, satellites and plain folders included.
- **Restoring `.claude/settings.json` on rollback**: Claude Code's records under `~/.claude/plugins/` would still say the plugin is installed, and the two would disagree.

## Consequences

- An install touches state shared by the whole machine, so installs run one instance at a time.
- A decline lives in `private/maestro-sync.declined`; deleting the `agenda@maestro` line offers the plugin again. An update is never remembered as declined, and the next sync offers it again.
- A failed or unwanted install is undone by hand with the uninstall command that rollback prints.
- The committed `.claude/settings.json` carries the agenda key. That is acceptable in an instance repository, which belongs to the owner and is never a satellite.
- The plan reads `claude plugin list --json` once, and apply reads it again to re-check a selected plugin item.

## References

`docs/decisions-log/2026-09-13-plugin-user-scope.md`, `docs/decisions-log/2026-09-15-maestro-sync-in-plugin.md`, `docs/decisions-log/2026-09-28-maestro-sync-as-a-command.md`; the agenda-port work (kept outside the repository): V3 plan.
