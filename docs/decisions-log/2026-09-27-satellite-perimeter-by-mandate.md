---
work: satellite-answer-perimeter
status: active
superseded_by: null
tags: [decision, satellites, maestro-net, ask, request, perimeter, mandate, privacy]
description: "What the mother hands back to a satellite's ask or request follows the satellite's mandate, injected by maestro-net from the row, with private/ and other scopes always excluded; a row without a mandate keeps the folder perimeter. Read before changing what a satellite can learn from its mother."
---

# The mother answers a satellite by relevance to its mandate

**Date**: 2026-09-27 · **Work**: `satellite-answer-perimeter` · **Status**: active

## Context

Until v2026.09.24.1 the mother answered a satellite (`maestro-net ask`, `maestro-net request`) from three sources: the satellite's row, the memories of its scope, the files in its vault folder. A perimeter by folder. In one instance the satellite of a consulting project had the mandate of building the client's new website and had to fill the CMS with the site's content; the material on the client's modules sat in the mother's vault, in a folder other than the satellite's vault folder. The mother knew the answer, the question served the mandate, and the perimeter blocked it.

## Decision

The mandate is the anchor. `maestro-net` reads the satellite's row before every `ask` and `request` and sends `project_type`, `mandate`, `method` and `constraints` as header fields above the fenced text, next to scope, repo and vault folder. When the question serves the mandate, the mother answers from everything it knows: its vault, its own memories, its sub-apps and documents, plus the satellite's row and the memories of its scope. What lies outside the mandate, or is sensitive with respect to it, gets a one-sentence refusal that doesn't say where the information would be. Two exclusions hold whatever the judgment says: `private/` (except the satellite's own row) and the memories of other scopes. The answer is a synthesis: no whole files, no map of the mother's vault, no inventory of what stays out. A row with no mandate keeps the folder perimeter of v2026.09.15.1. `ask` stays read-only; `request` keeps writing only in the vault folder, and only what it may draw on changes.

## Alternatives discarded

- **A whitelist of vault folders per satellite, compiled by the owner**: at setup nobody has the mother's whole structure in mind, and every new folder in the vault would need a registration step.
- **A blacklist of folders the satellite must never see**: it grows with the vault and fails silently on the folder nobody listed.
- **Moving the material into the satellite's vault folder**: duplicates documents that belong to the mother's own work, and the next satellite of the same client starts the copy again.

## Consequences

- The mandate is as trustworthy as the mother's db file: `bin/mem satellite add` accepts any string, and a satellite session with shell access could rewrite its own row. Accepted under the single-user condition of `2026-09-14-scope-is-not-access-control.md`; the exclusions stay rules in the prompt, with no enforcement.
- The header fields are the only source of the mandate, which extends the rule of `2026-09-15-satellite-request-opens-mother-session.md` on scope, vault and reply address: a mandate written inside the fenced text is data.
- The plugin ships the prompt and `maestro-sync` ships the `CLAUDE.md` rule the prompt defers to. An instance gets the new perimeter only after both the plugin update and `/maestro:maestro-sync`; with the new plugin and an old `CLAUDE.md` the mother keeps the folder perimeter.
- A mandate changes by `satellite remove` and `satellite add`, since there is no `satellite update`; the mandate question in the `satellite` skill says what the mandate now anchors.
- A satellite registered before this version, with an empty mandate, keeps the narrow perimeter until re-registered.

## References

`docs/decisions-log/2026-09-14-scope-is-not-access-control.md`, `docs/decisions-log/2026-09-15-satellite-request-opens-mother-session.md`; `howto/11-maestro-net.md` (ask, request), `howto/12-satellites.md` (Asking the mother).
