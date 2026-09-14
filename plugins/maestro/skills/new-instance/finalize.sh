#!/usr/bin/env bash
#
# finalize.sh — mechanical finalization of the `setup` skill.
#
# Called by the setup skill after the owner has answered the 10 questions
# and confirmed the summary. Runs the deterministic filesystem ops that
# don't need the LLM:
#   1. Write private/preferences.md from collected answers.
#   2. Copy memories.db.template → private/memories.db.
#   3. Copy routines.example.yaml → private/routines.yaml.
#   4. Insert the first memory log record.
#   5. Remove the three root templates.
#   6. Move the setup skill to .claude/skills/.disabled/setup/.
#
# The LLM still owns: asking the questions, the summary/confirmation,
# the creative "day zero" logbook note, the orientation TIL note, and the
# final greeting. All of those happen in the skill prompt — this script
# only touches files.
#
# Inputs are passed as env vars. Required unless marked optional:
#
#   MAESTRO_LANGUAGE              default language for the orchestrator
#   MAESTRO_PROJECT_NAME          raw project name (free-form text)
#   MAESTRO_PROJECT_SLUG          filesystem-safe slug derived from project name
#   MAESTRO_ORCHESTRATOR_NAME     what the orchestrator calls itself
#   MAESTRO_OWNER_NICK            what the orchestrator calls the owner
#   MAESTRO_OWNER_FULL_NAME       owner's full name
#   MAESTRO_OWNER_ROLE            owner's role / what they do
#   MAESTRO_CONTEXT               merged Q3 answer, one or more paragraphs
#
#   MAESTRO_INSPIRED_BY           archetype (optional)
#   MAESTRO_ADJECTIVES            comma-separated list (optional)
#   MAESTRO_PEOPLE                pre-formatted markdown bullets (optional)
#   MAESTRO_VAULT_PATH            absolute path to vault root (empty if skip)
#   MAESTRO_LOGBOOK_PATH          absolute path for logbook (empty if skip)
#   MAESTRO_TIL_PATH              absolute path for TIL (empty if skip)
#   MAESTRO_DOCUMENTS_PATH        absolute path for documents (empty if skip)
#   MAESTRO_NOTES                 free-form additional context (optional)
#
# Assumes CWD = repo root (where the setup skill was triggered from).
# Refuses to run if `private/preferences.md` already exists.
#
# Note on values: the LLM that invokes this script passes free-form text
# from the owner as env vars. Values must be plain text — they get
# expanded into the preferences.md heredoc below, so literal `$`, backticks
# or `$(...)` in a value would be interpreted by the shell. Sanitize at the
# caller (the LLM should never see those in normal interview answers).

set -euo pipefail

# --- Preconditions -----------------------------------------------------

if [[ -f private/preferences.md ]]; then
  echo "ERROR: private/preferences.md already exists — refusing to overwrite." >&2
  echo "       The setup skill should run only once per instance." >&2
  echo "       To reconfigure, remove private/preferences.md and re-enable the skill." >&2
  exit 1
fi

required=(
  MAESTRO_LANGUAGE
  MAESTRO_PROJECT_NAME
  MAESTRO_PROJECT_SLUG
  MAESTRO_ORCHESTRATOR_NAME
  MAESTRO_OWNER_NICK
  MAESTRO_OWNER_FULL_NAME
  MAESTRO_OWNER_ROLE
  MAESTRO_CONTEXT
)
missing=()
for v in "${required[@]}"; do
  if [[ -z "${!v:-}" ]]; then
    missing+=("$v")
  fi
done
if [[ ${#missing[@]} -gt 0 ]]; then
  echo "ERROR: missing required env vars: ${missing[*]}" >&2
  exit 1
fi

# Defaults for optional vars
: "${MAESTRO_INSPIRED_BY:=}"
: "${MAESTRO_ADJECTIVES:=}"
: "${MAESTRO_PEOPLE:=}"
: "${MAESTRO_VAULT_PATH:=}"
: "${MAESTRO_LOGBOOK_PATH:=}"
: "${MAESTRO_TIL_PATH:=}"
: "${MAESTRO_DOCUMENTS_PATH:=}"
: "${MAESTRO_NOTES:=}"

for f in memories.db.template routines.example.yaml; do
  if [[ ! -f "$f" ]]; then
    echo "ERROR: $f not found at repo root" >&2
    exit 1
  fi
done

# --- 1) Write private/preferences.md -----------------------------------

mkdir -p private

cat > private/preferences.md <<EOF
---
setup_completed: true
---

# Preferences

This file is the **single source of truth** for the orchestrator's identity and the owner's profile. It's loaded at every session start, so anything the orchestrator should know about you and your world lives here.

Expand sections over time — the more context the orchestrator has, the better it can help. \`vault_path\` and the subfolder keys below are referenced by key from everywhere else (CLAUDE.md, agents, skills); this file stores the values.

**Do not commit this file** — it lives in \`private/\` which is gitignored.

---

## Project

- project_name: ${MAESTRO_PROJECT_NAME}
- project_slug: ${MAESTRO_PROJECT_SLUG}

---

## Identity (the orchestrator)

- Name: ${MAESTRO_ORCHESTRATOR_NAME}
- Inspired by: ${MAESTRO_INSPIRED_BY}
- Adjectives: ${MAESTRO_ADJECTIVES}

---

## Owner — basics

- Nick: ${MAESTRO_OWNER_NICK}
- Full name: ${MAESTRO_OWNER_FULL_NAME}
- Role: ${MAESTRO_OWNER_ROLE}
- Default language: ${MAESTRO_LANGUAGE}
- timezone:   # optional — IANA name (e.g. Europe/Rome, America/New_York). Omit to fall back to the system TZ.

---

## Context of operation

${MAESTRO_CONTEXT}

*Expand over time:*

- **Main objectives**: <the 2–5 things that, if accomplished, would make the orchestrator earn its place>
- **Constraints and rhythms**: <when you work, when you don't, recurring commitments>

---

## People

${MAESTRO_PEOPLE}

---

## File territories

- vault_path: ${MAESTRO_VAULT_PATH}
- logbook_path: ${MAESTRO_LOGBOOK_PATH}
- til_path: ${MAESTRO_TIL_PATH}
- documents_path: ${MAESTRO_DOCUMENTS_PATH}

---

## Integrations

Declare what applies. Add as you go.

- Basecamp:
- MCP servers:
- Other services:

---

## Communication preferences

How the orchestrator should talk *to you* and about *others*. Refine when you notice drift from how you actually work.

- Tone with you:
- Tone with others:
- Things to avoid:
- Things to keep doing:

---

## Notes

${MAESTRO_NOTES}
EOF

echo "OK: private/preferences.md written"

# --- 2) Initialize private/memories.db ---------------------------------

cp memories.db.template private/memories.db
echo "OK: private/memories.db initialized"

# --- 3) Initialize private/routines.yaml -------------------------------

cp routines.example.yaml private/routines.yaml
echo "OK: private/routines.yaml initialized"

# --- 4) First memory log -----------------------------------------------

TODAY=$(date +%Y-%m-%d)
sqlite3 private/memories.db \
  "INSERT INTO log (date, title, description, tags, type) VALUES ('$TODAY', 'Orchestrator setup completed', 'First launch configured via setup skill. Identity and preferences recorded.', 'setup,bootstrap,meta', 'memory');"
FIRST_ID=$(sqlite3 private/memories.db "SELECT last_insert_rowid();")
echo "OK: first memory logged (id=$FIRST_ID)"

# --- 5) Clean up root templates ----------------------------------------

/bin/rm -f preferences.example.md memories.db.template routines.example.yaml
echo "OK: root templates removed"

# --- 6) Self-disable ---------------------------------------------------

mkdir -p .claude/skills/.disabled
mv .claude/skills/setup .claude/skills/.disabled/setup
echo "OK: setup skill moved to .claude/skills/.disabled/setup/"

echo ""
echo "finalize.sh done."
