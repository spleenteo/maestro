---
tags: [maestro, devflow, guidelines, tests, conventions, template]
description: "Rules plans and code follow in the Maestro template repo: tests, naming, placement, dependencies, commits and the gate. Read by devflow in every plan, review and execution."
---

# Development guidelines

Rules the plans and the code must follow. Devflow passes this file to every plan, review and execution. This repo is the origin of the Maestro template: it has no `private/`, and tests never touch a real instance.

## Tests

- `unittest`, stdlib only. One file per tool: `tests/test_<tool>.py`, with classes named by behaviour (`TestRecap`, `TestDayBoundary`).
- Scripts are tested as black boxes through `subprocess`, against a temporary db or directory created by the test. Never `private/`, never a real instance, never the network. External commands (`claude`, another instance's `bin/mem`) are replaced by recorder scripts that capture argv, cwd and environment.
- Tests that need optional machine dependencies (sqlite-vec, Ollama) skip themselves when missing.
- Before changing the `memories.db` schema or the behaviour of `bin/mem`, characterization tests on the current behaviour come first (decision of 2026-07-15, spring upgrade).
- One behaviour per test; no `sleep`.

## Naming

- Executables in `bin/` have no extension and start with `# origin: maestro` and `# maestro_version: vYYYY.MM.DD.N`. Executables in `plugins/maestro/bin/` carry neither marker: the plugin distributes them, not `maestro-sync`.
- Skill and agent directories are kebab-case. SQL tables and columns are snake_case.
- Exit codes that callers rely on are named constants and documented in the tool's `--help` and in its howto.

## Functions and modules

- CLIs use `argparse` subcommands, one `cmd_<verb>` function per subcommand returning the exit code.
- Every failure is explicit: a named exit code and a message on stderr. Optional layers degrade with exit code 3 and callers fall back silently.

## Code placement

- `bin/` executables distributed to instances. `.claude/skills/`, `.claude/agents/`, `CLAUDE.md`, `howto/` behaviour distributed to instances, marked `origin: maestro`.
- `plugins/maestro/` replaces `user-skills/`: skills and executables distributed by the Claude Code plugin, versioned by commit SHA, outside `maestro-sync`.
- `tests/` tests. `docs/` shaping and devflow material for the template itself, kept out of distribution.
- Every read or write on `memories.db` from a skill or an agent goes through `bin/mem`.

## Dependencies

- Python 3 stdlib for every distributed script. Heavier dependencies (sqlite-vec, Ollama, uv, yap) stay optional, run through `uv run --with`, and degrade gracefully.
- No Node, no packages to publish.

## Commits

- English, imperative mood, conventional prefix with scope: `feat(mem): …`, `docs(howto/12): …`, `test(mem): …`.
- A release commit is `vYYYY.MM.DD.N: <theme>`, and bumps `maestro_version` on the touched files plus the `CHANGELOG.md` entry.
- Explicit `git add` on touched files. Never `private/`, never `.claude/settings.local.json`, never a real `memories.db`.

## Prose

- Every file in the repo is in English.
- The writing register (`howto/10-writing-register.md`) applies to README, CHANGELOG and devflow documents. Skills, agents, `CLAUDE.md` and howto are specification files outside it (`howto/10-writing-register.md`, Perimeter): emphasis and contrasts that carry an instruction stay. A skill or agent that produces prose for a reader states the register in its own instructions. (Corrected on 2026-09-14: the first version put skills, agents and howto inside the register, and the V1 and V2 register passes on howto followed that error.)
- Markdown files carry `tags:` and `description:` frontmatter (`howto/08-markdown-discipline.md`).

## Gate

```bash
python3 -m unittest discover -s tests -t .
bin/register-check <every README, CHANGELOG or devflow document touched by the slice>
```

Baseline on 2026-09-13: 160 tests, OK, 5 skipped.
