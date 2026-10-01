# CHANGELOG

Versioned record of intentional changes to the Maestro template: patterns, skills, agents, conventions distributed to instances.

Versions follow the `vYYYY.MM.DD.N` scheme (date-based, incremental within the day). Each entry documents what changed, why it matters, and any migration note for instances syncing in.

The `maestro-sync` command of the Maestro plugin reads this file from the read-only mirror (`~/.maestro/`, refreshed at every `plan`) and shows the slice between an instance's oldest `maestro_version` and the mirror's top version before any file-level diff is applied.

## Versions at a glance

One line per version; the full entry below carries the reasons and the migration notes.

| Version | Theme |
|---|---|
| v2026.10.01.2 | A satellite session knows when to write a memory, and two plugin hooks remind it: a short closing message after some work, an hour of work with no memory in its scope |
| v2026.10.01.1 | The librarian searches by meaning first, tells archived from deprecated, renames with a link sweep and logs every write; the `archive` skill closes a vault folder; HR converges a custom agent onto the upstream one |
| v2026.09.29.1 | The sync opens with a numbered list of what's new, and asks about auto-update only when it is off |
| v2026.09.28.3 | `maestro-sync` asks for a plugin update only when the plugin changed, and runs the update itself |
| v2026.09.28.2 | `### Task creation thresholds` is a heading again in `CLAUDE.md`; a test catches references to missing headings |
| v2026.09.28.1 | The project review: `maestro-sync` becomes a command with backup sets and rollback, an update notice at session start, `CLAUDE.md` at a third of its size, the register rules in one place, English everywhere, the README as the guide, MIT license |
| v2026.09.27.1 | The mother answers a satellite's `ask` and `request` by relevance to its mandate, with `private/` and other scopes always excluded |
| v2026.09.24.1 | Task creation thresholds in `CLAUDE.md` and in every channel skill; the `steward` agent reviews the backlog weekly |
| v2026.09.17.1 | The writing register gains domains (communication, documentation, synthesis), tones, per-instance values and the `translate` skill |
| v2026.09.16.1 | `/listen` moves into the plugin as the `maestro-listen` command, usable from any session |
| v2026.09.15.1 | Satellites and the Maestro plugin: `new-instance`, `maestro-sync` and `maestro-net` ship as plugin skills; a project repo borrows an instance's identity and memory |
| v2026.09.10.1 | The `listen` skill: live capture of a call with `yap`, questions during the call, a note at close |
| v2026.09.05.1 | Idea versus task: undated work goes to the task manager, ideas carry `workbench` or `dormant` |
| v2026.08.26.2 | `maestro-net`: `recap` and `ask` between an owner's instances, with the machine registry |
| v2026.08.26.1 | The logbook reads the day's parallel sessions through `bin/session-digest` |
| v2026.08.14.1 | The writing register: seven prohibitions, the `writing-register` post-pass skill, `bin/register-check` |
| v2026.07.16.2 | The semantic layer extends to the markdown vault, chunked by section, with one fused recall |
| v2026.07.16.1 | Optional semantic layer over `memories.db`: `search --semantic`, `similar`, `dupes`, `embed` |
| v2026.07.15.2 | `CLAUDE.md` slimmed from 489 to about 260 lines; reference material moves to canonical sources |
| v2026.07.15.1 | `maestro-sync` delivers files created upstream after an instance was cloned |
| v2026.05.28.1 | The librarian gains tag parsimony and a symlink safety rail |
| v2026.05.23.2 | The warm task channel: an external task manager as the warm layer, `memories.db` as the cold one, a lazy garbage collector |
| v2026.05.23.1 | `bin/mem`, the CLI over `memories.db` |
| v2026.04.30.4 | The `tools:` frontmatter field may be customized per instance on distributed files |
| v2026.04.30.3 | The `maestro-sync` skill, the sync engine |
| v2026.04.30.2 | Three patterns promoted from a personal instance into the template |
| v2026.04.30.1 | Available apps moves from `CLAUDE.md` into `preferences.md`; the distribution rule |
| v2026.04.29.1 | Initial snapshot for changelog tracking |

---

## v2026.10.01.2 — 2026-10-01

**Theme**: satellites that remember what they did. A satellite session worked for hours, shipped several things that mattered, and left no memory in its scope. Its session-start context said how to write a memory but only pointed to the mother's `CLAUDE.md` for when, and a satellite never loads that file. A satellite need not be a git repo, so the reminders cannot hang on push or merge: they hang on time and on how the owner closes an exchange.

### Added

- **Two nudges in the plugin** (`plugins/maestro/hooks/hooks.json`, `satellite-hook`), active only in a satellite session:
  - `UserPromptSubmit`: a message of at most four words opening with a closing word ("ok", "perfetto", "grazie", "funziona", "thanks", "next"), after at least 10 minutes of work, adds one line asking whether the last exchange deserves a memory. At most once every 10 minutes of work.
  - `Stop`: after 60 minutes of work, the hook asks the mother's `bin/mem` for the highest row id in the scope. A new row resets the count; no new row blocks the end of the turn once, asking to save the outcome or to say why nothing needs saving. It never blocks twice in a row, and a failing `bin/mem` never blocks.
  - Work time counts each turn whole and the owner's pause before the next message only when it lasts 15 minutes or less, so a session left open overnight gains nothing. The count survives compaction; `/clear` starts a new one.
  - The hooks create the moment; what to save stays with the session.

### Changed

- **The satellite context says when to write**: the first paragraph of `### Writing to the log`, read from the mother's `CLAUDE.md` at every session start, the rule that a memory records an outcome and never every step, and examples for the project type (`development`, `ux`, `consulting`).
- **`vault-guard` becomes `satellite-guard`**, the one shell guard in front of the PreToolUse, UserPromptSubmit and Stop hooks: outside a satellite it exits without starting Python.
- **`howto/12-satellites.md`** describes the criterion and the two nudges.

### Migration

1. **Update the plugin**: `claude plugin update maestro@maestro` (automatic when the marketplace has auto-update on).
2. **Restart the open satellite sessions**: hooks load at startup, so `/clear` is not enough.
3. **Run `/maestro:maestro-sync`** in the instances for `howto/12-satellites.md`. Nothing else in an instance changes, and the mother's `CLAUDE.md` already carries the section the hook reads.

---

## v2026.10.01.1 — 2026-10-01

**Theme**: a librarian that finds notes by meaning and a way to close a project without losing why it ended. One instance had grown its own librarian to about 400 lines, with semantic recall, a `deprecated` convention, typo renames and an archive workflow tested on real folders. The sync never touched it because it carried no `origin: maestro` marker, so every upstream change had to be grafted by hand. The generic parts now ship upstream, and HR has a procedure to replace a custom agent with the upstream one.

### Added

- **The `archive` skill** (`.claude/skills/archive/SKILL.md`): closes a vault folder in ten steps. The librarian analyses the folder without writing; the orchestrator asks at most four questions, the first always "why are you archiving it?"; a closing document `00 Archived — <Name>.md` (`type: closure`, `archive_reason` in the owner's words) opens the folder; the folder moves with `mv` into one archive root, with `.canvas` paths and path-qualified wikilinks repaired; every note gets four archive fields and a reading callout; an Obsidian Bases index (`00 Archive index.base`) lists the archive and updates itself. A plain markdown folder gets a markdown index and a quoted line instead of the callout.
- **`howto/13-archive.md`**: the flow, the closing document, archived against deprecated, the vault without Obsidian.
- **Two optional keys in File territories**: `archive_path` (default `<vault_path>/_Archive`) and `off_limits`, the vault folders no agent reads or writes. `CLAUDE.md`, `preferences.example.md`, `howto/03` and `howto/09` describe them; `off_limits` folders belong in `.mem-ignore` too.
- **Convergence in HR** (`.claude/agents/hr.md`, `howto/02`): HR compares a custom agent with the upstream one, retires the custom file to `.claude/agents/.retired/`, installs the upstream file, keeps the alias and `hired_at`, and records `converged_from` and `converged_at` in the roster.

### Changed

- **The librarian** (`.claude/agents/librarian.md`, roster version 2.0.0):
  - Semantic recall first: `bin/mem search --semantic --only vault` frames the documents by meaning, then `rg` pinpoints exact terms; exit code 3 falls back to `rg` silently.
  - Two signals: `deprecated: "true"` (superseded or wrong) is hidden from searches unless asked and never linked; `status: archived` (a snapshot) is always searched, after the living notes, closing documents first. Setting `deprecated` needs the owner's yes.
  - The catalog mandate grows to `related:`, `date:` from the filename, YAML quoting, and trivial renames (typos, double extensions, generic basenames prefixed with their project) followed by a sweep of every wikilink to the old name. Other renames stay suggestions.
  - Every write and every suggestion is one JSON line in `private/librarian.log.jsonl`: timestamp, file, operation, before, after, reason.
  - Two archive tasks: `archive-analysis`, read-only, and `archive-fields`, which writes `status`, `archived`, `archived_from`, `archive_note` inside the archive flow only.
  - `off_limits` folders are excluded from `rg` and from semantic hits.

### Migration

1. **Run `/maestro:maestro-sync`**. `librarian.md`, `hr.md`, `CLAUDE.md`, `howto/02`, `howto/03`, `howto/09` and `howto/README` arrive as diffs; `.claude/skills/archive/SKILL.md` and `howto/13-archive.md` arrive as new files. The roster is instance data: update the `librarian` entry's `description` and `version` (2.0.0) from the template's `.claude/roster.yaml`, keeping your alias.
2. **An instance with its own archive skill** (a `.claude/skills/archive/SKILL.md` without the marker): the sync skips a path that already exists, so the upstream skill never arrives. Compare the two, move yours to `.claude/skills/.disabled/archive/`, and run the sync again. Folders you already archived stay valid when they carry `type: closure` and the four archive fields.
3. **An instance with a custom librarian** (`.claude/agents/librarian.md` without `origin: maestro`): ask the orchestrator to converge it. HR follows `## Convergence` in `hr.md`:
   - retires the custom file to `.claude/agents/.retired/librarian.md`;
   - installs the upstream file from the mirror (`maestro_mirror_path` in preferences, `~/.maestro` by default), extending only its `tools:` line if you use instance tools;
   - keeps the roster `alias` (your librarian's name) and `hired_at`, takes the upstream `description` and `version`, adds `converged_from: librarian` and `converged_at`;
   - renames the old intervention log to `private/librarian.log.jsonl` with its history (the schema is the same: `timestamp`, `file`, `operation`, `before`, `after`, `reason`);
   - lists the instance specifics for preferences: the vault path stays in `vault_path`, forbidden folders go to `off_limits`, a non-default archive root to `archive_path`, a legacy archive location to a line in `## Notes`.
   Then update the files of your own that named the old log or the old librarian rules (a vault skill, notes in preferences).
4. **Add the keys you need** to `private/preferences.md` → `## File territories`: `off_limits: [<folder>/, …]` and, only when the archive is not `<vault_path>/_Archive`, `archive_path`. Check that every `off_limits` folder is listed in `<vault_path>/.mem-ignore`, and that the archive root is not.
5. **Re-index**: `bin/mem embed` (with `MEM_VAULT_ROOTS` set to every root you index), so semantic recall covers what the librarian now searches first.

---

## v2026.09.29.1 — 2026-09-29

**Theme**: a sync that tells you what changed and stops asking what is already settled. After the auto-update guide landed in `howto/11`, every sync proposed turning auto-update on, even on machines where it already was.

### Added

- **What's new, first**: `/maestro:maestro-sync` opens with the two versions and a numbered list of the changes you will notice, drawn from the `CHANGELOG` slice, in plain words and in your language.
- **`maestro-sync autoupdate`**: sets `"autoUpdate": true` on the `maestro` marketplace in `~/.claude/settings.json` (or `$CLAUDE_CONFIG_DIR/settings.json`), keeping every other key.

### Changed

- **`maestro-sync plan`** reports `AUTOUPDATE on|off`, read from the user settings and from Claude Code's list of known marketplaces. The skill asks about auto-update only when it is off, once per sync, and runs `autoupdate` on a yes.

### Migration

1. **Update the plugin** (automatic with auto-update on; otherwise `claude plugin marketplace update maestro`, then `claude plugin update maestro@maestro`) and restart Claude Code.
2. **Run `/maestro:maestro-sync`**: `howto/05-backup-and-sync.md` and `howto/11-maestro-net.md` arrive as diffs.

---

## v2026.09.28.3 — 2026-09-28

**Theme**: fewer plugin updates, and no commands to copy. `maestro-sync plan` stopped with exit 5 whenever the installed plugin was older than the last commit on `main`, even when that commit touched only `CLAUDE.md` or the README. Every release sent every instance through an update and a restart it didn't need.

### Changed

- **The plugin check** (`plugins/maestro/bin/maestro-sync`) looks at the plugin's own files: an installed commit behind `main` passes when `main` changed nothing under `plugins/maestro/` and `.claude-plugin/`. A plugin that really is behind still stops the plan with exit 5.
- **The `maestro-sync` skill** offers the update on exit 5 and, on the owner's yes, runs it; then it asks for a restart of Claude Code and stops, as before.

### Added

- **`maestro-sync update-plugin`**: runs `claude plugin marketplace update maestro` then `claude plugin update maestro@maestro`, and exits 5 with the reason when either fails. Documented in `--help` and in `howto/05-backup-and-sync.md`.

### Fixed

- **`tests/test_claude_md_refs.py`** is `export-ignore` in `.gitattributes`: v2026.09.28.2 let it into the archive a new instance is built from, where it checks the template's own files.

### Migration

1. **Update the plugin** one last time by hand and restart Claude Code: `claude plugin marketplace update maestro`, then `claude plugin update maestro@maestro`. From this version on the sync offers to do it.
2. **Run `/maestro:maestro-sync`** in each instance: `howto/05-backup-and-sync.md` arrives as a diff.

---

## v2026.09.28.2 — 2026-09-28

**Theme**: a patch. The slimming of `CLAUDE.md` in v2026.09.28.1 turned `### Task creation thresholds` into a plain paragraph, while four files still sent their readers to that heading by name. An instance noticed it while onboarding the `steward`: HR could not find the section it was told to read.

### Fixed

- **`CLAUDE.md` → `## Memory`** has two subsections again: `### Task creation thresholds`, the heading that `steward.md`, `howto/04`, `howto/07` and `preferences.example.md` cite, and `### Writing to the log`, which holds the proactive triggers and the `bin/mem` rules so they don't fall under the thresholds. No rule changed.

### Added

- **`tests/test_claude_md_refs.py`**: every `` `CLAUDE.md` → `## …` `` reference in the tracked markdown files must name a heading that exists, and a `###` cited under a `##` must sit in that section. `CHANGELOG.md` and `docs/decisions-log/` are left out, because they record the headings of their own time.

### Migration

1. **Run `/maestro:maestro-sync`** in each instance and accept the `CLAUDE.md` diff. Nothing else changes.

---

## v2026.09.28.1 — 2026-09-28

**Theme**: the project review. A brutal read of the template as a whole, from an external, expert reader's seat, turned into four blocks of work: the plugin and the `bin/` tools cleaned up and put in English, the prompt layer slimmed and deduplicated, the README rewritten as the guide to Maestro, and then the two developments the review asked for: `maestro-sync` as a command with backup sets and a rollback, and an update notice at the start of an instance's session.

### Added

- **`maestro-sync`, the command** (`plugins/maestro/bin/maestro-sync`, with `maestro_versions.py`): `plan` refreshes the mirror, checks the plugin, scans the instance and the mirror and writes `private/maestro-sync.plan.json`; `apply` applies items by id or by kind after a backup set; `note` records the outcomes only the conversation decides; `rollback <stamp>` restores a set, its items in reverse order and the db last; `backups` lists the sets. Eleven exit codes, documented in `--help`. Backup sets live in `private/backups/<stamp>-sync/`, one per plan, with `manifest.json` written before the first write and rewritten after each item, a checked copy of `memories.db`, and every replaced or removed file under `files/`; the five newest sets stay, older ones go once past seven days, twenty at most. An `update` keeps the instance's `tools:` group (the one behaviour change against the bash skill); a file the owner edited by hand is recognised by history and never overwritten by an "apply all". `rollback` refuses a set that belongs to another instance.
- **The update notice** (`plugins/maestro/hooks/satellite-hook`, `.version` at the repo root): an instance whose `CLAUDE.md` is behind the template gets one line at session start, `Maestro v… is available (this instance is on v…): run /maestro:maestro-sync`. The hook reads a cache in `~/.claude/maestro-update-check.json` and, at most every 12 hours, spawns a detached fetch of `.version` from GitHub that never delays a session; `maestro-sync plan` and `apply` refresh the cache. Satellites and plain folders get nothing. Overrides: `MAESTRO_VERSION_URL`, `MAESTRO_UPDATE_CACHE`, `MAESTRO_UPDATE_INTERVAL`.
- **One command for a satellite**: `maestro-net satellite add --type …` writes the role into the mother and the entry into the registry, undoing the first when the second fails; `satellite remove` drops both.
- **`LICENSE`**: MIT.

### Changed

- **The `maestro-sync` skill** is 66 lines: a conversation over the command, one question per kind of item, a merge proposal for a locally modified file, the summary from the set's manifest. The 41 tests that extracted its bash blocks are gone; the command has its own black-box tests.
- **`maestro-net`** split into `maestro_registry.py` (parser, validation, atomic writes, line surgery) and `maestro_satellites.py` (satellite matching, the role in the mother); the session hook imports the two modules instead of executing the whole script. `recap` passes the title after `--`; a satellite scope must be a slug and is quoted before reaching `CLAUDE_ENV_FILE`. Registry writes are atomic.
- **`bin/` fixes**: `mem update --status done` stamps `completed_date` and any other status clears it, `--status` is validated, `marker set` needs a value; `vault_vec` gains a `root` column so two vault roots sharing a relative path don't collide, and the vault walk no longer follows symlinks; `session-digest` reuses `bin/mem`'s date parsing and the early-morning rule; `maestro-listen` stops orphan `yap` processes when its supervisor dies, notices a capture that exited, and builds `audiowatch` before the start budget.
- **English everywhere**: help texts, docstrings, comments and messages of `maestro-net`, `bin/mem`, `bin/mem-vec`, `bin/session-digest`, `bin/register-check`; `howto/09-memoria-semantica.md` becomes `howto/09-semantic-memory.md` (the old name is a retired path the sync proposes for removal); the registry header and the example commands in the guides.
- **`CLAUDE.md`** from 354 to 132 lines with no rule dropped: the satellite block is three lines (the request header carries the rules), the writing register keeps the seven prohibitions and the perimeter and points to the skill for domains and tones, the memory section loses its rationale and the flags `bin/mem --help` already carries. The register rules live in one place, `.claude/skills/writing-register/SKILL.md`; agents and skills declare their domain and tone in one paragraph.
- **Drift fixed**: `Task` tool → `Agent`; `installed_at` → `hired_at`; HR rewritten on the roster as shipped; `guide` indexes all twelve howto guides; the retired local `maestro-sync` skill removed from the template; the pointer skill path in `preferences.example.md`; `add-external-app`'s rollback and section references; "matrix" wording; the steward's roster description; chezmoi steps and implementation notes dropped from `howto/11`.
- **README** rewritten as an overview for GitHub readers: one instance per context, the three layers of long-term memory, sub-apps versus satellites with examples and a table, preferences, install, sync, what's included, requirements, a table of contents. The CHANGELOG opens with a one-line-per-version table; `docs/decisions-log/` has an index; `docs/development-guidelines.md` names the new gate baseline and the `.version` bump in a release commit.

### Why

Three reviewers (prompt layer, code, documentation) found the same rule written in up to seven files, names the runtime no longer had, four verified bugs, and a sync procedure of 658 lines of bash run by the model with loose backups in `private/`. The owner approved every theme. The sync moved into a command because the mechanics were hiding in quoting and `pipefail`, and because a set with a manifest is the only backup an owner can roll back without reading a skill. The update notice exists because seven instances drifted for weeks without anyone knowing.

- **Work**: `sync-script` (the review itself ran outside devflow, as a conversation)
- **Decision**: [`maestro-sync` is a command; the skill is the conversation over it](docs/decisions-log/2026-09-28-maestro-sync-as-a-command.md)

### Migration

1. **Update the plugin** and restart Claude Code: `claude plugin marketplace update maestro`, then `claude plugin update maestro@maestro`. The new `maestro-sync` skill and command, the split `maestro-net` and the update notice arrive with it.
2. **Run `/maestro:maestro-sync`** in each instance: `CLAUDE.md`, the agents, the skills and the guides arrive as diffs, `howto/09-semantic-memory.md` as a new file and `howto/09-memoria-semantica.md` as a retired path; say yes to the `bin/` copy (the db is backed up into the set first; `vault_vec` gains its `root` column and the vault re-embeds once). The first sync creates `private/backups/`; the loose `private/*.bak.*` files of earlier syncs stay as they are.
3. **Satellites**: nothing to do; the registry format is unchanged.

---

## v2026.09.27.1 — 2026-09-27

**Theme**: the mother answers a satellite by relevance to its mandate. `maestro-net ask` and `maestro-net request` used to bind the mother's answer to three sources, the satellite's row, the memories of its scope and the files in its vault folder: a perimeter by folder, which blocked a question the mandate called for whenever the material sat elsewhere in the mother's vault. The mandate now travels in the prompt and anchors the mother's judgment.

### Changed

- **Perimeter by mandate** (`plugins/maestro/bin/maestro-net`, `CLAUDE.md` → `## Requests from satellites`): when the question serves the satellite's mandate, the mother answers from everything it knows, its vault, its own memories, its sub-apps and documents, plus the satellite's row and the memories of its scope, as a synthesis in the service of the question: no whole files, no map of the vault, no inventory of what stays out. What lies outside the mandate, or is sensitive with respect to it, gets a one-sentence refusal that doesn't say where the information would be. Two exclusions hold whatever the judgment says: `private/` (except the satellite's own row) and the memories of other scopes. `ask` stays read-only; `request` keeps writing only in the vault folder, and only what it may draw on changes.
- **The script injects the role** (`maestro-net`): both prompts carry `project_type`, `mandate`, `method` and `constraints` as header fields after `vault_folder`, read from the satellite's row in the mother's db (`none` when empty, newlines collapsed to one line). The sentence that names the header-only fields lists them, so a mandate written inside the fenced text stays data. The satellite never declares its own mandate.
- **A row without a mandate keeps the folder perimeter**: with `mandate: none` the prompt carries the text of v2026.09.15.1 (row, memories of its scope, files in the vault folder, nothing named beyond them) and a request is judged against the row.
- **Docs and the satellite side**: `howto/11` (ask, request), `howto/12` (Asking the mother; the `satellite update` line, since re-registering is how a mandate changes), the `maestro-net` skill (a refusal is passed on as it is, the question is never rephrased to get around it), the `satellite` skill (the mandate question says what the mandate anchors), and the line the session hook injects into a satellite, which branches on the mandate too.
- **Tests**: the fake `bin/mem` of `tests/test_maestro_net.py` emits its row through python, so role fields may hold newlines and quotes; nine new or retargeted cases on the header, the two boundary texts, null and empty columns; two hook cases in `tests/test_satellite_hook.py`.

### Why

An instance for a consulting engagement had a satellite with the mandate of building the client's new website, which had to fill the CMS with the site's content. The material on the client's modules sat in the mother's vault, in a folder other than the satellite's, and the perimeter by folder refused a question the mother could answer. A whitelist or a blacklist of folders compiled by the owner was discarded: at setup nobody has the mother's whole structure in mind, and a blacklist grows long and fails on the folder nobody listed. The mandate is the anchor the decision of 2026-09-15 already assumed when it made the mother's judgment against the row the only filter; the prompt now supplies it.

- **Work**: `satellite-answer-perimeter`
- **Decision**: [the mother answers a satellite by relevance to its mandate](docs/decisions-log/2026-09-27-satellite-perimeter-by-mandate.md)

### Migration

1. **Update the plugin** and restart Claude Code: `claude plugin marketplace update maestro`, then `claude plugin update maestro@maestro`.
2. **Run `/maestro:maestro-sync`** in each mother of satellites: `CLAUDE.md`, `howto/11` and `howto/12` arrive as diffs. The prompt defers to the mother's `CLAUDE.md`, so a mother with the new plugin and the old `CLAUDE.md` keeps the folder perimeter until it syncs.
3. **A satellite registered without a mandate** keeps the folder perimeter: `bin/mem satellite remove` and `add` with `--mandate` to give it one.

---

## v2026.09.24.1 — 2026-09-24

**Theme**: fewer, truer tasks. The rules that decide whether a task is created now sit in `CLAUDE.md` and in every channel skill, whatever store holds the tasks. A steward agent reviews the backlog against them each week.

### Added

- **Task creation thresholds** (`CLAUDE.md` → `## Memory` → `### Task creation thresholds`): a task is created on a direct request, a date by which the action has to happen, or evident urgency (legal deadline, money consequence, a third party waiting). With none of the three it stays an idea, or the orchestrator asks once. A step toward an outcome already tracked goes into that task's notes; search before creating; neutral priority by default; no numeric cap per area. The rules decide admission and leave the store's field defaults alone.
- **`## Creation` section in the channel skill contract** (`howto/07-warm-task-channel.md`): each `<channel>-task-manager` skill maps the thresholds onto its channel (where a step goes, the read call that finds related tasks, the neutral priority value) and adds no rule of its own. New anti-pattern: micro-step flood.
- **`steward` agent** (`.claude/agents/steward.md`, alias Della, enrolled in `.claude/roster.yaml`): a weekly review, never on Monday, of the open task rows in `memories.db` and the live tasks on the warm channel. Four passes (lapsed rows, groups for a parent idea, true duplicates versus recurring occurrences, routing), a synthesis report and a JSON block of operations the orchestrator applies after the owner's yes. It reads the log through `bin/mem`, reads the channel through its skill, and writes nothing. The instance adds the channel's read tools to its `tools:` field.
- **Optional override** in `preferences.example.md`: `## Warm task channel` → `### Task creation thresholds`, which wins over `CLAUDE.md` where it differs.

### Changed

- **The proactive trigger for things to do** (`CLAUDE.md` → `### Proactive triggers`) applies the thresholds, then creates the task through the warm channel's skill when preferences declare one, in `memories.db` otherwise. It used to write `task` rows in `memories.db` unconditionally, even with a warm channel declared.
- `howto/04`, `README.md`, `.claude/agents/data/README.md` and the `maestro-sync` skill's list of distributed agents follow.

### Why

In one instance the unconditional trigger wrote 161 task rows next to its warm channel between April and September 2026, 45 of them still open. In a second instance the trigger already went to the warm channel, and creations still climbed from 7 a month to 31 in three months, with 22 of 46 closed tasks closed within three days. Routing fixes the first case; the thresholds, written where tasks are created, address the second.

- **Work**: `task-creation-thresholds`
- **Decision**: [task creation thresholds live in `CLAUDE.md` and in the channel skill](docs/decisions-log/2026-09-24-task-creation-thresholds.md)

### Migration

1. **Run `/maestro:maestro-sync`** in each instance: `CLAUDE.md`, `howto/04`, `howto/07` and the roster arrive as diffs, `steward.md` as a new file.
2. **Add a `## Creation` section** to the instance's channel skill, following the table in `howto/07`.
3. **Thresholds already written in preferences** can stay as the override block, or go if they repeat `CLAUDE.md`.
4. **Add the channel's read tools** to `steward`'s `tools:` field, then run a first pass by hand.

---

## v2026.09.17.1 — 2026-09-17

**Theme**: the writing register learns what kind of text it is shaping. One set of prohibitions had been binding an email to a partner and a daily recap alike, so the email lost its greeting and its sign-off. The register now names three domains (communication, documentation, synthesis), each with a default tone the owner sets once, and the same rules translate a draft.

### Added

- **Rule zero and three domains** (`CLAUDE.md` → `## Writing register`, 26 lines): a list match is a candidate and only a confirmed defect in context gets corrected; a claim is never added and a figure, date, name, URL or placeholder never dropped; stripping the warmth from a message to a person is a defect. Communication (emails, messages, quick translations: an opening line to the person, one topic per paragraph, a close on a concrete next step, the instance sign-off, no markdown in an email body), documentation (vault documents, README, howto guides, decision records, technical notes: subject first, no recap coda, evaluations anchored to a fact) and synthesis (reports, recaps, status lines, task titles: one line per fact, past participle first in Italian, past-tense verb first in English, always neutral). Four tones: friendly, professional, formal, neutral; the request overrides the default. Prohibition 3 keeps a factual contrast between two real alternatives ("Use the CMA, not the CDA").
- **`writing-register` skill for two moments** (`.claude/skills/writing-register/SKILL.md`): loaded before drafting an email, a message, a post or a document, it carries the full rules, a catalog of lexical tells, calques from the source language, rhythm checks by eye, the domains, the tones and the preference keys with their defaults; at delivery it runs as the post-pass, aware of the domain, with rule zero inside the fidelity guard. In a satellite it reads the values from the session block the hook injects.
- **`## Writing register` block in preferences**, one fenced `yaml` block with every key optional: `suspended`, `post_pass`, `tone_default` per domain, `voice`, `communication.sign_off`, `translation.*`, `avoid_words`. Where it overlaps `## Communication preferences` ("Tone with others", "Things to avoid"), the block wins. `preferences.example.md` documents it commented.
- **`translate` skill** (`.claude/skills/translate/SKILL.md`, optional): two labeled versions of a draft the owner wrote, the first keeping the source's form, the second what a native speaker would write with the same voice and facts; a fresh translation when the draft opens with the owner's marker; `Revised` for a draft already in the target language; one `Note:` line for a doubt about the source. It runs only where `translation.enabled` is true and hands any other request back to chat; interface strings and code are never its business. The sign-off closes the versions only when the owner set one.
- **`maestro-register-keys`** (`plugins/maestro/bin/`): renders, reports and writes the preferences block. `write` appends the missing keys inside the existing block and leaves every other line of the section as it was, converts the old two-line block to the fenced shape, backs the file up next to itself first, and refuses a tone outside the four before writing anything. Both `/maestro:new-instance` and `/maestro:maestro-sync` use it, so the two cannot drift.
- **Six optional questions at setup** (`/maestro:new-instance`, after Question 10): tone of emails, tone of documents, voice, sign-off, translation (only when the destination has the `translate` skill), words to avoid; `skip` writes every default with a `# default` comment.
- **Phase 6c of `/maestro:maestro-sync`**: reads an existing instance's block, asks once for the keys it lacks (the owner's `## Communication preferences` lines suggest the answers) and writes them on the owner's yes, after a backup. A skipped question writes its default, so the next sync asks nothing.
- **Tests**: `tests/test_maestro_register_keys.py` (22), Phase 6c blocks in `tests/test_maestro_sync.py`, the register block in `tests/test_finalize.py`, the hook pointers in `tests/test_satellite_hook.py`, 21 new cases in `tests/test_register_check.py`.

### Changed

- **The perimeter follows the reader.** The register covers every text a person reads, wherever it lands: vault documents, logbook, external posts, and in a repository `README`, `CHANGELOG`, the howto guides, decision records, shaping and devflow documents. `CLAUDE.md`, skill and agent files are written for the agent that reads them and stay outside. Chat replies to the owner follow the prohibitions and `## Tone` with no domain; a text for someone else drafted in chat takes its domain. The post-pass extends to `README`, `CHANGELOG` entries, howto guides and decision records written to a repository; devflow work documents keep `bin/register-check` as their gate.
- **One pass over `README.md` and the howto guides** under the new rules: 88 em dashes used as pauses, 30 bold emphases and seven framing sentences went; instructions, commands, paths and tables stayed. `howto/01` to `07` and `howto/README.md` now carry `origin: maestro`, so the pass reaches instances through sync, and `howto/*.md` joins the sync's scan list. The index moves the guide numbers into their own column.
- **Prose producers declare their domain**: `logbook` (documentation, with its first-person narrative as the genre's override of the neutral tone), `scheduler` (synthesis), `librarian` (synthesis for reports, documentation for descriptions and bodies, the tone passed by the orchestrator in the task), the plugin's `listen` note and the day-zero notes of `new-instance` (documentation).
- **Satellites**: the session hook points at the mother's `writing-register` skill when it exists, at the mother's `translate` when the extract enables translation, and always writes the quoted `register-check` path. The identity extract keeps the fenced block intact; a bare sign-off line such as `--` would have closed the section, which is why the block is fenced.
- **`howto/10-writing-register.md`** rewritten: rule zero, the domains and tones with bilingual examples, the catalog, the per-instance values and the questions setup and sync ask, coexistence with `humanizer` and `unslop`. `howto/12`, `README.md`, `howto/README.md`, the `guide` skill's index and the development guidelines follow.

### Fixed

- **`bin/register-check` reported two-item phrases as triads** (`For any question, reply here or grab a slot`). Without the Oxford comma a run of three is now reported only when its items are parallel: same length as the middle item, no function word (`the`, `with`, `its`, `no`; `il`, `con`, `senza`), the first item not closing a prepositional phrase. Headings skip rule 6 as they skip rule 4. Given up on purpose: a no-Oxford triad whose last item opens with a preposition, and one whose items carry an article; both stay a reader's call.
- **Quoted examples raised findings**: balanced double quotes (straight, curly, guillemets) are masked like inline code. Single quotes stay, they are apostrophes; a straight quote after a digit is an inch mark and never opens or closes a quotation.

### Why

The owner writes three kinds of text that need different shapes, and kept a second rule set for translations that contradicted the register in places. A spike in one instance on five real texts (a recap, a call note, a follow-up email, two translations) settled the model; the second translated version converged with the email the owner had sent by hand. The perimeter was redrawn by who reads the text: the cleanup goes wherever a person reads, including the guides a newcomer meets on GitHub, and files for a model are written for the model. `translate` lives in the template because a plugin skill would be listed in every session on the machine, code repositories included; satellites reach it through the hook. The sync writes the owner's preferences for the first time, only the missing keys and after a backup, because an existing instance is never asked otherwise.

- **Work**: `register-domains`
- **Decision**: [the register's perimeter follows the reader](docs/decisions-log/2026-09-17-register-perimeter-follows-reader.md), [maestro-sync asks for missing register keys](docs/decisions-log/2026-09-17-maestro-sync-asks-register-keys.md), [translate is a template skill](docs/decisions-log/2026-09-17-translate-template-skill.md)

### Migration

1. **Update the plugin** and restart Claude Code: `claude plugin marketplace update maestro`, then `claude plugin update maestro@maestro`. Until an instance syncs, the updated hook points its satellites at the mother's old `writing-register`, which is post-pass only.
2. **Run `/maestro:maestro-sync`** in each instance: `CLAUDE.md`, the skills, the agents and the howto guides arrive as diffs, `translate` and the newly marked guides through the reverse scan (a declined `translate` is offered again at every sync), `bin/register-check` through the `bin/` copy of Phase 5b. Phase 6c then asks the six register questions once and writes the block after a backup; a bare `suspended`/`post_pass` block is converted with its values kept.
3. **Nothing changes for an owner who skips every question**: professional emails, neutral documents and recaps, no sign-off, translation off.

---

## v2026.09.16.1 — 2026-09-16

**Theme**: `/listen` in every session. Live capture of a call moves from the instance template into the Maestro plugin, so it works in an instance, in a satellite repo and in any other folder, and files the note where that context keeps documents.

### Added

- **`/maestro:listen`** (`plugins/maestro/skills/listen/`): the skill, now in the plugin. It works out whether the session is an instance, a satellite or a plain folder, and from that picks the language, the labels, the folder it proposes for the note and the transcript, where the memory of the call goes and which register pass the note gets. The owner still confirms the destination before anything is written. A bare `/listen` reaches it wherever no local skill holds the name.
- **`maestro-listen`** (`plugins/maestro/bin/`): the capture command, formerly `bin/listen`, with `updates <minutes>` in place of `bin/listen-updates`. One stable name on the `PATH`, so one allow rule, `Bash(maestro-listen *)`, covers every call the skill makes during a call. Every call passes the session's project folder, so a `cd` between questions never loses the capture.

### Changed

- **A capture belongs to its folder**: the lock stays machine-wide, but from another folder `maestro-listen` reports only who holds it and since when. Title, context and transcript stay with the folder that started it, and so do `text`, `stop` and `updates`. The boundary keeps sessions of one user from stepping on each other's calls; it is no access control.
- **The satellite hook** tells a satellite session that the plugin's skills run there, next to the `maestro-net request` line for the mother's own skills.
- **`/maestro:maestro-sync` Phase 6b** retires the old copy as one `listen` unit (`.claude/skills/listen/`, `bin/listen`, `bin/listen-updates`, `bin/audiowatch.swift`) with a single answer. It removes only the members that carry `origin: maestro`, copies them to `private/retired.bak.<stamp>-listen/` first, keeps the whole unit when the local skill has no marker, and postpones while a capture or an old updates monitor is running.
- **Docs**: `README.md`, `howto/12-satellites.md`, the optional dependencies table of `/maestro:new-instance` and the plugin descriptions name the skill in its new home.

### Fixed

- **Closing a capture**: `stop` deleted the state before the close read the whole transcript, so `text --raw` failed at every close since v2026.09.10.1. The closed capture now stays readable from its folder, with every segment at its offset.
- **Stopping after a change of audio input**: a segment rotation could write the placeholder pid 0 back into the state, and `stop` would then signal the caller's own process group. A pid at or below 0 reads as dead, and the supervisor records its own pid.

### Removed

- **The template copy of listen**: `.claude/skills/listen/`, `bin/listen`, `bin/listen-updates` and `bin/audiowatch.swift` now live in the plugin.

### Why

A satellite session told the owner that `/listen` runs only from the mother. A satellite has no `.claude/`, receives skills only from the plugin, and its hook sent the mother's skills through `maestro-net request`. The capture never depended on the instance, and a call happens wherever the owner is working. The command's shape came from permissions: a skill's `allowed-tools` grant lasts the turn that invokes it, every question asked during a call is a later turn, and a path inside the plugin cache changes with every update. A prefixed command on the `PATH` is the one form an owner can allow once; a bare `listen` is shadowed on machines where a Ruby gem installs its own.

- **Work**: `listen-plugin`
- **Decision**: [listen ships as the maestro-listen command](docs/decisions-log/2026-09-16-maestro-listen-command.md), [maestro-sync in the plugin](docs/decisions-log/2026-09-15-maestro-sync-in-plugin.md) (amended for the `listen` unit)

### Migration

1. **Update the plugin** and restart Claude Code: `claude plugin marketplace update maestro`, then `claude plugin update maestro@maestro`. `/maestro:maestro-sync` refuses to run with a plugin behind `main`.
2. **Allow the command once**: add `Bash(maestro-listen *)` to `permissions.allow` in `~/.claude/settings.json`. Allow rules saved for `bin/listen` no longer match anything.
3. **Run `/maestro:maestro-sync`** in each instance and say yes to the `listen` unit. Until then a bare `/listen` there runs the local copy, while `/maestro:listen` reaches the new one; both share `~/.local/state/listen/`, so a capture opened by either is seen by the other.
4. **Satellites** need only step 1.

---

## v2026.09.15.1 — 2026-09-15

**Theme**: **satellites and the Maestro plugin**. A project repository can now work as a context of an instance you already have, its mother: same identity, same memory (under its own scope), a linked vault folder, and no files added to the repo. Everything that has to be the same for every instance on the machine moves into one Claude Code plugin: creating an instance, the channel between instances, satellites, and the template sync itself.

### Added

- **The `maestro` Claude Code plugin** (`plugins/maestro/`, marketplace in `.claude-plugin/`), installed once at user scope: `claude plugin marketplace add spleenteo/maestro`, `claude plugin install maestro@maestro`. It carries `/maestro:new-instance`, `/maestro:maestro-sync`, `maestro-net`, the `satellite` skill and the session hooks.
- **Scoped memory** — `log` gains a `scope` column through `bin/mem_schema.py` (`SCHEMA_API` 2), added by `bin/mem` and `bin/mem-vec` the first time they open an older db. A satellite session (`MEM_SCOPE=<slug>`) reads and writes only its scope; the mother reads its own rows by default and a satellite's with `--scope` or `--all-scopes`. `todo` and `overdue` list every scope in the mother.
- **`bin/mem satellite add|list|show|remove`** — the mother's registry of the repos it lends its memory to: project type, mandate, method, constraints, language, vault folder.
- **`/maestro:new-instance`** — creates an instance in a new folder from the template at the plugin's commit (`git archive`, with `.gitattributes` keeping template-only material out), runs the first-launch interview, finalizes and registers it. Replaces the `setup` skill.
- **Satellites** — the `satellite` skill registers a repo (role in the mother, repo in `~/.claude/maestro-instances.yaml`), checks the chain and hands off. The plugin's `SessionStart` hook recognises the repo in every new session, exports `MEM_SCOPE`, and injects the role, the mother's identity sections and the memory rules; a `PreToolUse` hook opens the vault folder to the file tools. See `howto/12-satellites.md`.
- **`maestro-net request`** — from a satellite, opens a visible background session in the mother (`claude --bg`), which judges the request against the satellite's row, works with its own tools, replies with a message and saves one memory in the satellite's scope. Granted per instance in `accepts`, never by default.
- **`## Requests from satellites` in `CLAUDE.md`** — how a mother serves a request or a question from a satellite, and the boundary of what it hands back.

### Changed

- **`maestro-net`** moves from `user-skills/` into the plugin, gains `register`, `unregister` and `satellite add|remove`, and from a satellite `ask` reaches only the mother, within the satellite's boundary.
- **`/maestro:maestro-sync`** — the sync moves into the plugin. It runs only in an instance root, stops when the loaded plugin is stale or behind upstream `main`, offers to copy a drifted `bin/` after backing up the db and the replaced scripts, and proposes the removal of retired paths. The old local skill at `.claude/skills/maestro-sync/` becomes a redirect.
- **Skills and agents read `log` through `bin/mem` only** (`logbook`, `scheduler`, `add-external-app`, `guide`): the logbook reads every scope and writes a Satellites section.
- **`CLAUDE.md`** — scope rules, satellite commands, session start points to `/maestro:new-instance` and recognises the template repository; `howto/` 08 to 12 updated, `howto/README.md` lists them.

### Removed

- **`.claude/skills/setup/`** (now `/maestro:new-instance`) and **`user-skills/`** (now in the plugin).

### Why

A project repo needed the orchestrator already running the owner's context, and the only way was a copy of the instance inside the repo: two memories drifting apart and files a team doesn't want. A scope column in one db keeps a single memory with per-context views; a plugin hook gives a repo its context without writing into it. The same pressure moved the shared skills into the plugin: a skill copied into every instance is as old as the instance, and a sync that can't know what changed after it can't protect the release that changes it.

- **Work**: `satellites-plugin`
- **Decision**: [scope column in a single db](docs/decisions-log/2026-09-13-scope-column-single-db.md), [bin/mem stays in each instance](docs/decisions-log/2026-09-13-bin-mem-stays-in-instance.md), [plugin at user scope](docs/decisions-log/2026-09-13-plugin-user-scope.md), [identity extract whitelist](docs/decisions-log/2026-09-13-identity-extract-whitelist.md), [satellite leaves no repo files](docs/decisions-log/2026-09-14-satellite-leaves-no-repo-files.md), [scope is not access control](docs/decisions-log/2026-09-14-scope-is-not-access-control.md), [satellite request opens a mother session](docs/decisions-log/2026-09-15-satellite-request-opens-mother-session.md), [maestro-sync in the plugin](docs/decisions-log/2026-09-15-maestro-sync-in-plugin.md)

### Migration

1. **Install the plugin** at user scope (commands above) and restart Claude Code. If `maestro-net` was installed by hand under `~/.claude/skills/maestro-net`, remove that copy.
2. **Start the first sync as `/maestro:maestro-sync`**, typed exactly. `/maestro-sync` or "sync maestro" still reach the old local skill until the redirect lands, and that copy has none of the new checks.
3. **Say yes to the `bin/` copy** when the sync offers it: the new skills call `bin/mem` options an older copy lacks, and the copy runs the `scope` migration right after a checked backup.
4. **Remove the retired paths** the sync proposes: `.claude/skills/maestro-sync/`, `.claude/skills/setup/`, `.claude/skills/.disabled/setup/`, `user-skills/maestro-net/`.
5. **`.claude/agents/data/channels.yaml`** isn't distributed: if the instance's copy still queries `memories.db` with raw `sqlite3`, rewrite those queries with `bin/mem` as in the template.
6. A **mother** of satellites needs `SCHEMA_API` 2 (step 3) before any satellite session; `request` is granted by adding it to the mother's `accepts` in the registry.

---

## v2026.09.10.1 — 2026-09-10

**Theme**: the orchestrator learns to **listen to a call while it is happening**. Meeting tools transcribe and hand back a summary once everyone has hung up, which is the moment the transcript stops being useful for the conversation itself. The `listen` skill keeps a transcript growing on disk, so the owner can ask what was already said, what a name was, whether a topic from their own list has come up yet, while they are still in a position to act on the answer. Everything runs on the machine: nothing is uploaded, and no bot joins the call.

### Added

- **`.claude/skills/listen/SKILL.md`** — the skill. Opens a capture, works out what the call is from calendar, memory and vault instead of asking, answers in two or three lines while the owner is talking, and on close proposes where to file a note plus the transcript. Automatic updates exist but stay off until asked for during the call, and they are worth sending only when they name something the owner can still act on: a topic untouched, a number mentioned once, a contradiction with what was said earlier.
- **`bin/listen`** — the capture. A machine-wide lock, so a second `/listen` from another instance is refused with the details of the one already running. A capture is a **sequence of segments**, each one a `yap` run with its own file and a known offset, merged back into one timeline on read.
- **`bin/audiowatch.swift`** — a CoreAudio listener on the default input device, built on first use. It notifies by callback, so it costs nothing while idle.
- **`bin/listen-updates`** — the monitor behind the automatic updates. Emits one line per block of new speech and exits on its own when the capture stops.
- **`## Optional machine dependencies` in the `setup` skill** — a check for the tools an optional skill needs (`yap`, macOS 26, `swiftc`), reporting what is missing and the command that installs it. It installs nothing and never blocks the setup.

### Why

Two failures found on the first real call, both silent, both fixed here.

`yap` binds to the input device it finds at launch. Plugging in headphones mid-call switches the system default, `yap` stays on the old device, and the microphone channel dies with no error: ten minutes of the owner's own voice vanished from a transcript that looked healthy. The segment model exists for this. When the input device changes, the supervisor closes the segment, opens a new one on the new device, and records the offset; the owner sees continuous timestamps and one transcript.

The second is acoustic. Without headphones the far side's voice leaves the speakers and re-enters the microphone, so the same words land on both channels and half the lines end up attributed to the wrong person. Meet and Zoom cancel this because they know the signal they are playing; a tool that opens the microphone from outside receives it already mixed. `bin/listen` drops what it can with two rules tuned on a real call, and the attribution is settled by reading the raw two-channel transcript at close, where judgment beats a similarity ratio: the two channels segment the same words differently, so one channel's cue is often a fragment of the other's, which no comparison can pair.

### Migration

Nothing breaks and nothing is required. Instances that sync in get the skill, and it stops with a clear message when `yap` is missing rather than improvising a fallback. `swiftc` is the only soft dependency: without it captures still run, with a single segment and no rotation, and `status` says `rotation: off`.

Two things to tell the owner rather than let them assume. macOS shows no persistent indicator for system-audio capture, and the microphone dot only appears when the microphone is part of the capture, so telling the other party is on them. And each segment boundary drops a second or two, the time of the restart.

---

## v2026.09.05.1 — 2026-09-05

**Theme**: `memories.db` learns to tell an **idea** from a **task**, and to stop hoarding. The two types have always been in the schema, but nothing said where the line falls, so undated work piled up as open ideas: things already decided, waiting only for a free afternoon, sitting in the one place the owner never looks while planning. The rule that closes the gap came from an instance owner during a backlog triage that took 56 open ideas down to 20.

### Added

- **`### Idea or task` in the Memory section of `CLAUDE.md`** — the criterion (an idea still holds an open question, a task holds only its execution), the corollary (a task with no date is still a task, and lives in the owner's task manager, not in `memories.db`), the conversion procedure (create the task, mark the idea `dismissed`, write the new id into the description so the trail survives), and the periodic review, where every surviving idea carries either the decision it waits for or the condition that wakes it up.

### Changed

- **`### Rules`** gains two lines: the `idea-<id>` convention that links a task to the idea that generated it, so an initiative can be read from either end; and the three-month check on open ideas, which either carry a live question or have already become a task elsewhere.

### Why

An idea backlog that grows without pruning stops being a backlog and becomes an archive: the owner scrolls past the same fifty rows and reads none of them. The decided work is the part that pollutes the most, because it looks like thinking while it's really just waiting. Sending it to the task manager empties the list of everything that has no question left in it, and what remains is short enough to be read in one pass.

### Migration

Nothing breaks: the schema is unchanged and existing rows stay valid. On the first sync, instances should run one pass over their open ideas and split them, moving anything already decided into their own task manager (with a reference back to the source id), and tagging what stays with its pending decision or its wake-up condition. Instances with no external task manager keep those rows as `task` with `status: todo` and no `due_date`.

---

## v2026.08.26.2 — 2026-08-26

**Theme**: **maestro-net**, the cross-talk channel between an owner's Maestro instances. An owner living in several contexts runs several instances, each with its own memory and its own domain, and the separation holds until something learned in one belongs in another. Two verbs cross that gap, `recap` and `ask`, under one constraint: the channel carries memories, never permissions.

### Added

- **`user-skills/maestro-net/maestro-net`** (Python, stdlib only) — the tool behind the channel. `recap <instance> "<text>"` writes a memory into the recipient's db by invoking **their** `bin/mem` with an absolute path, tagged `from:<sender>`, with no model involved. `ask <instance> "<question>"` runs `claude -p` in the recipient's directory, so their `CLAUDE.md`, preferences and memory apply, and reports the answer; the prompt carries a read-only clause and no persistent session is opened. `scan` censuses the instances on disk, `list` shows what is registered and flags dead paths. The sender of a recap resolves in three steps (`--from`, the registry name of the current directory, that directory's name) and the confirmation states which one applied. `MEM_DB` and `PWD` are stripped from the remote process's environment, so a caller that declares its own database can't divert a recap into it.
- **`user-skills/maestro-net/SKILL.md`** — the skill, meant to be installed **user-level** in `~/.claude/skills/`. The typical caller is a development session in an unrelated repository that has no Maestro skills loaded, so a project-level skill would never fire. The Maestro repository authors it and owns its version, tests and changelog; installation is a copy.
- **`~/.claude/maestro-instances.yaml`** (registry, written by the owner) — schema `version` plus `instances.<name>.{path, domain, accepts}`. `domain` carries the routing when the owner names no recipient; `accepts` lists the verbs that instance allows, and absent or empty means none. Deliberately outside `~/.maestro/`, which is the read-only template mirror that `maestro-sync` resets with `git reset --hard`.
- **`howto/11-maestro-net.md`** — the pattern: the constraint and the incident behind it, the two verbs, the registry schema, why the skill is user-level, the installation path through chezmoi, the exit-code table, and the reading side that isn't built yet.
- **`tests/test_maestro_net.py`** — 59 tests, stdlib only, no real instances and no network: `TestRegistryLoading`, `TestInstanceResolution`, `TestAcceptsGate`, `TestRecap`, `TestAsk`, `TestScan`, `TestCli`. Both verbs run against recorder scripts that capture argv, cwd and environment. Run: `python3 -m unittest tests.test_maestro_net`.

### Changed

- **`README.md`** — `user-skills/` listed among the repository's components, and the `howto/` index brought back in line with the folder (guides 08 to 11 were missing).

### Why

- The four instances already existed on disk with their own `bin/mem`, and the primitives were already there: `bin/mem` invoked with an absolute path resolves its database from the script's location, and `claude -p` run in another directory inherits that instance's `CLAUDE.md`. What was missing was the addressing — the paths would otherwise be hardcoded in whoever typed the command — and a place for the skill where any session can see it.
- `handoff` was dropped from the design. Pushing a memory covers most of what it was for, and a verb that opens a session inside another instance is exactly the kind of reach the constraint exists to prevent.
- `accepts` is what turns the constraint from an intention into a value. The precedent: a work instance once read the owner's personal task manager, because MCP servers load user-level and are visible to every session regardless of folder. Preferences declared the boundary and nothing enforced it.
- The registry parser is a small strict reader rather than a YAML dependency, so a line it doesn't understand is an error with a line number instead of a silently missing instance. Same reasoning behind the exit-code table: a channel that can't deliver says so, and a recap that can't reach its recipient is never written somewhere else.
- The scanner reads the real `cwd` out of the transcripts under `~/.claude/projects/`, because those directory names are slugs where `-` replaces `/`, `.` and spaces, and can't be turned back into paths.

### Migration

- Nothing arrives through `/maestro-sync`: `user-skills/` is outside its scope by design, since the skill is installed user-level rather than into an instance. Copy it by hand: `cp -R user-skills/maestro-net ~/.claude/skills/`, then `chezmoi add ~/.claude/skills/maestro-net` if `~/.claude` is chezmoi-managed.
- Populate the registry with `~/.claude/skills/maestro-net/maestro-net scan --write`, then fill in each `domain` and review each `accepts`. The scanner proposes both verbs for every instance it finds; narrow it with `--accepts recap` if the owner would rather grant `ask` case by case.
- Nothing changes for an instance that doesn't install it. No file distributed to instances was touched, and `memories.db` is unchanged: a recap is an ordinary `memory` row that happens to carry a `from:` tag.

---

## v2026.08.26.1 — 2026-08-26

**Theme**: The logbook learns to read the **parallel sessions** of the day. Claude Code's agent view lets the owner keep several conversations open at once and jump between them; the memories they produce already converge in `memories.db`, but the thread of each discussion stayed locked in its own transcript, visible only to the session that hosted it. Two behaviors instances had been growing on their own — flushing the warm task channel before writing, and documenting a day other than today — are absorbed into the template in the same pass.

### Added

- **`bin/session-digest`** (Python, stdlib only, no network) — extracts, for a given day, the messages the owner typed in every session of the current project. Reads the transcripts under `~/.claude/projects/<slug>/*.jsonl` (override with `CLAUDE_PROJECTS_ROOT`) and returns each session's name plus its messages in chronological order. Human messages are identified by `origin.kind == "human"`, which excludes tool results, subagent traffic (`isSidechain`) and harness noise (`<system-reminder>`, command wrappers) without heuristics on the text. Session names come from the last `custom-title` record, so a rename wins over the original; `ai-title` is the fallback. The assistant's replies stay out: they run to megabytes, while a full day of the owner's messages fits in a few KB. Filtering is by message timestamp rather than file mtime, because a session open across several days holds messages from all of them. Sessions whose messages are a strict subset of another's are dropped as shadow transcripts, the pair a backgrounded or forked conversation leaves behind (`--no-dedup` keeps them). Options: `--date` (`YYYY-MM-DD`, `today`/`oggi`, `yesterday`/`ieri`, `Nd`), `--cwd`, `--session`, `--exclude-session`, `--max-chars`, `--json`. Exit 0 clean (an empty day is not an error), 2 when no transcript directory matches the project.
- **`tests/test_session_digest.py`** — 21 tests, stdlib only, no real transcripts: `TestExtraction`, `TestDayBoundary`, `TestShadowSessions`, `TestSelection`, `TestCli`. Run: `python3 -m unittest tests.test_session_digest`.

### Changed

- **`.claude/skills/logbook/SKILL.md`** — new step 3 in the procedure, `Pick up the threads of the parallel sessions`, invoking `bin/session-digest` before grouping by theme. It states that the db stays the source of facts while the digest carries context and nuance, asks that anything substantial found only in the digest be saved as a memory before the note is written, and degrades without blocking when the script is missing. `## Sources for composing the note` gains the parallel sessions as source 3, and records that the db is the one source already spanning every session. The closing confirmation now reports how many sessions fed into the note.
- **`.claude/skills/logbook/SKILL.md`** — new step 2, `Pre-flush the warm task channel`: when `preferences.md` declares a `## Warm task channel` block with `channel != none`, the skill named there runs its `## Garbage Collector` before the note is composed. Writing the logbook is an end-of-session trigger, so the tasks closed in the warm layer land in `memories.db` dated to the target day instead of staying behind in the task manager. Announces only when it archives something, degrades without blocking, skips entirely when no channel is declared.
- **`.claude/skills/logbook/SKILL.md`** — new step 3, `Decide which day you are documenting`: the target day follows the same early-morning rule that already governs every write to `memories.db`. Called before 06:00 local with no note yet for the previous day, the skill documents the previous day and pulls in the entries of the night that follows, which are the tail of the same lived session. The filename carries the target day rather than the day of writing, and the closing confirmation reports it when the two differ.
- **`README.md`** — `bin/session-digest` listed next to `bin/mem`.
- `maestro_version` bumped to `v2026.08.26.1` on `.claude/skills/logbook/SKILL.md` and `bin/session-digest`.

### Why

- Instances write memories from any session, so the *facts* of a parallel day already converge. What evaporated was the reasoning around them: constraints that emerged, options discarded, threads left open with no recorded outcome. The owner had to remember to flush each session before leaving it, which is a discipline that fails exactly on the busy days worth documenting.
- Reading only the owner's messages is what makes this affordable. Measured on a real instance, the busiest session of a day held 11 KB of typed text against a transcript of several megabytes. The owner's side alone is enough to reconstruct what a session was about, and the db supplies the outcomes.
- A separate script rather than instructions in the skill: the parsing has enough edge cases (day boundaries in local time, shadow transcripts, noise in the `user` channel) that prose instructions would have been re-derived, differently, at every invocation.
- The warm-channel pre-flush and the target-day rule arrive from an instance that had written them into its local copy of the skill. Both are general: the warm task channel is already a template pattern (`howto/07`, session-start step 4) whose skill simply never got invoked at logbook time, and the early-morning rule is already stated in `CLAUDE.md` for every `memories.db` write. Leaving them in a fork meant the instance stopped receiving diffs on a distributed file, which is how a local customisation quietly costs an instance every future update.

### Migration

- Run `/maestro-sync`: `.claude/skills/logbook/SKILL.md` arrives as a diff. **`bin/session-digest` needs a manual copy**, since `bin/*` stays outside sync scope: `cp ~/.maestro/bin/session-digest bin/ && chmod +x bin/session-digest`. Optionally `cp ~/.maestro/tests/test_session_digest.py tests/`.
- Without the script the skill still runs: step 3 degrades to a minor note and the logbook is composed from the db and the current conversation, as before.
- Instances that had forked their `logbook` skill locally to add a warm-channel pre-flush or a target-day rule can now drop the fork and take the upstream file whole: both behaviors are in the template. Check that the frontmatter carries `origin: maestro` again, otherwise `maestro-sync` keeps treating the file as local and offers no further diffs.
- Nothing to migrate in `memories.db`, and no change to how the note is written.

---

## v2026.08.14.1 — 2026-08-14

**Theme**: A **writing register** distributed to every instance: seven prose prohibitions that bind any text the orchestrator produces for a human reader, plus a Maestro-owned post-pass skill and a deterministic checker. The template had opinions about *where* files go and *how* they are tagged, and none about how the prose reads.

### Added

- **`## Writing register` in `CLAUDE.md`** (~14 lines, after `## Tone`) — the seven prohibitions condensed, the perimeter, the post-pass, and the pointer to the canonical reference. Same pointer-plus-canonical-source shape as `## Markdown discipline`. The prohibitions: 1 meta-commentary on the text itself, 2 sycophantic concessions, 3 negative parallelism in every variant including the tailing form, 4 em dash as a pause, 5 bold as rhetorical emphasis, 6 rhythmic triads, 7 judgment as tone of voice.
- **`howto/10-writing-register.md`** — canonical reference: perimeter, the seven prohibitions with bilingual (EN/IT) before-and-after examples, the removal test for prohibition 7, post-pass mechanics, the extended net, `bin/register-check` usage, the exceptions block, and a `## Reference` section crediting [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) and [`humanizer`](https://github.com/blader/humanizer) (MIT).
- **`.claude/skills/writing-register/SKILL.md`** — post-pass on finished text, invoked before every vault write and every post or comment going to an external channel, with no length threshold. Checks the seven prohibitions plus a wider net (vague attributions, promotional language, `-ing` analyses, hedging, filler, false ranges, elegant variation, copula avoidance). **Fidelity guard**: form only, no claim added or removed, quotations and code and paths and numbers and proper nouns off limits, unresolvable passages left and reported. **Silent delivery**: returns the corrected text with no summary of changes.
- **`bin/register-check`** (Python, stdlib only, no network) — deterministic check of the four prohibitions with a syntactic signature: 3 negative parallelism (11 patterns across Italian and English, including the tailing `Y, not X` form), 4 em dash as a pause, 5 bold outside structural-label position, 6 rhythmic triads. Rules 4 and 5 report as `violation`, rules 3 and 6 as `candidate`. Skips YAML frontmatter, fenced blocks and blockquote lines; masks inline code, wikilinks, link targets and bare URLs before matching, preserving column numbers. Triad detection counts the whole enumeration run, so three consecutive items inside a longer list do not fire. `--skip N,M` suspends rules, `--json` emits machine-readable output, exit 0 clean / 1 findings / 2 usage error.
- **`tests/test_register_check.py`** — 54 tests, stdlib only, always run: `TestRule3NegativeParallelism`, `TestRule4EmDash`, `TestRule5Bold`, `TestRule6Triads`, `TestMasking`, `TestSkip`, `TestCli`. Run: `python3 -m unittest tests.test_register_check`.
- **`## Writing register` block in `preferences.example.md`** — optional per-instance exceptions: `suspended: [4, 6]` and `post_pass: on|off`. The section absent means the full register with the pass on, so `setup` writes nothing new.
- **`docs/shaping-writing-register.md`** — shaping doc for the grill session of 2026-08-14: the fourteen decisions, the two that moved during the session, the rejected alternatives.

### Changed

- **`.claude/agents/librarian.md`** — new `## Writing register` section. Binds the reports handed back to the orchestrator, because the synthesis inherits the shape of its source, and any `description` or body text written in the owner's territories.
- **`.claude/agents/scheduler.md`** — new `## Writing register` section, focused on the two prohibitions that bite on a structured list: meta-commentary and judgment as tone.
- **`.claude/skills/logbook/SKILL.md`** — new `## Writing register` section, plus the instruction to pass the finished note through the `writing-register` skill before writing it, and to confirm path and tags without narrating what the pass changed.
- **`CLAUDE.md` `## Tone`** — the "Direct, no fluff" bullet rewritten to drop an em dash used as a pause and a definition by negation.
- `maestro_version` bumped to `v2026.08.14.1` on: `CLAUDE.md`, `howto/10-writing-register.md`, `.claude/skills/writing-register/SKILL.md`, `.claude/skills/logbook/SKILL.md`, `.claude/agents/librarian.md`, `.claude/agents/scheduler.md`, `bin/register-check`.

### Why

- The seven prohibitions are a strict subset of the 29 patterns in the external `humanizer` skill. Three ways to get them into instances were on the table: depend on the external skill, vendor its `SKILL.md`, or inline its content. Skills load lazily and `CLAUDE.md` loads in full at every session start, so a Maestro-owned skill costs one `description` line per session while inlining 27 KB would have undone the compression release B of the spring upgrade paid for.
- The external skill stays out of the automatic flow on purpose. Its process is interactive (two prompts, three output blocks) and it carries no fidelity guard: its own canonical example removes a cited study, two named interviewees and a set of figures from the text it rewrites. On a Basecamp comment that is the difference between a post published and a post retracted.
- No length threshold, because the discriminant is reversibility rather than length. A two-line comment on a public channel is harder to take back than a thirty-line note that stays on disk.
- Existing template prose was left untouched. `CLAUDE.md` still contains 84 em dashes used as pauses inside the file that bans them, which works against prohibition 4 by imitation. Accepted knowingly: rewriting 84 sentences in a behavioral specification risks moving the meaning of instructions, and specification files sit outside the register's perimeter anyway.

### Migration

- Run `/maestro-sync`. `howto/10-writing-register.md` and `.claude/skills/writing-register/SKILL.md` arrive as new files through the reverse scan; `CLAUDE.md`, `logbook`, `librarian` and `scheduler` arrive as diffs.
- **`bin/register-check` needs a manual copy**, since `bin/*` is still outside sync scope: `cp ~/.maestro/bin/register-check bin/ && chmod +x bin/register-check`. Optionally `cp ~/.maestro/tests/test_register_check.py tests/`. Without the tool the skill still runs, doing the whole pass by reading.
- **`preferences.example.md` does not reach existing instances**, because `setup` removes the root templates after the first run. Instances that want the exceptions block add the section by hand, following `howto/10-writing-register.md` → "Per-instance exceptions". Instances that want the full register do nothing.
- Nothing to migrate in `memories.db`, and no change to any existing behavior beyond the shape of the prose.

---

## v2026.07.16.2 — 2026-07-16

**Theme**: Extend the semantic layer to the markdown **vault**, chunked by section — one fused recall over `memories.db` *and* the vault. Built on v2026.07.16.1 and fully additive: `log`/`log_vec` are untouched, and an instance that never supplies a vault root behaves exactly as before. Same model, dimensions, and vector format as `log_vec`, so the two indexes are co-queryable.

### Added

- **Markdown chunker in `bin/mem-vec`** (stdlib only — `re`, `fnmatch`, `hashlib`, `pathlib`): `parse_frontmatter`, `split_sections` (splits on `##`/`###`, ignores headings inside code fences, keeps the heading chain), `subsplit` (light overlap for oversized sections), `build_embed_text` (a **context sign** — file `description` + heading chain + `tags` — prepended to the chunk so cryptic headings still embed meaningfully), `make_snippet`, `compute_chunk_id`, `chunk_file`. No new dependency.
- **`vault_vec` table** — additive, self-creating alongside `log_vec` (PK = `sha256(rel_path | heading_path | sub_index)`; stores `rel_path`, `heading`/`anchor`, per-row `model`/`dims`, `content_hash`, `snippet`, `file_mtime`, and the float32-LE `embedding`). `rel_path` (relative, not absolute) keeps the index portable across machines.
- **Vault walk + `.mem-ignore`** — `walk_vault`/`load_ignore` iterate `*.md` under each root, honoring a `<vault_root>/.mem-ignore` (gitignore-style: comments, globs, `dir/`, `!negation`); dot-directories are always skipped. The ignore file lives in the vault (travels with it via iCloud/across machines), never in the template.
- **Root injection** — `bin/mem embed --root <path>` (repeatable) or env `MEM_VAULT_ROOTS` (`:`-separated). The engine stays preferences-agnostic; the orchestrator, which already reads `vault_path`, is the natural bridge. No root → `embed` does memories only, silently.
- **Incremental vault embed** — `scan_vault_state` classifies chunks as pending/stale/ok/orphan via an `mtime` pre-filter plus per-chunk `content_hash`: editing one section re-embeds only that section, deleting a file removes its chunks (orphan cleanup).
- **Fused search** — `search --semantic` merges `log_vec` + `vault_vec` in the data layer into a single ranking with a `source` field (`memory`/`vault`), a citable `ref` (`#id` or `rel_path#Section`, ready for an Obsidian `[[file#Section]]` wikilink), `score`, and `snippet`. Anti-flooding cap `--vault-frac` (default 0.6) and `--min-score` threshold; `--only memory|vault` restricts the source.
- **`tests/test_mem_vec.py`** — `TestChunker`, `TestIgnoreWalk` (stdlib, always run) plus `TestVaultEmbed`, `TestFusedSearch` (self-skip without sqlite-vec/Ollama). Full run green: 26 tests under `uv run --python 3.12 --with sqlite-vec python -m unittest tests.test_mem_vec`.

### Changed

- **`bin/mem` semantic output columns** — now `source | ref | title | score | snippet` (was `id | date | type | status | title | tags | score`). `search --semantic` forwards `--only`/`--vault-frac`; `embed` forwards `--root`.
- **`bin/mem-vec embed --status` shape** — now nested: `{"model", "memory": {…}, "vault"?: {…}}` (top-level `embedded`/`total`/`stale`/`missing` moved under `memory`). `bin/mem`'s human `--status` line was updated to read the nested shape and print a vault summary.
- **`CLAUDE.md` → `### Semantic layer (optional)`** — notes the layer now spans `log` + the markdown vault, `embed`'s `--root`/`MEM_VAULT_ROOTS`, and the `source`/`ref`/`--only` of fused search.
- **`howto/09-memoria-semantica.md`** — new "Vault index (chunked)" section (root injection, `.mem-ignore`, output columns, anti-flooding, degrade).
- `maestro_version` bumped to `v2026.07.16.2` on: `CLAUDE.md`, `howto/09-memoria-semantica.md`, `bin/mem`, `bin/mem-vec`.

### Why

- The richest context in an instance lives in the vault (logbooks especially), yet the semantic layer only saw `memories.db`. A real miss — a client whose context lived only in a logbook — was found by neither keyword nor `--semantic`, only a manual `rg`. Chunk-by-section indexing closes that gap while keeping the `.md` files the single source of truth: the db stores only vectors + a `path#anchor` pointer + a short snippet, never the prose (recovered on demand by opening the file).
- No new failure mode: same exit-3 degrade, same model/format, additive tables. Root absent → memories only. The engine never parses preferences; the vault root is declared once (in the instance) and injected by the caller.

### Migration

- Run `/maestro-sync`: `howto/09-memoria-semantica.md` arrives as a diff and `CLAUDE.md` gains the vault notes; copy `bin/mem` and `bin/mem-vec` from the mirror manually (`bin/*` stays outside sync's diff scope — `cp ~/.maestro/bin/mem bin/mem`, same for `mem-vec`).
- To index the vault on an instance: create `<vault_path>/.mem-ignore` (at least `Diario/` for privacy + noise globs like `*.excalidraw`), export `MEM_VAULT_ROOTS=<vault_path>` before `bin/mem embed` (e.g. in the session-start hook — today it runs rootless and would keep doing memories only), then `bin/mem embed --rebuild` once. Without a root, `bin/mem` is unchanged.
- **Contract change**: any consumer parsing `bin/mem embed --status` JSON must read `memory.*` (and optional `vault.*`) instead of the former top-level keys.

---

## v2026.07.16.1 — 2026-07-16

**Theme**: Optional semantic layer for `memories.db` — recall by meaning, duplicate detection, pattern discovery — built and calibrated on a real instance, then upstreamed. Strictly opt-in per machine and fully additive: an instance without Ollama/uv behaves exactly as before.

### Added

- **`bin/mem-vec`** (new, PEP 723 script) — the data layer. Runs via `uv run --script`, declares its own dependency (`sqlite-vec`) inline, needs no project-level install. Talks to a local Ollama instance for embeddings (default model `bge-m3`, override via `MEM_EMBED_MODEL` or `--model`). Commands: `embed` (vectorize new/changed rows, `--rebuild`/`--status`), `search` (cosine similarity ranking), `similar` (rows close to a given id), `dupes` (candidate duplicate pairs). Vectors live in `log_vec`, a plain additive table that self-creates on first use — `log` and `memories.db.template` are untouched.
- **`bin/mem`** — thin delegation to `bin/mem-vec` via a new `_vec_run` helper (`uv run --script`, capturing stdout/stderr). New subcommands `embed`, `similar`, `dupes`; `search` gains `--semantic`, `--min-score`, `--model` and branches to `_cmd_search_semantic` in `cmd_search` when `--semantic` is set. `EXIT_SEM_UNAVAILABLE = 3` is returned (with a clear stderr message) whenever `uv` is missing or Ollama is unreachable — every other command is unaffected. Epilog documents exit code 3.
- **`tests/test_mem_vec.py`** (new, + `tests/__init__.py`) — stdlib-only unit tests (content hashing, pack/roundtrip, `log_vec` auto-creation, embed-state lifecycle) plus integration tests that self-skip when `sqlite-vec` or Ollama aren't available in the running interpreter. Full run: `uv run --with sqlite-vec python -m unittest tests.test_mem_vec -v`.
- **`howto/09-memoria-semantica.md`** (new, `origin: maestro`) — setup (`brew install ollama uv`, `ollama pull bge-m3`, `bin/mem embed --rebuild`), command reference, how embeddings are derived data (rebuildable from scratch, safe across machine changes), degradation behavior, and the evolution markers that signal a future move to vec0 KNN indexes (scale) or an FTS5 hybrid (exact-term recall).
- **`CLAUDE.md` → `## Memory`**: new `### Semantic layer (optional)` subsection (between `### Commands — via bin/mem` and `### Rules`) documenting the four commands, the anti-duplication rule (`--semantic --limit 3`, propose update on score ≥ 0.80 instead of inserting a duplicate), and the degradation rule (exit 3 → silent keyword fallback, never surfaced as an error).

### Why

- Keyword search on `log` misses paraphrases and near-duplicates by construction — the owner routinely thinks in concepts, not in the exact words a past entry used. A semantic layer closes that gap without touching the write path or the schema instances already depend on.
- Zero-risk by design: additive table, opt-in per machine (no Ollama/uv → identical behavior to today), derived data (embeddings are a pure function of text + model, always reconstructible via `--rebuild`), and delegated to a separate PEP-723 script so `bin/mem`'s own dependency surface stays at zero.
- `bge-m3` and the `0.80` anti-duplication threshold are concrete defaults calibrated against a real instance's data, not placeholders — instances can retune both without any code change.

### Migration

- Run `/maestro-sync`: `bin/mem`, `bin/mem-vec`, `tests/test_mem_vec.py`, `tests/__init__.py`, `howto/09-memoria-semantica.md` arrive as diffs/new files; the `CLAUDE.md` diff adds the `### Semantic layer (optional)` subsection. `bin/*` stays outside sync's diff scope for `maestro_version` bookkeeping — copy manually if the sync skill doesn't offer it (`cp ~/.maestro/bin/mem bin/mem` etc.).
- To activate on an instance: `brew install ollama uv && brew services start ollama && ollama pull bge-m3 && bin/mem embed --rebuild`. Without this setup, `bin/mem` is unchanged — semantic subcommands simply exit 3.

---

## v2026.07.15.2 — 2026-07-15

**Theme**: Slim `CLAUDE.md` from 489 to ~260 lines — second half of the "spring upgrade" (see `docs/shaping-spring-upgrade.md`). Behavioral rules stay resident and are rewritten tighter; reference material moves to canonical sources loaded on demand. **No rule was dropped** — only prose, examples, and duplicated reference were compressed or extracted.

### Added

- **`howto/08-markdown-discipline.md`** — new distributed reference file (`origin: maestro`, the first marked howto) carrying the full markdown discipline extracted from `CLAUDE.md`: frontmatter style (tags + description), YAML safety with examples, Obsidian wikilink rules. Delivered to instances by the reverse scan shipped in v2026.07.15.1.

### Changed

- **`CLAUDE.md`** — restructured (~-47%):
  - "Frontmatter and search discipline" + "YAML safety" + "Linking discipline" merged into one condensed **"Markdown discipline"** section (all rules kept) pointing to `howto/08` for details and examples.
  - **Memory section**: the SQL schema block is dropped (the schema ships in `memories.db.template`; type/status semantics stay inline); the full `bin/mem` command/report reference is replaced by a ~10-line cheatsheet plus `bin/mem --help` as the canonical reference.
  - Verbose behavioral sections (Session start step 4, Validation before touching a sub-app, Preferences evolution, Delegation, Handoff) rewritten tighter with every rule preserved.
- **`bin/mem`** — argparse help texts enriched so `--help` can serve as the canonical reference: top-level epilog documents relative dates, the early-morning rule, output modes, and `MEM_DB`; per-flag help added for `--date`, `--due`, `--status` (allowed values per type), `--bulk` (row keys), `marker`, and `search` filters. No behavior change.
- **`.claude/skills/logbook/SKILL.md`** — points to `howto/08-markdown-discipline.md` for the markdown discipline; the "retrieve today's entries" step uses `bin/mem today` (raw `sqlite3` kept as fallback).
- **`.claude/agents/librarian.md`** — frontmatter-discipline section points to `howto/08-markdown-discipline.md`.
- `maestro_version` bumped to `v2026.07.15.2` on: `CLAUDE.md`, `howto/08-markdown-discipline.md`, `.claude/skills/logbook/SKILL.md`, `.claude/agents/librarian.md`.

### Why

- ~40–45% of the old `CLAUDE.md` was reference material, not behavior. Loaded at every session start in every instance, it diluted the weight of the rules that matter (announce-every-write, access gate) and cost ~7–8k tokens per session. Reference belongs where it can't drift: the CLI documents itself via `--help`, the markdown discipline lives in one distributed file that skills and agents point to.
- Future SQLite work (FTS5, indexes, `sqlite-vec`) will land in `bin/mem` and its `--help` without touching `CLAUDE.md` again.

### Migration

- Instances that applied v2026.07.15.1 (reverse scan): run `/maestro-sync` — the slimmed `CLAUDE.md`, `logbook`, `librarian` arrive as diffs; `howto/08-markdown-discipline.md` is proposed as a new file. Copy `bin/mem` manually from the mirror (`cp ~/.maestro/bin/mem bin/mem`) — `bin/*` is still outside sync scope.
- Instances still on ≤ v2026.05.28.1: run `/maestro-sync` **twice** — the first run installs the reverse-scan-capable skill, the second delivers the new howto. The CLAUDE.md diff applies on the first run either way; the pointer to `howto/08` stays dangling until the second run (harmless: the condensed rules in CLAUDE.md are self-sufficient).
- Instances that hand-edited their `CLAUDE.md` despite the distribution rule: review the diff carefully per file — this release rewrites most lines.

---

## v2026.07.15.1 — 2026-07-15

**Theme**: Close the new-file delivery gap in `maestro-sync` — first half of the "spring upgrade" (see `docs/shaping-spring-upgrade.md`). Until now the skill only scanned the instance, so files created upstream after an instance was cloned (new skills, `bin/mem`, marked howtos) were never proposed and required manual copies.

### Added

- **`maestro-sync` → Phase 4b — Reverse scan**: after scanning the instance, the skill walks the mirror for `*.md` files marked `origin: maestro` whose path doesn't exist in the instance, and proposes each as a **new file** in the per-file confirmation flow (content preview instead of diff, same `a/s/A/n` prompt, `(new)` marker in the log, `Added:` line in the final summary). The reverse scan is glob-based over the whole mirror, so future distributed files are delivered regardless of where they live.

### Changed

- **`maestro-sync` → Memory log**: the post-sync memory entry now prefers `bin/mem save`, with raw `sqlite3` kept as fallback for instances that don't have the CLI yet.
- **`README.md`** — drift fixes: the roster ships with `librarian` and `scheduler` enrolled (was described as "empty at install"); the shipped skills/agents list and `bin/mem` are now stated; the howto index lists all seven guides (06 and 07 were missing); the Status section points at this CHANGELOG instead of "version 0.1.0".
- **`maestro-sync` frontmatter** — `maestro_version` bumped to `v2026.07.15.1`.

### Why

- The second half of the spring upgrade (planned as the next release) slims `CLAUDE.md` by extracting reference material into a **new** distributed file. Without the reverse scan, instances would sync the slimmed `CLAUDE.md` but never receive the file it points to. Shipping the sync fix **first** guarantees that by the time the refactor lands, every instance that syncs regularly already has the delivery mechanism.
- The manual-copy step documented for `bin/mem` in v2026.05.23.1 was a symptom of this gap. Note: `bin/mem` itself is still outside the scan scope (it carries a comment marker, not YAML frontmatter) — the reverse scan only covers `*.md` files for now.

### Migration

- Instances: run `/maestro-sync` and apply the `maestro-sync` skill diff. No data migration. From the **next** invocation onward, new upstream files will be proposed automatically.
- Instances that never copied `bin/mem` manually: the copy step from v2026.05.23.1 still applies (the reverse scan doesn't cover `bin/*` yet).

---

## v2026.05.28.1 — 2026-05-28

**Theme**: Promote two librarian disciplines proven in a client instance into the base agent — tag parsimony and a symlink safety rail — generalized to be instance-agnostic.

### Changed

- **`.claude/agents/librarian.md`** gains two sections:
  - **`### Tag discipline — parsimony over creativity`** (under Frontmatter discipline): no orphan tags (a tag must be used by ≥2 files), reuse before inventing, prefer cross-cutting axes over content-descriptive adjectives, the orchestrator's controlled vocabulary wins on bulk catalog.
  - **`## Forbidden targets — symlinks to other repositories`** (after the catalog report format) + a matching `## Never` bullet: resolve `realpath` before any write, refuse to write if the real target sits outside the task's named territory (e.g. a symlink into an application code repo). Generic — names no specific repos.
- **`librarian.md` frontmatter** — `maestro_version` bumped to `v2026.05.28.1`.

### Why

Both patterns surfaced in a client instance as hand-edits to the librarian: a tag-hygiene rule and a safety rail against writing through symlinks into application code. They are generic and benefit every instance, so they belong in the template rather than living as an instance fork.

### Migration

- Instances that had **not** customized `librarian.md`: pull via `maestro-sync` and apply the diff. No data migration.
- The client instance carried these two sections as a local fork; after this promotion it re-aligns to the upstream (generalized) librarian and rejoins `maestro-sync` scope.

---

## v2026.05.23.2 — 2026-05-23

**Theme**: Extract the warm/cold/GC task pattern from instance-level boilerplate into a generic, opt-in Maestro feature. Instances declare a warm task channel in `preferences.md`; the orchestrator runs a lazy GC at session start. No hardcoded channel names in `CLAUDE.md`.

### Added

- **`howto/07-warm-task-channel.md`** — new how-to that describes the warm (external task system) / cold (`memories.db`) / GC (skill `<channel>-task-manager`) pattern, the skill contract, the archive-memory format, optional weekly trend, and reusability across instances. Includes worked examples for Acme and Basecamp.
- **`preferences.example.md` → `## Warm task channel`** — new optional block with `channel`, `skill`, `archive_tag`, `marker_name`. Skip the block entirely (or set `channel: none`) to keep `memories.db` as the only task store.

### Changed

- **`CLAUDE.md` → `## Session start`** — added step 4 "Warm task channel — lazy GC" as an optional, channel-driven instruction. If `preferences.md` declares a warm task channel, the orchestrator invokes the named skill's `## Garbage Collector` section. Idempotency guard (1h), cross-week-boundary trend (if the skill defines it), non-blocking on errors, one-line announcement only when N > 0.
- **`CLAUDE.md` → `## Identity and customizations`** — added "Warm task channel" to the list of expected preferences blocks, marked optional.
- **`howto/README.md`** — added the new how-to to the index.
- **`CLAUDE.md` frontmatter** — `maestro_version` bumped to `v2026.05.23.2`.

### Why

- Pre-2026.05.23.2 instances that used a warm task channel (e.g. `home` with Acme) hardcoded the channel name in their own copy of `CLAUDE.md`, drifting from the template and making the same pattern hard to reuse on other instances (`work` with Basecamp, `side` with Basecamp).
- Extracting the pattern lets every instance opt-in by editing `preferences.md` alone, without touching `CLAUDE.md`. New channels are added by writing a skill that conforms to the GC contract — the orchestrator's top-level behavior stays unchanged.
- The howto is the single source of truth for the contract, so each `<channel>-task-manager` skill (Acme, Basecamp, etc.) can point at it instead of redefining the flow.

### Migration

- Instances with no warm task channel: **no action needed**. The new session-start step is a no-op when the preferences block is absent.
- Instances that already hardcoded a channel (e.g. `home`): pull this version via `maestro-sync`, then move the channel declaration into a `## Warm task channel` block in `private/preferences.md` and delete any instance-level edits to `CLAUDE.md`'s session-start section. The existing `<channel>-task-manager` skill keeps working as-is — only the entry point moves from CLAUDE.md to preferences.

---

## v2026.05.23.1 — 2026-05-23

**Theme**: Ship `bin/mem` — a Python CLI wrapper for `memories.db` that replaces verbose raw SQL with a consistent, escape-safe, output-aware interface.

### Added

- **`bin/mem`** new executable Python script (stdlib only, no dependencies). Subcommands:
  - **Writes**: `save`, `task`, `idea`, `update`, `done`, `reopen`
  - **Reads**: `today`, `todo`, `overdue`, `search`, `show`, `stats`
  - **Bulk**: `save --bulk` reads a JSON array from stdin, inserts every row in a single SQLite transaction
  - **Markers**: `marker get|set <name>` for sync watermarks (upsert in-place on the `log` table — retro-compatible with marker rows created before the CLI existed)
- Cross-cutting features in the CLI:
  - Parameterized SQL — no more escape errors on apostrophes/accents/quotes
  - Relative dates: `today`, `yesterday`, `tomorrow`, `+Nd`, `-Nd`, `+Nw`, `+Nm`
  - Early-morning rule (00:00–06:00 → previous day) applied automatically when `--date` is omitted
  - Output: ASCII table on TTY, dense JSON on pipe; `--json` forces JSON
  - DB path resolution: env `MEM_DB` > `<repo-root>/private/memories.db` (auto-detected from the script's location)

### Changed

- **`CLAUDE.md` → `## Memory` → "Commands" / "Reports"** rewritten to promote `bin/mem` as the preferred access layer. Raw `sqlite3` is kept as a documented fallback for queries the CLI doesn't cover (custom joins, integrity checks, vacuum, `ALTER TABLE`).
- **`howto/04-memory-and-integrations.md`** new section "CLI helper — `bin/mem`" explaining the why and the surface.
- **`CLAUDE.md` frontmatter** — `maestro_version` bumped to `v2026.05.23.1`.

### Why

- Verbosity of raw SQL was the dominant token cost in the orchestrator's memory writes (~700–800 tokens per non-trivial save). The CLI cuts this by 30–40%.
- Escape of Italian (or any non-ASCII) text in raw SQL was a recurring source of silent INSERT failures. Parameterized SQL closes that.
- Bulk writes via single transaction unlock efficient flush flows (e.g., archiving an external task store's done items into the cold memory layer in one round-trip instead of N).
- Markers as named upsert give a clean replacement for the pattern of "row in `log` with a sentinel title".

### Migration note for instances

**`bin/mem` is not yet in `maestro-sync`'s scan scope.** The sync skill only walks Markdown files with `origin: maestro` frontmatter (CLAUDE.md, hub skills, base agents). Python files in `bin/` have an `# origin: maestro` comment marker but the parser doesn't read it yet.

At the next sync, after running `/maestro-sync` and applying the markdown diffs, **copy `bin/mem` manually** from the mirror:

```bash
mkdir -p bin
cp ~/.maestro/bin/mem bin/mem
chmod +x bin/mem
```

This is a one-shot step per instance (idempotent — running it again just overwrites with the current upstream version). A future Maestro release may extend `maestro-sync` to scan `bin/*` for comment-style frontmatter; until then, copy by hand.

### Roadmap (open)

The work behind this release is part of a larger shaping, tracked as an idea in the instance's `memories.db`. What's deferred for now:

- **FTS5 + indexes + views** — relevant when the row count grows past a few thousand
- **`sqlite-vec` + semantic similarity** — `bin/mem similar <id-or-query>` k-NN search
- **MCP server layer** — would eliminate the Bash round-trip the CLI still incurs; deferred because the dominant cost was verbosity (now solved) and an MCP server reopens the multi-instance isolation question
- **Scope extension of `maestro-sync`** to handle `bin/*` with comment-style markers — would remove the manual copy step above

### Commit

- (commit hash on this version)

---

## v2026.04.30.4 — 2026-04-30

**Theme**: Allow per-instance customization of the `tools:` frontmatter field on `origin: maestro` files.

### Changed

- **`CLAUDE.md` → "Distribution and modifications"** gets a new "Single exception" paragraph. Each instance can extend the `tools:` whitelist of a skill or agent marked `origin: maestro` with its own MCPs/tools, without violating the no-in-place-edits rule. This is necessary because MCP installations are per-instance: an agent that needs to call Acme tools needs `mcp__acme__*` in its `tools:`, but Acme may not exist on every instance. The `maestro-sync` skill ignores diffs limited to the `tools:` field — only the body and other frontmatter keys are diffed for sync.

### Why

Without this exception, an instance that wants to use the base `scheduler` agent (Maestro-distributed) couldn't add its own MCP tools without forking the file or fighting the sync. The exception keeps the agent body as upstream's source of truth and lets the instance own its tool whitelist.

### Commit

- (commit hash on this version)

---

## v2026.04.30.3 — 2026-04-30

**Theme**: Introduce the `maestro-sync` skill — the actual sync engine.

### Added

- **`.claude/skills/maestro-sync/SKILL.md`** new hub skill. Implements the full sync flow:
  1. Locate mirror (`~/.maestro/`) and primary working tree
  2. Pre-sync check on the working tree (warn on uncommitted changes / unpushed commits)
  3. Refresh the read-only mirror with `git fetch origin && git reset --hard origin/main`
  4. Scan the instance for files marked `origin: maestro`, read each `maestro_version`
  5. Show the changelog delta from instance floor to mirror version
  6. Per-file diff and confirmation (`a` / `s` / `A` / `n`)
  7. Apply, log to `private/maestro-sync.log`, summarize, log a memory
- **`CLAUDE.md` → "Hub skills"** — new entry for `maestro-sync` so instances know the skill exists and how to trigger it.

### Bootstrap notes

- A brand new instance cloned from this template gets `maestro-sync` already installed.
- An old instance predating `origin: maestro` markers needs the owner to mark its inheritable files manually with `maestro_version: v2026.04.29.1` (the baseline) before the first sync — then the normal flow handles it.

### Self-update

`maestro-sync` is itself marked `origin: maestro`. When upstream ships a new version of the skill, instances pick it up like any other file in the scan.

### Commit

- (commit hash on this version)

---

## v2026.04.30.2 — 2026-04-30

**Theme**: Promote three patterns proven in a personal instance into the template.

### Added

- **`CLAUDE.md` → "Decide which `date:` to write — early-morning rule"** under the Memory section. New sub-section that codifies the rule: writes to `memories.db` between 00:00 and 06:00 local time are attributed to the previous day (`date('now','-1 day')`) unless the owner has explicitly closed it. Avoids fragmenting one lived session across two calendar days.
- **`CLAUDE.md` → "YAML safety in frontmatter values"** under "Frontmatter and search discipline". Lists the trigger characters (`: `, `# `, leading `[{>|*&!%@\``) that force a value to be quoted with double quotes, and the rule "when in doubt, quote".
- **`CLAUDE.md` → "Linking discipline (Obsidian wikilinks)"** new top-level section. When the vault is an Obsidian one, references to other vault files use `[[Filename]]` syntax (with optional `[[Filename|alias]]`). Lists what stays in monospace (folder paths, files outside the vault, code identifiers, URLs). Explains the graph-connectivity reason. Section is conditional: skipped when the vault is plain filesystem.

### Migration for existing instances

These three patterns may already exist in instance-level customizations of `CLAUDE.md` (instances that surfaced them earlier). On sync, prefer the template's wording for consistency unless the local version has owner-specific examples worth keeping.

### Commit

- (commit hash filled in by the commit itself — see git log on this version's commit)

---

## v2026.04.30.1 — 2026-04-30

**Theme**: Available apps moves out of `CLAUDE.md` into `preferences.md`; new distribution rule.

### Changed

- **`CLAUDE.md`** — the "Available apps" table no longer lives here. The section now points to `private/preferences.md`. Two cross-references updated:
  - In "Hub skills", the `add-external-app` entry now says it updates the section in preferences.
  - In "Validation before touching a sub-app", the access gate paragraph references the section in preferences instead of the table.
- **`preferences.example.md`** — introduces a new "Available apps" section with a 4-column table (Alias, Path, Purpose, Access) and a placeholder row. New instances get this template at setup time.
- **`.claude/skills/add-external-app/SKILL.md`** — Step 3 is rewritten to update `private/preferences.md` instead of `CLAUDE.md`. Frontmatter description, intro, Q3 of the Q&A flow, confirmation recap, Step 4 final summary, and the memory log line are all aligned to the new target.

### Added

- **`CLAUDE.md` → "Distribution and modifications"** new section. Forbids in-place edits of files marked `origin: maestro` in their frontmatter. Any change must go through Maestro origin and be reabsorbed via sync.

### Migration for existing instances

Instances on the previous version (or earlier) have the apps table living in their own `CLAUDE.md`. After a sync that applies this version:

1. The local `CLAUDE.md` "Available apps" section becomes a pointer to `preferences.md`.
2. The instance must move its existing apps table from `CLAUDE.md` into `private/preferences.md` (under a new "Available apps" section) — `maestro-sync` does not migrate data, only patterns.
3. The "Distribution and modifications" section is added to the local `CLAUDE.md`.

For instances bootstrapped from this version onward, the table lives in preferences from day one; no migration needed.

### Commit

- `f515fbf` (origin/main) — *V1.a → template: move "Available apps" out of CLAUDE.md into preferences*

---

## v2026.04.29.1 — 2026-04-29

**Theme**: Initial snapshot for changelog tracking.

This is the baseline version. Instances bootstrapped before this date may not declare `maestro_version` in their `origin: maestro` files; the first `maestro-sync` against `v2026.04.30.1` or later will treat them as `v2026.04.29.1` and propose all subsequent changes.

### State at this version

The template provides:

- Top-level `CLAUDE.md` describing the orchestrator role, session start, role rules, tone, repo structure, available apps (as table), hub skills, delegation/roster, routing, validation before touching sub-app, handoff between apps, file territories (vault root + three subfolder keys), frontmatter discipline, memory (SQLite at `private/memories.db`), preferences evolution, Basecamp scope, permissions/paths.
- Hub skills: `setup` (interactive first-launch configuration), `logbook` (daily logbook to `logbook_path`), `add-external-app` (registers an external project as a sub-app with a pointer skill, updates the apps table in `CLAUDE.md`), `guide` (answers questions about the orchestrator from `CLAUDE.md` and `howto/`).
- Craft agents: `librarian` (vault hygiene + research), `scheduler` (cold data layer for prospective/retrospective queries), `hr` (recruiter for the agent roster).
- Roster registry, `routines.example.yaml`, `memories.db.template` for setup seeding.
- `preferences.example.md` template (without "Available apps" section — that's introduced in v2026.04.30.1).
- `howto/` documentation set.

### Commit

- `c542a2e` (origin/main, parent of f515fbf) — *Install librarian + scheduler agents; rework setup with finalize.sh*
