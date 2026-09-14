---
work: satellites-plugin
status: active
superseded_by: null
tags: [decision, satellites, plugin, hooks, git, privacy]
description: "A satellite leaves no files in its repo: a plugin SessionStart hook recognises the repo from the machine registry and injects scope, role and identity; rules out role files and settings written into the repo."
---

# A satellite leaves no files in its repo

**Date**: 2026-09-14 · **Work**: `satellites-plugin` · **Status**: active

## Context

The first design of 2026-09-13 put the satellite's role in the repo's `CLAUDE.md`, the db pointer in `.claude/settings.local.json`, and planned to hide the rest with `.git/info/exclude`. The impact review found that the first satellite, a personal app's repo, already tracks `.claude/settings.local.json` in git: exclusions don't apply to tracked files, so the mother's absolute paths would reach GitHub with the next commit. Repos shared with a client make the same risk worse.

## Decision

Nothing is written into the repo. `~/.claude/maestro-instances.yaml` lists each satellite (repo path, mother, scope). A `SessionStart` hook shipped by the Maestro plugin matches the session's real path against that list. In a satellite it exports `MEM_SCOPE` through `CLAUDE_ENV_FILE` and injects the role, the identity extract, and the mother's Memory and Writing register blocks with absolute paths. The role, chosen at init, is stored in the mother's `satellites` table. `MEM_DB` is not used: the mother's `bin/mem` finds its db from its own path. Spike S1 verifies the mechanism before V5 is planned.

## Alternatives discarded

- **Role in the repo's `CLAUDE.md`, pointer in `.claude/settings.local.json`, exclusions in `.git/info/exclude`** (the first design's hypothesis): fails on files already tracked, and edits a file the project's team owns.
- **`MEM_DB` in the environment**: redirects every `bin/mem` run from the session, including other instances' and development copies, to the mother's db.

## Consequences

- A collaborator who clones the repo sees nothing of the satellite.
- The hook runs in every session on the machine, so it has to be silent and fast outside satellites.
- Editing a satellite's role happens in the mother, through `bin/mem satellite`.
- Access to the linked vault folder can't come from repo settings: S1 chooses between user-level settings and permission prompts.
- If S1 finds the hook can't export the scope, this decision is revisited before V5.

## References

The satellites-plugin design work (kept outside the repository): the decisions taken at the impact review, spike S1, V5.
