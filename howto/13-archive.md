---
origin: maestro
maestro_version: v2026.10.01.1
tags: [howto, archive, vault, librarian, closure, obsidian, frontmatter]
description: "How a vault folder is closed with the archive skill: the interview on why, the closing document, the archive root and its index, the reading callout, the move, and how the librarian tells archived notes from deprecated ones. Reference before archiving or when a search returns archived material."
---

# 13 — Archive

A project ends, its folder stays in the vault, and a year later nobody remembers why it stopped. The `archive` skill closes a folder in one pass: it asks you why, writes a closing document that keeps the decisions, and moves the folder into a single archive where it stays searchable.

Say "archive X", "this project is closed", or `/archive`.

## Where the archive lives

One root for the whole vault: `archive_path` in `private/preferences.md` → `## File territories`, `<vault_path>/_Archive` when the key is missing. Each archived folder keeps its name (`_Archive/Garden redesign/`); the path it came from is written in the frontmatter, so the archive tree stays flat.

Folders listed under `off_limits` in the same block are never archived and never read.

## The flow

1. **Scope.** The orchestrator confirms the folder and its file count.
2. **Analysis.** The librarian reads the folder without writing and returns a short summary, the decisions it found, the notes that hold knowledge worth keeping outside the archive, the links a move would break, the assets only this folder uses, and the gaps: what the documents never say.
3. **Interview.** At most four questions, in one message. The first is always "why are you archiving it?", and your answer goes into the closing document in your words. A question you leave unanswered is written as "not documented", never guessed.
4. **Living notes out.** The notes you approve (a guide, a reusable prompt, a procedure still in use) move to your TIL or documents territory before the archiving.
5. **Closing document.** `00 Archived — <Name>.md`, first in the folder.
6. **Move.** A shell `mv`, then the links are repaired.
7. **Archive fields and reading callout** on every note of the folder.
8. **Index**, which updates itself in Obsidian.
9. **Memory.** One `memory` row for the archiving, and a refresh of the semantic index.

## The closing document

The entry point to the folder's history. Its name starts with `00` so it sorts first, and carries the project name so its basename is unique in the vault. Frontmatter:

```yaml
type: closure
status: archived
archived: 2026-10-01
archived_from: "Projects/Garden redesign"
archive_reason: "Postponed the redesign; the budget went to the roof"
```

Sections, with headings written in your language: why it is archived, how it went, decisions and why, what stays valid, what expired, out of the archive, index. File and field names stay in English in every instance, so agents find them the same way everywhere.

## Every other note

The librarian adds four fields to each note of the archived folder:

```yaml
status: archived
archived: 2026-10-01
archived_from: "Projects/Garden redesign"
archive_note: "[[00 Archived — Garden redesign]]"
```

The orchestrator then puts a reading callout at the top of the body, pointing to the closing document. Kanban boards are skipped, since the plugin might stop parsing them.

## Reading the archive

Index first, then the closing document, then the detail only when it is needed. In Obsidian the index is `_Archive/00 Archive index.base`, a Bases file that lists every closing document with its date, origin and reason, and every archived note grouped by folder. It needs no edits after an archiving.

Searches keep archived material and put it last: living notes first, then closing documents labelled `📦 archive` with their reason, then the rest of the archive. A question about the past ("what did we decide about the garden") starts from the closing document.

## Archived or deprecated

| | `status: archived` | `deprecated: "true"` |
|---|---|---|
| Means | a snapshot of a past moment, still true for that moment | superseded, useless or wrong |
| In searches | included, after the living notes | excluded unless you ask, then flagged `⚠️ deprecated` |
| As a link target | the closing document, yes | never |
| Who sets it | the `archive` skill | the librarian proposes, you confirm |

Archiving never marks a note deprecated. If during the interview you say a document was wrong, the orchestrator proposes `deprecated` for that note alone. A folder that used `deprecated` as its archive marker in the past is converted to `status: archived` only with your yes for that folder.

## Without Obsidian

A vault that is a plain markdown folder (no `.obsidian/` at its root) gets the same flow with three differences:

- the index is `00 Archive index.md`, a markdown table the skill regenerates at every archiving;
- the reading callout is a single quoted line with a relative markdown link;
- links in the closing document are relative markdown links, and `archive_note` holds the closing document's filename.

## The move, in detail

- A shell move does not update links the way Obsidian does: after `mv`, the skill fixes the `"file"` paths inside `.canvas` files and every wikilink written with a path. Wikilinks by bare name resolve by themselves.
- Generic names (`Logs`, `README`) get the project prefix before the move, with every link to them updated, so the vault never holds two `[[Logs]]`.
- Assets used only by the folder move with it, into `assets/`.
- Byte-identical copies of notes that live elsewhere go to the vault's `.trash/`, with your yes, and the index names the living copy.
- An empty source folder is removed; a non-empty one never is.
- A folder already sitting in an older archive location (`Projects/_Archive/`, `_Archivio/`) migrates through the same flow.

## Memory and the semantic index

One `memory` row records the archiving: old and new path, the reason, the notes moved out. Existing rows about the project stay as they are. At the end the skill runs `bin/mem embed`, which re-reads every indexed root, so the semantic index forgets the old paths; the archive root is never listed in `.mem-ignore`.
