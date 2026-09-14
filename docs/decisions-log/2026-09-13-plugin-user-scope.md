---
work: satellites-plugin
status: active
superseded_by: null
tags: [decision, plugin, claude-code, distribution, marketplace]
description: "The Maestro plugin installs at user scope with autoUpdate off; rules out project-scope installs declared in each repo."
---

# The Maestro plugin installs at user scope, updated by hand

**Date**: 2026-09-13 · **Work**: `satellites-plugin` · **Status**: active

## Context

The Maestro repo becomes a Claude Code marketplace carrying `maestro-net`, `new-instance`, `satellite` and `maestro-sync`. A plugin can be enabled for the user or for a project, and a marketplace can update itself automatically.

## Decision

The plugin is installed at `user` scope, with `autoUpdate` off on the marketplace. Updates run by hand with `claude plugin update`.

## Alternatives discarded

- **Project scope**: each instance and each satellite repo would declare the plugin in `enabledPlugins` inside a committed `.claude/settings.json`, which leaves a trace in repos shared with other people, and `new-instance` must run from a folder that doesn't exist yet.
- **User scope with `autoUpdate` on**: one update reaches every instance at once, including an update that breaks something.

## Consequences

- Every session on the machine sees the plugin's skills, including sessions that aren't instances or satellites. `maestro-sync` has to stop by itself outside an instance.
- An update applies to all instances at the same moment: the owner decides when.

## References

The satellites-plugin design work (kept outside the repository): the decisions taken at slicing, V3.
