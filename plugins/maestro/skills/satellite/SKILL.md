---
name: satellite
description: "Attach a project repository to an existing Maestro instance as a satellite: the repo borrows that instance's identity, memory (its own scope) and a vault folder, with no files added to the repo. Use only when the owner explicitly asks to make a repo a satellite (\"make this repo a satellite of home\"); never on your own initiative."
---

# Satellite

A satellite is a project repository that works as a context of a Maestro instance, its mother. Nothing is written into the repo. The mother keeps the satellite's role in its `satellites` table and its memories in its own `memories.db` under a scope; the machine registry (`~/.claude/maestro-instances.yaml`) maps the repo to the mother; the Maestro plugin's `SessionStart` hook recognises the repo in every new session, exports `MEM_SCOPE`, and injects the role, the mother's identity and the memory rules. A `PreToolUse` hook opens the linked vault folder to the file tools.

This skill registers one satellite, checks the chain end to end, and hands off to a new session in the repo. It runs from the repo itself or from any other folder, the mother included.

## Command blocks

Each fenced `bash` block runs as one Bash call, exactly as written except for the placeholders. Replace each placeholder and keep the double quotes around it. Expand a leading `~` yourself: a quoted `~` doesn't expand. If a block exits non-zero, show its stderr to the owner and stop, unless its section says what to do. Never complete a step by hand.

Placeholders: `<folder>` and `<repo>` (step 1), `<mother>` and `<mother-path>` (step 2), `<scope>` and the role values (step 3).

## 1. Repository

The repo is the folder this session runs in, unless the owner named another one. Resolve it to its main checkout, so a worktree or a subfolder registers the repo itself:

```bash
set -eo pipefail
FOLDER="<folder>"
COMMON=$(git -C "$FOLDER" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)
if [ -n "$COMMON" ] && [ "$(basename "$COMMON")" = ".git" ]; then
  REPO=$(cd "$(dirname "$COMMON")" && pwd -P)
else
  REPO=$(cd "$FOLDER" && pwd -P)
fi
if [ -f "$REPO/private/preferences.md" ] && [ -f "$REPO/bin/mem" ]; then
  echo "$REPO is a Maestro instance, not a project repository." >&2
  exit 1
fi
echo "$REPO"
```

The printed path is `<repo>`. Confirm it with the owner in one line.

## 2. Mother

List the registered instances:

```bash
set -o pipefail
MAESTRO_NET=maestro-net
command -v maestro-net >/dev/null 2>&1 || MAESTRO_NET="${CLAUDE_PLUGIN_ROOT}/bin/maestro-net"
"$MAESTRO_NET" list --json
```

The owner names the mother; when only one instance is registered, propose it. `<mother>` is its registry name, `<mother-path>` its `path`. Exit 3 means no registry: the owner creates an instance with `/maestro:new-instance` or runs `maestro-net scan --write` first.

Check that the mother's `bin/mem` supports satellites, and read its warm task channel:

```bash
set -o pipefail
API=$(sed -n 's/^SCHEMA_API *= *\([0-9][0-9]*\).*/\1/p' "<mother-path>/bin/mem_schema.py" 2>/dev/null)
if [ "${API:-0}" -lt 2 ]; then
  echo "<mother> has SCHEMA_API ${API:-none}: its bin/mem is too old for satellites." >&2
  echo "Update its bin/ from the Maestro template first (/maestro-sync in <mother>)." >&2
  exit 1
fi
awk '/^## Warm task channel/{f=1;next} /^## /{f=0} f && /^channel:/{print "warm channel: " $2}' "<mother-path>/private/preferences.md"
echo "SCHEMA_API $API: ok"
```

## 3. Interview

Ask one question per turn, in the language the owner is using, each with a proposed answer when there is one:

1. **Scope**: the slug that tags this satellite's memories. Propose the repo folder name normalised: lowercase, every character outside `a-z0-9` replaced by `-`, repeated `-` collapsed, leading and trailing `-` stripped. When it equals the mother's warm channel printed in step 2 (a repo named like the task manager it implements), say so: markers are scoped, so the names don't collide, but reading the rows later is easier with a distinct slug.
2. **Project type**: `ux`, `consulting` or `development`.
3. **Mandate**: what the satellite is here to do, one or two sentences.
4. **Method**: how work is done here (e.g. "TDD, small commits, PRs reviewed by the owner"). Optional.
5. **Constraints**: what must not happen (e.g. "never push to main"). Optional.
6. **Language**: the language of documents and replies in this repo. Optional; the mother's language applies when empty.
7. **Vault folder**: an absolute folder in the mother's vault for this project's documents. Optional; propose `<documents_path>/<scope>` from the mother's preferences.

The role describes a mandate and a method. The voice and the identity stay the mother's: when an answer sounds like a persona ("a grumpy senior engineer"), keep the method it implies and drop the persona.

Every value sits inside double quotes in the next block: put a backslash before each `"`, `$` and backtick.

## 4. Register

First the role in the mother, then the repo in the machine registry. When the second command fails, the block removes the first row, so nothing stays half registered.

```bash
set -o pipefail
MAESTRO_NET=maestro-net
command -v maestro-net >/dev/null 2>&1 || MAESTRO_NET="${CLAUDE_PLUGIN_ROOT}/bin/maestro-net"
MEM="<mother-path>/bin/mem"
env -u MEM_DB -u MEM_SCOPE "$MEM" satellite add "<scope>" --repo "<repo>" --type "<type>" \
  --mandate "<mandate>" --method "<method>" --constraints "<constraints>" \
  --language "<language>" --vault "<vault-folder>" || exit $?
"$MAESTRO_NET" satellite add "<scope>" --repo "<repo>" --mother "<mother>" || {
  rc=$?
  env -u MEM_DB -u MEM_SCOPE "$MEM" satellite remove "<scope>"
  exit $rc
}
```

Drop each optional flag the owner left empty (`--method`, `--constraints`, `--language`, `--vault`) instead of passing an empty string. On a failure, read the exit code:

- `6` (`bin/mem`) or `2` (`maestro-net`): the slug was refused. Normalise it and run the block again.
- `7` (`bin/mem`): the repo or the vault folder isn't an absolute path, or the repo doesn't exist.
- `8` (`bin/mem`) or `9` (`maestro-net`): the scope or the repo is already registered, or the repo contains or sits inside the mother or another satellite. Show the message; `bin/mem satellite list` and `maestro-net list` show what is there. A wrong earlier registration is removed with `satellite remove` in both, by the owner's decision.
- `5` (`maestro-net`): the mother isn't in the registry.

## 5. Chain check

Run the checks the new session relies on. The memory written here stays in the satellite's scope as the record of the registration; announce it like any other write.

```bash
set -eo pipefail
MEM="<mother-path>/bin/mem"
BEFORE=$(git -C "<repo>" status --porcelain 2>/dev/null || true)
env -u MEM_DB MEM_SCOPE="<scope>" "$MEM" save "Satellite <scope> attached to <mother>" -t satellite,setup,<scope> \
  -d "Repo <repo>; role and vault folder in the mother's satellites table."
env -u MEM_DB MEM_SCOPE="<scope>" "$MEM" search "Satellite <scope> attached" --json | grep "attached to" >/dev/null \
  || { echo "The memory isn't found in scope <scope>." >&2; exit 1; }
if env -u MEM_DB -u MEM_SCOPE "$MEM" search "Satellite <scope> attached" --json | grep "attached to" >/dev/null; then
  echo "The memory leaks into the mother's default search." >&2; exit 1
fi
echo "memory: saved and found in scope <scope>, invisible from the mother's default search"
AFTER=$(git -C "<repo>" status --porcelain 2>/dev/null || true)
[ "$BEFORE" = "$AFTER" ] || { echo "git status in <repo> changed." >&2; exit 1; }
echo "repo: git status unchanged"
```

With a vault folder, check it too:

```bash
set -eo pipefail
VAULT="<vault-folder>"
mkdir -p "$VAULT"
NOTE="$VAULT/.maestro-satellite-check.md"
printf -- '---\ntags: [satellite, check]\ndescription: "Temporary note written by the satellite skill chain check."\n---\n\nThe satellite can write here.\n' > "$NOTE"
"<mother-path>/bin/register-check" "$NOTE"
grep -q "The satellite can write here." "$NOTE"
command rm -f "$NOTE"
echo "vault: note written, register-checked, read back and deleted in $VAULT"
```

## 6. Hand-off

Tell the owner, in two or three lines: the satellite is registered; the role and the scope apply from the next session opened in the repo, because the hook runs at session start; the command to open it, `cd "<repo>" && claude`. There they can check `printenv MEM_SCOPE` through a Bash call. The Maestro plugin must stay enabled at user scope: its hooks are what make the repo a satellite.

To undo: `bin/mem satellite remove <scope>` in the mother and `maestro-net satellite remove <scope>`. The scope's memories stay in the mother's db.

## Writing register

The hand-off is a chat reply: the register applies, with no post-pass. Role fields and the check memory are `memories.db` rows, outside the register.
