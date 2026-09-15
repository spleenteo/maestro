---
work: satellites-plugin
status: active
superseded_by: null
tags: [decision, maestro-sync, plugin, bin-mem, migration, distribution]
description: "maestro-sync moves into the Maestro plugin, refuses to run with a stale or behind plugin, copies drifted bin/* on the owner's yes after backups, and retires the old local copy with a redirect. Read before changing how instances receive template updates."
---

# `maestro-sync` lives in the plugin and copies `bin/` on request

**Date**: 2026-09-15 · **Work**: `satellites-plugin` · **Status**: active

## Context

Each instance carried its own copy of `maestro-sync`, updated by running itself. A copy older than the template it applied had no way to know what it didn't know: the satellites work changed `bin/mem`, the skills that call it, and the checks a sync needs. `bin/*` stayed outside sync scope (decision of 2026-09-13), so every release asked the owner to copy scripts by hand before syncing, and a missed copy left skills calling options the instance's `bin/mem` lacked.

## Decision

The skill ships in the plugin as `/maestro:maestro-sync`. It refuses to run outside an instance root, when the loaded plugin differs from the installed one, and when the installed plugin is behind the template's `main`. After a checksum report it offers to copy drifted `bin/*`: on yes it backs up `private/memories.db` (checked for integrity and page count) and the scripts it replaces, copies, and runs `bin/mem stats` so migrations run next to a fresh backup, with a restore block for a failed run. It proposes removing retired paths (the old local copy, `setup`, `user-skills/maestro-net`), each on its own yes and only when they carry the distribution marker. Upstream keeps a one-line redirect at `.claude/skills/maestro-sync/` for instances still running the old copy, excluded from new instances.

## Alternatives discarded

- **Keep the skill in each instance**: the copy that runs is as old as the instance, so a new check can't protect the release that introduces it.
- **`bin/mem` in the plugin**: still ruled out, for the reason of 2026-09-13; the copy keeps each instance's script next to its own db.
- **Delete the old skill upstream without a redirect**: an old sync would keep running itself and report its own file as an orphan.

## Consequences

- The first sync after the release must be started as `/maestro:maestro-sync`; the release note says so.
- A hand-edited `bin/` script is overwritten on yes; the backup folder under `private/` keeps the previous version.
- The redirect can be deleted upstream once every instance has synced past it.

## References

`docs/decisions-log/2026-09-13-bin-mem-stays-in-instance.md`, `docs/decisions-log/2026-09-13-plugin-user-scope.md`; the satellites-plugin design work (kept outside the repository): slice V7 and its final review.
