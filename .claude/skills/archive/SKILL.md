---
origin: maestro
maestro_version: v2026.10.01.1
name: archive
description: Archive a folder of the owner's vault into a single archive root (`_Archive/` under `vault_path` by default), after a short interview on why it is being closed, and write a closing document that stays as that folder's history. Use when the owner says "archive X", "this project is closed", "move X to the archive", "/archive", or the same in their language (Italian "archivia X", "questo progetto è chiuso"); also when a folder sits in a legacy archive location without its closing document.
tags: [vault, archive, librarian, closure]
---

# Archive

Archiving a vault folder means three things: understand why it is being closed, write a closing document that keeps its meaning, and move it into a single archive where it stays searchable as a snapshot of its time.

## Values from preferences

From `private/preferences.md` → `## File territories`:

- `vault_path`: the vault root. Every path below is relative to it.
- `archive_path`: the archive root, default `<vault_path>/_Archive` when the key is missing. Written below as `<archive>`.
- `off_limits`: folders never archived and never read.

Obsidian or not: the vault is Obsidian when `<vault_path>/.obsidian/` exists. Every step below says what changes for a plain markdown folder.

## Principles

- **One archive.** Each archived folder keeps its name (`<archive>/Garden redesign/`). The original location lives in the frontmatter (`archived_from`), not in the folder tree.
- **Archived and deprecated are two signals.** `status: archived` means a snapshot of a past moment, still worth consulting (a 2026 trip plan stays true for 2026). `deprecated: "true"` means superseded, useless or wrong, and hides the file from default searches. Archiving never applies `deprecated`; when the owner says during the interview that a document is wrong, propose `deprecated` separately, note by note, through the librarian.
- **The why lives in the owner's head.** Documents record what was done, rarely why it stopped. No closing document without the reason in the owner's words.
- **Nothing is lost.** No file is deleted; byte-identical duplicates go to the vault's `.trash/` with the owner's yes. The archive stays in the semantic index: never add it to `.mem-ignore`.
- **Vault content follows the owner's language.** File and field names are fixed and in English (`00 Archived — <Name>.md`, `archive_reason`); the headings of the closing document and the reading callout are written in the owner's default language.

## Flow

### 1. Scope

Identify the folder (or folders) and confirm with the owner in one line: path, number of files. Refuse a folder under `off_limits`. A folder already in a legacy archive location (an older `_Archive/` or `Archive/` inside a project folder, a localised `_Archivio/`) is a migration: same flow, and `archived_from` is the path it had before the legacy archive, recovered from memory (`bin/mem search`), from `related:` or from `private/librarian.log.jsonl`; ask when it cannot be recovered.

### 2. Analysis (librarian)

Delegate to `librarian` with `task=archive-analysis`, the folder path, `vault_path`, `archive_path`, `off_limits` and `obsidian: true|false`. The agent is read-only here and returns: a 5-line summary, decisions with their reasons, living knowledge with proposed destinations, incoming links and path-qualified links, `.canvas` references, assets used only by the folder, basename collisions, existing `status`/`deprecated` values, and the gaps phrased as questions.

Also search `memories.db` (`bin/mem search "<name>" --limit 0` and `bin/mem search "<name>" --semantic`): memory rows often hold decisions the documents lack.

### 3. Interview

One round of questions in chat, four at most, aimed at the gaps. The first is always the reason:

1. **Why are you archiving it?** (e.g. "the client moved the work in-house", "we sold the car, the maintenance log no longer matters")
2. What would you want to find again in a year, if you came back to it?
3. Did anything turn out to be wrong? (the only case where `deprecated` is considered, note by note)
4. One specific question on the largest gap the analysis found.

In the same message, propose the notes leaving the archive (from step 2) with their destinations. Wait for the answers. Short answers are fine: the reason is quoted in the owner's own words. An unanswered question is written as "not documented" in the closing document, never guessed.

### 4. Living notes out of the archive

Move the notes the owner approved to the agreed destination, with their embedded assets, following that territory's conventions (`til_path`, `documents_path`). These notes get no archive fields; drop tags that only made sense inside the project.

### 5. Closing document

File: `<archive>/<Name>/00 Archived — <Name>.md`. The `00` prefix puts it first in the folder, "Archived" makes it recognisable in a file list, and the project name keeps the basename unique (no ambiguous `[[README]]`). Writing register domain: synthesis. Template (headings shown in English; write them in the owner's language):

```markdown
---
tags: [archive, closure, <area>, <people>, <objects>]
description: "Closing document of <Name>: <reason in one line>; entry point to the archive"
type: closure
status: archived
archived: YYYY-MM-DD
archived_from: "<source folder, relative to the vault root>"
archive_reason: "<reason in one line, from the owner's words>"
related: ["[[...]]"]
---

# <Name>: archived

## Why it is archived
<The owner's reason, quoted in their words with only typos fixed. Date.>

## How it went
<What the project was, when, how it ended. 3-6 lines.>

## Decisions and why
<Table or list: date, decision, reason. Includes what was discarded.>

## What stays valid
<Facts, conclusions, contacts, procedures that do not expire. Say so if nothing.>

## What expired
<Deadlines, prices, versions, conditions that no longer hold, with the date they expired.>

## Out of the archive
<Notes moved elsewhere, as links. Omit the section if none.>

## Index
<A link to every note in the folder, one line each.>
```

Links are `[[wikilinks]]` in Obsidian and relative markdown links (`[Title](file.md)`) in a plain folder; `related:` is omitted in a plain folder. Before writing: the `writing-register` post-pass (form only; the owner's quoted words stay verbatim). Links only to verified targets.

### 6. Move

- Create `<archive>` if missing. If `<archive>/<Name>/` already exists, use `<Name> (YYYY)`.
- When the interview shows the folder name is wrong (e.g. "Move" for what turned out to be a renovation), rename it inside the archive and tell the owner; `archived_from` keeps the original path.
- Byte-identical duplicates of files living elsewhere (`diff -rq`, or a diff of the body without frontmatter and callouts): do not archive them as new material; propose moving them to the vault's `.trash/`, and list them in the closing document's index with the path of the living copy.
- Before moving, resolve the basename collisions from step 2: generic names (`Logs`, `Documentation`, `README`) get the project prefix (`<Name> — Logs`) through the librarian's rename with a wikilink sweep.
- Move with `mv` (a shell move does not update links the way Obsidian does). Then fix the `"file"` paths in `.canvas` JSON and the path-qualified wikilinks or embeds found in step 2, inside and outside the folder. Bare-basename wikilinks resolve by themselves. In a plain folder, fix every relative link that crosses the folder boundary.
- Assets outside the folder referenced only by it move to `<archive>/<Name>/assets/`, with their references fixed.
- If the source folder (or the legacy archive location) is left empty, remove it; never remove a non-empty folder.

### 7. Archive fields and reading callout

Delegate to `librarian` with `task=archive-fields`, the moved folder, `vault_path`, the closing document's name and `obsidian: true|false`: it writes `status`, `archived`, `archived_from` and `archive_note` on every `.md` except the closing document, and logs each change in `private/librarian.log.jsonl`. An old `deprecated` used as an archive marker (not as "wrong") is converted only with the owner's explicit yes for that folder: ask, then pass `convert_deprecated: true`.

Then the orchestrator (body edits are outside the librarian's mandate) puts the reading callout at the top of every archived `.md` body, right under the frontmatter, in the owner's language. Obsidian:

```markdown
> [!note] 📦 Archive
> Read [[00 Archived — <Name>]] first: this note is historical detail.
```

A plain folder gets a single quoted line:

```markdown
> 📦 Archived: read [00 Archived — <Name>](00%20Archived%20%E2%80%94%20<Name>.md) first; this note is historical detail.
```

An optional extra line points to the living note that took the project's place. An older archive callout at the top is replaced, never duplicated. Excluded: the closing document, files under dot-folders, kanban boards (`kanban-plugin` in the frontmatter), which the plugin might stop parsing.

### 8. Index

Obsidian: `<archive>/00 Archive index.base` (Obsidian Bases) reads the frontmatter and updates itself. Create it when missing, with the property display names in the owner's language; nothing to edit per archiving, as long as the closing document has `type: closure` and `archive_reason`.

```yaml
filters:
  and:
    - file.inFolder("_Archive")
properties:
  note.archived:
    displayName: Archived
  note.archived_from:
    displayName: Origin
  note.archive_reason:
    displayName: Reason
  note.archive_note:
    displayName: Closing document
  file.folder:
    displayName: Folder
views:
  - type: table
    name: Archived
    filters:
      and:
        - note.type == "closure"
    order: [file.name, archived, archived_from, archive_reason]
    sort:
      - property: archived
        direction: DESC
  - type: table
    name: All archive
    filters:
      and:
        - file.ext == "md"
    groupBy:
      property: file.folder
      direction: ASC
    order: [file.name, archive_note, description]
```

`file.inFolder` takes the archive root relative to the vault: change `"_Archive"` when `archive_path` differs.

Plain folder: `<archive>/00 Archive index.md`, a markdown table (closing document as a link, `archived`, `archived_from`, `archive_reason`), newest first. Regenerate it at every archiving from `rg -l '^type: closure' "<archive>"`; it carries `tags` and `description` like every file.

### 9. Memory

- One `memory` row: `bin/mem save "<Name> archived with closing document" -t archive,<project tags> -d "<source path> → <new path>; reason: <owner's words>; moved out: <notes>; closing document: <path>"`.
- Existing rows about the project stay untouched. If they are many and risk polluting answers about the present, propose adding the `archive` tag to them.
- Run `bin/mem embed` at the end (it reads the indexed roots from `MEM_VAULT_ROOTS`; never narrow it with a single `--root`, which drops the chunks of the other roots), so the semantic index drops the old paths. Exit code 3 (layer absent) or 4 (a satellite session) means skip it silently.

### 10. Report

Tell the owner in a few lines: where the folder is now, the closing document (full path), the notes moved out, the links fixed, the memory writes.

## Reading the archive

Reading order: the index first (`00 Archive index.base` or `.md`; for an agent, `rg -l '^type: closure' "<archive>"`), then the folder's `00 Archived — <Name>`, the rest only when the detail is needed.

When the orchestrator or the librarian report vault results, the order is: living notes, then closing documents labelled `📦 archive` with their `archive_reason`, then the rest of the archive with the same label. A question about the past ("what did we decide about the garden") starts from the closing document. Files with `deprecated` stay excluded unless explicitly requested.
