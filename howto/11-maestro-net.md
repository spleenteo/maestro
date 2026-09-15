---
origin: maestro
maestro_version: v2026.08.26.2
tags: [howto, maestro-net, cross-istanza, registry, skill, plugin, marketplace, chezmoi, isolamento, orchestrator]
description: "How several Maestro instances talk to each other: the two verbs `recap` and `ask`, the `~/.claude/maestro-instances.yaml` registry, installing `maestro-net` from the Maestro Claude Code plugin, and how a failure degrades explicitly. Reference for maestro-net."
---

# 11 — maestro-net

An owner who lives in more than one context ends up with more than one instance: work, personal, one client, another client. Each keeps its own `memories.db`, its own preferences, its own domain. That separation is the point, and it holds until the day something learned in one context belongs in another.

maestro-net is the channel between them. Two verbs, one registry, one hard constraint.

## Install

maestro-net ships in the Maestro Claude Code plugin, not as a skill copied by hand into `~/.claude/skills/`.

```bash
claude plugin marketplace add spleenteo/maestro
claude plugin install maestro@maestro
```

`claude plugin install` defaults to user scope, which is what this plugin wants: installed once, reachable from every session on the machine regardless of which folder it opens in. Auto-update is off, and stays off without any setting on the marketplace entry: Claude Code enables auto-update by default only for `claude-plugins-official` and the other Anthropic-run marketplaces, and leaves it disabled by default for a third-party marketplace like this one. A new version published upstream sits there until asked for, in two steps — the marketplace listing and the installed plugin update separately, so refresh what the marketplace knows about before updating to it:

```bash
claude plugin marketplace update maestro
claude plugin update maestro@maestro
```

From any session, the skill runs as `/maestro:maestro-net` (the `<plugin>:<skill>` form every plugin skill uses), and the Bash tool can call the `maestro-net` command directly, because the plugin puts its `bin/` on the Bash tool's `PATH` while it's enabled:

```bash
maestro-net recap home "titolo" -d "contesto" -t tag1,tag2
```

**That `PATH` entry exists only inside a Claude Code session's Bash tool.** It is not on the owner's own terminal `PATH`, and it is not on a hook process's `PATH` — hooks run outside the Bash tool's environment entirely. A hook that needs `maestro-net` calls it by full path instead, built from the variable Claude Code sets to the plugin's own root: `${CLAUDE_PLUGIN_ROOT}/bin/maestro-net`.

### Migrating from the user-level copy

Instances that installed the earlier `user-skills/maestro-net` by hand (`cp -R user-skills/maestro-net ~/.claude/skills/`, per an older version of this guide) now carry two copies: the hand-copied one in `~/.claude/skills/`, and the plugin's. If `~/.claude` is managed with chezmoi, drop the old copy from chezmoi first:

```bash
chezmoi forget ~/.claude/skills/maestro-net
```

`forget` drops the entry from chezmoi's source state; the live folder stays on disk until removed by hand, which is also the only step when chezmoi isn't involved:

```bash
/bin/rm -rf ~/.claude/skills/maestro-net
```

On a second machine chezmoi manages, `chezmoi forget` isn't the instruction to repeat: once the chezmoi source commit carrying this change has reached it, that machine's chezmoi source state no longer has the entry either, so `forget` has nothing left to drop there and fails. The instruction on the second machine is the plain removal above (`/bin/rm -rf ~/.claude/skills/maestro-net`) only — or skip per-machine `forget` entirely and list the path in `.chezmoiremove` in the chezmoi source directory, so `chezmoi apply` deletes the folder on every machine that applies that source state.

## The constraint

**The channel carries memories, not permissions.**

No verb touches files, MCP servers or tasks belonging to another instance. A session that needs to *act* inside another instance opens a session there. What crosses the channel is a memory, a question, or, from a satellite to its mother, a request.

A request still carries no permission. The satellite asks; the mother opens its own session, judges the request against the satellite's row and its own rules, and acts with its own tools. The request text can't widen what the mother does, and `request` is granted per instance in `accepts`, never by default.

The constraint comes from an incident: a work instance read the owner's personal task manager to answer a question about the day, because MCP servers load user-level and are therefore visible to every session regardless of the folder it runs in. Preferences declared the boundary; nothing enforced it. Here the boundary is a field in a file, `accepts`, that the owner can read and change.

Enforcement, concretely: the remote command's environment is stripped of `MEM_DB` (a sender-side override would otherwise make the recipient's `bin/mem` write into the sender's own database) and of `MEM_SCOPE` (a `recap` or `ask` launched from inside a satellite session would otherwise land in the sender's scope inside the recipient's db, instead of the recipient's own null scope). `PWD` and `CLAUDE_PROJECT_DIR` are stripped too, so the recipient's tools and the plugin's session hook see the recipient's folder, not the sender's.

## The verbs

### recap

Writes a memory into the recipient's db by invoking the recipient's own `bin/mem` with an absolute path. `bin/mem` resolves its database from the location of the script, so an instance invoked from anywhere still writes into its own db.

```bash
maestro-net recap home "titolo" -d "contesto" -t tag1,tag2
```

The row is always tagged `from:<sender>`, which is what makes the arrival readable later. The sender is resolved in three steps: `--from` if given, otherwise the registry name of the directory the command runs from, otherwise that directory's name. The confirmation says which one applied.

No model is involved. This is the cheap verb, and the reason handoff was left out of the design: pushing a memory covers most of what a handoff was for, at a fraction of the cost.

### ask

Runs `claude -p` in the recipient's directory. The recipient's `CLAUDE.md`, preferences and memory apply, so the answer comes from that instance rather than from a generic model reading its files.

```bash
maestro-net ask home "cosa sappiamo delle biciclette?"
```

The prompt carries a read-only clause: answer, write nothing, open no task, call no state-changing MCP. No persistent session is opened, and nothing appears in the agent view. Default timeout 180 seconds.

### request

Runs only from a registered satellite repo, and always reaches that satellite's mother. It launches a background session in the mother's folder and returns at once:

```bash
maestro-net request "write a dossier on the onboarding flow in my vault folder"
```

- The session is `claude --bg --name <mother>-<scope>-<4 hex>`, so it appears as a row in `claude agents`; `claude attach <id>` opens it, `claude stop <id>` stops it, `claude rm <id>` removes the row.
- The prompt carries `requesting_scope`, `satellite_repo`, `vault_folder`, `reply_to` (`uds:` plus the satellite session's `CLAUDE_CODE_MESSAGING_SOCKET`, or `none`), the request name, and the rules the mother follows. The mother's own `## Requests from satellites` section in `CLAUDE.md` stays the authority.
- The linked vault folder is passed as `--add-dir`, so writes there don't stop on a permission prompt. No permission mode is passed unless `--permission-mode` is given: the session starts in the mode configured for the mother's folder.
- The mother replies once with `SendMessage` to `reply_to`, with absolute paths, and always saves one memory in the requesting scope, `request <name>: done` or `request <name>: refused`. When the satellite session is gone, or had no messaging socket, that memory is the answer: `MEM_SCOPE=<scope> <mother>/bin/mem search "request <name>"`.
- The request session writes documents only in the vault folder and never edits the mother's repository: a background session that edits files of a git repo moves into a worktree first, where `bin/mem` finds no `private/memories.db`.
- Before launching, the verb reads the satellite's row through the mother's `bin/mem satellite show`; no row means exit 8 and no session. The launched environment drops `MEM_DB`, `MEM_SCOPE`, `PWD`, `CLAUDE_PROJECT_DIR`, `CLAUDE_CODE_MESSAGING_SOCKET` and `CLAUDE_ENV_FILE`.
- On macOS the background session host asks for folder access separately from the terminal: a mother or a vault in iCloud Drive may need access granted in System Settings, Privacy & Security, Files and Folders.

## The registry

`~/.claude/maestro-instances.yaml`:

```yaml
version: 1
instances:
  home:
    path: /Users/you/Sites/home-instance
    domain: vita personale
    accepts: [recap, ask]
  work:
    path: /Users/you/Sites/work-instance
    domain: lavoro in azienda SaaS
    accepts: [recap]
```

- **`path`**: the instance's root, the directory holding `bin/mem` and `private/preferences.md`.
- **`domain`**: what the instance is for. It carries the routing when the owner doesn't name a recipient. The scanner leaves it empty on purpose: only the owner knows.
- **`accepts`**: the verbs that instance allows. Absent or empty means none. A verb this copy of `maestro-net` doesn't recognize — the case a future template version adds one that an older plugin install hasn't seen — doesn't fail the whole registry: it's dropped from that instance's `accepts` with a warning on stderr. That dropped verb was never a valid subcommand for this older copy in the first place, so trying to *invoke* it directly (`maestro-net <that-verb> …`) never reaches the `accepts` check at all — argument parsing rejects it as an invalid choice first (exit 2, the same as any other typo'd verb). Exit 6 is for a verb this copy does recognize (`recap` or `ask`) that the recipient's own `accepts` simply doesn't list.

### Why not `~/.maestro/`

`~/.maestro/` is the read-only mirror of the template, updated by `maestro-sync` with `git fetch && git reset --hard origin/main`. A registry living there would be wiped by the next sync. `~/.claude/` is the owner's own configuration directory, independent of wherever `maestro-net` itself happens to be installed from.

### Populating it

```bash
maestro-net scan          # prints the proposal
maestro-net scan --write  # writes the file
```

The scanner works from `~/.claude/projects/`. Those directory names are slugs where `-` replaces `/`, `.` and spaces, so they can't be turned back into paths; the real `cwd` is inside the transcripts, and that's what the scanner reads. A directory is kept when it holds both `private/preferences.md` and `bin/mem`. The name comes from the `Identity` block, tolerating the bold or plain form of the field. Several project slugs pointing at one directory collapse into one entry, and two instances that answer to the same name are disambiguated with a numeric suffix and a warning.

`--accepts recap` narrows what the proposal grants; `--force` overwrites an existing registry, which `--write` refuses to do on its own. `maestro-net list` shows what's currently registered, and flags any path that no longer exists on disk.

The registry itself stays out of chezmoi when instance paths differ between machines; add it there only once the paths match on every machine chezmoi applies to.

### Adding or removing one instance

`scan --write --force` rewrites the whole file, so it loses every `domain` and `accepts` the owner filled in by hand (the `satellites:` block is carried over; a malformed registry holding one is refused with exit 4), and it can't see an instance that has no transcript yet. `register` adds one instance without touching the others — the way `/maestro:new-instance` registers the instance it just created:

```bash
maestro-net register home --path /Users/you/Sites/home-instance \
  --domain "vita personale" --accepts recap,ask
```

- **`NAME`** must already be a lowercase slug, `^[a-z0-9][a-z0-9-]*$`. It is checked as given, never lowercased for you — an uppercase letter is a usage error (exit 2).
- **`--path`** must be absolute. It is stored as its real path, symlinks resolved, and compared by real path against every entry already in the registry: a name already there (case-insensitively) or a path already there (by real path, so a symlink to an already-registered instance is caught too) exits 9.
- **`--domain`** defaults to empty and is always written double-quoted, matching the quoting `scan` already uses. A value carrying `"` or a line break can't be represented and is refused (exit 2).
- **`--accepts`** defaults to `recap,ask`. Every value must be a verb this copy of `maestro-net` recognizes, or it's a usage error — stricter than a registry it only *reads*, where an unknown verb in `accepts` is dropped with a warning instead.
- `register` refuses a `--path` that isn't a Maestro instance's own root: no `private/preferences.md` and `bin/mem` there is the same signature check the scanner applies, in its own function so a later satellite-entry command can register a project root without it.

The entry lands with the same field order and indentation `render_registry` uses (`path`, then `domain`, then `accepts`), inserted at the end of the `instances:` block. Every other line in the file, including comments and the other instances' `domain` and `accepts`, is untouched — `register` edits the text surgically rather than reparsing and rewriting the whole registry the way `scan --write` does.

`unregister <name>` removes one instance the same surgical way. An unknown name resolves like everywhere else in this tool (exit 5, known names listed in the error).

```bash
maestro-net unregister home
```

Both assume a single writer: nothing locks the registry file, so two `register`/`unregister` calls racing on it can each read before the other writes, and the second write silently loses the first's change.

### Satellites

A satellite is a project repo attached to an instance, its mother (`howto/12-satellites.md`). The registry keeps satellites in their own top-level block, read by the plugin's session hook to recognise the repo:

```yaml
satellites:
  acme:
    repo: /Users/you/Sites/acme
    mother: home
```

```bash
maestro-net satellite add acme --repo /Users/you/Sites/acme --mother home
maestro-net satellite remove acme
```

- The scope is a lowercase slug, like an instance name (exit 2 otherwise). `--repo` must be an absolute path to an existing directory (exit 2, exit 7) and is stored as its real path.
- `--mother` must be a registered instance (exit 5).
- A scope already registered, or a repo equal to, inside or containing an instance path or another satellite's repo, exits 9. `register` applies the mirror check: an instance path inside or containing a satellite's repo exits 9.
- `satellite remove` edits only the `satellites:` block; an unknown scope exits 5.
- A satellite is never a recipient: `recap` and `ask` resolve instance names only, and `request` only goes from a satellite to its mother. `list` shows satellites apart.

The `satellite` skill of the plugin calls `satellite add` after `bin/mem satellite add` in the mother; used by hand, the two registrations have to agree.

## Degradation

Every failure has its own exit code and says what happened.

| Exit | Meaning |
|---|---|
| 0 | Done |
| 2 | Usage error |
| 3 | Registry missing |
| 4 | Registry malformed (with the offending line number) |
| 5 | Unknown instance, or a name matching more than one; `request` run outside a satellite repo, or a satellite whose mother isn't registered |
| 6 | Verb not in the recipient's `accepts` |
| 7 | The recipient's path no longer exists, or has no `bin/mem` — also `register`'s `--path`, when it isn't a directory or isn't a Maestro instance's own root |
| 8 | The remote command failed, timed out, or couldn't be started; `request` found no row for the satellite in its mother |
| 9 | `register` found the name or the path already in the registry, or a path overlapping a satellite's repo; `satellite add` the scope, or a repo overlapping an instance or another satellite |

The rule behind the table: a channel that can't deliver says so. A recap that can't reach its recipient is never written somewhere else, and a malformed registry never degrades into an empty one.

The registry parser is deliberately strict for the same reason. It reads a small closed schema and rejects everything outside it, rather than skipping what it doesn't understand — with the one deliberate exception of an unknown verb in `accepts`, above. A silently ignored *line* would mean an instance quietly missing from the network; a silently ignored *verb* would mean an older `maestro-net` copy refusing to read a registry a newer one wrote.

## What isn't built yet

The reading side. Each instance would pick up, at session start, the `from:*` rows that arrived since its last marker and announce them in one line, the same shape as the warm channel's garbage collector (`howto/07`). Until then, recaps are found the way any memory is: with `bin/mem search from:<name>`.

## Tests

```bash
python3 -m unittest tests.test_maestro_net
```

90 tests, stdlib only, no real instances and no network: registry parsing and its malformations (including the unknown-verb warning), name resolution including the ambiguous case, the `accepts` gate, the scanner against fake transcripts, both verbs against recorder scripts that capture their arguments and environment (`MEM_DB`, `MEM_SCOPE` and `PWD` stripped), and `register`/`unregister` against temp registries — creation from nothing, surgical append and removal that leaves comments and every other entry's fields untouched (including a comment sitting between two instances, or trailing after the last one), the duplicate and slug checks, and the instance-signature check on `--path`.
