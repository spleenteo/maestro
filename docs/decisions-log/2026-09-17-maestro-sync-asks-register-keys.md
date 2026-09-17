---
work: register-domains
status: active
superseded_by: null
tags: [decision, maestro-sync, preferences, writing-register, new-instance, migration]
description: "maestro-sync asks an existing instance for the Writing register keys it lacks and writes the answers into private/preferences.md on the owner's yes, after a backup; the first time sync writes the owner's preferences. Read before adding preference keys or changing what sync writes under private/."
---

# `maestro-sync` asks for missing register keys and writes them

**Date**: 2026-09-17 · **Work**: `register-domains` · **Status**: active

## Context

The register gains per-instance values in the `## Writing register` block of `private/preferences.md`: tone defaults per domain, voice, sign-off, translation settings, words to avoid. A new instance can ask for them at setup. An existing instance never receives `preferences.example.md`, which setup removes, and until now `maestro-sync` wrote under `private/` only backups. The owner expects every instance to be asked once.

## Decision

`/maestro:maestro-sync` gains a phase that reads the instance's `## Writing register` block and asks only the keys it lacks, one question at a time, each with its default and an example. On the owner's yes it copies `preferences.md` to a backup and writes the answers into the block. A skipped question writes its default, so the next sync does not ask it again. `/maestro:new-instance` asks the same questions after its ten, skippable with one answer. Both skills take the questions from `howto/10-writing-register.md`. Every key stays optional: a missing key falls back to its documented default.

## Alternatives discarded

- **Ask at first use**: the question interrupts the task that needs the value, and a new instance is never asked at setup.
- **List the missing keys in the sync summary for a manual edit**: nothing is asked, and most instances would stay on defaults without knowing the keys exist.

## Consequences

- Sync now writes an owner file under `private/`; the backup and the explicit yes are the guard.
- The question list lives in one place, so a change in `howto/10` changes both flows.
- The phase covers this block only; another block that gains keys later needs its own entry in the phase.

## References

`docs/decisions-log/2026-09-15-maestro-sync-in-plugin.md`, `docs/decisions-log/2026-09-17-register-perimeter-follows-reader.md`; the register-domains design work (kept outside the repository): shaping, part C5.
