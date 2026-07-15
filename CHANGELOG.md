# CHANGELOG

Versioned record of intentional changes to the Maestro template — patterns, skills, agents, conventions distributed to instances.

Versions follow the **`vYYYY.MM.DD.N`** scheme (date-based, incremental within the day). Each entry documents what changed, why it matters, and any migration note for instances syncing in.

The skill `maestro-sync` reads this file from the latest pull of the read-only mirror (`~/.maestro/`) and shows the delta between an instance's current `maestro_version` and `HEAD` before applying file-level diffs.

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

**Theme**: Promote two librarian disciplines proven in the Luigi instance into the base agent — tag parsimony and a symlink safety rail — generalized to be instance-agnostic.

### Changed

- **`.claude/agents/librarian.md`** gains two sections:
  - **`### Tag discipline — parsimony over creativity`** (under Frontmatter discipline): no orphan tags (a tag must be used by ≥2 files), reuse before inventing, prefer cross-cutting axes over content-descriptive adjectives, the orchestrator's controlled vocabulary wins on bulk catalog.
  - **`## Forbidden targets — symlinks to other repositories`** (after the catalog report format) + a matching `## Never` bullet: resolve `realpath` before any write, refuse to write if the real target sits outside the task's named territory (e.g. a symlink into an application code repo). Generic — names no specific repos.
- **`librarian.md` frontmatter** — `maestro_version` bumped to `v2026.05.28.1`.

### Why

Both patterns surfaced in the Luigi instance (Gestart) as hand-edits to the librarian: a tag-hygiene rule and a safety rail against writing through symlinks into application code. They are generic and benefit every instance, so they belong in the template rather than living as an instance fork.

### Migration

- Instances that had **not** customized `librarian.md`: pull via `maestro-sync` and apply the diff. No data migration.
- The Luigi instance carried these two sections as a local fork; after this promotion it re-aligns to the upstream (generalized) librarian and rejoins `maestro-sync` scope.

---

## v2026.05.23.2 — 2026-05-23

**Theme**: Extract the warm/cold/GC task pattern from instance-level boilerplate into a generic, opt-in Maestro feature. Instances declare a warm task channel in `preferences.md`; the orchestrator runs a lazy GC at session start. No hardcoded channel names in `CLAUDE.md`.

### Added

- **`howto/07-warm-task-channel.md`** — new how-to that describes the warm (external task system) / cold (`memories.db`) / GC (skill `<channel>-task-manager`) pattern, the skill contract, the archive-memory format, optional weekly trend, and reusability across instances. Includes worked examples for Slacky and Basecamp.
- **`preferences.example.md` → `## Warm task channel`** — new optional block with `channel`, `skill`, `archive_tag`, `marker_name`. Skip the block entirely (or set `channel: none`) to keep `memories.db` as the only task store.

### Changed

- **`CLAUDE.md` → `## Session start`** — added step 4 "Warm task channel — lazy GC" as an optional, channel-driven instruction. If `preferences.md` declares a warm task channel, the orchestrator invokes the named skill's `## Garbage Collector` section. Idempotency guard (1h), cross-week-boundary trend (if the skill defines it), non-blocking on errors, one-line announcement only when N > 0.
- **`CLAUDE.md` → `## Identity and customizations`** — added "Warm task channel" to the list of expected preferences blocks, marked optional.
- **`howto/README.md`** — added the new how-to to the index.
- **`CLAUDE.md` frontmatter** — `maestro_version` bumped to `v2026.05.23.2`.

### Why

- Pre-2026.05.23.2 instances that used a warm task channel (e.g. Alfred with Slacky) hardcoded the channel name in their own copy of `CLAUDE.md`, drifting from the template and making the same pattern hard to reuse on other instances (Pam with Basecamp, Claudio with Basecamp).
- Extracting the pattern lets every instance opt-in by editing `preferences.md` alone, without touching `CLAUDE.md`. New channels are added by writing a skill that conforms to the GC contract — the orchestrator's top-level behavior stays unchanged.
- The howto is the single source of truth for the contract, so each `<channel>-task-manager` skill (Slacky, Basecamp, etc.) can point at it instead of redefining the flow.

### Migration

- Instances with no warm task channel: **no action needed**. The new session-start step is a no-op when the preferences block is absent.
- Instances that already hardcoded a channel (e.g. Alfred): pull this version via `maestro-sync`, then move the channel declaration into a `## Warm task channel` block in `private/preferences.md` and delete any instance-level edits to `CLAUDE.md`'s session-start section. The existing `<channel>-task-manager` skill keeps working as-is — only the entry point moves from CLAUDE.md to preferences.

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

The work behind this release is part of a larger shaping (see Alfred's `memories.db` idea #408). What's deferred for now:

- **FTS5 + indexes + views** — relevant when the row count grows past a few thousand
- **`sqlite-vec` + semantic similarity** — `bin/mem similar <id-or-query>` k-NN search (idea #407 in Alfred)
- **MCP server layer** — would eliminate the Bash round-trip the CLI still incurs; deferred because the dominant cost was verbosity (now solved) and an MCP server reopens the multi-instance isolation question (idea #455)
- **Scope extension of `maestro-sync`** to handle `bin/*` with comment-style markers — would remove the manual copy step above

### Commit

- (commit hash on this version)

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
