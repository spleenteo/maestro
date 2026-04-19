---
shaping: true
tags: [shaping, orchestrator, bootstrap, template, spleenteo]
description: Shaping doc for the spleenteo-orchestrator bootstrap repo — a reusable template to scaffold new orchestrator projects, distilled from two reference instances (one personal, one work).
---

# Spleenteo Orchestrator — Shaping

Bootstrap repo to scaffold new orchestrators in a consistent way, distilling the lessons from two reference instances — one for personal life, one for a work domain.

## Context

The pattern was developed across two reference instances (one personal, one for a work domain), and a by-hand playbook was kept. Creating the next orchestrator from scratch is error-prone and repetitive, hence a **template repo** that encodes the conventions: structure, files, skills, HR agent, memory pattern, logbook.

Key corrections observed while building the reference instances:

- Files must be in **English** (template targets reuse; Italian is owner-specific)
- The **owner's name** must not be hardcoded anywhere — parameterized
- All **customizations** should consolidate in `preferences.md`, loaded at session start (moved away from CLAUDE.md)
- The **db filename** must be agnostic: `memories.db`

## Requirements (R)

| ID | Requirement | Status |
|----|-------------|--------|
| R0 | Provide a reusable bootstrap repo that scaffolds a new orchestrator matching the proven pattern (structure, CLAUDE.md, HR, roster, memories, logbook) | Core goal |
| R1 🟡 | All template files are in English. Each instance sets its own default language for communication in preferences; the orchestrator honors it at runtime | Must-have |
| R2 | No hardcoded personal info (owner, vault paths, Basecamp, adjectives) — all parameterized via preferences | Must-have |
| R3 🟡 | All customizations live in `private/preferences.md` (not in CLAUDE.md). Preferences is the single source of identity + owner + language + vault + integrations, and is loaded at every session start | Must-have |
| R4 🟡 | The memory database is named `memories.db` (agnostic, not owner-bound). Ships as template-owned skill, not as external submodule | Must-have |
| R5 | Owner-specific data (preferences, db) lives in `private/` (gitignored) | Must-have |
| R6 🟡 | First-launch **interactive setup**: running Claude Code in a freshly cloned repo triggers a skill that asks the owner Q&A (orchestrator name, inspiration, owner nick/name, language, vault path, logbook folder, integrations) and fills preferences + initializes db | Must-have |
| R7 🟡 | The template ships a minimal, generic skill set: HR agent, memories, logbook, obsidian (with configurable territory), frontmatter/search discipline. Does NOT ship any instance-specific integrations (those stay in each instance) | Must-have |
| R8 🟡 | Public repo. The two reference instances stay as frozen forks; future playbook will backport improvements to them | Leaning yes |

## Shapes

### A: Git clone + interactive first-launch setup + preferences-centric config

The owner clones the repo, opens Claude Code in it, and a **Setup skill** triggers automatically. The skill runs a short Q&A session, writes `private/preferences.md`, initializes `private/memories.db`, and removes or disables itself. From that point on, the orchestrator boots reading preferences at every session.

| Part | Mechanism |
|------|-----------|
| **A1** | **Template repo skeleton** |
| A1.1 | `CLAUDE.md` generic, English, with sections: Customizations pointer to `preferences.md`, Role (orchestrator), Delega e roster, Routing, Sub-app validation, Handoff, Memoria (path to `private/memories.db`), Obsidian territory (placeholder), Frontmatter & search discipline |
| A1.2 | `private/preferences.md.template` — skeleton fields (owner nick, full name, role, language, vault root, basecamp config, integrations, adjectives) |
| A1.3 | `.gitignore` covers `private/`, `workspace/` |
| A1.4 | `.claude/agents/hr.md` (English), `.claude/agents/data/.gitkeep`, `.claude/roster.yaml` empty |
| A1.5 | `.claude/skills/memories/SKILL.md` — owner-agnostic memory skill, reads/writes `private/memories.db`, schema-compatible with `skill-spleenteo-memories` but self-contained |
| A1.6 | `.claude/skills/logbook/SKILL.md` — generic "Captain's logbook" skill, default folder name configurable at setup (e.g., `Logbook/`, or `Diario di bordo/` if owner picks Italian) |
| A1.7 | `.claude/skills/obsidian/SKILL.md` — English rules, territory root pulled from preferences at runtime |
| A1.8 | `.claude/skills/setup/SKILL.md` — interactive first-launch setup (see A2) |
| A1.9 | `workspace/handoff/.gitkeep`, `README.md` with clone → open → answer-Q&A flow |
| **A2** | **Interactive setup skill** |
| A2.1 | Triggers on first launch: detects absence of `private/preferences.md` (or a `setup_completed: true` flag in it) |
| A2.2 | Asks: orchestrator name, inspiration for personality ("any character or archetype? I'll propose 5-7 adjectives from there"), owner nick + full name + role, default language for our conversation, Obsidian vault root (or "skip if no vault"), logbook folder name (defaults to `Logbook`), Basecamp config (optional) |
| A2.3 | Writes `private/preferences.md` with the collected values, using a template with clear sections |
| A2.4 | Initializes `private/memories.db` with the schema |
| A2.5 | Sets `setup_completed: true` in preferences frontmatter so it doesn't re-trigger |
| A2.6 | Confirms to owner: "I am {{name}}. Ready to go." |
| **A3** | **Customizations consolidation** |
| A3.1 | `CLAUDE.md` has a single sentence at the top: "Read `private/preferences.md` at session start — it contains my identity, the owner's profile, and all customizations." |
| A3.2 | `preferences.md` has structured sections: Identity (name + adjectives), Owner (nick, full name, role, language), Integrations (Obsidian vault root + territory, Basecamp, etc.), Logbook (folder path, language for the log text) |
| A3.3 | All skills and agents in the template read what they need from preferences — no hardcoded lookups to `{{owner_name}}` tokens |
| **A4** | **Ships skills** |
| A4.1 | Memories skill: reads/writes `private/memories.db`, tables per `skill-spleenteo-memories` schema, but code-independent from Sites/claude-skills |
| A4.2 | Logbook skill: writes a daily note in `<obsidian_vault>/<logbook_folder>/YYYY-MM-DD-slug.md`, frontmatter with tags + description, body in preferences' default language |
| A4.3 | Obsidian skill: territory = `obsidian.territory_root` from preferences, off-limits folders configurable, default permission rules (no recursive reads, TIL and logbook pre-authorized) |
| A4.4 | Frontmatter & search discipline: no separate skill, lives in CLAUDE.md. Rules: every file gets `tags:` and `description:`; `rg` on frontmatter first, read body only for survivors |
| **A5** | **HR agent** |
| A5.1 | Same pattern used by the reference instances: recruiter + onboarding + offboarding. English. Manages `.claude/roster.yaml` and `.claude/agents/<name>.md` |
| **A6** | **No domain skills** |
| A6.1 | No instance-specific skills (whether personal domains or work integrations). Those are installed/symlinked later by the owner |

### B: Static template with placeholder tokens + bash setup script

Template files contain `{{owner_name}}`, `{{language}}`, etc. After clone, user runs `./setup.sh`, a shell script that prompts for values and does search-replace across files. No Claude Code involvement for setup.

| Part | Mechanism |
|------|-----------|
| B1 | Template files carry `{{token}}` placeholders in CLAUDE.md, skills, agents |
| B2 | `setup.sh` (bash) asks the same questions of A2, sed-replaces tokens in-place |
| B3 | Writes `private/preferences.md` and `private/memories.db` |
| B4 | CLAUDE.md, after substitution, is final and self-contained (no runtime lookups to preferences) |

### C: Manual edit + documentation

No automation. Owner clones, reads a checklist in README, manually edits preferences.md.template → preferences.md and fills fields. Opens a running session.

| Part | Mechanism |
|------|-----------|
| C1 | `README.md` has a "Setup checklist" with 6-8 fields to fill |
| C2 | Owner runs `cp private/preferences.md.template private/preferences.md` and edits |
| C3 | Owner runs `sqlite3 private/memories.db "<schema>"` manually |
| C4 | No skill or script involved |

## Fit Check

| Req | Requirement | Status | A | B | C |
|-----|-------------|--------|---|---|---|
| R0 | Reusable bootstrap repo scaffolds a new orchestrator matching the proven pattern | Core goal | ✅ | ✅ | ✅ |
| R1 | All template files in English; each instance sets its own default language | Must-have | ✅ | ✅ | ✅ |
| R2 | No hardcoded personal info — parameterized via preferences | Must-have | ✅ | ✅ | ✅ |
| R3 | All customizations live in `private/preferences.md`, loaded every session | Must-have | ✅ | ❌ | ✅ |
| R4 | DB named `memories.db` (agnostic), template-owned skill | Must-have | ✅ | ✅ | ✅ |
| R5 | `private/` gitignored | Must-have | ✅ | ✅ | ✅ |
| R6 | First-launch interactive Q&A driven setup | Must-have | ✅ | ❌ | ❌ |
| R7 | Ships: HR, memories, logbook, obsidian, frontmatter discipline. Does NOT ship slacky | Must-have | ✅ | ✅ | ✅ |
| R8 | Public repo; existing orchestrators frozen | Leaning yes | ✅ | ✅ | ✅ |

**Notes:**
- B fails R3: the `{{token}}` search-replace bakes values into files at setup time, so the source of truth ends up scattered across the repo rather than consolidated in preferences. Changes later (e.g., owner renames themselves) require re-running setup.
- B fails R6: a bash script is prompt-driven, but not conversational nor using Claude Code. The owner explicitly preferred the "Claude asks you questions" flavor.
- C fails R6: manual, no interactive Q&A.
- A passes all: interactive, centralized, reusable.

**Shape A is the recommended direction.**

## Decisions taken on Shape A

1. **Setup skill's self-disable**: move to `.claude/skills/.disabled/setup/` after successful first-run, preserving traceability and allowing re-run if needed.
2. **Memories live in CLAUDE.md, not as a skill.** The adopted view: memory is the engine of the orchestrator, not an optional capability. Embedding it in CLAUDE.md guarantees it's always in context at session start, with full schema + triggers + SQL commands inline. No external submodule, no separate skill to invoke.
3. **File territories are path-agnostic.** The orchestrator doesn't need to know "Obsidian" — it just needs three configurable paths in preferences: `logbook_path`, `til_path`, `documents_path`. The owner can point them to Obsidian folders, plain filesystem folders, anywhere. Obsidian-specific rules (tree command, off-limits conventions) drop out of the template. No dedicated `obsidian/` skill is shipped.
4. **Frontmatter discipline placement**: deferred. Default: stays in CLAUDE.md as policy. We may reopen if the orchestrator or other agents benefit from addressing it as a skill. Not a blocker.
5. **README structure**: short intro about what the repo is, then install steps (clone → open Claude Code in repo → answer setup questions → done), then a brief tour of the pattern for curious readers.

## Finalized skills set for the template

| Skill | Why |
|---|---|
| `setup` | Interactive first-launch Q&A that writes `private/preferences.md` and initializes `private/memories.db`, then self-moves to `.disabled/` |
| `logbook` | Writes a daily logbook note in the `logbook_path` declared in preferences, frontmatter with tags + description |

No obsidian skill, no memories skill (inline in CLAUDE.md), no slacky, no domain skills.

## Finalized agents set for the template

| Agent | Why |
|---|---|
| `hr` | Recruiter + onboarding + offboarding of craft agents. Manages `.claude/roster.yaml` |

Empty roster at install time. No pre-installed craft agents.

## Structure to build

```
spleenteo-orchestrator/
├── CLAUDE.md                        ← orchestrator template (English)
├── README.md                        ← intro + install flow
├── preferences.example.md           ← reference for the preferences file
├── shaping.md                       ← this document
├── .gitignore                       ← private/, workspace/, etc.
├── .claude/
│   ├── roster.yaml                  ← active: [], retired: []
│   ├── agents/
│   │   ├── hr.md                    ← HR agent (English)
│   │   └── data/
│   │       └── .gitkeep
│   └── skills/
│       ├── setup/
│       │   └── SKILL.md             ← first-launch Q&A
│       └── logbook/
│           └── SKILL.md
└── workspace/
    └── handoff/
        └── .gitkeep
```

`private/` is created by the setup skill on first run (it's gitignored).

## Next steps

1. ✅ Shape A finalized with the owner's answers
2. Build the repo structure file-by-file
3. Initialize git, first commit
4. Test: clone into a scratch location, run setup, verify preferences + db are generated
