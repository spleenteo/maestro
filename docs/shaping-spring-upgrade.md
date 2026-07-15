---
shaping: true
tags: [shaping, maestro, claude-md, sync, optimization, spring-upgrade]
description: "Shaping doc for the spring-upgrade audit: slim CLAUDE.md (behavior stays, reference moves out), close the maestro-sync new-file delivery gap, groundwork for the future SQLite upgrade. Decisions taken via grill session on 2026-07-15."
---

# Spring upgrade — Shaping

> **Status: 🔨 in progress.** Release A implemented on branch `spring-upgrade` (this session, 2026-07-15). Release B planned, not yet started. Release C (SQLite) deliberately out of scope — see "Deferred".

Audit of the Maestro template with two goals: make `CLAUDE.md` lighter and better-structured (it is 489 lines / ~31KB, loaded at every session start in every instance), and close distribution gaps in `maestro-sync` — all without touching the two-layer contract (distributed `origin: maestro` files identical everywhere; personalizations only in `private/preferences.md`, agents, task channel).

## Context — what the audit found

Numbers at audit time (2026-07-15, template at `v2026.05.28.1`):

- `CLAUDE.md`: 489 lines / ~31KB (~7–8k tokens resident in every session of every instance). Roughly **40–45% is reference material, not behavior**: the full `bin/mem` command reference (~110 lines), a SQL schema block self-declared "reference only", YAML-safety examples, wikilink discipline (~80 lines combined).
- `bin/mem`: 648 lines of Python, stdlib-only, no tests. `--help` exists per subcommand but several flags lack help text (`--date` doesn't document relative dates or the early-morning rule).
- `maestro-sync` scans **the instance only**: a file that exists upstream but not in the instance is invisible to the sync. Known symptoms: `bin/mem` requires a documented manual copy (changelog v2026.05.23.1); `howto/07` never reached pre-existing instances.
- `howto/*.md` carry no `origin: maestro` marker → out of sync scope entirely.
- README drift: claims roster is "empty at install" (template ships `librarian` + `scheduler` active), claims "four practical guides" (there are seven), guide list stops at 05.
- The origin repo itself matches the "fresh clone pre-setup" filesystem signature (`memories.db.template` present, no `private/`), so the session-start rule would nominally trigger `setup` here.

## Decisions (grill session, 2026-07-15)

| # | Question | Decision |
|---|----------|----------|
| 1 | Primary optimization goal | **Balance** of behavioral adherence, token cost, sync maintainability — case by case |
| 2 | Extraction mechanism | **Pointer + canonical source**: compact `bin/mem` cheatsheet inline, full reference delegated to `bin/mem --help`; markdown discipline (YAML safety, wikilinks, frontmatter details) moves to a new `origin: maestro` reference file; SQL schema block dropped |
| 3 | Aggressiveness on behavioral sections | **Extraction + moderate compression**: no rule lost, less prose; target ~250 lines |
| 4 | Origin-repo vs fresh-instance ambiguity | **Leave as is** — no guard, no marker file; context judgment suffices |
| 5 | Delivery of new distributed files | **Reverse scan in maestro-sync**: after the instance scan, scan the mirror for `origin: maestro` files the instance lacks and propose them. Howto marking deferred |
| 6 | Release sequencing | **Two releases**: A ships the reverse scan first, B ships the CLAUDE.md refactor + new file. Avoids the broken-pointer window (old sync logic can't deliver the new file in the same run that slims CLAUDE.md) |
| 7 | `bin/mem` scope this round | **Only `--help` enrichment** (in B), since `--help` becomes the canonical reference. Tests and schema work belong to the SQLite round, tests first |
| 8 | Session deliverable | Shaping doc + Release A implemented now; Release B in a dedicated session |

## Release A — sync delivery (v2026.07.15.1)

- **`maestro-sync` reverse scan**: new step after the instance scan — walk the mirror for `*.md` files with `origin: maestro` whose path doesn't exist in the instance; propose each as a *new file* in the per-file confirmation flow (same `a/s/A/n` prompt; show content instead of diff). Phase 7 summary gains an `Added:` line. Declined files are re-proposed at the next sync (owner can keep declining).
- **Memory log alignment**: the post-sync memory entry uses `bin/mem save` when the CLI is present, falling back to raw `sqlite3` otherwise.
- **README drift fixes**: roster ships with `librarian` + `scheduler`; seven howto guides listed; shipped skills/agents list aligned to reality.
- `maestro_version` bump on `.claude/skills/maestro-sync/SKILL.md`; CHANGELOG entry.

## Release B — CLAUDE.md refactor (planned)

Section-by-section triage agreed:

| Section | Fate |
|---------|------|
| Session start | Keep; compress step 4 (warm channel) |
| Identity / Role / Tone / Repo structure / Available apps / Routing | Keep; light tightening |
| Hub skills | Keep; one line per skill (full descriptions already live in each SKILL.md) |
| Delegation and roster | Keep; compress prose |
| Validation before touching a sub-app | Keep **all** rules; compress ~60→~35 lines |
| Handoff / No-app requests / Permissions | Keep; minor tightening |
| File territories | Keep; trim examples |
| Frontmatter and search discipline | Keep core rules; **YAML safety → extracted** |
| Linking discipline (wikilinks) | **Extracted**; 3-line rule + pointer stays |
| Memory — triggers, announce rule, early-morning rule | Keep, compressed (behavioral heart) |
| Memory — SQL schema block | **Dropped** (redundant with `memories.db.template`) |
| Memory — commands & reports | **~12-line cheatsheet** + pointer to `bin/mem --help` |
| Preferences evolution | Keep all three tiers; compress ~70→~35 lines |
| Basecamp / Distribution and modifications | Keep |

Plus:

- **New reference file** carrying the extracted markdown discipline (YAML safety, wikilinks, frontmatter style), marked `origin: maestro` + `maestro_version` so the reverse scan delivers it. Proposed location: `howto/08-markdown-discipline.md` (first marked howto; sets the precedent, does not force marking the others). Writing skills/agents (logbook, librarian) point to it.
- **`bin/mem --help` enrichment**: argparse help texts for relative dates, early-morning rule, `--bulk` example, marker semantics.
- CHANGELOG entry with migration notes (instances simply sync; those skipping A will need two sync runs, stated explicitly).

Target: `CLAUDE.md` ~250 lines (~-50%), zero rules lost.

## Deferred — Release C and beyond (SQLite round)

Tracked in changelog v2026.05.23.1 roadmap and Alfred ideas #407/#408/#455; explicitly out of scope here:

- Test suite for `bin/mem` (**first step** of the SQLite round, before any schema change)
- FTS5 + indexes + views (relevant past a few thousand rows)
- `sqlite-vec` + `bin/mem similar` semantic search
- MCP server layer (reopens multi-instance isolation, idea #455)
- Extending `maestro-sync` to `bin/*` comment-style frontmatter (would retire the manual-copy note)
- Marking `howto/*.md` with `origin: maestro` (their updates still don't travel)

## Risks

- **Instances that hand-edited `origin: maestro` files**: the B diff will surface conflicts; the per-file confirm flow handles them, but the changelog should warn.
- **Behavioral regressions from compression**: mitigated by "no rule lost" constraint and by reviewing B's diff rule-by-rule against the current file.
- **Reverse scan proposing unwanted agents**: an instance may not want a future distributed agent; the `s` (skip) answer covers it, at the cost of re-proposal each sync. Accepted.
