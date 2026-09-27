---
tags: [maestro, decisions, index, architecture, documentation]
description: "Index of the decision records of the Maestro template, one line each with the date and what the decision rules out. Read before changing memory, satellites, the plugin, the writing register or how instances receive updates."
---

# Decision records

One file per decision, in the shape `YYYY-MM-DD-<slug>.md`: context, the decision, the alternatives discarded, the consequences. A record is `active` until another one supersedes it (`superseded_by` in the frontmatter). Decisions taken before 2026-09-13 live in the entries of `CHANGELOG.md`.

| Date | Decision | Rules out |
|---|---|---|
| 2026-09-13 | [Satellite memory is a scope column in the mother's db](2026-09-13-scope-column-single-db.md) | One db per satellite; a db inside the project repo |
| 2026-09-13 | [`bin/mem` stays in each instance](2026-09-13-bin-mem-stays-in-instance.md) | Shipping `bin/mem` in the plugin; installing code into each repo |
| 2026-09-13 | [The plugin installs at user scope](2026-09-13-plugin-user-scope.md) | Project-scope installs declared in each repo |
| 2026-09-13 | [A satellite imports the mother's identity through a whitelisted extract](2026-09-13-identity-extract-whitelist.md) | Importing `preferences.md` whole; a model-generated extract |
| 2026-09-14 | [A satellite leaves no files in its repo](2026-09-14-satellite-leaves-no-repo-files.md) | Role files and settings written into the repo |
| 2026-09-14 | [Scope is not access control](2026-09-14-scope-is-not-access-control.md) | Treating the scope column as a permission boundary |
| 2026-09-15 | [`maestro-sync` moves into the plugin](2026-09-15-maestro-sync-in-plugin.md) | A local sync skill copied into each instance |
| 2026-09-15 | [A satellite may open a background session in its mother](2026-09-15-satellite-request-opens-mother-session.md) | Verbs that act inside another instance in any other direction |
| 2026-09-16 | [`listen` ships as the `maestro-listen` command](2026-09-16-maestro-listen-command.md) | Scripts called through `${CLAUDE_SKILL_DIR}`; a user-level skill symlinked into `~/.claude/skills` |
| 2026-09-17 | [`maestro-sync` asks for the writing register keys](2026-09-17-maestro-sync-asks-register-keys.md) | Leaving an existing instance without the keys |
| 2026-09-17 | [The register perimeter follows the reader](2026-09-17-register-perimeter-follows-reader.md) | Applying the register to files a model reads |
| 2026-09-17 | [`translate` is a template skill](2026-09-17-translate-template-skill.md) | A plugin skill; a section of `writing-register` |
| 2026-09-24 | [Task creation thresholds live in `CLAUDE.md` and in every channel skill](2026-09-24-task-creation-thresholds.md) | Thresholds that depend on the store |
| 2026-09-27 | [The mother answers a satellite by relevance to its mandate](2026-09-27-satellite-perimeter-by-mandate.md) | A fixed folder perimeter for a satellite with a mandate |
