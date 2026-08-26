---
origin: maestro
maestro_version: v2026.08.26.2
tags: [howto, maestro-net, cross-istanza, registry, skill, user-level, chezmoi, isolamento, orchestrator]
description: "How several Maestro instances talk to each other: the two verbs `recap` and `ask`, the `~/.claude/maestro-instances.yaml` registry, why the skill is installed user-level, and how a failure degrades explicitly. Reference for maestro-net."
---

# 11 — maestro-net

An owner who lives in more than one context ends up with more than one instance: work, personal, one client, another client. Each keeps its own `memories.db`, its own preferences, its own domain. That separation is the point, and it holds until the day something learned in one context belongs in another.

maestro-net is the channel between them. Two verbs, one registry, one hard constraint.

## The constraint

**The channel carries memories, not permissions.**

No verb touches files, MCP servers or tasks belonging to another instance. A session that needs to *act* inside another instance opens a session there. What crosses the channel is a memory or a question.

The constraint comes from an incident: a work instance read the owner's personal task manager to answer a question about the day, because MCP servers load user-level and are therefore visible to every session regardless of the folder it runs in. Preferences declared the boundary; nothing enforced it. Here the boundary is a field in a file, `accepts`, that the owner can read and change.

## The two verbs

### recap

Writes a memory into the recipient's db by invoking the recipient's own `bin/mem` with an absolute path. `bin/mem` resolves its database from the location of the script, so an instance invoked from anywhere still writes into its own db.

```bash
~/.claude/skills/maestro-net/maestro-net recap alfred "titolo" -d "contesto" -t tag1,tag2
```

The row is always tagged `from:<sender>`, which is what makes the arrival readable later. The sender is resolved in three steps: `--from` if given, otherwise the registry name of the directory the command runs from, otherwise that directory's name. The confirmation says which one applied.

No model is involved. This is the cheap verb, and the reason handoff was left out of the design: pushing a memory covers most of what a handoff was for, at a fraction of the cost.

### ask

Runs `claude -p` in the recipient's directory. The recipient's `CLAUDE.md`, preferences and memory apply, so the answer comes from that instance rather than from a generic model reading its files.

```bash
~/.claude/skills/maestro-net/maestro-net ask alfred "cosa sappiamo delle biciclette?"
```

The prompt carries a read-only clause: answer, write nothing, open no task, call no state-changing MCP. No persistent session is opened, and nothing appears in the agent view. Default timeout 180 seconds.

## The registry

`~/.claude/maestro-instances.yaml`:

```yaml
version: 1
instances:
  alfred:
    path: /Users/…/spleenteo-majordomo
    domain: vita personale, clienti a ritenuta
    accepts: [recap, ask]
  pam:
    path: /Users/…/pam
    domain: lavoro DatoCMS
    accepts: [recap]
```

- **`path`**: the instance's root, the directory holding `bin/mem` and `private/preferences.md`.
- **`domain`**: what the instance is for. It carries the routing when the owner doesn't name a recipient. The scanner leaves it empty on purpose: only the owner knows.
- **`accepts`**: the verbs that instance allows. Absent or empty means none.

### Why not `~/.maestro/`

`~/.maestro/` is the read-only mirror of the template, updated by `maestro-sync` with `git fetch && git reset --hard origin/main`. A registry living there would be wiped by the next sync. `~/.claude/` is the owner's own configuration directory, which is also where the skill lives.

### Populating it

```bash
~/.claude/skills/maestro-net/maestro-net scan          # prints the proposal
~/.claude/skills/maestro-net/maestro-net scan --write  # writes the file
```

The scanner works from `~/.claude/projects/`. Those directory names are slugs where `-` replaces `/`, `.` and spaces, so they can't be turned back into paths; the real `cwd` is inside the transcripts, and that's what the scanner reads. A directory is kept when it holds both `private/preferences.md` and `bin/mem`. The name comes from the `Identity` block, tolerating the bold or plain form of the field. Several project slugs pointing at one directory collapse into one entry, and two instances that answer to the same name are disambiguated with a numeric suffix and a warning.

`--accepts recap` narrows what the proposal grants; `--force` overwrites an existing registry, which `--write` refuses to do on its own.

## Where the skill lives

**User-level, in `~/.claude/skills/maestro-net/`**, not inside any instance.

The typical caller is a development session in some unrelated repository, where the owner has just finished a piece of work and wants it recorded in their personal instance. That session has no Maestro skills loaded and no reason to. A user-level skill is visible from every session on the machine.

The Maestro repository is where the skill is *authored*: it owns the version, the tests, the changelog entry. Installation is a copy:

```bash
cp -R user-skills/maestro-net ~/.claude/skills/
```

If `~/.claude` is managed by chezmoi, register the copy so the second machine gets it:

```bash
chezmoi add ~/.claude/skills/maestro-net
```

The registry stays out of chezmoi if the instance paths differ between machines; add it only when they match.

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
| 7 | The recipient's path no longer exists, or has no `bin/mem` |
| 8 | The remote command failed, timed out, or couldn't be started |

The rule behind the table: a channel that can't deliver says so. A recap that can't reach its recipient is never written somewhere else, and a malformed registry never degrades into an empty one.

The registry parser is deliberately strict for the same reason. It reads a small closed schema and rejects everything outside it, rather than skipping what it doesn't understand. A silently ignored line would mean an instance quietly missing from the network.

## What isn't built yet

The reading side. Each instance would pick up, at session start, the `from:*` rows that arrived since its last marker and announce them in one line, the same shape as the warm channel's garbage collector (`howto/07`). Until then, recaps are found the way any memory is: with `bin/mem search from:<name>`.

## Tests

```bash
python3 -m unittest tests.test_maestro_net
```

59 tests, stdlib only, no real instances and no network: registry parsing and its malformations, name resolution including the ambiguous case, the `accepts` gate, the scanner against fake transcripts, and both verbs against recorder scripts that capture their arguments and environment.
