---
origin: maestro
maestro_version: v2026.09.28.3
tags: [howto, backup, sync, privacy, gitignore, symlinks, cloud-drive, orchestrator, maestro-sync, rollback]
description: "How to back up and synchronize your orchestrator safely: what to keep out of git, how to sync across machines via cloud drives, how to symlink external apps, skills and agents, and how template updates reach an instance through the maestro-sync command (mirror and worktree keys, the six verbs, backup sets and rollback) and how the session-start update notice works (cache, interval, env overrides)."
---

# How to handle backups and sync

The orchestrator's repo mixes two very different kinds of content:

- **Code and conventions** (CLAUDE.md, skills, agents, howto): safe to publish, intended to be versioned
- **Private data** (`private/preferences.md`, `private/memories.db`): personal, potentially sensitive, must never end up on a public remote

The default `.gitignore` reflects that split, but every owner has different needs: you may want to sync across machines, pull a skill from a shared repo, or symlink a sub-app that lives elsewhere on your filesystem. This guide covers the common patterns.

## Rule #1 — keep `private/` out of git

The `.gitignore` shipped with the template ignores the whole `private/` folder:

```
private/
```

Do not remove this line unless you are absolutely sure what you're doing. `preferences.md` contains your nick, role, team, integrations: often enough to identify you and your professional context. `memories.db` contains your log of events, tasks, and ideas, which can be even more sensitive.

### What if you want to version a subset?

Sometimes the structure of `preferences.md` is worth sharing (with a colleague, with yourself across machines). Do not push it anywhere public. If you want to version it in a private repository, consider two cleaner alternatives:

- **Keep the main repo public** and store `private/` separately in an encrypted store (e.g., a separate repository managed with [chezmoi](https://www.chezmoi.io/) + age encryption)
- **Make the main repo private** entirely, and keep `private/` tracked, but then the whole orchestrator is non-public

Never mix a public main repo with `private/` tracked.

## Rule #2 — `memories.db` doesn't like being in two places at once

SQLite uses lock files (`.db-wal`, `.db-shm`) while it's open. If two machines open the same db via a synced folder at the same time, you can end up with corruption or lost writes. Mitigations, in order of effectiveness:

- **Use one machine at a time.** If only one Claude Code session is active against `memories.db`, sync tools are happy.
- **Close the session before switching machines.** End the Claude Code process on machine A before opening it on machine B, so the db is quiesced.
- **"Always keep downloaded"** on the folder containing the db (iCloud Drive, Dropbox) to prevent on-demand fetches mid-write.
- **WAL checkpoint** before switching: `sqlite3 private/memories.db "PRAGMA wal_checkpoint(TRUNCATE);"`, which collapses the WAL into the main file and reduces sync conflicts.

If you work on multiple machines often, think of `memories.db` as a workspace file, not a shared resource.

## Syncing the whole orchestrator folder via cloud drive

If you want the same orchestrator available on both your laptop and your desktop, keeping the repo folder inside a synced drive works well:

- **iCloud Drive** (`~/Library/Mobile Documents/com~apple~CloudDocs/...`)
- **Dropbox** (`~/Dropbox/...`)
- **Google Drive** (`~/Google Drive/...`)

Trade-off: the git repo itself is now synced by two systems (git + cloud). It's usually harmless (cloud drives sync the `.git/` folder like any other directory), but:

- If a `git` operation is mid-flight while the cloud tries to sync, you may get transient file-state glitches. Run `git status` again and they usually resolve.
- Cloud conflict copies (`file (conflict from Your Mac).md`) can creep in. Spot them with `find . -name "*conflict*"` periodically.

The cleaner alternative: keep the repo under a normal location (e.g., `~/Code/my-orchestrator/`) and sync only `private/` via the cloud by symlinking it into the drive.

## Keeping an instance up to date

Template changes reach an instance through `/maestro:maestro-sync`: a short conversation in the orchestrator over the plugin's `maestro-sync` command, which does the mechanics and asks nothing itself (`maestro-sync --help` lists every verb and exit code). It runs from the instance root only.

### The mirror and the working tree

The sync reads the template from a read-only clone, the mirror, reset to `origin/main` at every run. It lives at `~/.maestro/` unless `private/preferences.md` declares another path under `maestro_mirror_path`. A second key, `maestro_worktree_path`, names the working tree where you develop the template, when you have one: the plan reports its uncommitted files or unpushed commits, and the orchestrator asks whether to push, continue or abort before anything else. Both keys are read in either shape, first match wins, `~` expanded:

```markdown
- **maestro_mirror_path**: ~/.maestro
maestro_worktree_path: ~/Code/maestro
```

The mirror can be neither the instance nor the working tree, and a mirror with local edits is refused.

### The six verbs

- `plan`: refreshes the mirror, checks that the loaded plugin is not behind it (only the plugin's own files count: a release that leaves `plugins/maestro/` and `.claude-plugin/` alone doesn't ask for a plugin update), and writes `private/maestro-sync.plan.json`: the changelog slice from the instance's oldest `maestro_version` to upstream, and one item per thing to do, of kind `update`, `new`, `bin`, `retired`, `register` or `orphan`.
- `apply`: applies items of the last plan, by id (`--items u1,u2`) or by kind (`--kind update`), after the backup set is open; `--from FILE` writes a merged text for one update, `--register KEY=VALUE` answers a missing register key.
- `note`: records in `private/maestro-sync.log` an outcome the conversation decided: skipped, aborted or kept.
- `rollback STAMP`: restores a set, its items in reverse order, then the memory db.
- `update-plugin`: runs `claude plugin marketplace update maestro` then `claude plugin update maestro@maestro`, the way out when `plan` stops with exit 5 for a plugin behind upstream. The conversation offers it; the new plugin loads after a restart of Claude Code, and the sync runs again from the new session.
- `backups`: lists the sets, newest first, with the two versions and the item counts.

### Backup sets and rollback

The first `apply` on a plan creates `private/backups/<stamp>-sync/`, and every later `apply` on the same plan appends to it. The set holds `manifest.json` (written before the first write, rewritten after every item with its outcome), a checked copy of `private/memories.db` under `db/`, and under `files/` every file the run replaces or removes, at its path in the instance. `maestro-sync rollback <stamp>` reads the manifest, puts every file back, removes the files the sync added and copies the db back; the conversation names the command once at the end of a sync. Retention runs after each `apply`: the five newest sets stay whatever their age, older ones go once they are past seven days, and at most twenty stay in any case.

### Loose backups from earlier syncs

Before the command existed, the sync wrote loose copies next to the files it replaced: `private/*.bak.<stamp>` files and `private/retired.bak.<stamp>-listen/` folders. They are not sets: `rollback` does not read them, nothing removes them, and `maestro-sync backups` names them in one line. Delete them by hand once you no longer need them.

### The update notice

The plugin's `SessionStart` hook tells you when the instance is behind the template. In an instance root (never in a satellite, a plain folder or the template repository itself) it compares the `maestro_version` of `CLAUDE.md` with the upstream version cached at `~/.claude/maestro-update-check.json`, a JSON file with `upstream` and `checked_at`, and when upstream is newer it adds one line to the session's context: `Maestro <upstream> is available (this instance is on <local>): run /maestro:maestro-sync.` The line is context, so it comes back after `/clear` and stays until the instance is synced.

The hook never fetches anything itself. When the cache is missing, unreadable or older than 12 hours, it stamps `checked_at` (so two sessions starting together fetch once) and spawns a detached fetcher that reads `https://raw.githubusercontent.com/spleenteo/maestro/main/.version` with a 3-second timeout and a 5-second alarm, then rewrites the cache; on any error the cache stays as it was. The session never waits on the network, and the notice comes from the cache as it stood when the session opened: the first session after a long silence may say nothing, the next one does. The raw GitHub host serves the file from a cache of a few minutes, so a release can take that long to show up.

`maestro-sync plan` and a successful `maestro-sync apply` rewrite the cache with the mirror's top `CHANGELOG.md` version, so an instance you have just synced shows no notice. Three environment variables override the defaults, for tests or a fork: `MAESTRO_VERSION_URL` (the URL the fetcher reads), `MAESTRO_UPDATE_CACHE` (the cache file) and `MAESTRO_UPDATE_INTERVAL` (seconds between fetches, default 43200).

## Backing up `private/`

Since `private/` is not in git, it needs its own backup. Pick one (or combine):

- **Cloud drive**: if the repo lives in iCloud/Dropbox/GDrive, `private/` is already synced.
- **Time Machine** (macOS): covers the whole repo, including `private/`. Simple, default good.
- **chezmoi + age encryption**: track `private/` in a separate encrypted repository managed by chezmoi. Offers cross-machine sync with encrypted-at-rest history. Higher setup cost, higher privacy guarantees.
- **Manual periodic snapshot**: `tar czf private-$(date +%F).tgz private/` to an encrypted external drive or a private cloud bucket.

Restore procedure, in all cases: clone the main repo, put `private/` back where it was, launch Claude Code.

## Claude's own project memory (outside the repo)

Even with `private/` locked down, Claude Code maintains its own per-project data in a folder on your machine, outside your repo:

```
~/.claude/projects/<slugified-project-path>/
```

The slug is derived from the absolute path of the project, with slashes replaced by dashes. For an orchestrator at `/Users/you/Code/my-orchestrator/`, the folder is:

```
~/.claude/projects/-Users-you-Code-my-orchestrator/
```

Inside it Claude keeps session transcripts, an auto-memory system (`memory/MEMORY.md` plus individual memory files), and other state. You don't control what goes there: Claude writes to it as a natural side-effect of running. Even if you're meticulous about not committing personal info, notes Claude took during a session live here too, and they can be just as sensitive as `memories.db` or `preferences.md`.

Practical implications:

- **Treat `~/.claude/projects/<slug>/` as part of "your orchestrator's lived history".** If you want to be able to restore everything (including what Claude learned across sessions), include this folder in your backup strategy.
- **Back it up alongside `private/`.** Time Machine and most cloud drives will pick it up from `~/.claude/` automatically; chezmoi can track it like any other dotfile path if you want encrypted history.
- **Be mindful when sharing or publishing your orchestrator.** This folder isn't in the repo, so publishing a public version is safe on that front, but if you copy the whole `~/.claude/` between machines, you're also copying the transcripts.
- **If you move or rename the project folder, the slug changes** and Claude will start fresh at the new path. If you want the history to follow, copy the old `~/.claude/projects/<old-slug>/` to the new slug's location before launching Claude there.

## Registering an external app

If you have a project that lives elsewhere on your filesystem and you want the orchestrator to treat it as a sub-app, **use the `add-external-app` skill**:

```
/add-external-app
```

It asks six questions (path, name, one-line description, trigger keywords, access: read-only or read-write, and an optional notes folder in the vault) and then:

1. Creates the symlink `apps/<name>/` → the target path.
2. Generates a pointer skill at `.claude/skills/<name>/SKILL.md` with a frontmatter `description` rich in trigger phrases: that description is what lets the orchestrator automatically recognize when a request is relevant to this app.
3. Updates the "Available apps" table in `private/preferences.md` (replacing the placeholder row on the first registration, appending afterwards).
4. Logs a memory entry.

The reason for the pointer skill: a symlink in `apps/` alone is invisible to the orchestrator. Skills are the trigger mechanism Claude Code uses at session start; a description like *"Use when the user mentions posts, drafts, publishing, SEO for the blog"* is what actually cues a match.

You should never have to edit `CLAUDE.md` by hand to register an app. Let the skill do it.

### Why symlinks (not submodules)

Symlinks are the right choice when:

- The app has its own independent lifecycle (different owner, different release cycle)
- You work on the app alone, and submodule ceremony adds friction
- The app is already a live workspace on your machine

Use a git submodule instead when you want the reference to be shareable with others cloning the orchestrator repo. Symlinks are local to your machine.

### What the pointer skill looks like

For reference: this is what `add-external-app` generates automatically, so you usually don't write it by hand. Example for a blog project:

```markdown
---
name: blog
description: Personal blog project. Use when the user mentions posts, drafts, publishing, editorial calendar, or SEO for the blog. The project lives in `apps/blog/` (symlinked).
access: read-only
---

# Blog — pointer

The `blog` project is symlinked at `apps/blog/`. Its own `CLAUDE.md` is the source of truth for conventions, tools, and internal routing.

**Access: read-only.** The orchestrator must not modify files inside this app through the symlink. Reads are allowed for context; any edit requires the owner to open a dedicated Claude Code session inside the app.

For any non-trivial work (drafting a post, scaffolding, deploying), prefer a dedicated Claude Code session inside the app — see the orchestrator's `CLAUDE.md` → "Validation before touching a sub-app".
```

The `access` field is the switch: `read-only` is the safer default (the orchestrator can't accidentally change files in the app through the symlink), `read-write` lets it edit freely. You can flip it later by editing this file.

The skill body is almost empty on purpose. The whole value is in the `description`: trigger-rich, one line, worth iterating on over time if you notice the orchestrator missing matches.

### Removing a registered app

There's no `/remove-external-app` skill yet. To do it by hand: remove the symlink from `apps/`, delete `.claude/skills/<name>/`, and drop the row from the "Available apps" table in `private/preferences.md`. If this becomes a frequent need, promote it to a skill.

## Symlinking third-party skills or agents

The same trick works for skills and agents. A skill you maintain in a shared repo can be pulled into multiple orchestrators via symlink:

```bash
# You have a shared skills collection
ls /Users/you/claude-skills/
# → logbook-enhanced, weekly-digest, basecamp-helper, ...

# Link one into this orchestrator's skills
ln -s /Users/you/claude-skills/logbook-enhanced .claude/skills/logbook-enhanced
```

Pros:

- One canonical version of the skill, used by every orchestrator that links it
- Updates propagate instantly: pull in the source repo, all orchestrators see the change
- No duplication, no drift

Cons:

- Breaks if the target moves or the drive isn't mounted
- Harder to ship as part of a reproducible setup

For agents, the same pattern applies: symlink into `.claude/agents/`. Make sure the agent's file frontmatter declares it consistently across the orchestrators that use it.

## A typical layout

A production-ready setup that balances privacy and portability:

- `~/Code/my-orchestrator/`: main repo, tracked in git (private or public), no `private/` committed
- `~/Code/my-orchestrator/private/`: a symlink to `~/iCloud Drive/orchestrators/my-orchestrator/private/`, synced across your machines
- `~/Code/my-orchestrator/apps/*`: symlinks to other project folders on the machine
- `~/Code/my-orchestrator/.claude/skills/<shared-skill>`: symlink to a shared `claude-skills/` repo for anything reused across orchestrators
- Time Machine + the cloud drive provide two independent backup layers for `private/` and for `~/.claude/projects/<slug>/`

You don't have to start here. Start simple: a plain repo with `private/` inside, backed up by Time Machine (which also catches `~/.claude/` by default), and add sync/symlinks as your setup grows.

## Red flags to watch for

- `git status` showing `private/` files as untracked and staged together → check your `.gitignore`, don't commit accidentally.
- Conflict copies in a cloud-synced repo (`... (conflict from Your Mac).md`) → clean them up promptly and consider working on one machine at a time.
- `memories.db-journal` or `memories.db-wal` files that don't disappear → the db didn't quiesce properly. Run `sqlite3 private/memories.db "PRAGMA wal_checkpoint(TRUNCATE);"`.
- A symlinked skill or app that silently disappears from the orchestrator's awareness → the target folder probably isn't accessible (unmounted drive, deleted source). Fix the target or remove the symlink.

Set up at least one layer before you accumulate real memory in the db.
