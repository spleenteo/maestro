# CHANGELOG

Versioned record of intentional changes to the Maestro template — patterns, skills, agents, conventions distributed to instances.

Versions follow the **`vYYYY.MM.DD.N`** scheme (date-based, incremental within the day). Each entry documents what changed, why it matters, and any migration note for instances syncing in.

The skill `maestro-sync` reads this file from the latest pull of the read-only mirror (`~/.maestro/`) and shows the delta between an instance's current `maestro_version` and `HEAD` before applying file-level diffs.

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
