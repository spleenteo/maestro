---
origin: maestro
maestro_version: v2026.04.30.4
name: maestro-sync
description: Sync this orchestrator instance with the latest Maestro template. Updates the read-only mirror at `~/.maestro/`, scans the instance for files marked `origin: maestro`, shows the changelog delta, and proposes diffs for confirmation before applying. Use when the owner says "sync maestro", "update from maestro", "pull maestro changes", "/maestro-sync", or asks whether new patterns are available from the template.
---

# maestro-sync

This skill keeps the orchestrator instance aligned with the **Maestro template** at `https://github.com/spleenteo/maestro`. It applies upstream pattern changes (CLAUDE.md sections, base hub skills, base craft agents) without ever touching the instance's personalizations.

## Architecture

Two paths, two roles (decided 2026-04-30):

- **`~/Sites/me/maestro/`** — primary working tree. Where the owner promotes new patterns from this instance to the template (modify, commit, push). This skill **never writes here**. It only reads its git status to warn the owner if there are uncommitted changes that should be pushed before syncing.
- **`~/.maestro/`** — read-only mirror used by this skill as a stable comparison point. The mirror is updated only by this skill, with `git fetch origin && git reset --hard origin/main`. Never committed to, never modified by hand.

The skill scans the **instance** (the orchestrator that invokes the skill) for files with `origin: maestro` in their frontmatter, compares each with the mirror version, and proposes a diff per file with confirmation.

## Files in scope

The skill operates on files marked with both `origin: maestro` and `maestro_version: vYYYY.MM.DD.N` in their frontmatter. Typical inheritable files:

- `CLAUDE.md` (top-level)
- `.claude/skills/<name>/SKILL.md` for hub skills distributed by Maestro (e.g. `setup`, `logbook`, `add-external-app`, `guide`, `maestro-sync` itself)
- `.claude/agents/<name>.md` for craft agents distributed by Maestro (e.g. `librarian`, `scheduler`, `hr`)

Files **never** in scope:

- `private/*` (preferences, memories.db, logs, anything sensitive)
- `apps/*` (sub-apps and their internals)
- Custom skills/agents added by the instance (no `origin: maestro` marker)
- `.claude/roster.yaml` (instance-specific list of active agents — Maestro doesn't choose which agents an instance enrolls)

## When this skill runs

Invoke it when the owner says something like:

- *"Sync Maestro"* / *"Update from Maestro"* / *"Pull Maestro changes"*
- *"/maestro-sync"*
- *"Are there new patterns from the template?"*
- *"Bring this instance up to date with the latest Maestro"*

## Operational flow

Six phases. Stop and report on the first error — never continue past a failure silently.

### Phase 1 — Locate the two paths

Resolve from preferences (or use sensible defaults):

- **Mirror path**: `~/.maestro/` (default). If preferences declare `maestro_mirror_path:`, use that.
- **Working tree path**: `~/Sites/me/maestro/` (default). If preferences declare `maestro_worktree_path:`, use that.

If the **mirror** doesn't exist yet, bootstrap it: `git clone git@github.com:spleenteo/maestro <mirror-path>`. Tell the owner: *"First run: I'm cloning the Maestro mirror at <mirror-path>."*

If the **working tree** doesn't exist, that's fine — promotions can still be done by cloning it on demand. Skip Phase 2 with a soft note: *"No primary working tree at <worktree-path>; skipping the uncommitted-changes check. Nothing to lose."*

### Phase 2 — Pre-sync check on the working tree

This is the hook that catches in-flight promotions before they get clobbered by a sync. Run on the **primary working tree**, never on the mirror.

```bash
cd <worktree-path>
git status --porcelain          # any uncommitted changes?
git log @{u}..HEAD --oneline    # any local commits not yet pushed?
```

- If `git status --porcelain` returns non-empty → there are uncommitted changes.
- If `git log @{u}..HEAD` returns non-empty → there are local commits not pushed.

In either case, **stop** and ask the owner:

> ⚠ I see local changes in your Maestro working tree (`<worktree-path>`):
> - <list of modified/untracked files, max 10>
> - <list of unpushed commits, max 5>
>
> If you're in the middle of promoting a pattern to the template, push these first — otherwise the sync will pull `origin/main` without them, and the instance won't see your work-in-progress.
>
> Options:
> - `push` — let me push them now (only if all changes are committed; if there are uncommitted edits, I won't `git add -A` for you)
> - `continue` — sync anyway, knowing the local work isn't reflected
> - `abort` — stop here, you handle it manually

Wait for the owner. If `push`, run `git push origin main` from the working tree. If `continue`, proceed to Phase 3. If `abort`, exit with a clean message.

### Phase 3 — Refresh the read-only mirror

```bash
cd <mirror-path>
git fetch origin
git reset --hard origin/main
```

This is the only write operation on the mirror — it brings it to whatever `origin/main` is. The mirror is never trusted as a working tree; it's a reproducible snapshot of upstream.

After this, capture:

- `MIRROR_HEAD` = `git -C <mirror-path> rev-parse HEAD` (commit SHA at the mirror)
- `MIRROR_VERSION` = the latest `## v...` heading in `<mirror-path>/CHANGELOG.md`

### Phase 4 — Scan the instance

Walk the instance's repository (cwd from which the skill was invoked, expected to be the orchestrator instance root) and collect files with `origin: maestro` in their frontmatter. The scan should cover:

- `CLAUDE.md` (root)
- `.claude/skills/*/SKILL.md`
- `.claude/agents/*.md`

For each match, read the file's `maestro_version` value. Build a list:

```
[
  { path: "CLAUDE.md",                       version: "v2026.04.29.1" },
  { path: ".claude/skills/setup/SKILL.md",   version: "v2026.04.30.1" },
  { path: ".claude/agents/librarian.md",     version: "v2026.04.30.1" },
  ...
]
```

If `maestro_version` is missing in a file that has `origin: maestro`, treat it as the baseline `v2026.04.29.1` (the snapshot version before versioning was introduced).

### Phase 5 — Show changelog delta

Read `<mirror-path>/CHANGELOG.md`. The CHANGELOG is ordered most-recent-first, with each entry headed `## vYYYY.MM.DD.N — YYYY-MM-DD`.

Compute the **lowest** instance `maestro_version` across all scanned files (call it `INSTANCE_FLOOR`). Show the owner all CHANGELOG entries strictly between `INSTANCE_FLOOR` and `MIRROR_VERSION` (inclusive of `MIRROR_VERSION`, exclusive of `INSTANCE_FLOOR`).

Format:

```
🔍 Maestro changelog from your version to upstream:

## v2026.04.30.2 — 2026-04-30
**Theme**: Promote three patterns proven in the Alfred instance into the template.
- (Added) early-morning rule, YAML safety, wikilinks discipline

## v2026.04.30.1 — 2026-04-30
**Theme**: Available apps moves out of CLAUDE.md into preferences.md.
- (Changed) CLAUDE.md, preferences.example.md, add-external-app skill
- (Added) Distribution and modifications section

You are at: v2026.04.29.1 (oldest file in this instance).
Upstream is at: v2026.04.30.2.
```

This is **context** before the diff, not a confirmation prompt yet.

### Phase 6 — Per-file diff and confirmation

For each file in the scan list, compute the diff between the instance's version and the mirror's version of the same file path.

```bash
diff -u <instance-path>/<file> <mirror-path>/<file>
```

Skip files that are byte-identical (already up to date — common when the instance is mostly aligned).

**Frontmatter `tools:` exemption** (per `CLAUDE.md` → "Distribution and modifications"): when comparing skill or agent files, **ignore differences in the `tools:` frontmatter field**. The instance is free to extend that field with its own MCPs/tools, and those changes must survive the sync. Concretely: parse the YAML frontmatter, set `tools:` of the mirror version to match the instance's `tools:` before computing the diff, then proceed as usual on body and other frontmatter keys. If only `tools:` differs, the file is considered identical and skipped.

For each file with a non-empty diff, show:

```
─── <file> ───
Instance version: <maestro_version of instance file>
Mirror version:   <MIRROR_VERSION>

<unified diff, colorized if terminal supports it>

Apply this change?
  [a] apply this file
  [s] skip this file
  [A] apply all remaining files (no further prompts)
  [n] abort the whole sync
```

For files where the owner answers `a` or `A`:

1. Copy the mirror file over the instance file.
2. **Update the `maestro_version` in the file's frontmatter** to `MIRROR_VERSION`. The mirror file already has the correct value — copying preserves it.
3. Append an entry to `private/maestro-sync.log` (create the file if it doesn't exist):

```
2026-04-30T18:42:13Z  v2026.04.29.1 → v2026.04.30.2  CLAUDE.md (applied)
2026-04-30T18:42:13Z  v2026.04.30.1 → v2026.04.30.2  .claude/skills/setup/SKILL.md (skipped by owner)
```

If the owner answers `n` (abort), stop immediately. Files already applied stay applied; files not yet shown are not touched. Log a final entry: `2026-04-30T18:42:13Z  ABORTED by owner after <N> files`.

### Phase 7 — Final summary

After all files are processed (or the owner picked `A`), summarize:

```
✅ Maestro sync complete

Updated:  3 files  (CLAUDE.md, .claude/skills/setup/SKILL.md, .claude/agents/librarian.md)
Skipped:  1 file   (.claude/skills/logbook/SKILL.md — owner declined)
Identical: 4 files (no change in upstream)

Instance now at: v2026.04.30.2

Log: private/maestro-sync.log
```

If everything was identical:

```
✅ Maestro sync — already up to date (v2026.04.30.2)
```

## Self-update

This skill is itself marked `origin: maestro`, so it will appear in its own scan. When upstream releases a new version of `maestro-sync`, the skill applies the new version to itself like any other file. The next invocation will use the updated logic.

There's no special handling for self-update beyond this — the standard flow works because each invocation is a single shot from start to finish, not a long-running daemon.

## Bootstrap notes

**Brand new instance** (instance was just created from the template, never synced before):

- Files already carry the `maestro_version` declared in their frontmatter at template-clone time.
- First run of `maestro-sync` finds the mirror at `<MIRROR_VERSION>`. If the instance was cloned recently from `origin/main`, files match the mirror exactly → sync reports "already up to date".
- If the instance was cloned from an older commit, the diff workflow handles it normally.

**Old instance** (predates the introduction of `origin: maestro` frontmatter, ~before v2026.04.30.1):

- Files have no `maestro_version` (and possibly no `origin: maestro` either). Two recovery options:
  1. **Owner adds the markers manually** to the files they recognize as Maestro-distributed (CLAUDE.md, hub skills, base agents), using `maestro_version: v2026.04.29.1` as the safe baseline. Then runs `maestro-sync`.
  2. **Re-clone the instance scaffold separately and reconcile by hand.** Heavier, but clean.

The skill itself does not auto-mark files — that would risk misclassifying instance customizations as upstream patterns.

## What this skill does NOT do

- Push to upstream. Promotions happen in the primary working tree (`~/Sites/me/maestro/`), not from this skill.
- Edit files in `private/`, `apps/`, or any file without `origin: maestro` marker.
- Resolve conflicts when the owner has hand-edited a file marked `origin: maestro` and upstream also changed it. The diff is shown, the owner decides per file. Hand-editing `origin: maestro` files is discouraged in `CLAUDE.md` → "Distribution and modifications" precisely to avoid this.
- Run silently. Every phase that touches state (mirror reset, file copy, log append) reports to the owner.

## Memory log

Per the "Announce every write" rule, after the sync, insert one memory entry summarizing the run:

```bash
sqlite3 private/memories.db "INSERT INTO log (date, title, description, tags, type) VALUES (date('now'), 'Maestro sync: <FROM_VERSION> → <TO_VERSION> (<N> files updated)', '<list of updated files, comma-separated>. Skipped: <list>. Log: private/maestro-sync.log.', 'maestro,sync,upstream', 'memory');"
```

Announce:

```
📝 saved: "Maestro sync: <FROM_VERSION> → <TO_VERSION>" [maestro,sync,upstream] (memory)
```

## Failure modes

- **Mirror clone fails (no network, no SSH key)**: stop, report the error, suggest `gh auth status` or checking SSH agent.
- **Working tree has uncommitted changes and owner picks `push` but staging is needed**: refuse silently to `git add -A` (would risk staging files the owner didn't intend); ask the owner to stage manually and re-run.
- **CHANGELOG.md missing or unparseable in the mirror**: warn but continue — files are still diffable, just no high-level context.
- **A file marked `origin: maestro` exists in the instance but not in the mirror** (e.g. an old skill that has since been retired upstream): show this in the summary as "orphan: file is no longer in upstream — keep, archive, or delete by hand?". Do not auto-delete.
