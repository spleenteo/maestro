# CHANGELOG

Versioned record of intentional changes to the Maestro template — patterns, skills, agents, conventions distributed to instances.

Versions follow the **`vYYYY.MM.DD.N`** scheme (date-based, incremental within the day). Each entry documents what changed, why it matters, and any migration note for instances syncing in.

The skill `maestro-sync` reads this file from the latest pull of the read-only mirror (`~/.maestro/`) and shows the delta between an instance's current `maestro_version` and `HEAD` before applying file-level diffs.

---

## v2026.04.30.4 — 2026-04-30

**Theme**: Allow per-instance customization of the `tools:` frontmatter field on `origin: maestro` files.

### Changed

- **`CLAUDE.md` → "Distribution and modifications"** gets a new "Single exception" paragraph. Each instance can extend the `tools:` whitelist of a skill or agent marked `origin: maestro` with its own MCPs/tools, without violating the no-in-place-edits rule. This is necessary because MCP installations are per-instance: an agent that needs to call Slacky tools needs `mcp__slacky__*` in its `tools:`, but Slacky may not exist on every instance. The `maestro-sync` skill ignores diffs limited to the `tools:` field — only the body and other frontmatter keys are diffed for sync.

### Why

Without this exception, an instance that wants to use the base `scheduler` agent (Maestro-distributed) couldn't add its own MCP tools without forking the file or fighting the sync. The exception keeps the agent body as upstream's source of truth and lets the instance own its tool whitelist.

### Commit

- (commit hash on this version)

---

## v2026.04.30.3 — 2026-04-30

**Theme**: Introduce the `maestro-sync` skill — the actual sync engine.

### Added

- **`.claude/skills/maestro-sync/SKILL.md`** new hub skill. Implements the full sync flow:
  1. Locate mirror (`~/.maestro/`) and primary working tree (`~/Sites/me/maestro/`)
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

**Theme**: Promote three patterns proven in the Alfred instance into the template.

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
