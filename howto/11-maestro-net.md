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

No verb touches files, MCP servers or tasks belonging to another instance. A session that needs to *act* inside another instance opens a session there. What crosses the channel is a memory or a question.

The constraint comes from an incident: a work instance read the owner's personal task manager to answer a question about the day, because MCP servers load user-level and are therefore visible to every session regardless of the folder it runs in. Preferences declared the boundary; nothing enforced it. Here the boundary is a field in a file, `accepts`, that the owner can read and change.

Enforcement, concretely: the remote command's environment is stripped of `MEM_DB` (a sender-side override would otherwise make the recipient's `bin/mem` write into the sender's own database) and of `MEM_SCOPE` (a `recap` or `ask` launched from inside a satellite session would otherwise land in the sender's scope inside the recipient's db, instead of the recipient's own null scope). `PWD` is stripped too, so it doesn't confuse the recipient's tools with the sender's directory.

## The two verbs

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

`scan --write --force` rewrites the whole file, so it loses every `domain` and `accepts` the owner filled in by hand, and it can't see an instance that has no transcript yet. `register` adds one instance without touching the others — the way `/maestro:new-instance` registers the instance it just created:

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

## Degradation

Every failure has its own exit code and says what happened.

| Exit | Meaning |
|---|---|
| 0 | Done |
| 2 | Usage error |
| 3 | Registry missing |
| 4 | Registry malformed (with the offending line number) |
| 5 | Unknown instance, or a name matching more than one |
| 6 | Verb not in the recipient's `accepts` |
| 7 | The recipient's path no longer exists, or has no `bin/mem` — also `register`'s `--path`, when it isn't a directory or isn't a Maestro instance's own root |
| 8 | The remote command failed, timed out, or couldn't be started |
| 9 | `register` found the name or the path already in the registry |

The rule behind the table: a channel that can't deliver says so. A recap that can't reach its recipient is never written somewhere else, and a malformed registry never degrades into an empty one.

The registry parser is deliberately strict for the same reason. It reads a small closed schema and rejects everything outside it, rather than skipping what it doesn't understand — with the one deliberate exception of an unknown verb in `accepts`, above. A silently ignored *line* would mean an instance quietly missing from the network; a silently ignored *verb* would mean an older `maestro-net` copy refusing to read a registry a newer one wrote.

## What isn't built yet

The reading side. Each instance would pick up, at session start, the `from:*` rows that arrived since its last marker and announce them in one line, the same shape as the warm channel's garbage collector (`howto/07`). Until then, recaps are found the way any memory is: with `bin/mem search from:<name>`.

## Tests

```bash
python3 -m unittest tests.test_maestro_net
```

87 tests, stdlib only, no real instances and no network: registry parsing and its malformations (including the unknown-verb warning), name resolution including the ambiguous case, the `accepts` gate, the scanner against fake transcripts, both verbs against recorder scripts that capture their arguments and environment (`MEM_DB`, `MEM_SCOPE` and `PWD` stripped), and `register`/`unregister` against temp registries — creation from nothing, surgical append and removal that leaves comments and every other entry's fields untouched, the duplicate and slug checks, and the instance-signature check on `--path`.
