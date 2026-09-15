---
work: satellites-plugin
status: active
superseded_by: null
supersedes: "CHANGELOG v2026.08.26.2, Why: handoff dropped from maestro-net"
tags: [decision, maestro-net, satellites, request, background-session, permissions, channel-constraint]
description: "A satellite may open a background session in its mother with maestro-net request; it supersedes the rejection of handoff in v2026.08.26.2 for the satellite-to-mother direction only. Read before adding a verb that acts inside another instance."
---

# A satellite's request opens a session in its mother

**Date**: 2026-09-15 · **Work**: `satellites-plugin` · **Status**: active

## Context

In v2026.08.26.2 `handoff` was dropped from maestro-net: a verb that opens a session inside another instance was the reach the channel constraint exists to prevent, and a memory covered most of what it was for. Satellites changed the picture. A satellite borrows the mother's identity and memory but none of its skills, agents or vault write rules, so work such as a dossier in the linked vault folder can only be done by the mother. A memory can't do that work; `ask` is read-only by design.

## Decision

`maestro-net request` launches a visible background session (`claude --bg`) in the mother, only from a registered satellite and only towards its own mother. The request grants no permission: the mother reads the satellite's row, judges the request against its mandate and its own rules, acts with its own tools, and replies with one message plus one memory in the satellite's scope. The owner grants the verb per instance in `accepts`; `register` and `scan` never add it by default. The satellite can't choose the permission mode: the session starts in the mode configured for the mother's folder, with the vault folder added as a working directory. The satellite's text is fenced by lines carrying a random value, and the header fields are the only source of scope, vault and reply address.

## Alternatives discarded

- **Headless `claude -p` in the mother**: invisible to the owner, no way to attach, stop or answer a question, and a write-capable headless run is harder to trust than a row in agent view.
- **A result file instead of a memory for the fallback**: a new path convention the satellite would need to know; the memory already sits where the satellite reads.
- **A `--permission-mode` flag on the verb**: it would let the requesting session pick how freely the mother acts, a permission crossing the channel.
- **Requests between full instances**: out of scope. Full instances keep `recap` and `ask`; the constraint as written in v2026.08.26.2 still holds between them.

## Consequences

- The channel constraint now reads "memories, questions and a satellite's requests, never permissions" (`howto/11-maestro-net.md`).
- A request session can stall on a permission prompt when the mother's mode asks; the row shows it as blocked until the owner attaches.
- Whoever controls a satellite session can ask the mother for work; the mother's judgment against the row is the only filter. This holds while the owner is the only user of both, the same condition as `2026-09-14-scope-is-not-access-control.md`.

## References

`docs/decisions-log/2026-09-14-scope-is-not-access-control.md`, `docs/decisions-log/2026-09-14-satellite-leaves-no-repo-files.md`; `CHANGELOG.md` v2026.08.26.2; the satellites-plugin design work (kept outside the repository): spike S2 on background sessions and cross-session messaging.
