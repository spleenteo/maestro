---
name: maestro-sync
description: "Sync the Maestro instance this session runs in with the latest Maestro template, as a conversation over the plugin's `maestro-sync` command: it refreshes the read-only mirror at ~/.maestro, checks the loaded plugin isn't behind it, plans the update (changed files, new files, drifted bin/, retired paths, missing writing register keys) and applies each kind on the owner's yes, after a backup set with a rollback. Use when the owner says \"sync maestro\", \"update from maestro\", \"pull maestro changes\", \"/maestro:maestro-sync\", or asks whether new patterns are available from the template. Runs only in an instance root."
---

# maestro-sync

Run every block from the instance root (`private/preferences.md` next to `bin/mem`), never from the Maestro template repository (`plugins/maestro/` present): the command refuses both with exit 3. The command does the mechanics and never asks (`maestro-sync --help`); this skill asks. Show stderr and stop on any non-zero exit this file doesn't name. Replace each `<placeholder>` and keep its double quotes.

## 1. Plan

```bash
set -o pipefail
SYNC=maestro-sync
command -v maestro-sync >/dev/null 2>&1 || SYNC="${CLAUDE_PLUGIN_ROOT}/bin/maestro-sync"
"$SYNC" plan --plugin-root "${CLAUDE_PLUGIN_ROOT}"
```

Every later call uses the same `SYNC` resolution, so repeat those two lines in each block. Read the summary: `VERSIONS <floor> -> <upstream>`, the `CHANGELOG` block, `ITEMS <N>` then one line per item (`<id> <kind> <path> ...`), `WORKTREE <state> <path>` with its files and commits, `WARNING` lines, `PLAN <file>`. Diffs and previews are in `private/maestro-sync.plan.json`: `items[]` with `id`, `kind`, `path`, `from`, `to`, `diff` or `preview`, `locally_modified`, `state`, `members`, `missing`, `hints`. On a first run the mirror is cloned: say so. Exit 3, 4 or 5: show the message and stop. Exit 5 for a plugin behind upstream carries the way out: `claude plugin marketplace update maestro`, `claude plugin update maestro@maestro`, restart Claude Code, run `/maestro:maestro-sync` again; never update and retry in the same session.

## 2. Working tree

`WORKTREE uncommitted` or `unpushed`: show the files and commits listed and ask before anything else. `push`: only when the state is `unpushed` (everything committed), run `git push origin main` in the worktree path, never `git add`, then go on. `continue`: sync without that work. `abort`: stop, nothing done. `absent` or `clean`: say nothing.

## 3. Context

Show the `CHANGELOG` block with the two versions as context, no question yet. `ITEMS 0`: say the instance is up to date at `<upstream>` and stop, no memory row.

## 4. One question per kind

Kinds in this order, one question per kind, never merged: `update`, `new`, `bin`, `retired`, `register`; `orphan` is reported only. `[a]` and `[s]` answer one item; `[A]` covers the remaining items of the current kind only; `[n]` aborts: `"$SYNC" note --outcome aborted --count <N>` with the files applied so far, then stop (applied items stay). Every skipped item: `"$SYNC" note <id> --outcome skipped`. Every apply goes through `"$SYNC" apply ...`; read `SET <path>` and `RESULT applied=<n> failed=<n> postponed=<n> pending=<n>` from its output, and a `failed` line stops the sync with the set path shown.

- **update** (`u1`, `u2`, ...): show `diff`, `from` and `to`, ask `[a] apply [s] skip [A] apply the remaining updates [n] abort`. `a`: `apply --items <id>`; `A`: `apply --kind update`, which leaves out `locally_modified` items, then ask those one by one. A `locally_modified: true` item is a merge: quote back the owner's lines (the `-` lines of the diff that are theirs, not old template text), then offer three ways: write the merged text (upstream plus their lines) to a temporary file and `apply --items <id> --from "<file>"`; overwrite with `apply --items <id>`; skip. Never write the instance file by hand.
- **new** (`n1`, ...): show `description`, `preview` and `lines`, same answers. `a`: `apply --items <id>`; `A`: `apply --kind new`.
- **bin** (`b1`): always its own question. Name each script with its state (`missing`, `differs`) and say the memory db and the replaced scripts are copied into the set first, then `bin/mem stats` runs on the new scripts; a `differs` script the owner edited by hand is overwritten. Yes: `apply --items b1`. No: `note b1 --outcome skipped` and warn that a skill may call a `bin/mem` option the instance lacks.
- **retired** (`r1`, ...): one question per item, never merged: "Remove `<path>`? It was retired upstream", listing its `files`; for the `listen` unit name the marked `members` ("it moved into the plugin as `/maestro:listen`"). `state: kept` (the owner's own unmarked `listen` skill, everything stays) and `state: postponed` (a capture or an old monitor runs, `reason` says which; proposed again next sync): one line, nothing to ask. Yes: `apply --items <id>`, where exit 10 is a postponement, not a failure. No: `note <id> --outcome kept`.
- **register** (`g1`): say how many keys are `missing`, then ask the questions of `howto/10-writing-register.md` → "The questions setup and sync ask" for those keys only, one per turn, each with its default and example; a `hints` line for a key becomes the proposed answer (a tone among `friendly`, `professional`, `formal`, `neutral`; the single words for `avoid_words`). Skip the translation questions when `.claude/skills/translate/SKILL.md` is absent. Then ask "Write these into `private/preferences.md`? It is backed up in the set first." Yes: `apply --kind register --register KEY=VALUE ...`, dotted keys as `missing` lists them (`tone_default.communication`, `communication.sign_off`, ...), an unanswered key takes its default; a rejected value is exit 2 with nothing written, ask again. `skip` on the block: `note g1 --outcome kept`.
- **orphan** (`o1`, ...): marked here, gone upstream. Report them: keep, archive or delete by hand. Never applied.

## 5. Summary

Read `private/backups/<stamp>-sync/manifest.json` (`from`, `to`, `items[]` with `kind`, `path`, `outcome`, `keys_added`) and report one line per kind with something to report: updated, added, bin scripts copied, removed, register keys added, skipped, postponed; then `Instance now at: <to>`, the set path, and the way back named once: `maestro-sync rollback <stamp>`. When nothing was applied there is no set: say so.

## 6. Memory row

```bash
env -u MEM_DB -u MEM_SCOPE bin/mem save "Maestro sync: <from> → <to> (<N> files updated, <M> added)" -t maestro,sync,upstream -d "<applied items, by path>. Skipped: <paths, or none>. Backup set: <path>."
```

Announce: `📝 saved: "Maestro sync: <from> → <to> (<N> files updated, <M> added)" [maestro,sync,upstream] (memory)`.

## Never in scope

`private/`, except the backup sets under `private/backups/`, `private/maestro-sync.lock`, `private/maestro-sync.log`, `private/maestro-sync.plan.json`, and the writing register keys on the owner's yes. `apps/`. Files without the `origin: maestro` marker. `.claude/roster.yaml`. The old local `.claude/skills/maestro-sync/` is a retired path the plan lists, never the skill to run.

## What it does not do

Push to upstream: promotions happen in the working tree. Resolve a conflict alone: a locally modified file is a merge the owner decides line by line. Run silently: every apply prints its set and result, every db write is announced. Update itself: a new version arrives with the plugin.

## Failure modes

- Exit 3 or 5: not an instance root, or the plugin can't be checked or is behind. Show the message (exit 5 names the update commands and the restart) and stop.
- Exit 4: the mirror clone or fetch, the working tree or a git call failed (no network, a mirror with local edits, a mirror that is the instance or the worktree). Show it and stop.
- Exit 6: the plan is older than the mirror or than a file. Run `plan` again; a new set starts.
- Exit 7, 9 or 11: unknown item or set, bad plan or manifest, another apply or rollback holds `private/maestro-sync.lock`, or the set, lock, log or plan can't be written; nothing applied. Show it and stop. Exit 10 is the postponed `listen` unit, never a failure.
- Exit 8: a write failed after others succeeded; the set holds every file touched. Show the failed item, offer `maestro-sync rollback <stamp>`, run it only on the owner's yes.
