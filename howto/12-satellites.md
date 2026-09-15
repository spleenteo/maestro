---
origin: maestro
maestro_version: v2026.09.15.1
tags: [howto, satellites, scope, plugin, hooks, maestro-net, bin-mem, vault, orchestrator]
description: "How a project repository becomes a satellite of a Maestro instance: the satellite skill, what the plugin's hooks inject at session start, where the registration lives, the vault folder, how the mother reads a satellite's memories, removal and limits. Reference for satellites."
---

# 12 — Satellites

A project repository often needs the orchestrator you already have: its identity, its memory, its vault. Copying an instance into the repo would split the memory and add files a team doesn't want. A satellite keeps the repo untouched and borrows all three from an existing instance, its mother.

## What a satellite is

- **Memory**: the satellite writes into the mother's `private/memories.db`, every row tagged with the satellite's scope (a slug). A satellite session reads only its scope; the mother reads its own rows by default and a satellite's with `--scope` (see `howto/04-memory-and-integrations.md` and the `## Memory` section of `CLAUDE.md`).
- **Role**: a project type (`ux`, `consulting`, `development`), a mandate, a method, constraints, a language. The role adds what the work needs; the voice and the identity stay the mother's.
- **Vault folder**: an optional folder in the mother's vault for the project's documents.
- **No files in the repo**: nothing is added, so `git status` stays as it was.

## Requirements

- The Maestro plugin installed at user scope, with its hooks enabled:

  ```bash
  claude plugin marketplace add spleenteo/maestro
  claude plugin install maestro@maestro
  ```

- A mother registered in `~/.claude/maestro-instances.yaml` (`/maestro:new-instance` registers the instances it creates; see `howto/11-maestro-net.md` for older ones).
- The mother's `bin/mem_schema.py` at `SCHEMA_API = 2` or later. An older mother gets its `bin/` from the template first.

## Create one

Open a session in the repo and ask: "make this repo a satellite of home". The plugin's `satellite` skill:

1. resolves the repo to its main checkout, so a worktree or a subfolder registers the repo itself;
2. picks the mother from the registry and checks its `SCHEMA_API`;
3. asks the scope (the folder name normalised), the role fields and the vault folder;
4. registers the role in the mother (`bin/mem satellite add`) and the repo in the machine registry (`maestro-net satellite add`), undoing the first when the second fails;
5. runs a chain check: a memory saved and found in the satellite's scope and absent from the mother's default search, a note written in the vault folder, passed to `bin/register-check`, read back and deleted, `git status` in the repo unchanged;
6. tells you to open a new session in the repo.

## What a session in the repo gets

The plugin's `SessionStart` hook runs at every session start, whatever its source (startup, resume, `/clear`, compaction). It resolves the session folder (symlinks and worktrees included) against the `satellites:` block of the registry. Outside a registered repo, and inside a folder that is itself a registered instance, it prints nothing. Inside a satellite repo it:

- appends `export MEM_SCOPE=<scope>` to the session's environment file, when Claude Code provides one, so Bash calls carry the scope;
- asks the mother's `bin/mem satellite show` for the role;
- reads the mother's `private/preferences.md` and keeps only the level-2 sections named `Identity`, `Owner — basics`, `Communication preferences` or `Writing register`, optionally followed by a parenthetical such as `(the orchestrator)`. Code fences never open a section, and any other heading or `---` rule closes one: people, integrations and the rest stay in the mother;
- injects role, identity and the operating rules as context: every memory command written as `MEM_SCOPE=<scope> "<mother>/bin/mem" …`, so the scope holds even without the environment file (the context says when the export didn't happen), the pointer to the mother's `## Memory` and `## Writing register` sections, the vault folder, and two prohibitions (no `bin/mem embed`, no warm task channel garbage collector: both belong to the mother).

The `PreToolUse` hook opens the vault folder to `Read`, `Write`, `Edit`, `Grep` and `Glob`. It runs on every file tool call on the machine, so a shell guard exits at once unless the session start wrote a marker for the project under the plugin's data folder.

When the registry names a mother that is missing or too old, has no row for the scope, or has a row pointing to another repo, the session gets one line of context saying so, no scope and no vault access.

## Asking the mother

A satellite session can ask its mother a question with `maestro-net ask <mother> "…"`: the answer comes only from the satellite's row, the memories of its scope and the files in its vault folder, never from the rest of the mother's vault or memory. It can hand work to its mother with `maestro-net request "<goal and where the result goes>"`, once the owner has added `request` to the mother's `accepts` in the registry. The verb opens a background session in the mother, visible in `claude agents`, and returns. The mother judges the request against the satellite's row, works with its own skills and agents, writes documents in the linked vault folder, and replies with a message to the satellite session. It also saves one memory in the satellite's scope, `request <name>: done` or `refused`, which is the answer when the satellite session is closed. The request runs in the mother's own permission mode: in the default mode its first write waits for the owner in `claude agents`, while `acceptEdits` or `auto` let it write in the vault unattended. A vault folder inside the mother's own repository isn't supported: the first write would move the session into a git worktree. Details and failure codes: `howto/11-maestro-net.md`.

## From the mother

```bash
bin/mem satellite list
bin/mem search --scope acme --limit 20
bin/mem today --all-scopes
```

`todo` and `overdue` already list every scope's tasks in the mother, with a `scope` column.

## Remove one

```bash
bin/mem satellite remove acme            # in the mother
maestro-net satellite remove acme
```

The scope's memories stay in the mother's db. The next session in the repo drops the marker: after the first command it prints the one-line notice, after both it starts as an ordinary session.

## Limits

- One mother per repo, one repo per scope. A repo inside another satellite or inside an instance is refused, and so is an instance registered inside a satellite repo.
- No `satellite update`: to change a role, remove and add again.
- Semantic search from a satellite ranks its own memories and the whole vault index.
- A satellite reaches its mother only through `maestro-net recap`, `ask` and `request`; a request grants no permission, and the mother decides.
- The hook needs `python3` and `git` on the machine.
