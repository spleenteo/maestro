---
origin: maestro
maestro_version: v2026.04.30.1
name: add-external-app
description: Register an external project as a sub-app of this orchestrator. Creates a symlink in `apps/<name>/`, generates a pointer skill at `.claude/skills/<name>/` with a discoverable description, optionally attaches a notes territory in the owner's vault, and updates the "Available apps" section in `private/preferences.md`. Use when the owner asks to add, register, link, hook up, connect, or integrate an external app/project/repo.
---

# Add external app

This skill registers an external project as a sub-app of the orchestrator, without the owner having to touch `preferences.md` or symlinks by hand. It performs three actions in sequence:

1. Creates a symlink `apps/<name>/` pointing at the external project.
2. Generates a **pointer skill** at `.claude/skills/<name>/SKILL.md` — nearly empty body, rich `description` in frontmatter. The description is what lets the orchestrator automatically recognize when the owner's request is relevant to this app.
3. Updates the "Available apps" section in `private/preferences.md` with a new row.

## When this skill runs

Invoke it when the owner says something like:

- *"I have a project at `~/Sites/me/my-blog`, add it as a sub-app"*
- *"Register ACME's dashboard as an external app"*
- *"Hook up my Notion export repo"*
- *"Connect the portfolio site"*

## Q&A flow

Ask one question per turn, in the owner's default language (from preferences). Show progress as `N/6`.

### Question 1/6 — Path

> `1/6` — Where does the project live on disk? Give me the absolute path (or a `~`-relative path).

Validate: the path must exist and be a directory. If it's a file or doesn't exist, stop and ask again.

### Question 2/6 — Name

> `2/6` — What name should I use for this app? I'll use it for the symlink (`apps/<name>/`) and for the pointer skill. Keep it short, lowercase, kebab-case (e.g. `blog`, `portfolio`, `acme-dashboard`).

Validate:

- Not empty, lowercase letters + digits + dashes only
- Not already used in `apps/` or `.claude/skills/` — if it is, explain the clash and ask for a different name
- Not a reserved name like `setup`, `logbook`, `add-external-app`, `hr`, `data`, `.disabled`

### Question 3/6 — One-line description

> `3/6` — In one sentence, what is this app about? (It'll show up in the "Available apps" section of `preferences.md` and in the pointer skill description.)

Example: *"Personal blog built with Astro, Markdown-first content pipeline."*

### Question 4/6 — Trigger phrases

> `4/6` — What kinds of things should make me think of this app? Give me a few keywords or short phrases the orchestrator should use as triggers. (E.g. for a blog: "posts, drafts, publishing, editorial calendar, SEO". For a CRM: "contacts, deals, pipeline, outreach".)

Collect a comma-separated list. Keep it generous — false positives are cheap, missed matches are expensive.

### Question 5/6 — Access: read-only or read-write

> `5/6` — Should I be able to **write** into this app through the symlink, or is it **read-only** for me?
>
> - **read-only** (safer default): I can read files inside to gather context, but I won't modify anything there. For edits, you'll open a dedicated Claude Code session inside the app.
> - **read-write**: I can edit files inside the app directly, respecting the usual "Validation before touching a sub-app" check for larger work.

Accept only `read-only` or `read-write`. If the owner is unsure, recommend `read-only` as the safer default; they can change it later by editing the pointer skill's frontmatter.

The choice is saved in the pointer skill's frontmatter as `access: <value>` and stated explicitly in the body. The orchestrator reads it before any write inside `apps/<name>/` (see `CLAUDE.md` → "Validation before touching a sub-app").

### Question 6/6 — Notes territory (independent from access)

> `6/6` — Is there a directory in your vault where I should write notes, drafts, or reference material **about** this app? Give me an absolute path (or `~`-relative). Leave blank if you don't want a dedicated spot.
>
> Tip: pick a subfolder of one of your declared territories (`logbook_path`, `til_path`, `documents_path`) so the standard frontmatter discipline applies naturally. E.g. `<documents_path>/projects/<name>/`.

This question is **independent from the `access` answer above**: `access` governs writes *inside* the symlinked project, while `notes_dir` governs where you write notes *about* the project, in the owner's own territories. A read-only app can perfectly well have a notes territory in the vault — that's in fact a common setup (no edits to third-party code, but plenty of notes the owner wants to keep).

Validate:

- **Blank** → no notes territory for this app. Skip the `notes_dir:` frontmatter key and the "Notes territory" paragraph in the pointer skill body.
- **Provided** → resolve `~` to the owner's home. Must be an **absolute** path. Existence is not required — the directory may be created later.
- If the path falls **outside** the three declared territories (`logbook_path`, `til_path`, `documents_path` from preferences), warn the owner explicitly: *"this will declare a new write territory dedicated to this app — ok?"* and require a yes before accepting.

If a path is provided, save it into the pointer skill frontmatter as `notes_dir: <absolute-path>`, and include the "Notes territory" paragraph in the body (see Step 2).

## Confirmation

Recap the answers and ask for confirmation before acting. Example:

> I'll create:
> - Symlink: `apps/blog/` → `/Users/you/Sites/me/my-blog`
> - Pointer skill: `.claude/skills/blog/SKILL.md` with the description and triggers above (access: `read-only`)
> - Notes territory: `/Users/you/.../Projects/Blog/` (I'll write notes about this app there, with standard frontmatter)
> - A new row in `private/preferences.md` → "Available apps" section
>
> Proceed?

Omit the "Notes territory" line if the owner left Q6 blank.

## Actions

### Step 1 — Create the symlink

```bash
ln -s "<absolute-path>" "apps/<name>"
```

If `apps/` doesn't exist yet, `mkdir -p apps` first.

Announce:

```
🔗 symlink created: apps/<name> → <absolute-path>
```

### Step 2 — Create the pointer skill

Write `.claude/skills/<name>/SKILL.md` with this content (substitute `<name>`, `<description>`, `<triggers>`, `<access>`, and — only if provided at Q6 — `<notes_dir>`):

```markdown
---
name: <name>
description: <one-line description>. Use when the user mentions <triggers>. The project itself lives in `apps/<name>/` (symlinked).
access: <read-only | read-write>
notes_dir: <absolute-path>   # OMIT THIS LINE ENTIRELY if Q6 was blank
---

# <Name> — pointer

The `<name>` project is symlinked at `apps/<name>/`. Its own `CLAUDE.md` (if present) is the source of truth for conventions, tools, and internal routing inside the app.

**Access: <read-only | read-write>.** <one of the two sentences below>

- For read-only: *The orchestrator must not modify files inside this app through the symlink. Reads are allowed for context; any edit requires the owner to open a dedicated Claude Code session inside the app.*
- For read-write: *The orchestrator may edit files inside this app, respecting the "Validation before touching a sub-app" check in the root `CLAUDE.md`.*

## Notes territory

<INCLUDE THIS WHOLE SECTION ONLY IF notes_dir IS SET; OMIT OTHERWISE>

Notes, drafts, and reference material *about* this app are written at `<notes_dir>`. This is separate from the app's own files (which live under `apps/<name>/`) and is governed by the owner's standard territory rules.

Every markdown file created or meaningfully edited in that directory must carry the standard frontmatter — `tags: [a, b, c]` (multi-dimensional) and `description: one-line` — per the root `CLAUDE.md` → "Frontmatter and search discipline". Don't skip it, and don't assume inheritance: restate the discipline whenever a new write goes in.

---

For any non-trivial work (scaffolding, long iteration, git operations on the app's remote), prefer a dedicated Claude Code session inside the app — see the orchestrator's `CLAUDE.md` → "Validation before touching a sub-app".
```

(Capitalize `<Name>` in the H1 for readability, e.g. `Blog`, `Acme-dashboard`. Use sentence-case on the description. Pick the matching sentence for the Access paragraph based on the owner's answer. Include or omit the `notes_dir:` frontmatter line and the entire "Notes territory" section as a unit — they travel together.)

Announce:

```
🧩 pointer skill created: .claude/skills/<name>/SKILL.md
```

### Step 3 — Update the "Available apps" section in private/preferences.md

The template ships with a placeholder row `| — | — | No app connected yet | — |` in the "Available apps" section of `private/preferences.md`. On first registration, **replace** that placeholder with the real row. On subsequent registrations, **append** a row to the existing table.

Target row format (the `Access` column lets the owner and the orchestrator see permissions at a glance):

```
| <name> | `apps/<name>` | <one-line description> | <read-only | read-write> |
```

The template ships with a 4-column apps table (Alias, Path, Purpose, Access) and a placeholder row. On first registration, **replace** the placeholder; on subsequent registrations, **append**.

Use the `Edit` tool, not shell, to make a precise string replacement inside `private/preferences.md`.

Announce:

```
✏️ updated preferences.md → Available apps: +<name>
```

### Step 4 — Final summary

Tell the owner the files that changed and the paths to open if they want to verify:

```
Done. You can verify:
- apps/<name> → <absolute-path>
- .claude/skills/<name>/SKILL.md
- private/preferences.md → "Available apps" section
```

If a `notes_dir` was set, add one more line:

```
- Notes territory: <notes_dir>  (I'll write notes about this app here)
```

If the app has its own `CLAUDE.md` inside (`<absolute-path>/CLAUDE.md`), add:

> The app has its own `CLAUDE.md` — I'll read it the next time we work on this project.

Otherwise, offer gently:

> The app doesn't have its own `CLAUDE.md` yet. You might want to create one on site to document its conventions.

## Also log a memory

Per the "Announce every write" rule, after the actions, insert a memory entry:

```bash
sqlite3 private/memories.db "INSERT INTO log (date, title, description, tags, type) VALUES (date('now'), 'Registered external app <name>', 'Symlinked <absolute-path> → apps/<name>, created pointer skill, updated preferences.md Available apps section.', 'app,symlink,setup,<name>', 'memory');"
```

Announce:

```
📝 saved: "Registered external app <name>" [app,symlink,setup,<name>] (memory)
```

## Rules

- **One question per turn**, always with the `N/6` progress indicator.
- **Validate every input** before moving on (path exists, name is valid/unused, description isn't empty, triggers isn't empty, access is one of the two values, notes_dir is blank or a valid absolute path).
- **`access` and `notes_dir` are independent axes** — don't gate Q6 on the answer to Q5. A read-only app can have a notes territory; a read-write app can have no notes territory. Ask both regardless.
- **Announce every write** — symlink, file, CLAUDE.md edit, memory insert. One line each.
- **Never run this skill without owner confirmation** at the summary step.
- **If any action fails mid-flow, roll back** what's been done (rm symlink, rm skill folder, revert CLAUDE.md) and report clearly.
- **Never touch the owner's actual project** (the target of the symlink). This skill only adds references to it from the orchestrator side. The one write territory this skill produces in the owner's vault is the `notes_dir` — and that's only reached via the pointer skill at write time, not by this skill itself.
