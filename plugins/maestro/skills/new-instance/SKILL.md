---
name: new-instance
description: "Create a new Maestro instance in a new folder: fetch the template at the plugin's commit, run the first-launch interview, finalize and register it. Use only when the owner asks to create a new Maestro instance or runs /maestro:new-instance."
disable-model-invocation: true
---

# New instance

This skill creates a Maestro instance in a new or empty folder. It takes the template at the commit the Maestro plugin was installed from, runs the first-launch interview in the current session, finalizes the new folder and registers it in the machine registry. Outside the destination it writes only the template mirror at `$HOME/.maestro` and the registry.

The interview collects only the essentials. Richer context (team, objectives, work rhythms, integrations) is added later by editing `private/preferences.md` in the new instance.

## When this skill runs

Only on explicit request: the owner runs `/maestro:new-instance` or asks to create a new Maestro instance. It never starts on its own, not even in a folder that has no `private/preferences.md`.

Once invoked, **stop all other work** and drive the flow to the end, in order: steps 1 to 5 prepare the folder, then the interview, the day-zero notes, finalize, register and the hand-off. The mechanical steps come first so that a failure there never wastes the owner's answers.

Until Question 1 settles the language, talk in the language the owner is already using in this session (English when they only typed the command).

## Command blocks

Each fenced `bash` block below runs as one Bash call, exactly as written except for the placeholders. Replace each placeholder and keep the double quotes around it:

- `<destination>`: the absolute path confirmed in step 2.
- `<sha>`: the commit printed by step 3.
- `<project_slug>`: the slug derived from Question 2.
- `<orchestrator-slug>` and `<domain>`: see Register.

Paths into the plugin's own folder are already absolute in the blocks: leave them as they are.

If a block exits non-zero, show its stderr to the owner and stop, unless its section says what to do on that failure (Destination, Register). Never complete a step by hand.

## 1. Kind

Ask:

> Do you want a full instance or a satellite? A full instance is a complete Maestro with its own identity, memory and vault, in a new folder. A satellite attaches a project repository to an instance you already have.

If the owner picks **satellite**: tell them satellites arrive with the `satellite` skill of the Maestro plugin, which this version doesn't ship yet, and stop here.

If the owner picks **full instance**: go on.

## 2. Destination

Ask for the folder that will hold the new instance, as an absolute path (e.g. `/Users/you/instances/home`). It must be new or empty. An empty folder is an allowed destination, the folder this session runs in included; a folder with anything in it is refused, which keeps an instance out of a project repository and away from another instance. If the owner gives a path starting with `~`, expand it to their home directory yourself before filling `<destination>`: a quoted `~` doesn't expand.

```bash
set -eo pipefail
DEST="<destination>"
case "$DEST" in
  /*) ;;
  *) echo "The destination must be an absolute path: $DEST" >&2; exit 2 ;;
esac
if [ -e "$DEST" ] && [ -n "$(command ls -A "$DEST")" ]; then
  echo "The destination exists and is not empty: $DEST" >&2
  echo "Choose a new or empty folder." >&2
  exit 1
fi
mkdir -p "$DEST"
echo "Destination ready: $DEST"
```

On exit 2 or 1, ask for another path and run the block again.

## 3. Plugin commit

The instance is built from the template at the commit the plugin was installed from, so the instance's files match the plugin's skills. `claude plugin list --json` reports that commit as the `version` of the user-scope `maestro@maestro` row.

```bash
set -o pipefail
claude plugin list --json | python3 -c '
import json, re, sys
rows = [r for r in json.load(sys.stdin) if r.get("id") == "maestro@maestro" and r.get("scope") == "user"]
if not rows:
    sys.exit("maestro@maestro is not installed at user scope. Install it with: claude plugin install maestro@maestro --scope user")
version = str(rows[0].get("version", ""))
if not re.fullmatch(r"[0-9a-f]{7,40}", version):
    sys.exit("maestro@maestro reports version " + repr(version) + ", not a commit SHA. Install the plugin from its marketplace, which versions it by commit.")
print(version)
'
```

The printed commit is `<sha>` for steps 4 and 5.

## 4. Template mirror

The template comes from the plugin's repository (`repository` in the plugin's `plugin.json`), through the local mirror at `$HOME/.maestro`, the same read-only mirror `maestro-sync` uses. The block clones the mirror when it is missing and fetches it otherwise, then checks that the commit from step 3 is there.

```bash
set -eo pipefail
REPO_URL=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["repository"])' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json")
MIRROR="$HOME/.maestro"
if [ -e "$MIRROR/.git" ]; then
  git -C "$MIRROR" fetch --quiet origin
else
  git clone --quiet "$REPO_URL" "$MIRROR"
fi
if ! git -C "$MIRROR" cat-file -e "<sha>^{commit}" 2>/dev/null; then
  echo "Commit <sha> is not in $MIRROR, even after a fetch." >&2
  echo "Update the plugin, then run /maestro:new-instance again:" >&2
  echo "  claude plugin marketplace update maestro" >&2
  echo "  claude plugin update maestro@maestro" >&2
  exit 1
fi
echo "Mirror ready at $MIRROR with commit <sha>"
```

## 5. Extract

```bash
set -eo pipefail
git -C "$HOME/.maestro" archive "<sha>" | tar -x -C "<destination>"
if [ ! -f "<destination>/CLAUDE.md" ] || [ ! -x "<destination>/bin/mem" ]; then
  echo "The archive of <sha> has no CLAUDE.md or no executable bin/mem: <destination> is not an instance skeleton." >&2
  exit 1
fi
echo "Template <sha> extracted into <destination>"
```

The template's `.gitattributes` keeps its own material (`docs/`, `plugins/`, `.claude-plugin/`, the tests of the template repo) out of the archive, so nothing is deleted after extraction. The new folder is not a git repository; the owner can turn it into one later.

## Interview: 10 questions, one at a time

Ask **one question per turn** (not in groups). Prefix each question with its progress indicator, e.g. `3/10`. After each answer, move to the next. Don't dump a checklist, don't batch.

### Question 1/10 — Language

Asked in the language of the session so far, before any other interview question:

> The folder is ready. Before we start: **what language should I use to talk to you?** (e.g., English, Italian, Spanish, French…)

From the owner's next turn onward, **conduct the rest of the flow, and every future interaction with the new instance, in the language they named**. Translate the following prompts into the chosen language; the English wordings here are illustrative.

### Question 2/10 — Project name

> `2/10` — What's the name of the project or context this orchestrator is for? (e.g., "Personal life", "Acme startup", "Novel draft", "Freelance partnership work"…) I'll use it as the top-level scope, and later suggest a slugified version of it as the default vault folder name.

Derive a **slug** from the answer: lowercase, non-alphanumeric characters replaced by `-`, collapse repeated `-`, strip leading/trailing `-`. Example: `"Acme Startup"` → `acme-startup`. Keep both values: `project_name` (the raw string) and `project_slug` (for the filesystem). Both go into preferences; the slug is also the default for the internal-mode vault folder (Q10).

### Question 3/10 — Project context and expectations

> `3/10` — Tell me about this project: what's the context like day to day, and what do you expect from an AI assistant? A few lines — no essays.

The answer blends two things: the **setting** (what this world looks like, the problems that come up) and the **motivation** (why the owner set you up, what they hope you'll do for them). Accept whichever shape comes naturally — some owners lead with context, others with expectations. Record the whole answer verbatim; it becomes the core of the "Context of operation" block in preferences.

### Question 4/10 — Orchestrator's name

> `4/10` — What should I call myself?

### Question 5/10 — Inspiration

> `5/10` — Is there a character, archetype, or role that captures the personality you want from me? (e.g., a calm butler, a sharp analyst, a patient librarian, a quiet mentor.) Based on what you say, I'll propose 3–5 adjectives.

After the answer: propose 3–5 adjectives in the owner's language (e.g., "a calm butler" → calm, discreet, paternal, proactive, patient). Wait for confirmation or edits. Record the final list.

### Question 6/10 — Owner's nick

> `6/10` — How do you want me to call you in chat?

### Question 7/10 — Owner's full name

> `7/10` — What's your full name? (I'll use it rarely — it's for context.)

### Question 8/10 — Owner's role

> `8/10` — What's your role, or what do you do? A short description is fine.

### Question 9/10 — People you work with

> `9/10` — Are there people I should know about? (Team, collaborators, family, clients — whoever is relevant to the work we'll do together. Just names and one line each is enough. Or skip if you work solo.)

### Question 10/10 — File territories (one compound question)

This is the last question, and it branches based on the owner's preference for where their notes live.

The owner's territory is organized around a single **vault root** (the key is `vault_path`). Logbook, TIL, and documents live as subfolders inside it by default. The vault path is declared once in preferences and referenced by key from anywhere else — no other file stores the value.

> `10/10` — Where should I save your notes? Three options:
>
> - **internal** — keep everything inside the new instance, in `<destination>/<project_slug>/` (derived from the project name you gave in Q2). Logbook, TIL, and documents become subfolders there. Nothing external to configure. Migrate later by editing preferences. The vault folder will be gitignored, so nothing leaks.
> - **external** — you have a vault or folder on disk (Obsidian, iCloud, anywhere). I'll ask for its absolute root path, then use `logbook/`, `til/`, `documents/` as subfolders by default. Override any of them later in preferences if you want non-standard layout.
> - **skip** — no territories right now. I won't write any markdown files until you set at least `vault_path` in preferences later.

Handle the answer:

**If `internal`**: record **four** absolute keys for preferences, using the `project_slug` computed in Q2. The folders are created after the summary is confirmed (see Territory folders).

- `vault_path: <destination>/<project_slug>`
- `logbook_path: <destination>/<project_slug>/logbook`
- `til_path: <destination>/<project_slug>/til`
- `documents_path: <destination>/<project_slug>/documents`

Confirm in one line: *"Got it — notes will live in `<destination>/<project_slug>/` inside the new instance (gitignored, so they stay private)."*

**If `external`**: ask the owner for the vault root first, in a single follow-up:

> Absolute path for your vault root? (e.g., `/Users/you/Obsidian/MyVault`)

Check whether the directory exists; if it doesn't, ask whether to create it. Once the root is settled:

1. Compute three default subpaths: `<vault_path>/logbook`, `<vault_path>/til`, `<vault_path>/documents`.
2. For each default subpath, check whether the folder exists. Missing ones: ask once whether to create them all (don't nag per folder). Nothing is created yet: record the answer for Territory folders.
3. Save **four** keys to preferences:
   - `vault_path: <absolute-vault-path>`
   - `logbook_path: <vault_path>/logbook`
   - `til_path: <vault_path>/til`
   - `documents_path: <vault_path>/documents`
4. Confirm in one line, then mention: *"If any subfolder should live elsewhere, edit the corresponding key in `preferences.md` — the orchestrator reads it fresh every session."*

**If `skip`**: record all four keys as empty in preferences. Remind the owner they can set at least `vault_path` anytime by editing `<destination>/private/preferences.md`.

### After the 10 questions — offer to add more context

Before writing, tell the owner:

> Those are the essentials. Other context — objectives, work rhythms, communication style, integrations like Basecamp or MCP servers — you can add later by editing `private/preferences.md` directly. Want to add anything else right now, or shall I save what we have?

If the owner wants to add something, accept it as free-form text and save it to the "Notes" section of preferences. Otherwise, proceed.

## Summary and confirmation

Recap what was collected, grouped by section, with every path absolute. Offer a chance to correct any field before writing. Beyond the extracted template, do NOT create any folder, write any file or run `finalize.sh` until the owner confirms.

## Territory folders

After the owner confirms the summary, create the territory folders with the final values.

**Internal vault**: create the vault and its three subfolders inside the new instance:

```bash
set -o pipefail
mkdir -p "<destination>/<project_slug>/logbook" "<destination>/<project_slug>/til" "<destination>/<project_slug>/documents"
```

Then append the slug to the instance's `.gitignore` when it isn't listed yet, so the vault stays out of git if the owner later turns the folder into a repository:

```bash
set -o pipefail
python3 - "<destination>/.gitignore" "<project_slug>/" <<'PY'
import sys
path, entry = sys.argv[1], sys.argv[2]
try:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
except FileNotFoundError:
    text = ""
if entry not in text.splitlines():
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(("" if text == "" or text.endswith("\n") else "\n") + entry + "\n")
print(entry + " is listed in " + path)
PY
```

**External vault**: create the root and the subfolders the owner agreed to create at Q10, with `mkdir -p` on each absolute path, quoted.

**Skip**: nothing to create.

## Day-zero logbook (if `logbook_path` is set)

Write a "day zero" logbook note at `<logbook_path>/YYYY-MM-DD-day-zero.md`. Two purposes:

1. Prove the pipeline works: the owner sees a real file created at the path they declared.
2. Show what a logbook note looks like, in their language, following the frontmatter discipline.

Voice: the **owner's first person** (per the `logbook` skill convention). Language: the owner's default language. Frontmatter must include `tags:` (multi-dimensional) and `description:` (one line).

The note follows the writing register of the new instance (`<destination>/howto/10-writing-register.md`). After writing it, run `"<destination>/bin/register-check" "<file>"` on it, with `<file>` the note's absolute path. Fix every violation it reports and re-run until it exits 0; judge the candidates it lists by reading them.

Template (translate into the owner's language):

```markdown
---
tags: [installation, setup, day-zero, <orchestrator-slug>, meta]
description: The day <Orchestrator-Name> was installed and configured, with the file territories it may write to.
---

## <date in owner's language, e.g. "19 April 2026" or "19 Aprile 2026">

# Day zero with <Orchestrator-Name>

Today I set up <Orchestrator-Name> as my orchestrator, in `<destination>`. The new-instance skill of the Maestro plugin interviewed me about myself and this project, then asked where it may write files for me.

<Orchestrator-Name> talks to me in <language> and may write in these territories:

- Logbook at `<logbook_path>`, starting with this note.
- TIL at `<til_path>`. <!-- omit line if til_path is empty -->
- Documents at `<documents_path>`. <!-- omit line if documents_path is empty -->

The memory database is ready, and its first entry records the installation. From here on <Orchestrator-Name> logs what we do as we go, and I pick up at the next session by opening Claude Code in `<destination>`.
```

Announce:

```
📖 logbook entry created: <absolute path>
```

Skip this step silently if `logbook_path` was left empty in preferences.

## Day-zero TIL (if `til_path` is set)

Write an orientation TIL note at `<til_path>/YYYY-MM-DD-how-to-work-with-<orchestrator-slug>.md`. Purpose: leave the owner a short reference they can revisit about how the orchestrator is organized.

Voice: owner's first person. Language: owner's default.

The note follows the writing register like the logbook note: run `"<destination>/bin/register-check" "<file>"` on it and fix what it reports before announcing.

Template (translate into the owner's language):

```markdown
---
tags: [til, <orchestrator-slug>, meta, onboarding, claude-code]
description: Where <Orchestrator-Name> keeps preferences, memory, logbook and TIL, and how to change its configuration later.
---

## <date>

# How to work with <Orchestrator-Name>

### Preferences are mine to edit

`private/preferences.md` belongs to me. I can open it and change it whenever I want: add people, switch the default language, refine what I need. <Orchestrator-Name> reads it at the start of every session.

<Orchestrator-Name> also proposes additions over time, based on durable patterns it notices, such as a colleague I mention often. It adds with a one-line notice and asks before changing anything I wrote.

### Where things are kept

- Memory (`private/memories.db`): the running log of what happens, what I have to do and the ideas that come up. <Orchestrator-Name> announces every write.
- Logbook (`<logbook_path>`): the daily synthesis, written when I ask for a recap of the day.
- TIL (`<til_path>`): single lessons like this one.

### Changing the configuration later

To change identity or territories, I edit `private/preferences.md`. To start again from scratch, I run `/maestro:new-instance` with a new empty folder; once that instance is finalized, I can move this `private/memories.db` into it to keep the memory.
```

Announce:

```
💡 TIL created: <absolute path>
```

Skip silently if `til_path` is empty.

## Finalize

After the logbook and TIL have been written (or skipped), run `finalize.sh` in the new instance, in a single Bash call: the `cd` and the script go on the same command, because the Bash tool doesn't keep a working directory outside the session's project. The script writes `private/preferences.md`, copies `memories.db.template` to `private/memories.db` and `routines.example.yaml` to `private/routines.yaml`, writes the first memory through the instance's own `bin/mem save`, and removes the three root templates.

Pass the collected answers as environment variables. Required: `MAESTRO_LANGUAGE`, `MAESTRO_PROJECT_NAME`, `MAESTRO_PROJECT_SLUG`, `MAESTRO_ORCHESTRATOR_NAME`, `MAESTRO_OWNER_NICK`, `MAESTRO_OWNER_FULL_NAME`, `MAESTRO_OWNER_ROLE`, `MAESTRO_CONTEXT`. Optional: `MAESTRO_INSPIRED_BY`, `MAESTRO_ADJECTIVES`, `MAESTRO_PEOPLE`, `MAESTRO_VAULT_PATH`, `MAESTRO_LOGBOOK_PATH`, `MAESTRO_TIL_PATH`, `MAESTRO_DOCUMENTS_PATH`, `MAESTRO_NOTES`.

- Every path value is absolute. For an internal vault they sit under `<destination>/<project_slug>`; for `skip` they are empty strings.
- `MAESTRO_PEOPLE` holds pre-formatted markdown bullets, one person per line, with real line breaks inside the double quotes (e.g. `- Jane Doe: CTO, technical lead` and `- John Smith: Account exec` on two lines). Empty string if the owner skipped the people question.
- Write the owner's answers verbatim. Each value sits inside double quotes on this command line, where the shell still interprets four characters: put a backslash before each of them. `\` becomes `\\`, `"` becomes `\"`, `$` becomes `\$`, and a backtick becomes `` \` ``. An apostrophe needs nothing, and a line break stays a literal line break inside the quotes. Without the backslashes, a `$` expands, a backtick runs a command and a `"` ends the value early, all with exit 0.

The values below are an example: replace every one with the owner's answers.

```bash
set -o pipefail
cd "<destination>" && \
MAESTRO_LANGUAGE="english" \
MAESTRO_PROJECT_NAME="Acme partnership" \
MAESTRO_PROJECT_SLUG="acme-partnership" \
MAESTRO_ORCHESTRATOR_NAME="Jarvis" \
MAESTRO_INSPIRED_BY="a calm butler" \
MAESTRO_ADJECTIVES="paternal, calm, discreet, proactive" \
MAESTRO_OWNER_NICK="Jane" \
MAESTRO_OWNER_FULL_NAME="Jane Doe" \
MAESTRO_OWNER_ROLE="Partnership Manager" \
MAESTRO_CONTEXT="Work: I manage 40+ partner relationships, juggle commitments across weeks, and need help drafting diplomatic messages on short notice." \
MAESTRO_PEOPLE="- A. Smith: CEO" \
MAESTRO_VAULT_PATH="<destination>/acme-partnership" \
MAESTRO_LOGBOOK_PATH="<destination>/acme-partnership/logbook" \
MAESTRO_TIL_PATH="<destination>/acme-partnership/til" \
MAESTRO_DOCUMENTS_PATH="<destination>/acme-partnership/documents" \
bash "${CLAUDE_SKILL_DIR}/finalize.sh"
```

Read the script's stdout to confirm each step. Announce the first memory write to the owner:

```
📝 saved: "Orchestrator setup completed" [setup,bootstrap,meta] (memory)
```

If the script exits non-zero, surface its stderr to the owner and stop: don't patch partial state by hand. The script refuses to run when `private/preferences.md` or `private/memories.db` already exists, so a run that failed halfway is retried from step 2 with a new empty folder. The answers are still in this conversation, so the interview doesn't need repeating; the day-zero notes are written again if they lived inside the abandoned folder.

## Register

Add the new instance to the machine registry (`~/.claude/maestro-instances.yaml`, or the file `MAESTRO_INSTANCES` names), so `maestro-net` can reach it. The block uses `maestro-net` from `PATH`, or the plugin's own copy when a session doesn't have the plugin's `bin/` on `PATH`. Fill the placeholders:

- `<orchestrator-slug>`: the orchestrator's name from Question 4 as a slug (lowercase letters, digits and `-`, starting with a letter or digit), e.g. `jarvis`.
- `<domain>`: one line taken from the project context of Question 3, with no double quotes, backslashes or line breaks (`maestro-net` refuses a double quote). It sits inside double quotes like the Finalize values: put a backslash before each `$` and each backtick.

```bash
set -o pipefail
MAESTRO_NET=maestro-net
if ! command -v maestro-net >/dev/null 2>&1; then
  MAESTRO_NET="${CLAUDE_PLUGIN_ROOT}/bin/maestro-net"
fi
"$MAESTRO_NET" register "<orchestrator-slug>" --path "<destination>" --domain "<domain>" --accepts recap,ask
```

On a failure, read the exit code:

- `9`: the name or the path is already registered. Propose another name to the owner (e.g. `<orchestrator-slug>-<project_slug>`) and run the block again with the one they choose.
- `2`: the slug or the domain was refused. Fix it and run the block again.
- `7`: the destination lacks `private/preferences.md` or `bin/mem`, so finalize didn't complete. Stop and report.
- `3`: the registry file exists but can't be read. Tell the owner its path and the error, so they can fix its permissions.
- `4`: the registry file is malformed. Show the owner the error `maestro-net` printed; the file is theirs to fix, never rewrite it.

A failed registration doesn't undo the instance, which is complete once finalize succeeds. Still give the hand-off, and add one line telling the owner how to register it later, with the values filled in: `maestro-net register "<orchestrator-slug>" --path "<destination>" --domain "<domain>" --accepts recap,ask`.

## Optional machine dependencies

Some skills need a tool on the machine that Maestro cannot install for the
owner. Check what is present, report what is missing, and install nothing.

Run the checks in one Bash call and read the results:

```bash
set -o pipefail
for tool in yap swiftc; do
  if command -v "$tool" >/dev/null 2>&1; then echo "$tool: found"; else echo "$tool: missing"; fi
done
sw_vers -productVersion
```

| Skill | Needs | Install | Without it |
|---|---|---|---|
| `listen` | `yap` | `brew install yap` | no live call transcription at all |
| `listen` | macOS 26 or later | — | `yap` will not run |
| `listen` | `swiftc` (Xcode Command Line Tools) | `xcode-select --install` | captures still work, but stop surviving a change of audio input device |

Report the outcome in one line per missing item, in the owner's language, with
the command that installs it. Then move on: a missing optional dependency never
blocks the new instance, and the skill that needs it says so again when invoked.

Skip the whole section silently when nothing is missing.

## Hand-off

End with a single sentence in character (owner's language), the files that were created with their absolute paths, and the command that opens the new instance. This session stays where it is: the new instance starts working in its own folder, at its first session there.

Example (English):

```
I am Jarvis. Ready.

Files you can open to verify everything is in place:
- Preferences: <destination>/private/preferences.md
- Memory db:   <destination>/private/memories.db
- Routines:    <destination>/private/routines.yaml
- Logbook:     <logbook_path>/YYYY-MM-DD-day-zero.md
- TIL:         <til_path>/YYYY-MM-DD-how-to-work-with-jarvis.md

To start working with me, open a terminal and run:

cd "<destination>" && claude

Once there, type /guide whenever you need orientation.
```

Fill `<destination>` and the territory paths with their absolute values. Omit the logbook/TIL lines if those territories were skipped. Translate the labels and the intro into the owner's language.

Then hand control back.

## Rules

- **Only on request**: never start this flow on your own.
- **New or empty folder only**: an empty folder is fine, the session's own folder included; a folder with anything in it (a project repository, another instance) is refused.
- **Mechanical steps first**: steps 1 to 5 run before the interview, and a failing block stops the flow instead of being worked around by hand.
- **Language first in the interview**: Question 1 is always "what language should I use?". From the next turn on, everything is in the owner's chosen language.
- **One question per turn, always**: never bundle. Always show the progress indicator (`N/10`) so the owner knows where they are.
- **Propose defaults**, especially for adjectives (from the inspiration).
- **Accept brevity, skip optional fields**: the owner may leave territories or people empty. Don't insist.
- **Absolute paths everywhere**: in the command blocks, in preferences and in the closing message, every path is absolute on the destination. Never write `~` inside quotes.
- **Answers verbatim, escaped for the shell**: free text goes into double-quoted values with a backslash before `\`, `"`, `$` and a backtick; never reword an answer to dodge the escaping.
- **Validate paths, create after confirmation**: for an external vault, check at Q10 whether each directory exists and ask about the missing ones; every territory folder is created in Territory folders, after the summary is confirmed.
- **The mirror is read-only**: this skill only clones and fetches `$HOME/.maestro`; it never commits, checks out or deletes anything there.
- **Never speak as "orchestrator"**: that term stays in CLAUDE.md. In chat, you use the chosen name once it exists.
- **Never invent data**: if a field isn't provided, leave it empty in preferences.
- **Keep the interview light**: deeper context (objectives, rhythms, communication style, team details, integrations) is for the owner to fill in later by editing `preferences.md`. Don't try to extract everything now.
- **Write the day-zero logbook and TIL before finalize**: they are real, useful content, not dummy files, and they pass `register-check` before they are announced.
- **Announce every write**: every db insert and every markdown file creation gets its one-line announcement. The owner should see what happened at each step.
