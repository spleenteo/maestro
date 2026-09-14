#!/usr/bin/env bash
#
# finalize.sh — mechanical finalization of the `new-instance` skill.
#
# Called by the new-instance skill after the owner has answered the 10
# interview questions and confirmed the summary, in the new instance's own
# folder. Runs the deterministic filesystem ops that don't need the LLM:
#   1. Write private/preferences.md from collected answers.
#   2. Copy memories.db.template → private/memories.db.
#   3. Copy routines.example.yaml → private/routines.yaml.
#   4. Insert the first memory log record, through the instance's own
#      bin/mem save.
#   5. Remove the three root templates.
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
# Assumes CWD = instance root.
# Refuses to run if `private/preferences.md` or `private/memories.db`
# already exists — a new instance always starts in a new or empty folder;
# re-running here would mean re-setup, which happens by editing preferences
# directly, not by re-running this script.
#
# Note on values: the LLM that invokes this script passes free-form text
# from the owner as env vars. Inside the heredoc below, `$VAR` is expanded
# once to the variable's value, and that value then lands as plain data —
# a literal `$`, backtick or `$(...)` an owner typed stays literal in
# preferences.md, the same way it would inside a double-quoted string.
# Escaping happens earlier, on the caller's command line that sets these
# env vars: SKILL.md (Finalize) spells out the rule.

set -euo pipefail

# --- Preconditions -----------------------------------------------------

if [[ -f private/preferences.md ]]; then
  echo "ERROR: private/preferences.md already exists — refusing to overwrite." >&2
  echo "       finalize.sh should run only once per instance, in a new or empty folder." >&2
  echo "       To reconfigure, edit private/preferences.md directly." >&2
  exit 1
fi

if [[ -f private/memories.db ]]; then
  echo "ERROR: private/memories.db already exists — refusing to overwrite." >&2
  echo "       finalize.sh should run only once per instance, in a new or empty folder." >&2
  echo "       To start a new instance, use a new or empty destination folder." >&2
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

# --- 4) First memory log -------------------------------------------------

# -u strips any MEM_DB/MEM_SCOPE the caller's environment happens to carry
# (a stray value from an unrelated instance, say), so the write always lands
# on this instance's own db, as the mother (scope NULL).
MEM_OUTPUT=$(env -u MEM_DB -u MEM_SCOPE "$PWD/bin/mem" save "Orchestrator setup completed" \
  -d "First launch configured via new-instance. Identity and preferences recorded." \
  -t setup,bootstrap,meta)
if [[ "$MEM_OUTPUT" =~ \#([0-9]+)$ ]]; then
  echo "OK: first memory logged (id=${BASH_REMATCH[1]})"
else
  echo "OK: first memory logged"
fi

# --- 5) Clean up root templates ----------------------------------------

/bin/rm -f preferences.example.md memories.db.template routines.example.yaml
echo "OK: root templates removed"

echo ""
echo "finalize.sh done."
