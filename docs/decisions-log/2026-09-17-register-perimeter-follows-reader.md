---
work: register-domains
status: active
superseded_by: null
tags: [decision, writing-register, perimeter, howto, readme, specification-files]
description: "The writing register covers every text a person reads, howto guides and README included, wherever it lands; CLAUDE.md, SKILL.md and agent files stay outside and are written for the agent. Read before changing which files the register or its post-pass touches."
---

# The register's perimeter follows the reader

**Date**: 2026-09-17 · **Work**: `register-domains` · **Status**: active

## Context

v2026.08.14.1 put specification files (`CLAUDE.md`, skills, agents, howto guides) outside the register, and the development guidelines confirmed it on 2026-09-14, after register passes on howto guides had moved instructions. The domains work had to say which texts each domain covers, and the spike behind it proposed applying part of the register to files read by a model. The owner answered with a different cut: the cleanup goes wherever people read, and files for a model are written for the model.

## Decision

The register applies to every text a person reads, wherever it lands (vault, a repository, GitHub): vault documents and dossiers, logbook entries, shaping and devflow documents, decision records, `README`, `CHANGELOG`, external posts. The post-pass runs on them when they are written to a repository too. `CLAUDE.md`, `SKILL.md` and agent files stay outside and are written for the agent that reads them. `howto/` guides are read by the owner, by whoever installs Maestro and by the `guide` skill: they sit on the people side, and rule zero protects the contrasts and emphasis that carry an instruction. The template's existing `README` and `howto/` guides get one pass in the work, reviewed by the owner as a diff; the `CHANGELOG` history stays as written.

## Alternatives discarded

- **`howto/` outside the register, as before**: the guides are the first prose a person installing Maestro reads on GitHub.
- **Lexical tells and prohibitions 1, 2, 3 and 7 on files read by a model**: none of the spike's trials ran on such a file, and instructions are shaped for the model that executes them.
- **The whole register everywhere**: it would reopen the em dashes kept in `CLAUDE.md`, and rewriting instructions risks moving what they say.

## Consequences

- A pass on a howto guide can still move an instruction the `guide` skill relies on; rule zero and the owner's review of the diff are the guard.
- The Prose section of the development guidelines changes: its 2026-09-14 correction no longer holds for `howto/`.
- No writing guide exists for files read by a model; it stays out of this work.

## References

`docs/decisions-log/2026-09-17-maestro-sync-asks-register-keys.md`, `docs/decisions-log/2026-09-17-translate-template-skill.md`; the register-domains design work (kept outside the repository): shaping, decision D4.
