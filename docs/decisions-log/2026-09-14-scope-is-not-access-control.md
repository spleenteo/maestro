---
work: satellites-plugin
status: active
superseded_by: null
tags: [decision, memory, memories-db, satellites, scope, privacy, security]
description: "The scope column filters what bin/mem shows and grants no access control: a satellite session can still open the mother's db file. Accepted while the memory has one user."
---

# Scope filters views and grants no access control

**Date**: 2026-09-14 · **Work**: `satellites-plugin` · **Status**: active

## Context

Satellites write into the mother's `memories.db` with their own scope, and `bin/mem` hides the other scopes by default. The impact review found that the same db file holds instance-specific tables with private data, and that a satellite session runs with shell access and knows the path of the mother's `bin/mem`, hence of its db.

## Decision

The scope is a default filter in `bin/mem` and nothing more. No permission layer protects rows or tables from a satellite session. The risk is accepted while the memory has one user, the owner, who is the same person on both sides.

## Alternatives discarded

- **Deny rules against `sqlite3` on the mother's db, written into each satellite**: needs files in the repo, against the decision of the same day, and a deny rule on one command doesn't stop other readers of the file.
- **A separate db per satellite**: real isolation, at the cost of the single index and the cross-context queries the scope column exists for (decision of 2026-09-13).

## Consequences

- The satellite's context says which rows belong to it; nothing enforces it.
- The day teamwork enters (a satellite used by someone other than the owner), this decision no longer holds and the memory needs real access control or separate dbs.

## References

`docs/decisions-log/2026-09-13-scope-column-single-db.md`, `docs/decisions-log/2026-09-14-satellite-leaves-no-repo-files.md`; the satellites-plugin design work (kept outside the repository): the decisions taken at the impact review.
