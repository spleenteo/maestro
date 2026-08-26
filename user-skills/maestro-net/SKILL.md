---
origin: maestro
maestro_version: v2026.08.26.2
name: maestro-net
description: Cross-talk between the owner's Maestro instances. Two verbs, `recap` (write a memory into another instance's db) and `ask` (query another instance headless and report the answer). Use when the owner says "fai un recap ad Alfred", "manda a Pam", "segna su Luigi", "chiedi ad Alfred cosa sa di X", "what does Pam know about Y", or names one of their instances as the recipient of something that happened here. Installed user-level, so it works from any Claude Code session, including ones that know nothing about Maestro.
---

# maestro-net

The owner runs several Maestro instances, one per life context, each with its own `memories.db` and its own domain. They stay separate on purpose. This skill is the channel between them.

**The channel carries memories, not permissions.** No verb touches files, MCP servers or tasks of another instance. A session that wants to *do* something inside another instance opens a session there; what crosses this channel is a memory or a question.

That constraint has a history: an instance once read the owner's personal task manager from a work session, because MCP servers load user-level and are visible to every session regardless of the folder. The registry's `accepts` field is where the constraint stops being a good intention and becomes a value the owner can edit.

## The tool

Everything runs through one script, next to this file:

```bash
~/.claude/skills/maestro-net/maestro-net --help
```

It is Python, stdlib only, no network beyond what `claude` itself does.

## Verb 1 — recap

Writes a memory into the recipient's `memories.db`, invoking the recipient's own `bin/mem` with an absolute path. No model involved, so the cost is zero.

```bash
~/.claude/skills/maestro-net/maestro-net recap alfred "titolo della memoria" \
  -d "contesto lungo, opzionale" -t tag1,tag2
```

- The row is always tagged `from:<sender>`. The sender is the instance the command runs from, or the current directory's name when that isn't an instance; `--from <name>` overrides it. The confirmation line says which name was used and why, so a wrong sender is visible immediately.
- **Compose the text, don't paste the conversation.** A recap is one line the recipient will read weeks later out of context: what happened, what changed, what it means for them. Add `-d` when the *why* doesn't fit the title.
- Tags: pick them from the recipient's world. `from:` is added for you.
- `--dry-run` prints the exact command without running it.

Report to the owner in one line what was written and to whom, the same discipline as an ordinary memory write.

## Verb 2 — ask

Runs `claude -p` in the recipient's directory, so their `CLAUDE.md`, their preferences and their memory apply, then reports the answer. No persistent session is opened.

```bash
~/.claude/skills/maestro-net/maestro-net ask alfred "cosa sappiamo delle biciclette?"
```

- The prompt carries a read-only clause: answer, write nothing, open no task, call no state-changing MCP.
- Default timeout 180s (`--timeout`). It is a real model call in another context: costs tokens, takes seconds.
- The answer comes back to the owner through you. Attribute it (*"Alfred dice che…"*), and don't merge it into your own knowledge without saying where it came from.

`recap` before `ask` when both fit: one is free.

## The registry

`~/.claude/maestro-instances.yaml` holds name, path, domain and accepted verbs.

```yaml
version: 1
instances:
  alfred:
    path: /Users/…/spleenteo-majordomo
    domain: vita personale, clienti a ritenuta
    accepts: [recap, ask]
```

- `domain` is what the instance is *for*. Use it to route when the owner doesn't name a recipient ("segna che ho pagato il commercialista" → the instance whose domain covers it). When two domains fit, ask; never pick silently.
- `accepts` lists the verbs that instance allows. Absent or empty means no verb is allowed.
- The file stays out of `~/.maestro/`: that is the read-only mirror of the Maestro template, reset by `maestro-sync`, and a registry there would be wiped.

First population:

```bash
~/.claude/skills/maestro-net/maestro-net scan            # proposes, prints to stdout
~/.claude/skills/maestro-net/maestro-net scan --write    # writes the file
```

The scanner reads `~/.claude/projects/`, resolves each project's real `cwd` from its transcripts, and keeps the directories that carry both `private/preferences.md` and `bin/mem`, the signature of a working Maestro instance. Names come from the `Identity` block. It leaves `domain` empty: only the owner can fill that in.

`list` shows what is registered, and flags paths that no longer exist.

## When something fails

Every failure is explicit and named. Report it to the owner as it is; never retry a different way, never fall back silently to writing in the local db.

| Exit | What happened | What to say |
|---|---|---|
| 3 | Registry missing | Nothing is registered yet, offer to run `scan` |
| 4 | Registry malformed | Report the line number the tool gives |
| 5 | Unknown or ambiguous name | List the known instances and ask which one |
| 6 | Verb not in `accepts` | Say that the instance doesn't accept it, and that the registry is where it changes |
| 7 | Path gone | The instance moved, offer to re-run `scan` |
| 8 | Remote command failed | Report the recipient's own error output |

A missing registry is not a reason to write the memory somewhere else. The owner asked to reach another instance; if the channel is down, they need to know.

## Writing register

The text of a `recap` is a `memories.db` row, which sits outside the writing register's perimeter: no post-pass. What binds it is brevity and the fact that it will be read out of context.

The reply from an `ask` is the other instance's text. Pass it through, quote it, don't rewrite it.
