---
work: sync-script
status: active
superseded_by: null
tags: [decision, maestro-sync, plugin, backups, rollback, distribution, migration]
description: "The mechanics of maestro-sync move from the bash blocks of the skill into the stdlib command maestro-sync (plan, apply, note, rollback, backups), with backup sets keyed on the plan under private/backups/ and a manifest written first; rules out bash in the skill, a Node or pip package, and one set per apply call. Read before changing how a sync applies, backs up or restores files."
---

# `maestro-sync` is a command; the skill is the conversation over it

**Date**: 2026-09-28 · **Work**: `sync-script` · **Status**: active

## Context

The skill of 2026-09-15 carried the whole sync as bash: 658 lines, phases 0 to 7, thirteen blocks the model ran in order, tested by 41 tests that extracted each block from the skill by heading. The backups were loose `private/*.bak.<stamp>` copies with no record of what a sync had touched, and a restore was a block the owner pasted. Issue #4 asked for the sync as a script with its backups in a folder. `maestro-register-keys` (Phase 6c) had already shown the shape: a command in the plugin's `bin/`, a skill that asks and calls it.

## Decision

The mechanics live in `plugins/maestro/bin/maestro-sync`, Python standard library only, with five verbs: `plan` (refresh the mirror, check the plugin, scan the instance and the mirror, write `private/maestro-sync.plan.json`), `apply` (items by id or by kind, after a backup set), `note` (the outcomes only the conversation decides), `rollback <stamp>` and `backups`. The skill drops to 66 lines: it runs `plan`, asks one question per kind, runs `apply` or `note`, reads the set's manifest for the summary and saves the memory row; it never writes an instance file by hand. The heading-extraction tests go; the command is tested black-box through `subprocess` against a temporary instance and a temporary mirror.

Backup sets are keyed on the plan: the first `apply` creates `private/backups/<plan-stamp>-sync/` and every later `apply` on the same plan appends to it. `manifest.json` is written before the first write, every selected item `pending`, and rewritten atomically after each item; the memory db is copied once per set through sqlite3's online backup and checked; every replaced or removed file is copied under `files/` before it is touched. Retention after a run: the five newest sets stay, older ones go once past seven days, the cap of twenty wins over the age floor, and the current run's set is never pruned.

Rulings taken during the slice. An `update` carries the instance's `tools:` group over onto the upstream text: the one change of behaviour against the bash skill, which wrote the upstream file as it was. `locally_modified` is computed by history: the instance file, with `tools:` normalised to the mirror's value, is looked for among the blobs of that path across the mirror's history, and a file found nowhere is the owner's; `--kind update` skips those, and they go through `--items ID` (overwrite) or `--items ID --from FILE` (the merge the conversation prepares). Register answers are validated with `maestro-register-keys render` before the set opens, so an invalid value changes nothing. Orphans are `E_ITEM` on `apply`, never touched. `E_BACKUP` (exit 11) names a failure of the set, the manifest, the db copy, the lock, the log or the plan file before any item is applied, so it is never mistaken for a partial run. `rollback` refuses a set whose manifest names another instance. The one-line redirect at `.claude/skills/maestro-sync/` was deleted upstream in `50be94f`; the path stays retired, and a marked copy in an instance is still proposed for removal.

## Alternatives discarded

- **Keep the bash in the skill**: every rule hid in quoting, `pipefail` and an `awk` that bailed on a missing frontmatter; the tests extracted blocks by heading, so a heading change broke them; and the model had to run thirteen blocks in order without skipping one.
- **A Node or pip package**: the plugin ships as a git checkout with no install step, and `docs/development-guidelines.md` keeps every distributed script on the Python standard library, with no Node and no package to publish.
- **One backup set per `apply` call**: the conversation applies in several calls and the owner thinks in syncs; a rollback would have needed several stamps in the right order.
- **Looking a template version up as a git commit** to find what changed: six changelog versions have no release commit, and files change between releases without a version bump. Content is compared against the path's history instead.

## Consequences

- The policy of 2026-09-15 stands: the sync ships in the plugin, refuses a stale or behind plugin, retires the old local copy. This record replaces its mechanics.
- Everything the sync writes under `private/` is one of the plan file, the lock, the log, the sets, and the register keys on the owner's yes; the skill's "never in scope" list names them.
- Loose `private/*.bak.*` files from earlier syncs are not sets: `rollback` ignores them, `backups` names them, nothing removes them.
- `plan` overwrites the previous plan file, and `apply` refuses a plan older than the mirror or than a file it names (`E_STALE`), so a re-run of `plan` starts a new set.
- The plan's item kinds and the exit codes 3 to 11 are the interface the skill depends on; a change to either changes the command, the skill and their tests together.

## References

`docs/decisions-log/2026-09-15-maestro-sync-in-plugin.md`, `docs/decisions-log/2026-09-17-maestro-sync-asks-register-keys.md`, `docs/decisions-log/2026-09-13-bin-mem-stays-in-instance.md`; issue [#4](https://github.com/spleenteo/maestro/issues/4); the sync-script design work (kept outside the repository): slices V1 and V2, the impact analysis of 2026-09-27 and its 28 findings.
