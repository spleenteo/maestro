---
name: maestro-sync
description: "Sync the Maestro instance this session runs in with the latest Maestro template. Updates the read-only mirror at ~/.maestro, checks the loaded Maestro plugin isn't behind it, offers to copy a drifted bin/ after backing up the memory db and the old scripts, applies per-file diffs of Maestro-distributed files with confirmation, proposes new upstream files and the removal of retired ones. Use when the owner says \"sync maestro\", \"update from maestro\", \"pull maestro changes\", \"/maestro:maestro-sync\", or asks whether new patterns are available from the template. Runs only in an instance root."
---

# maestro-sync

This skill keeps the orchestrator instance aligned with the **Maestro template** at `https://github.com/spleenteo/maestro`. It applies upstream pattern changes (CLAUDE.md sections, base hub skills, base craft agents, `bin/`) without ever touching the instance's personalizations.

It ships in the Maestro plugin, so it is the same for every instance on the machine and updates with the plugin (`claude plugin update maestro@maestro`), never through its own sync. Instances created before it moved carry an old local skill at `.claude/skills/maestro-sync/`: the first sync after the move must be started as `/maestro:maestro-sync`, and Phase 6b proposes removing the old copy.

## Architecture

Two paths, two roles (decided 2026-04-30):

- **Primary working tree** (optional, `maestro_worktree_path:` in preferences) — a clone of the template where the owner promotes new patterns from this instance to the template (modify, commit, push). This skill **never writes here**. It only reads its git status to warn the owner if there are uncommitted changes that should be pushed before syncing.
- **`~/.maestro/`** — read-only mirror used by this skill as a stable comparison point. Phase 3 fetches every branch from the plugin's repository URL and resets the mirror to `origin/main`. The Maestro plugin's `new-instance` skill also touches it, to clone it when missing or fetch it when present, so it holds the commit a new instance is built from; it never moves the mirror's `HEAD`, so `main` stays what this skill compares against. Never committed to, never modified by hand.

The skill scans the **instance** (the orchestrator that invokes the skill) for files with `origin: maestro` in their frontmatter, compares each with the mirror version, and proposes a diff per file with confirmation. It also scans the **mirror** in the opposite direction: files marked `origin: maestro` that exist upstream but not in the instance are proposed as **new files**, with the same per-file confirmation.

## Files in scope

The skill operates on files marked with both `origin: maestro` and `maestro_version: vYYYY.MM.DD.N` in their frontmatter. Typical inheritable files:

- `CLAUDE.md` (top-level)
- `.claude/skills/<name>/SKILL.md` for hub skills distributed by Maestro (e.g. `logbook`, `add-external-app`, `guide`)
- `.claude/agents/<name>.md` for craft agents distributed by Maestro (e.g. `librarian`, `scheduler`, `hr`)

Files **never** in scope:

- `private/*` (preferences, memories.db, logs, anything sensitive)
- `apps/*` (sub-apps and their internals)
- Custom skills/agents added by the instance (no `origin: maestro` marker)
- `.claude/roster.yaml` (instance-specific list of active agents — Maestro doesn't choose which agents an instance enrolls)
- `docs/`, `plugins/`, `.claude-plugin/` and `user-skills/` (template-only and plugin-distributed material — the same exclusion list the reverse scan applies in Phase 4b)
- The retired paths of Phase 6b: never diffed, never counted in the version floor, proposed for removal only

`bin/*` files carry no frontmatter: Phase 5b compares them by checksum and copies them only on the owner's yes, after backing up the memory db and the scripts it replaces.

## When this skill runs

Invoke it when the owner says something like:

- *"Sync Maestro"* / *"Update from Maestro"* / *"Pull Maestro changes"*
- *"/maestro:maestro-sync"*
- *"Are there new patterns from the template?"*
- *"Bring this instance up to date with the latest Maestro"*

When the instance still has a local skill named `maestro-sync`, this one is the skill to use: the local copy is retired.

## Operational flow

Stop and report on the first error — never continue past a failure silently. Each fenced `bash` block runs as one Bash call, exactly as written except for the placeholders. Every answer of the owner covers only the question it answers: an `[A]` in Phase 6 never extends to the `bin/` copy or to removals.

### Phase 0 — Check this is an instance

```bash
set -eo pipefail
INSTANCE="$(pwd -P)"
if [ -d "$INSTANCE/plugins/maestro" ]; then
  echo "$INSTANCE is the Maestro template repository, not an instance." >&2
  exit 1
fi
if [ ! -f "$INSTANCE/private/preferences.md" ] || [ ! -f "$INSTANCE/bin/mem" ]; then
  echo "$INSTANCE is not the root of a Maestro instance (no private/preferences.md next to bin/mem)." >&2
  echo "Open a session in the instance folder and run /maestro:maestro-sync there." >&2
  exit 1
fi
echo "$INSTANCE"
```

On a non-zero exit, show the message and stop: nothing else runs. The printed path is `<instance-path>` for every later phase.

### Phase 1 — Locate the two paths

Resolve from preferences (or use sensible defaults):

- **Mirror path**: `~/.maestro/` (default). If preferences declare `maestro_mirror_path:`, use that.
- **Working tree path**: the value of `maestro_worktree_path:` in preferences. No default: an instance that doesn't declare it has no primary working tree.

Paths are written with `~` for readability only. Before substituting a path into any `<mirror-path>`, `<worktree-path>` or `<instance-path>` placeholder in the commands below, expand it to an absolute path with `$HOME` resolved (e.g. `/Users/<name>/.maestro`) — **never** the literal `~`. Every placeholder in this skill's commands is quoted (`"<mirror-path>"`), and a quoted `~` is not a home-directory shortcut to the shell: it's just two characters, `git -C` fails on a path that doesn't exist, and — for the piped commands in Phase 4b and 5b — that failure would otherwise go unnoticed (see the `set -o pipefail` note there). Where no working tree is declared, fill `<worktree-path>` with `none`.

If the **mirror** doesn't exist yet, Phase 3 clones it. Tell the owner: *"First run: I'm cloning the Maestro mirror at <mirror-path>."*

If preferences declare no working tree, or the **working tree** doesn't exist, that's fine — promotions can still be done by cloning it on demand. Skip Phase 2 with a soft note: *"No primary working tree at <worktree-path>; skipping the uncommitted-changes check. Nothing to lose."*

### Phase 2 — Pre-sync check on the working tree

This is the hook that catches in-flight promotions before they get clobbered by a sync. Run on the **primary working tree**, never on the mirror.

```bash
git -C "<worktree-path>" status --porcelain          # any uncommitted changes?
git -C "<worktree-path>" log @{u}..HEAD --oneline    # any local commits not yet pushed?
```

- If `git status --porcelain` returns non-empty → there are uncommitted changes.
- If `git log @{u}..HEAD` returns non-empty → there are local commits not pushed.

In either case, **stop** and ask the owner:

> ⚠ I see local changes in your Maestro working tree (`<worktree-path>`):
> - <list of modified/untracked files, max 10>
> - <list of unpushed commits, max 5>
>
> If you're in the middle of promoting a pattern to the template, push these first — otherwise the sync will pull `origin/main` without them, and the instance won't see your work-in-progress.
>
> Options:
> - `push` — let me push them now (only if all changes are committed; if there are uncommitted edits, I won't `git add -A` for you)
> - `continue` — sync anyway, knowing the local work isn't reflected
> - `abort` — stop here, you handle it manually

Wait for the owner. If `push`, run `git -C "<worktree-path>" push origin main`. If `continue`, proceed to Phase 3. If `abort`, exit with a clean message.

### Phase 3 — Refresh the read-only mirror, check the plugin

```bash
set -eo pipefail
MIRROR="<mirror-path>"
INSTANCE="<instance-path>"
case "$MIRROR" in
  "$INSTANCE"|"<worktree-path>") echo "The mirror path $MIRROR is the instance or the working tree: refusing to reset it." >&2; exit 1 ;;
esac
REPO_URL=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["repository"])' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json")
if [ -e "$MIRROR/.git" ]; then
  if [ -n "$(git -C "$MIRROR" status --porcelain --untracked-files=no)" ]; then
    echo "The mirror at $MIRROR has local edits: it is not a plain mirror, refusing to reset it." >&2
    exit 1
  fi
else
  git clone --quiet "$REPO_URL" "$MIRROR"
fi
git -C "$MIRROR" fetch --quiet "$REPO_URL" '+refs/heads/*:refs/remotes/origin/*'
git -C "$MIRROR" reset --quiet --hard origin/main
if ! command -v claude >/dev/null 2>&1; then
  echo "The claude command isn't on PATH, so the installed plugin can't be checked." >&2
  exit 1
fi
PLUGIN=$(claude plugin list --json | python3 -c '
import json, os, re, sys
rows = [r for r in json.load(sys.stdin) if r.get("id") == "maestro@maestro" and r.get("scope") == "user"]
row = rows[0] if rows else {}
version = str(row.get("version", ""))
path = os.path.realpath(row.get("installPath") or "")
print((version if re.fullmatch(r"[0-9a-f]{7,40}", version) else "") + " " + path)
')
SHA="${PLUGIN%% *}"
INSTALLED="${PLUGIN#* }"
if [ -z "$SHA" ]; then
  echo "maestro@maestro isn't installed at user scope from its marketplace, so its commit is unknown." >&2
  exit 1
fi
LOADED="$(cd -P -- "${CLAUDE_PLUGIN_ROOT}" >/dev/null && pwd -P)"
if [ "$INSTALLED" != "$LOADED" ]; then
  echo "This session runs the Maestro plugin from $LOADED, but $INSTALLED is installed." >&2
  echo "Restart Claude Code, then run /maestro:maestro-sync again." >&2
  exit 1
fi
if ! git -C "$MIRROR" cat-file -e "$SHA^{commit}" 2>/dev/null || ! git -C "$MIRROR" merge-base --is-ancestor origin/main "$SHA"; then
  echo "The Maestro plugin ($SHA) is behind the template's main branch." >&2
  echo "Update it, restart Claude Code, then run /maestro:maestro-sync again:" >&2
  echo "  claude plugin marketplace update maestro" >&2
  echo "  claude plugin update maestro@maestro" >&2
  echo "If the marketplace was added from a branch, remove it and add spleenteo/maestro again without one." >&2
  exit 1
fi
echo "MIRROR_HEAD $(git -C "$MIRROR" rev-parse HEAD)"
echo "PLUGIN $SHA"
```

The clone on first run, the fetch and the reset are the only writes on the mirror: it becomes whatever `origin/main` is, a reproducible snapshot of upstream, never trusted as a working tree. The fetch reads the plugin's repository URL directly and takes every branch, so it needs no SSH key and still finds a plugin installed from a branch.

The plugin checks stop the sync in two cases. When the installed plugin differs from the one this session loaded, the skill text running now is stale: the owner restarts Claude Code. Never run the update commands and retry in the same session. When upstream `main` holds commits the installed plugin doesn't, the instance's files would align with a template whose plugin skills (this one included) the machine doesn't have yet: the owner updates the plugin and restarts.

After this, capture:

- `MIRROR_HEAD` = the commit printed by the block
- `MIRROR_VERSION` = the latest `## v...` heading in `<mirror-path>/CHANGELOG.md`

### Phase 4 — Scan the instance

Walk the instance's repository (`<instance-path>`) and collect files with `origin: maestro` in their frontmatter. The scan should cover:

- `CLAUDE.md` (root)
- `.claude/skills/*/SKILL.md`
- `.claude/agents/*.md`

Leave out every file under a retired path of Phase 6b (`.claude/skills/maestro-sync/`, `.claude/skills/setup/`, `.claude/skills/.disabled/setup/`, `.claude/skills/listen/`): they are never diffed and never lower the version floor.

For each match, read the file's `maestro_version` value. Build a list:

```
[
  { path: "CLAUDE.md",                              version: "v2026.04.29.1" },
  { path: ".claude/skills/add-external-app/SKILL.md", version: "v2026.04.30.1" },
  { path: ".claude/agents/librarian.md",            version: "v2026.04.30.1" },
  ...
]
```

If `maestro_version` is missing in a file that has `origin: maestro`, treat it as the baseline `v2026.04.29.1` (the snapshot version before versioning was introduced).

### Phase 4b — Reverse scan: new files from upstream

Walk the **mirror** for `*.md` files with `origin: maestro` in their frontmatter, excluding the folders that hold template-only or plugin-distributed material: `docs/` (shaping and devflow material for the template itself), `plugins/` and `.claude-plugin/` (the Maestro Claude Code plugin, distributed separately, never through this skill), `user-skills/` (skills installed at user level, outside `maestro-sync`), and `.claude/skills/maestro-sync/` (a redirect left upstream for instances still running the retired local skill). Any remaining file whose path does **not** exist in the instance is a **new upstream file** — the instance-side scan cannot see it, so without this step it would never be delivered.

The reverse scan is glob-based on purpose (the whole mirror, not just the Phase 4 path list): future distributed files may live in paths that don't exist yet in older instances (e.g. a marked `howto/` guide).

List the candidates, then keep only the ones whose frontmatter (the lines between the first two `---` markers) declares `origin: maestro`:

```bash
set -o pipefail
git -C "<mirror-path>" ls-files -- '*.md' ':!:docs/**' ':!:plugins/**' ':!:.claude-plugin/**' ':!:user-skills/**' ':!:.claude/skills/maestro-sync/**' | while read -r f; do
  if awk 'NR==1 && !/^---$/{exit} /^---$/{n++; print; if(n==2) exit; next} {print}' "<mirror-path>/$f" | grep -q '^origin: maestro$'; then
    echo "$f"
  fi
done
```

`set -o pipefail` (works in both bash and zsh) makes the pipeline's exit status reflect a failing `git` on the left, instead of the `while read` loop's own status on normal EOF (0, regardless of what `git` did) — without it, a bad `<mirror-path>` reports "no new files" instead of erroring. The `awk` script now also bails with no output as soon as it sees the first line isn't `---`: a file with no frontmatter at all has nothing to extract, and its body is never scanned for a line that merely looks like the marker.

Build a second list from the output:

```
new_from_upstream: [
  { path: "howto/08-markdown-discipline.md", version: "v2026.08.01.1" },
  ...
]
```

These files join the Phase 6 flow after the diffed ones. A new file the owner declines is simply not copied — it will be re-proposed at the next sync (the owner can keep declining; nothing is recorded to suppress it).

### Phase 5 — Show changelog delta

Read `<mirror-path>/CHANGELOG.md`. The CHANGELOG is ordered most-recent-first, with each entry headed `## vYYYY.MM.DD.N — YYYY-MM-DD`.

Compute the **lowest** instance `maestro_version` across all scanned files (call it `INSTANCE_FLOOR`). Show the owner all CHANGELOG entries strictly between `INSTANCE_FLOOR` and `MIRROR_VERSION` (inclusive of `MIRROR_VERSION`, exclusive of `INSTANCE_FLOOR`).

Format:

```
🔍 Maestro changelog from your version to upstream:

## v2026.04.30.2 — 2026-04-30
**Theme**: Promote three patterns proven in a personal instance into the template.
- (Added) early-morning rule, YAML safety, wikilinks discipline

## v2026.04.30.1 — 2026-04-30
**Theme**: Available apps moves out of CLAUDE.md into preferences.md.
- (Changed) CLAUDE.md, preferences.example.md, add-external-app skill
- (Added) Distribution and modifications section

You are at: v2026.04.29.1 (oldest file in this instance).
Upstream is at: v2026.04.30.2.
```

This is **context** before the diff, not a confirmation prompt yet.

### Phase 5b — Compare `bin/*` against the mirror

Skills may call `bin/mem` options an older `bin/*` copy doesn't have yet: applying a skill diff before the instance's `bin/*` is current can point the owner at a flag their `bin/mem` doesn't support. Compare each tracked file under `bin/` in the mirror against the instance's copy by checksum (`<instance-path>`: the instance's repository root, as in Phase 4):

```bash
set -o pipefail
git -C "<mirror-path>" ls-files bin/ | while read -r f; do
  if [ ! -f "<instance-path>/$f" ]; then
    echo "missing $f"
  elif [ "$(shasum "<mirror-path>/$f" | awk '{print $1}')" != "$(shasum "<instance-path>/$f" | awk '{print $1}')" ]; then
    echo "differs $f"
  fi
done
```

`set -o pipefail` guards this pipeline the same way as the Phase 4b one, above — a bad `<mirror-path>` fails the block instead of silently reporting no drift.

Each line is `differs bin/<name>` or `missing bin/<name>`; a file that matches prints nothing. If the command produced any output, tell the owner before Phase 6 starts:

> ⚠ Your `bin/` is behind the mirror: <list of `differs`/`missing` lines>. Copy these from `<mirror-path>/bin/` before applying skill diffs — a skill may call an option your current `bin/mem` doesn't support yet.

Then ask: *"Copy them now? I back up `private/memories.db` and the scripts I replace first."* A `bin/` file the owner changed by hand is overwritten, so name any `differs` line they recognize as theirs. On yes, run:

```bash
set -eo pipefail
MIRROR="<mirror-path>"
INSTANCE="<instance-path>"
STAMP="$(date +%Y%m%d-%H%M%S)"
DB="$INSTANCE/private/memories.db"
BINBAK="$INSTANCE/private/bin.bak.$STAMP-pre-sync"
if [ -f "$DB" ]; then
  BACKUP="$DB.bak.$STAMP-pre-sync"
  python3 -c '
import sqlite3, sys
src = sqlite3.connect(sys.argv[1]); dst = sqlite3.connect(sys.argv[2])
src.backup(dst)
dst.execute("PRAGMA journal_mode=DELETE")
ok = dst.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
same = src.execute("PRAGMA page_count").fetchone() == dst.execute("PRAGMA page_count").fetchone()
dst.close(); src.close()
sys.exit(0 if ok and same else "The backup failed its integrity or size check: " + sys.argv[2])
' "$DB" "$BACKUP"
  [ -s "$BACKUP" ] || { echo "The backup is empty: $BACKUP" >&2; exit 1; }
  echo "backup $BACKUP"
fi
git -C "$MIRROR" ls-files bin/ | while read -r f; do
  if [ ! -f "$INSTANCE/$f" ] || ! cmp -s "$MIRROR/$f" "$INSTANCE/$f"; then
    if [ -f "$INSTANCE/$f" ]; then
      mkdir -p "$(dirname "$BINBAK/$f")"
      command cp -p "$INSTANCE/$f" "$BINBAK/$f" </dev/null
    fi
    mkdir -p "$(dirname "$INSTANCE/$f")"
    command cp -p "$MIRROR/$f" "$INSTANCE/$f" </dev/null
    echo "copied $f"
  fi
done
[ -d "$BINBAK" ] && echo "old scripts $BINBAK"
env -u MEM_DB -u MEM_SCOPE "$INSTANCE/bin/mem" stats
```

`bin/mem stats` opens the db right after the copy, so a schema migration that the new `bin/mem` carries runs while the backup is minutes old. On no, go on to Phase 6 with the warning standing. Scripts upstream deleted stay in the instance's `bin/`; the drift check never lists them. The exception is the scripts of a retired unit, which Phase 6b proposes for removal.

**When the block exits non-zero after copying** (the output shows `copied` lines): stop the sync and show the output. Offer the way back, and run it only on the owner's yes, with the paths the block printed:

```bash
set -eo pipefail
INSTANCE="<instance-path>"
BINBAK="<old-scripts-path>"
BACKUP="<backup-path>"
command cp -Rp "$BINBAK/bin/." "$INSTANCE/bin/" </dev/null
command rm -f -- "$INSTANCE/private/memories.db-wal" "$INSTANCE/private/memories.db-shm"
command cp -p "$BACKUP" "$INSTANCE/private/memories.db" </dev/null
echo "restored bin/ and private/memories.db"
```

Scripts that were missing before the copy stay in `bin/` after the restore; they are unused by the old ones.

### Phase 6 — Per-file diff and confirmation

For each file in the scan list, compute the diff between the instance's version and the mirror's version of the same file path.

```bash
diff -u "<instance-path>/<file>" "<mirror-path>/<file>"
```

Skip files that are byte-identical (already up to date — common when the instance is mostly aligned).

**Frontmatter `tools:` exemption** (per `CLAUDE.md` → "Distribution and modifications"): when comparing skill or agent files, **ignore differences in the `tools:` frontmatter field**. The instance is free to extend that field with its own MCPs/tools, and those changes must survive the sync. Concretely: parse the YAML frontmatter, set `tools:` of the mirror version to match the instance's `tools:` before computing the diff, then proceed as usual on body and other frontmatter keys. If only `tools:` differs, the file is considered identical and skipped.

For each file with a non-empty diff, show:

```
─── <file> ───
Instance version: <maestro_version of instance file>
Mirror version:   <MIRROR_VERSION>

<unified diff, colorized if terminal supports it>

Apply this change?
  [a] apply this file
  [s] skip this file
  [A] apply all remaining files (no further prompts)
  [n] abort the whole sync
```

For files where the owner answers `a` or `A`:

1. Copy the mirror file over the instance file.
2. **Update the `maestro_version` in the file's frontmatter** to `MIRROR_VERSION`. The mirror file already has the correct value — copying preserves it.
3. Append an entry to `private/maestro-sync.log` (create the file if it doesn't exist):

```
2026-04-30T18:42:13Z  v2026.04.29.1 → v2026.04.30.2  CLAUDE.md (applied)
2026-04-30T18:42:13Z  v2026.04.30.1 → v2026.04.30.2  .claude/skills/add-external-app/SKILL.md (skipped by owner)
```

If the owner answers `n` (abort), stop immediately. Files already applied stay applied; files not yet shown are not touched. Log a final entry: `2026-04-30T18:42:13Z  ABORTED by owner after <N> files`.

**New files from the reverse scan (Phase 4b)** go through the same prompt, after all diffed files. Since there is no instance version to diff against, show the file's frontmatter (`description`, `maestro_version`) and the first ~30 lines of body instead of a diff, plus its total length:

```
─── NEW: <file> ───
Not present in this instance. Upstream version: <maestro_version>
Description: <frontmatter description>

<first ~30 lines of the file>
[... 145 more lines]

Add this file?
  [a] add this file
  [s] skip this file
  [A] apply all remaining files (no further prompts)
  [n] abort the whole sync
```

On `a` or `A`: copy the mirror file to the instance at the same relative path (creating parent directories if needed) and log it with the marker `(new)`:

```
2026-07-15T18:42:13Z  — → v2026.07.15.1  howto/08-markdown-discipline.md (new)
```

### Phase 6b — Retired paths

Some paths Maestro once distributed are gone upstream, and a sync can't see them through markers. List the ones still in the instance that carry `origin: maestro` (in a `SKILL.md` frontmatter, or in the first three lines of a script as `# origin: maestro` or `// origin: maestro`), so a skill or a script of the owner's that happens to share a name is never proposed:

```bash
INSTANCE="<instance-path>"
marked() {
  case "$1" in
    */SKILL.md) awk 'NR==1 && !/^---$/{exit} /^---$/{n++; if(n==2) exit; next} {print}' "$1" | grep -q '^origin: maestro$' ;;
    *) head -n 3 "$1" | grep -Eq '^(#|//) origin: maestro$' ;;
  esac
}
listen_running() {
  s="$HOME/.local/state/listen/current.json"
  [ -f "$s" ] || return 1
  pid=$(python3 -c 'import json, sys; print(int(json.load(open(sys.argv[1])).get("supervisor_pid") or 0))' "$s" 2>/dev/null) || return 1
  [ "${pid:-0}" -gt 0 ] && kill -0 "$pid" 2>/dev/null
}
for p in .claude/skills/maestro-sync .claude/skills/setup .claude/skills/.disabled/setup user-skills/maestro-net; do
  f="$INSTANCE/$p/SKILL.md"
  if [ -f "$f" ] && marked "$f"; then
    echo "retired $p"
    find "$INSTANCE/$p" -type f | sed "s|^$INSTANCE/|    |"
  fi
done
any=""
members=""
for m in .claude/skills/listen bin/listen bin/listen-updates bin/audiowatch.swift; do
  f="$INSTANCE/$m"
  [ -d "$f" ] && f="$f/SKILL.md"
  [ -f "$f" ] || continue
  if marked "$f"; then
    any=1
    members="$members    $m (marked)
"
  else
    members="$members    $m (not marked, kept)
"
  fi
done
if [ -n "$any" ]; then
  if listen_running; then
    echo "postponed listen: a capture is running"
  else
    echo "retired listen"
    printf '%s' "$members"
  fi
fi
true
```

- `.claude/skills/maestro-sync/`: the old local copy of this skill, or the redirect that replaced it.
- `.claude/skills/setup/` and `.claude/skills/.disabled/setup/`: instance creation moved to `/maestro:new-instance`.
- `user-skills/maestro-net/`: `maestro-net` moved into the plugin.
- `listen`, a unit of four members (`.claude/skills/listen/`, `bin/listen`, `bin/listen-updates`, `bin/audiowatch.swift`): the skill moved into the plugin as `/maestro:listen`, the scripts as `maestro-listen`. The unit goes with one answer: removing the scripts alone would leave the local skill, which still answers a bare `/listen`, calling scripts that are gone. Only the marked members go, copied to `private/retired.bak.<stamp>-listen/` first. While a capture is running the unit prints `postponed listen` and stays: an old `listen-updates` would lose its script and print errors until stopped by hand. Say so, and propose it again at the next sync.

For each printed path, show its files and ask *"Remove `<path>`? It was retired upstream."* For `listen`, ask *"Remove the old listen copy (<marked members>)? It moved into the plugin."* A yes covers that path or that unit only. On yes, run this block once for it, with `listen` as the retired path for the unit:

```bash
set -eo pipefail
INSTANCE="<instance-path>"
RETIRED="<retired-path>"
case "$RETIRED" in
  .claude/skills/maestro-sync|.claude/skills/setup|.claude/skills/.disabled/setup|user-skills/maestro-net|listen) ;;
  *) echo "Refusing to remove '$RETIRED': not a retired path." >&2; exit 2 ;;
esac
if [ ! -f "$INSTANCE/private/preferences.md" ] || [ ! -f "$INSTANCE/bin/mem" ]; then
  echo "Not an instance root: $INSTANCE" >&2
  exit 2
fi
if [ "$RETIRED" = "listen" ]; then
  marked() {
    case "$1" in
      */SKILL.md) awk 'NR==1 && !/^---$/{exit} /^---$/{n++; if(n==2) exit; next} {print}' "$1" | grep -q '^origin: maestro$' ;;
      *) head -n 3 "$1" | grep -Eq '^(#|//) origin: maestro$' ;;
    esac
  }
  listen_running() {
    s="$HOME/.local/state/listen/current.json"
    [ -f "$s" ] || return 1
    pid=$(python3 -c 'import json, sys; print(int(json.load(open(sys.argv[1])).get("supervisor_pid") or 0))' "$s" 2>/dev/null) || return 1
    [ "${pid:-0}" -gt 0 ] && kill -0 "$pid" 2>/dev/null
  }
  if listen_running; then
    echo "A capture is running: remove the old listen copy after it stops." >&2
    exit 3
  fi
  BAK="$INSTANCE/private/retired.bak.$(date +%Y%m%d-%H%M%S)-listen"
  for m in .claude/skills/listen bin/listen bin/listen-updates bin/audiowatch.swift; do
    f="$INSTANCE/$m"
    [ -d "$f" ] && f="$f/SKILL.md"
    [ -f "$f" ] || continue
    if marked "$f"; then
      mkdir -p "$(dirname "$BAK/$m")"
      command cp -Rp "$INSTANCE/$m" "$BAK/$m" </dev/null
      command rm -rf -- "$INSTANCE/$m"
      echo "removed $m"
    else
      echo "kept $m"
    fi
  done
  if [ -d "$BAK" ]; then
    echo "backup $BAK"
  fi
  exit 0
fi
command rm -rf -- "$INSTANCE/$RETIRED"
if [ "$RETIRED" = "user-skills/maestro-net" ]; then
  rmdir "$INSTANCE/user-skills" 2>/dev/null || true
fi
echo "removed $RETIRED"
```

Log it in `private/maestro-sync.log` with the marker `(retired, removed)` or `(retired, kept by owner)`. Files under these paths are never shown as orphans in Phase 7.

### Phase 7 — Final summary

After all files are processed (or the owner picked `A`), summarize:

```
✅ Maestro sync complete

Updated:  3 files  (CLAUDE.md, .claude/skills/add-external-app/SKILL.md, .claude/agents/librarian.md)
Added:    1 file   (howto/08-markdown-discipline.md — new from upstream)
bin:      2 files copied (bin/mem, bin/mem_schema.py), db backup private/memories.db.bak.20260915-143000-pre-sync
Removed:  1 retired path (.claude/skills/maestro-sync)
Skipped:  1 file   (.claude/skills/logbook/SKILL.md — owner declined)
Identical: 4 files (no change in upstream)

Instance now at: v2026.04.30.2

Log: private/maestro-sync.log
```

Omit the `Added:`, `bin:` and `Removed:` lines when they have nothing to report.

If everything was identical:

```
✅ Maestro sync — already up to date (v2026.04.30.2)
```

## Updating this skill

This skill carries no distribution marker and never appears in its own scan. A new version arrives with the plugin: `claude plugin marketplace update maestro`, `claude plugin update maestro@maestro`, then a restart. Phase 3 refuses to sync with a loaded plugin that differs from the installed one or is older than upstream `main`, so the skill that runs is never older than the files it applies.

## Bootstrap notes

**Brand new instance** (instance was just created from the template, never synced before):

- Files already carry the `maestro_version` declared in their frontmatter at template-clone time.
- First run of `maestro-sync` finds the mirror at `<MIRROR_VERSION>`. If the instance was created recently from `origin/main`, files match the mirror exactly → sync reports "already up to date".
- If the instance was created from an older commit, the diff workflow handles it normally.

**Old instance** (predates the introduction of `origin: maestro` frontmatter, ~before v2026.04.30.1):

- Files have no `maestro_version` (and possibly no `origin: maestro` either). Two recovery options:
  1. **Owner adds the markers manually** to the files they recognize as Maestro-distributed (CLAUDE.md, hub skills, base agents), using `maestro_version: v2026.04.29.1` as the safe baseline. Then runs `/maestro:maestro-sync`.
  2. **Create a new instance and reconcile by hand.** Heavier, but clean.

The skill itself does not auto-mark files — that would risk misclassifying instance customizations as upstream patterns.

## What this skill does NOT do

- Push to upstream. Promotions happen in the primary working tree (`maestro_worktree_path`), not from this skill.
- Edit files in `private/` (except the backups and the log it writes), `apps/`, or any file without `origin: maestro` marker, except `bin/*` and retired paths, each on the owner's explicit yes.
- Resolve conflicts when the owner has hand-edited a file marked `origin: maestro` and upstream also changed it. The diff is shown, the owner decides per file. Hand-editing `origin: maestro` files is discouraged in `CLAUDE.md` → "Distribution and modifications" precisely to avoid this.
- Run silently. Every phase that touches state (mirror reset, backups, file copy, removal, log append) reports to the owner.

## Memory log

Per the "Announce every write" rule, after the sync, insert one memory entry summarizing the run:

```bash
env -u MEM_DB -u MEM_SCOPE "<instance-path>/bin/mem" save "Maestro sync: <FROM_VERSION> → <TO_VERSION> (<N> files updated, <M> added)" -t maestro,sync,upstream -d "<list of updated/added files, comma-separated>. Skipped: <list>. Log: private/maestro-sync.log."
```

Announce:

```
📝 saved: "Maestro sync: <FROM_VERSION> → <TO_VERSION>" [maestro,sync,upstream] (memory)
```

## Failure modes

- **Mirror clone or fetch fails (no network)**: stop, report the error.
- **Loaded plugin differs from the installed one**: Phase 3 stops; the owner restarts Claude Code and runs the sync again.
- **Plugin behind upstream `main`**: Phase 3 stops with the update commands; the owner updates, restarts Claude Code and runs the sync again.
- **`bin/` copy fails after copying**: Phase 5b's restore block puts back the old scripts and the db backup, on the owner's yes.
- **Working tree has uncommitted changes and owner picks `push` but staging is needed**: refuse silently to `git add -A` (would risk staging files the owner didn't intend); ask the owner to stage manually and re-run.
- **CHANGELOG.md missing or unparseable in the mirror**: warn but continue — files are still diffable, just no high-level context.
- **A file marked `origin: maestro` exists in the instance but not in the mirror** (e.g. an old skill that has since been retired upstream and isn't in Phase 6b's list): show this in the summary as "orphan: file is no longer in upstream — keep, archive, or delete by hand?". Do not auto-delete.
