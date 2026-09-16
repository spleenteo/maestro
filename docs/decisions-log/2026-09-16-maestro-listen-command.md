---
work: listen-plugin
status: active
superseded_by: null
tags: [decision, listen, plugin, permissions, distribution]
description: "listen ships in the Maestro plugin as one command on the PATH, maestro-listen, with its Swift source in the skill folder; rules out scripts called through ${CLAUDE_SKILL_DIR}, a bare listen command, and a user-level skill symlinked into ~/.claude/skills."
---

# listen ships as the `maestro-listen` command of the plugin

**Date**: 2026-09-16 · **Work**: `listen-plugin` · **Status**: active

## Context

`listen` shipped in the instance template: a skill plus `bin/listen`, `bin/listen-updates` and `bin/audiowatch.swift`. A satellite has no `.claude/` and receives skills only from the plugin, so the skill never reached satellites or plain folders. Moving it into the plugin meant choosing where its three scripts live and how the skill calls them. During a call the skill calls the capture script on every question the owner asks, so each of those calls has to run without a permission prompt.

## Decision

The capture is one executable, `plugins/maestro/bin/maestro-listen`, on the Bash tool's `PATH` while the plugin is enabled. Its subcommands are `start`, `status`, `text`, `stop` and `updates <minutes>`, which absorbs the former `listen-updates`. `audiowatch.swift` lives in `plugins/maestro/skills/listen/`, and the command finds it through the plugin root. The skill calls `maestro-listen <verb>` as one simple command. The README documents a single user-level allow rule, `Bash(maestro-listen *)`; nothing writes it on the owner's behalf.

## Alternatives discarded

- **Scripts in the skill folder, called through `${CLAUDE_SKILL_DIR}` with `allowed-tools`**: chosen first, reversed by the impact review. The `allowed-tools` grant lasts only the turn that invokes the skill, so a free-form question mid-call prompts, and the expanded path carries the plugin cache SHA, so a saved allow rule breaks on every plugin update.
- **A bare `listen` in `plugins/maestro/bin/`**: plugin `bin/` directories are appended to `PATH`, and `listen` is a common executable name (the Ruby gem `listen` installs one), which shadows the plugin's.
- **A user-level skill symlinked into `~/.claude/skills/`**: the `user-skills/` mechanism that v2026.09.15.1 replaced with the plugin. It needs a manual install on every machine and a copy of the scripts kept up to date somewhere.

## Consequences

- One file on the `PATH` of every session. The name is prefixed, so the collision risk stays low.
- Allow rules instances saved for `bin/listen` stop matching. The owner adds the user-level rule once, or answers the first prompt.
- Instances keep their local copy until `/maestro:maestro-sync` retires it. Until then a bare `/listen` in an instance runs the local skill, and both copies share `~/.local/state/listen/`, so the state format has to stay readable by the old copy.

## References

The listen-plugin work (kept outside the repository): slices and the spike on plugin commands. Claude Code docs: `skills.md` ("Pre-approve tools for a skill", "Resolve skills that share a name"), `plugins-reference.md` (plugin `bin/`).
