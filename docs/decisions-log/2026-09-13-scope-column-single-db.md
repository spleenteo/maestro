---
work: satellites-plugin
status: active
superseded_by: null
tags: [decision, memory, memories-db, satellites, scope, schema]
description: "Satellite memory lives in the mother's memories.db as rows with a scope column; rules out one db per satellite and a db inside the project repo."
---

# Satellite memory is a scope column in the mother's db

**Date**: 2026-09-13 · **Work**: `satellites-plugin` · **Status**: active

## Context

A satellite is a context of the mother instance opened inside a project repo, and it needs its own memory without polluting the mother's. The satellites-plugin design work of 2026-09-13 weighed where that memory lives and how it stays separate.

## Decision

`log` gains a `scope TEXT` column. The satellite's rows carry its slug (default: the repo folder name); the mother's rows keep `scope` null. `bin/mem` applies the scope by default: with `MEM_SCOPE` set it reads and writes only that scope, without it the mother reads null-scope rows and opens the others with `--scope` or `--all-scopes`. The satellites registry is a table in the same db. Isolation depends on every read of `log` going through `bin/mem`, so skills and agents lose their direct `sqlite3` access to that table; instance-specific tables keep theirs (amended 2026-09-14 after the impact review).

## Alternatives discarded

- **One db per satellite**: isolation comes for free, but the logbook, "what do you know about X", the semantic index and moving rows between contexts all need code that reads several dbs. Kept as the way out if concurrent writes on iCloud cause trouble.
- **Db inside the project repo, versioned in git**: needed only for teamwork, which is out for now. SQLite in git conflicts on parallel writes, and a client's git history would carry private notes.
- **Tags instead of a column**: tags are free and multiple, so they can't act as a default filter.

## Consequences

- One id space and one semantic index across contexts.
- A single direct `sqlite3` query on `log` in a skill or agent leaks every scope: the rule "`log` only through `bin/mem`" carries the isolation of views. Access control is a separate matter (`2026-09-14-scope-is-not-access-control.md`).
- More sessions write the same file. An instance's db can live in iCloud with `journal_mode=delete`; concurrency stays under observation.

## References

The satellites-plugin design work (kept outside the repository): the framing and slices V1 and V2, plus an earlier shaping of 2026-04-20 on shared memory (column `actor`).
