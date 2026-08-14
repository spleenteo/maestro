---
shaping: true
tags: [shaping, maestro, writing-register, prose, style, humanizer, skills, distribution]
description: "Shaping doc for the writing register: seven prose prohibitions distributed to every instance, a Maestro-owned post-pass skill, and a deterministic checker. Decisions taken via grill session on 2026-08-14."
---

# Writing register — Shaping

> **Status: shaping.** Grill session of 2026-08-14 on branch `feature/humanizer`. Target release `v2026.08.14.1`.

Maestro distributes behavior, and until now that behavior said nothing about the shape of the prose an orchestrator produces. The register fills that gap: seven prohibitions that apply to every text an instance writes for a human reader, plus an optional post-pass on finished text.

## Context

The owner arrived with the seven prohibitions already formulated and one open tension: whether to absorb the content of the external `humanizer` skill into Maestro to avoid depending on a third-party repo.

Facts established before the first decision:

- `blader/humanizer` is MIT, actively maintained (the most recent commit adds a passive-voice rule), and its `SKILL.md` is 559 lines / 27 KB covering 29 patterns. Its process prompts the owner twice and returns three blocks: draft, audit, final version.
- `CLAUDE.md` is 21 KB and loads in full at every session start. Release B of the spring upgrade took it from 489 to 256 lines specifically to cut that cost.
- Skills load lazily. At session start a skill costs one `description` line.
- The seven prohibitions are a strict subset of humanizer's 29 patterns:

  | Prohibition | humanizer pattern |
  |---|---|
  | 1 meta-commentary | #28 signposting, #23 filler |
  | 2 sycophantic concessions | #22 sycophantic tone |
  | 3 negative parallelism | #9 negative parallelisms |
  | 4 em dash as pause | #14 em dash overuse |
  | 5 bold as emphasis | #15 boldface overuse |
  | 6 rhythmic triads | #10 rule of three |
  | 7 judgment as tone | #25 generic positive conclusions, #4 promotional |

- Of the remaining 22, several are unusable here: title case in headings, curly quotes and hyphenated word pairs are English-specific. The `PERSONALITY AND SOUL` section pushes against prohibition 7: it asks for prose with "a pulse", which on a logbook note or a Basecamp comment produces exactly the tone the register bans.

The decisive observation for the opening tension: "avoid an external dependency" and "don't inline 27 KB into an always-loaded file" are compatible. Maestro can ship its own lazy skill.

## Decisions (grill session, 2026-08-14)

| # | Question | Decision |
|---|---|---|
| 1 | Where the post-pass lives | **Maestro-owned skill**, `origin: maestro`, versioned with the template. No dependency on `blader/humanizer`, no session-start token cost |
| 2 | Skill contract | **Seven prohibitions plus an extended net**: vague attributions, promotional language, `-ing` analyses, hedging, filler, false ranges, elegant variation. Seven rules always, wider net when text is delivered |
| 3 | Placement in `CLAUDE.md` | **Standalone `## Writing register` section** after `## Tone`, shaped like `## Markdown discipline`: condensed rules plus a pointer to `howto/10` |
| 4 | Self-application | **No rewrite of existing files.** The 84 em dashes in `CLAUDE.md` stay. Specification files are a different genre, consumed by a model |
| 5 | Perimeter | **In**: vault documents, logbook, posts and comments on external channels, chat replies, internal agent-to-orchestrator reports. **Out**: specification files, `memories.db` titles and descriptions, commit messages, code |
| 6 | Explicit clause | **`librarian`, `scheduler`, `logbook`**, one pointer line each. Agents do not inherit, per the precedent already stated in the markdown discipline section |
| 7 | Threshold | **None.** Every vault document and every external post goes through the pass. Chat replies never do, and stay bound by the seven prohibitions |
| 8 | Fidelity and visibility | **Form only**, content untouchable: no claim added or removed; quotations, code, paths, wikilinks, numbers and proper nouns are off limits. **Silent delivery** |
| 9 | Operational test for rule 7 | **Removal test**: drop the phrase, and if the reader loses nothing it was tone. Judgment requested by the owner is legitimate, with the anchor still required |
| 10 | Verification | **`bin/register-check`**, deterministic, for prohibitions 3, 4, 5 and 6 in Italian and English, with tests |
| 11 | Naming and language | **`writing-register`** for section, guide and skill; `bin/register-check` for the tool. Files in English with bilingual examples |
| 12 | Owner-authored text | **Verbatim, never rewritten.** A flag line before publishing is allowed, the correction is the owner's call |
| 13 | Per-instance override | **`## Writing register` block in preferences**: `suspended: []`, `post_pass: on`. The tool stays preferences-agnostic and receives `--skip` from the skill |
| 14 | Coexistence with `humanizer` | **`writing-register` runs the automatic flow**, `humanizer` stays available on explicit request |

## Two decisions that moved during the session

**Decision 5, on specification files.** A first pass through the perimeter question produced a selection that read "new specification files follow the register, existing ones are grandfathered". On disambiguation the owner confirmed the stricter reading: specification files are outside the register entirely, new or old. `CLAUDE.md`, `SKILL.md` files, agent files and `preferences.md` are consumed by a model, not read as prose.

**Decision 14, on coexistence.** The first answer gave the installed `humanizer` priority over the Maestro skill. Traced through, that choice cancelled four earlier decisions on the owner's own machine, where `humanizer` is installed:

- the fidelity guard of decision 8 does not bind an external skill, and humanizer's canonical example removes a cited Google study, two named interviewees and the Uplevel figures from the text it rewrites;
- silent delivery is impossible, since humanizer's process issues two prompts and returns three blocks;
- `suspended: [4, 6]` would be read by nobody;
- `bin/register-check` would never run.

The owner reversed to the Maestro skill in the automatic flow.

## Alternatives rejected

- **Vendoring humanizer** (fork of `SKILL.md` under Maestro with LICENSE and attribution). Inherits 29 mature patterns, carries English-specific ballast and an upstream that keeps diverging.
- **Inlining the 29 patterns** into `CLAUDE.md` or an always-cited howto. Self-sufficient, and it would undo the compression that release B of the spring upgrade paid for.
- **Depending on the external skill** with a conditional pointer. Zero maintenance, and instance behavior would sit in a third-party repo.
- **Threshold uniform across channels** (the original `~10 lines` from the owner's brief). It left short comments on public channels uncovered, which is where bad prose costs most, since a published comment is hard to retract.
- **Falsifiability test** for rule 7. Sharper than the removal test and it discards legitimate recommendations: "I would not do it" is not falsifiable.
- **Closed list of banned phrases**. No ambiguity on what is listed, no coverage on what is not, and stock phrases regenerate faster than a list gets updated.

## Release manifest (`v2026.08.14.1`)

New:

- `howto/10-writing-register.md`, with a `## Reference` section crediting Wikipedia's "Signs of AI writing" and `blader/humanizer`
- `.claude/skills/writing-register/SKILL.md`
- `bin/register-check` and `tests/test_register_check.py`
- `docs/shaping-writing-register.md` (this file)

Modified, all with a `maestro_version` bump:

- `CLAUDE.md`, new section of roughly 12 lines
- `.claude/agents/librarian.md`, `.claude/agents/scheduler.md`, `.claude/skills/logbook/SKILL.md`, one line each
- `preferences.example.md`, commented block
- `CHANGELOG.md`

## Risks

- **Stylistic prior.** `CLAUDE.md` keeps 84 em dashes used as pauses while stating that they are banned. The file is the strongest style signal in the context of every session, so imitation works against prohibition 4. Accepted knowingly under decision 4; a cleanup release stays available.
- **Cost of the pass.** With no threshold, every logbook entry and every short Basecamp comment loads the skill and runs a rewrite. Expected volume is a handful of invocations per session.
- **Drift on rewrite.** The fidelity guard is stated in the skill, not enforced by a tool. `bin/register-check` verifies that prohibitions are met, not that content survived.
- **False positives in the checker.** Em dashes inside quoted material, tables and code fences must be skipped, and the Italian patterns for prohibition 3 have more variants than the English ones.

## Left out by explicit choice

- `howto/README.md` does not gain the index row for guide 10.
- `README.md` stays at "seven practical guides" and does not list 08, 09 or 10. This drift predates the register: guides 08 and 09 were never added to the README index.
