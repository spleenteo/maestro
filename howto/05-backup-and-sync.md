---
tags: [howto, backup, sync, privacy, gitignore, symlinks, cloud-drive, orchestrator]
description: How to back up and synchronize your orchestrator safely — what to keep out of git, how to sync across machines via cloud drives, and how to symlink external apps, skills, and agents.
---

# How to handle backups and sync

The orchestrator's repo mixes two very different kinds of content:

- **Code and conventions** (CLAUDE.md, skills, agents, howto) — safe to publish, intended to be versioned
- **Private data** (`private/preferences.md`, `private/memories.db`) — personal, potentially sensitive, must **never** end up on a public remote

The default `.gitignore` reflects that split, but every owner has different needs: you may want to sync across machines, pull a skill from a shared repo, or symlink a sub-app that lives elsewhere on your filesystem. This guide covers the common patterns.

## Rule #1 — keep `private/` out of git

The `.gitignore` shipped with the template ignores the whole `private/` folder:

```
private/
```

Do not remove this line unless you are absolutely sure what you're doing. `preferences.md` contains your nick, role, team, integrations — often enough to identify you and your professional context. `memories.db` contains your log of events, tasks, and ideas, which can be even more sensitive.

### What if you want to version a subset?

Sometimes the structure of `preferences.md` is worth sharing (with a colleague, with yourself across machines). Do not push it anywhere public. If you want to version it in a private repository, consider two cleaner alternatives:

- **Keep the main repo public** and store `private/` separately in an encrypted store (e.g., a dotfiles repo with [chezmoi](https://www.chezmoi.io/) + age encryption)
- **Make the main repo private** entirely, and keep `private/` tracked — but then the whole orchestrator is non-public

Never mix a public main repo with `private/` tracked.

## Rule #2 — `memories.db` doesn't like being in two places at once

SQLite uses lock files (`.db-wal`, `.db-shm`) while it's open. If two machines open the same db via a synced folder at the same time, you can end up with corruption or lost writes. Mitigations, in order of effectiveness:

- **Use one machine at a time.** If only one Claude Code session is active against `memories.db`, sync tools are happy.
- **Close the session before switching machines.** End the Claude Code process on machine A before opening it on machine B, so the db is quiesced.
- **"Always keep downloaded"** on the folder containing the db (iCloud Drive, Dropbox) to prevent on-demand fetches mid-write.
- **WAL checkpoint** before switching: `sqlite3 private/memories.db "PRAGMA wal_checkpoint(TRUNCATE);"` — collapses the WAL into the main file, reducing sync conflicts.

If you work on multiple machines often, think of `memories.db` as a workspace file, not a shared resource.

## Syncing the whole orchestrator folder via cloud drive

If you want the same orchestrator available on both your laptop and your desktop, keeping the repo folder inside a synced drive works well:

- **iCloud Drive** (`~/Library/Mobile Documents/com~apple~CloudDocs/...`)
- **Dropbox** (`~/Dropbox/...`)
- **Google Drive** (`~/Google Drive/...`)

Trade-off: the git repo itself is now synced by two systems (git + cloud). It's usually harmless — cloud drives sync the `.git/` folder like any other directory — but:

- If a `git` operation is mid-flight while the cloud tries to sync, you may get transient file-state glitches. Run `git status` again and they usually resolve.
- Cloud conflict copies (`file (conflict from Your Mac).md`) can creep in. Spot them with `find . -name "*conflict*"` periodically.

The cleaner alternative: keep the repo under a normal location (e.g., `~/Sites/me/my-orchestrator/`) and sync **only** `private/` via the cloud by symlinking it into the drive.

## Backing up `private/`

Since `private/` is not in git, it needs its own backup. Pick one (or combine):

- **Cloud drive** — if the repo lives in iCloud/Dropbox/GDrive, `private/` is already synced.
- **Time Machine** (macOS) — covers the whole repo, including `private/`. Simple, default good.
- **chezmoi + age encryption** — track `private/` in a separate encrypted dotfiles repo. Offers cross-machine sync with encrypted-at-rest history. Higher setup cost, higher privacy guarantees.
- **Manual periodic snapshot** — `tar czf private-$(date +%F).tgz private/` to an encrypted external drive or a private cloud bucket.

Restore procedure, in all cases: clone the main repo, put `private/` back where it was, launch Claude Code.

## Claude's own project memory (outside the repo)

Even with `private/` locked down, **Claude Code maintains its own per-project data** in a folder on your machine, outside your repo:

```
~/.claude/projects/<slugified-project-path>/
```

The slug is derived from the absolute path of the project, with slashes replaced by dashes. For an orchestrator at `/Users/you/Sites/me/my-orchestrator/`, the folder is:

```
~/.claude/projects/-Users-you-Sites-me-my-orchestrator/
```

Inside it Claude keeps session transcripts, an auto-memory system (`memory/MEMORY.md` plus individual memory files), and other state. You don't control what goes there — Claude writes to it as a natural side-effect of running. Even if you're meticulous about not committing personal info, notes Claude took during a session live here too, and they can be just as sensitive as `memories.db` or `preferences.md`.

Practical implications:

- **Treat `~/.claude/projects/<slug>/` as part of "your orchestrator's lived history".** If you want to be able to restore everything — including what Claude learned across sessions — include this folder in your backup strategy.
- **Back it up alongside `private/`.** Time Machine and most cloud drives will pick it up from `~/.claude/` automatically; chezmoi can track it like any other dotfile path if you want encrypted history.
- **Be mindful when sharing or publishing your orchestrator.** This folder isn't in the repo, so publishing a public version is safe on that front — but if you copy the whole `~/.claude/` between machines, you're also copying the transcripts.
- **If you move or rename the project folder, the slug changes** and Claude will start fresh at the new path. If you want the history to follow, copy the old `~/.claude/projects/<old-slug>/` to the new slug's location before launching Claude there.

## Registering an external app

If you have a project that lives elsewhere on your filesystem and you want the orchestrator to treat it as a sub-app, **use the `add-external-app` skill**:

```
/add-external-app
```

It asks five questions (path, name, one-line description, trigger keywords, and access: read-only or read-write) and then:

1. Creates the symlink `apps/<name>/` → the target path.
2. Generates a **pointer skill** at `.claude/skills/<name>/SKILL.md` with a frontmatter `description` rich in trigger phrases — that description is what lets the orchestrator automatically recognize when a request is relevant to this app.
3. Updates the "Available apps" table in `CLAUDE.md` (replacing the placeholder row on the first registration, appending afterwards).
4. Logs a memory entry.

The reason for the pointer skill: **a symlink in `apps/` alone is invisible to the orchestrator**. Skills are the trigger mechanism Claude Code uses at session start; a description like *"Use when the user mentions posts, drafts, publishing, SEO for the blog"* is what actually cues a match.

You should never have to edit `CLAUDE.md` by hand to register an app. Let the skill do it.

### Why symlinks (not submodules)

Symlinks are the right choice when:

- The app has its own independent lifecycle (different owner, different release cycle)
- You work on the app alone, and submodule ceremony adds friction
- The app is already a live workspace on your machine

Use a git submodule instead when you want the reference to be shareable with others cloning the orchestrator repo. Symlinks are local to your machine.

### What the pointer skill looks like

For reference — this is what `add-external-app` generates automatically, so you usually don't write it by hand. Example for a blog project:

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

The skill body is almost empty on purpose. The whole value is in the `description` — trigger-rich, one line, worth iterating on over time if you notice the orchestrator missing matches.

### Removing a registered app

There's no `/remove-external-app` skill yet. To do it by hand: remove the symlink from `apps/`, delete `.claude/skills/<name>/`, and drop the row from `CLAUDE.md`'s "Available apps" table. If this becomes a frequent need, promote it to a skill.

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
- Updates propagate instantly — pull in the source repo, all orchestrators see the change
- No duplication, no drift

Cons:

- Breaks if the target moves or the drive isn't mounted
- Harder to ship as part of a reproducible setup

For **agents**, the same pattern applies — symlink into `.claude/agents/`. Make sure the agent's file frontmatter declares it consistently across the orchestrators that use it.

## A typical layout

A production-ready setup that balances privacy, portability, and sanity:

- `~/Sites/me/my-orchestrator/` — main repo, tracked in git (private or public), no `private/` committed
- `~/Sites/me/my-orchestrator/private/` — a symlink to `~/iCloud Drive/orchestrators/my-orchestrator/private/`, synced across your machines
- `~/Sites/me/my-orchestrator/apps/*` — symlinks to other project folders on the machine
- `~/Sites/me/my-orchestrator/.claude/skills/<shared-skill>` — symlink to a shared `claude-skills/` repo for anything reused across orchestrators
- Time Machine + the cloud drive provide two independent backup layers for `private/` and for `~/.claude/projects/<slug>/`

You don't have to start here. Start simple — a plain repo with `private/` inside, backed up by Time Machine (which also catches `~/.claude/` by default) — and add sync/symlinks as your setup grows.

## Red flags to watch for

- `git status` showing `private/` files as untracked and staged together → check your `.gitignore`, don't commit accidentally.
- Conflict copies in a cloud-synced repo (`... (conflict from Your Mac).md`) → clean them up promptly and consider working on one machine at a time.
- `memories.db-journal` or `memories.db-wal` files that don't disappear → the db didn't quiesce properly. Run `sqlite3 private/memories.db "PRAGMA wal_checkpoint(TRUNCATE);"`.
- A symlinked skill or app that silently disappears from the orchestrator's awareness → the target folder probably isn't accessible (unmounted drive, deleted source). Fix the target or remove the symlink.

Backups are boring until you need them. Set up at least one layer before you accumulate real memory in the db.
