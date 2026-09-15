---
work: satellites-plugin
status: active
superseded_by: null
tags: [decision, bin-mem, plugin, satellites, distribution]
description: "bin/mem stays in each instance and satellites call the mother's copy by absolute path; rules out shipping bin/mem in the plugin and installing code into each repo with npx."
---

# `bin/mem` stays in each instance

**Date**: 2026-09-13 · **Work**: `satellites-plugin` · **Status**: active

## Context

The plugin distributes the cross-instance skills, and plugins can put executables on the PATH. `bin/mem` is the tool every satellite needs to reach the mother's memory, so the question is whether it belongs in the plugin too.

## Decision

`bin/mem` (with `bin/mem-vec`) stays in each instance. A satellite calls the mother's `bin/mem` by absolute path, which finds its db from its own location; the plugin's session hook exports `MEM_SCOPE` (amended 2026-09-14: the first version put `MEM_DB` and `MEM_SCOPE` in the repo's `.claude/settings.local.json`). The plugin carries skills, the session hook and the `maestro-net` script, never `bin/mem`.

## Alternatives discarded

- **`bin/mem` in the plugin**: one version on the PATH for every instance, while each instance's db schema moves with its own template version. An update would hit dbs not yet migrated.
- **npx package installed into each repo**: code to update in every repo, a Node dependency, a package to publish.

## Consequences

- The satellite runs whatever `bin/mem` version its mother has: the mother must be updated first.
- `bin/*` is still outside `maestro-sync` scope, so the mother gets a new `bin/mem` through a manual copy, as in every release so far.
- Moving `bin/*` into sync scope, or into the plugin once schemas are versioned, stays a separate question. (Amended 2026-09-15: `/maestro:maestro-sync` now copies drifted `bin/*` on the owner's yes, see `2026-09-15-maestro-sync-in-plugin.md`; `bin/mem` still lives in each instance.)

## References

The satellites-plugin design work (kept outside the repository): the framing criterion and the V5 gotchas.
