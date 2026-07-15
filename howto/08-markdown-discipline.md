---
origin: maestro
maestro_version: v2026.07.15.2
tags: [howto, markdown, frontmatter, yaml, wikilinks, obsidian, discipline, orchestrator]
description: "Full reference for the markdown discipline: frontmatter (tags + description) style, YAML safety in frontmatter values, and Obsidian wikilink rules. The condensed rules live in CLAUDE.md; this file carries the details and examples."
---

# Markdown discipline — frontmatter, YAML safety, wikilinks

This is the **canonical reference** for how the orchestrator (and every skill or agent that writes into the owner's territories) formats markdown files. `CLAUDE.md` carries the condensed rules; this file carries the full rationale, edge cases, and examples.

It is distributed by Maestro (`origin: maestro`): don't edit it in place — changes go through the template and come back via `maestro-sync`.

## Frontmatter — tags and description

Every markdown file created or meaningfully edited carries in its frontmatter:

- **`tags:`** — flow form `[a, b, c]`, multi-dimensional: people, areas, objects, actions. A single file should be retrievable from any relevant angle.
- **`description:`** — one line that says *what the file is about* and *when it's relevant*, in the style of a skill description.

**Why**: `description` lets a reader (the orchestrator, a future agent, the owner) decide whether the file is relevant **without opening it**. With good coverage, an `rg` pass on frontmatter answers "find docs about X" cheaply, in few tokens:

```bash
rg -l 'description:.*keyword' <path> --glob "*.md" -i
rg -l 'tags:.*keyword' <path> --glob "*.md"
```

**Style of `description`**: concise, one sentence, oriented to "what it's for / where it applies", no trivial repetition of the title.

**Tag style**: lowercase, kebab-case for multi-word tags (`team-review`, not `team_review` or `TeamReview`). Prefer reusing existing tags over inventing near-synonyms — a tag used by a single file is dead weight for retrieval (see the librarian's tag-parsimony discipline for the full rules).

**Search discipline**: when looking for information in unfamiliar files, start from frontmatter (`rg` on `description:` or `tags:`) and read bodies only for files that survive the filter. If you encounter a file with missing or vague frontmatter while editing nearby, improve it — that's not out of scope.

## YAML safety in frontmatter values

When a string value (typically `description:`) contains characters that YAML treats as syntactic, the value **must be quoted** with double quotes — otherwise Obsidian (and any YAML parser) silently rejects the frontmatter and falls back to raw-text rendering.

**Trigger characters** to watch for in unquoted scalar values:

- `: ` (colon followed by space) — most common offender. Example: `(14 May 2026): magnetic cube` breaks parsing.
- `# ` (hash followed by space) — interpreted as inline comment start.
- Leading `[`, `{`, `>`, `|`, `*`, `&`, `!`, `%`, `@`, `` ` `` — interpreted as flow/block markers.
- Strings starting with a number followed by other text mid-line.

**Rule**: when in doubt, quote with double quotes. Examples:

```yaml
# Broken — colon-space inside value
description: Frame for project X (14 May 2026): context + edges + alternatives.

# Fixed — value quoted
description: "Frame for project X (14 May 2026): context + edges + alternatives."

# Always safe — no special characters
description: Frame for project X — context, edges, alternatives.
```

`tags: [a, b, c]` flow-form is fine without quotes as long as tag values are simple identifiers (kebab-case ASCII). Wikilink values like `related: ["[[Filename]]", ...]` already require quoting because of the `[[...]]` syntax.

## Linking discipline (Obsidian wikilinks)

When the owner's vault is an **Obsidian vault** (the most common setup) and you write inside it — logbook, TIL, project documents, anything — and the text references **another markdown file in the same vault**, use **Obsidian wikilink syntax** `[[Filename]]`. Don't use a `monospace path/file.md`: it looks like a link but it isn't, it's not navigable, and it doesn't appear in the Obsidian graph.

If the owner's vault is a plain filesystem folder (no Obsidian), this section doesn't apply: use whatever convention the owner has set, or relative paths in monospace.

**Rules** (Obsidian case):

- `[[Filename]]` — bare filename, no path, no `.md` extension. Obsidian resolves names across the vault.
- `[[Filename|alias]]` — when the filename is technical and you want a more readable display in prose.
- Verify the file exists in the vault before linking to it. Wikilinks to non-existent files are still valid in Obsidian (they appear dim and become clickable to create the file), but using them by mistake creates phantom nodes in the graph.

**What stays in monospace** (these are NOT wikilinks):

- Folder paths (e.g. `Projects/Slacky/`)
- Files outside the vault (e.g. `private/memories.db`, `.claude/skills/<name>/SKILL.md`)
- Code identifiers (e.g. `type='task'`, function names)
- Domain names, URLs
- Skill / tool / function names

**Why**: wikilinks are the connective tissue of an Obsidian vault. A document that references three other documents via wikilinks creates four nodes and three edges in the graph, and reading any one of them reveals the others. The same document with `monospace path` references is a dead end — the connections exist only in the prose.
