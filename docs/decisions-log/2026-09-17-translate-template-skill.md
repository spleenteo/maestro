---
work: register-domains
status: active
superseded_by: null
tags: [decision, translate, translation, writing-register, plugin, template, satellites]
description: "The optional translation skill ships in the template as .claude/skills/translate, loaded only where preferences enable translation; rules out a plugin skill and a section of writing-register. Read before moving translate or adding another optional writing skill."
---

# `translate` is a template skill, loaded only where enabled

**Date**: 2026-09-17 · **Work**: `register-domains` · **Status**: active

## Context

Translating a draft under the register is optional: most owners never translate. The skill reads per-instance values (language pair, sign-off, labels, a marker that opens a fresh translation). A day earlier `listen` moved into the plugin so that it runs in every session, which made the plugin the obvious home to consider.

## Decision

`translate` ships as `.claude/skills/translate/` with `origin: maestro` and reaches instances through the reverse scan of `maestro-sync`. The `## Writing register` section of `CLAUDE.md` loads it only when the instance's preferences enable translation. A satellite of a mother that enables it reaches the mother's copy through a line of the plugin's session hook.

Note of 2026-09-17, slice V4: development satellites are code repositories too and receive the skill through the hook pointer, which names the trigger (a draft in the source language, or one opening with the marker) so a request about interface strings never reaches it; the "code repositories" argument below holds for folders outside Maestro. The sign-off on both versions is optional: `communication.sign_off` closes them only when the owner sets it.

## Alternatives discarded

- **A plugin skill**: it would be listed in every session on the machine, code repositories included, where a request to translate interface strings means something else; a plain folder has no preferences to enable it. `listen` went to the plugin because a call can happen in any folder and needs no per-instance values.
- **A section inside `writing-register`**: the translation rules would load each time the register skill loads, for owners who never translate.

## Consequences

- Translation is unavailable in plain folders.
- An instance gets the skill only after syncing.
- Satellites depend on the hook line that points to the mother's copy.

## References

`docs/decisions-log/2026-09-16-maestro-listen-command.md`, `docs/decisions-log/2026-09-17-register-perimeter-follows-reader.md`; the register-domains design work (kept outside the repository): shaping, part C6.
