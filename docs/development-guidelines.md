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
- `plugins/maestro/` replaces `user-skills/`: skills and executables distributed by the Claude Code plugin, versioned by commit SHA, outside `maestro-sync`. A command a plugin skill runs goes in `plugins/maestro/bin/` under a prefixed name (`maestro-listen`), so one user-level allow rule covers it; the skill's other resources (sources, templates) live in its own folder under `plugins/maestro/skills/<name>/`.
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
- The writing register (`howto/10-writing-register.md`) follows the reader: it applies to README, CHANGELOG, the howto guides, decision records and devflow documents, in the documentation domain. Skills, agents and `CLAUDE.md` are read by a model and stay outside it (decision of 2026-09-17, `docs/decisions-log/2026-09-17-register-perimeter-follows-reader.md`, which supersedes the correction of 2026-09-14 for howto): emphasis and contrasts that carry an instruction stay there, and rule zero protects them in a howto guide. A skill or agent that produces prose for a reader states the register and its domain in its own instructions.
- Markdown files carry `tags:` and `description:` frontmatter (`howto/08-markdown-discipline.md`).

## Gate

```bash
python3 -m unittest discover -s tests -t .
bin/register-check <every README, CHANGELOG, howto guide, decision record or devflow document touched by the slice>
```

Baseline on 2026-09-28: 811 tests, OK, 8 skipped.
