# CHANGELOG

Versioned record of intentional changes to the Maestro template — patterns, skills, agents, conventions distributed to instances.

Versions follow the **`vYYYY.MM.DD.N`** scheme (date-based, incremental within the day). Each entry documents what changed, why it matters, and any migration note for instances syncing in.

The skill `maestro-sync` reads this file from the latest pull of the read-only mirror (`~/.maestro/`) and shows the delta between an instance's current `maestro_version` and `HEAD` before applying file-level diffs.

---

## v2026.09.05.1 — 2026-09-05

**Theme**: `memories.db` learns to tell an **idea** from a **task**, and to stop hoarding. The two types have always been in the schema, but nothing said where the line falls, so undated work piled up as open ideas: things already decided, waiting only for a free afternoon, sitting in the one place the owner never looks while planning. The rule that closes the gap came from an instance owner during a backlog triage that took 56 open ideas down to 20.

### Added

- **`### Idea or task` in the Memory section of `CLAUDE.md`** — the criterion (an idea still holds an open question, a task holds only its execution), the corollary (a task with no date is still a task, and lives in the owner's task manager, not in `memories.db`), the conversion procedure (create the task, mark the idea `dismissed`, write the new id into the description so the trail survives), and the periodic review, where every surviving idea carries either the decision it waits for or the condition that wakes it up.

### Changed

- **`### Rules`** gains two lines: the `idea-<id>` convention that links a task to the idea that generated it, so an initiative can be read from either end; and the three-month check on open ideas, which either carry a live question or have already become a task elsewhere.

### Why

An idea backlog that grows without pruning stops being a backlog and becomes an archive: the owner scrolls past the same fifty rows and reads none of them. The decided work is the part that pollutes the most, because it looks like thinking while it's really just waiting. Sending it to the task manager empties the list of everything that has no question left in it, and what remains is short enough to be read in one pass.

### Migration

Nothing breaks: the schema is unchanged and existing rows stay valid. On the first sync, instances should run one pass over their open ideas and split them, moving anything already decided into their own task manager (with a reference back to the source id), and tagging what stays with its pending decision or its wake-up condition. Instances with no external task manager keep those rows as `task` with `status: todo` and no `due_date`.

---

## v2026.08.26.2 — 2026-08-26

**Theme**: **maestro-net**, the cross-talk channel between an owner's Maestro instances. An owner living in several contexts runs several instances, each with its own memory and its own domain, and the separation holds until something learned in one belongs in another. Two verbs cross that gap, `recap` and `ask`, under one constraint: the channel carries memories, never permissions.

### Added

- **`user-skills/maestro-net/maestro-net`** (Python, stdlib only) — the tool behind the channel. `recap <instance> "<text>"` writes a memory into the recipient's db by invoking **their** `bin/mem` with an absolute path, tagged `from:<sender>`, with no model involved. `ask <instance> "<question>"` runs `claude -p` in the recipient's directory, so their `CLAUDE.md`, preferences and memory apply, and reports the answer; the prompt carries a read-only clause and no persistent session is opened. `scan` censuses the instances on disk, `list` shows what is registered and flags dead paths. The sender of a recap resolves in three steps (`--from`, the registry name of the current directory, that directory's name) and the confirmation states which one applied. `MEM_DB` and `PWD` are stripped from the remote process's environment, so a caller that declares its own database can't divert a recap into it.
- **`user-skills/maestro-net/SKILL.md`** — the skill, meant to be installed **user-level** in `~/.claude/skills/`. The typical caller is a development session in an unrelated repository that has no Maestro skills loaded, so a project-level skill would never fire. The Maestro repository authors it and owns its version, tests and changelog; installation is a copy.
- **`~/.claude/maestro-instances.yaml`** (registry, written by the owner) — schema `version` plus `instances.<name>.{path, domain, accepts}`. `domain` carries the routing when the owner names no recipient; `accepts` lists the verbs that instance allows, and absent or empty means none. Deliberately outside `~/.maestro/`, which is the read-only template mirror that `maestro-sync` resets with `git reset --hard`.
- **`howto/11-maestro-net.md`** — the pattern: the constraint and the incident behind it, the two verbs, the registry schema, why the skill is user-level, the installation path through chezmoi, the exit-code table, and the reading side that isn't built yet.
- **`tests/test_maestro_net.py`** — 59 tests, stdlib only, no real instances and no network: `TestRegistryLoading`, `TestInstanceResolution`, `TestAcceptsGate`, `TestRecap`, `TestAsk`, `TestScan`, `TestCli`. Both verbs run against recorder scripts that capture argv, cwd and environment. Run: `python3 -m unittest tests.test_maestro_net`.

### Changed

- **`README.md`** — `user-skills/` listed among the repository's components, and the `howto/` index brought back in line with the folder (guides 08 to 11 were missing).

### Why

- The four instances already existed on disk with their own `bin/mem`, and the primitives were already there: `bin/mem` invoked with an absolute path resolves its database from the script's location, and `claude -p` run in another directory inherits that instance's `CLAUDE.md`. What was missing was the addressing — the paths would otherwise be hardcoded in whoever typed the command — and a place for the skill where any session can see it.
- `handoff` was dropped from the design. Pushing a memory covers most of what it was for, and a verb that opens a session inside another instance is exactly the kind of reach the constraint exists to prevent.
- `accepts` is what turns the constraint from an intention into a value. The precedent: a work instance once read the owner's personal task manager, because MCP servers load user-level and are visible to every session regardless of folder. Preferences declared the boundary and nothing enforced it.
- The registry parser is a small strict reader rather than a YAML dependency, so a line it doesn't understand is an error with a line number instead of a silently missing instance. Same reasoning behind the exit-code table: a channel that can't deliver says so, and a recap that can't reach its recipient is never written somewhere else.
- The scanner reads the real `cwd` out of the transcripts under `~/.claude/projects/`, because those directory names are slugs where `-` replaces `/`, `.` and spaces, and can't be turned back into paths.

### Migration

- Nothing arrives through `/maestro-sync`: `user-skills/` is outside its scope by design, since the skill is installed user-level rather than into an instance. Copy it by hand: `cp -R user-skills/maestro-net ~/.claude/skills/`, then `chezmoi add ~/.claude/skills/maestro-net` if `~/.claude` is chezmoi-managed.
- Populate the registry with `~/.claude/skills/maestro-net/maestro-net scan --write`, then fill in each `domain` and review each `accepts`. The scanner proposes both verbs for every instance it finds; narrow it with `--accepts recap` if the owner would rather grant `ask` case by case.
- Nothing changes for an instance that doesn't install it. No file distributed to instances was touched, and `memories.db` is unchanged: a recap is an ordinary `memory` row that happens to carry a `from:` tag.

---

## v2026.08.26.1 — 2026-08-26

**Theme**: The logbook learns to read the **parallel sessions** of the day. Claude Code's agent view lets the owner keep several conversations open at once and jump between them; the memories they produce already converge in `memories.db`, but the thread of each discussion stayed locked in its own transcript, visible only to the session that hosted it. Two behaviors instances had been growing on their own — flushing the warm task channel before writing, and documenting a day other than today — are absorbed into the template in the same pass.

### Added

- **`bin/session-digest`** (Python, stdlib only, no network) — extracts, for a given day, the messages the owner typed in every session of the current project. Reads the transcripts under `~/.claude/projects/<slug>/*.jsonl` (override with `CLAUDE_PROJECTS_ROOT`) and returns each session's name plus its messages in chronological order. Human messages are identified by `origin.kind == "human"`, which excludes tool results, subagent traffic (`isSidechain`) and harness noise (`<system-reminder>`, command wrappers) without heuristics on the text. Session names come from the last `custom-title` record, so a rename wins over the original; `ai-title` is the fallback. The assistant's replies stay out: they run to megabytes, while a full day of the owner's messages fits in a few KB. Filtering is by message timestamp rather than file mtime, because a session open across several days holds messages from all of them. Sessions whose messages are a strict subset of another's are dropped as shadow transcripts, the pair a backgrounded or forked conversation leaves behind (`--no-dedup` keeps them). Options: `--date` (`YYYY-MM-DD`, `today`/`oggi`, `yesterday`/`ieri`, `Nd`), `--cwd`, `--session`, `--exclude-session`, `--max-chars`, `--json`. Exit 0 clean (an empty day is not an error), 2 when no transcript directory matches the project.
- **`tests/test_session_digest.py`** — 21 tests, stdlib only, no real transcripts: `TestExtraction`, `TestDayBoundary`, `TestShadowSessions`, `TestSelection`, `TestCli`. Run: `python3 -m unittest tests.test_session_digest`.

### Changed

- **`.claude/skills/logbook/SKILL.md`** — new step 3 in the procedure, `Pick up the threads of the parallel sessions`, invoking `bin/session-digest` before grouping by theme. It states that the db stays the source of facts while the digest carries context and nuance, asks that anything substantial found only in the digest be saved as a memory before the note is written, and degrades without blocking when the script is missing. `## Sources for composing the note` gains the parallel sessions as source 3, and records that the db is the one source already spanning every session. The closing confirmation now reports how many sessions fed into the note.
- **`.claude/skills/logbook/SKILL.md`** — new step 2, `Pre-flush the warm task channel`: when `preferences.md` declares a `## Warm task channel` block with `channel != none`, the skill named there runs its `## Garbage Collector` before the note is composed. Writing the logbook is an end-of-session trigger, so the tasks closed in the warm layer land in `memories.db` dated to the target day instead of staying behind in the task manager. Announces only when it archives something, degrades without blocking, skips entirely when no channel is declared.
- **`.claude/skills/logbook/SKILL.md`** — new step 3, `Decide which day you are documenting`: the target day follows the same early-morning rule that already governs every write to `memories.db`. Called before 06:00 local with no note yet for the previous day, the skill documents the previous day and pulls in the entries of the night that follows, which are the tail of the same lived session. The filename carries the target day rather than the day of writing, and the closing confirmation reports it when the two differ.
- **`README.md`** — `bin/session-digest` listed next to `bin/mem`.
- `maestro_version` bumped to `v2026.08.26.1` on `.claude/skills/logbook/SKILL.md` and `bin/session-digest`.

### Why

- Instances write memories from any session, so the *facts* of a parallel day already converge. What evaporated was the reasoning around them: constraints that emerged, options discarded, threads left open with no recorded outcome. The owner had to remember to flush each session before leaving it, which is a discipline that fails exactly on the busy days worth documenting.
- Reading only the owner's messages is what makes this affordable. Measured on a real instance, the busiest session of a day held 11 KB of typed text against a transcript of several megabytes. The owner's side alone is enough to reconstruct what a session was about, and the db supplies the outcomes.
- A separate script rather than instructions in the skill: the parsing has enough edge cases (day boundaries in local time, shadow transcripts, noise in the `user` channel) that prose instructions would have been re-derived, differently, at every invocation.
- The warm-channel pre-flush and the target-day rule arrive from an instance that had written them into its local copy of the skill. Both are general: the warm task channel is already a template pattern (`howto/07`, session-start step 4) whose skill simply never got invoked at logbook time, and the early-morning rule is already stated in `CLAUDE.md` for every `memories.db` write. Leaving them in a fork meant the instance stopped receiving diffs on a distributed file, which is how a local customisation quietly costs an instance every future update.

### Migration

- Run `/maestro-sync`: `.claude/skills/logbook/SKILL.md` arrives as a diff. **`bin/session-digest` needs a manual copy**, since `bin/*` stays outside sync scope: `cp ~/.maestro/bin/session-digest bin/ && chmod +x bin/session-digest`. Optionally `cp ~/.maestro/tests/test_session_digest.py tests/`.
- Without the script the skill still runs: step 3 degrades to a minor note and the logbook is composed from the db and the current conversation, as before.
- Instances that had forked their `logbook` skill locally to add a warm-channel pre-flush or a target-day rule can now drop the fork and take the upstream file whole: both behaviors are in the template. Check that the frontmatter carries `origin: maestro` again, otherwise `maestro-sync` keeps treating the file as local and offers no further diffs.
- Nothing to migrate in `memories.db`, and no change to how the note is written.

---

## v2026.08.14.1 — 2026-08-14

**Theme**: A **writing register** distributed to every instance: seven prose prohibitions that bind any text the orchestrator produces for a human reader, plus a Maestro-owned post-pass skill and a deterministic checker. The template had opinions about *where* files go and *how* they are tagged, and none about how the prose reads.

### Added

- **`## Writing register` in `CLAUDE.md`** (~14 lines, after `## Tone`) — the seven prohibitions condensed, the perimeter, the post-pass, and the pointer to the canonical reference. Same pointer-plus-canonical-source shape as `## Markdown discipline`. The prohibitions: 1 meta-commentary on the text itself, 2 sycophantic concessions, 3 negative parallelism in every variant including the tailing form, 4 em dash as a pause, 5 bold as rhetorical emphasis, 6 rhythmic triads, 7 judgment as tone of voice.
- **`howto/10-writing-register.md`** — canonical reference: perimeter, the seven prohibitions with bilingual (EN/IT) before-and-after examples, the removal test for prohibition 7, post-pass mechanics, the extended net, `bin/register-check` usage, the exceptions block, and a `## Reference` section crediting [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) and [`humanizer`](https://github.com/blader/humanizer) (MIT).
- **`.claude/skills/writing-register/SKILL.md`** — post-pass on finished text, invoked before every vault write and every post or comment going to an external channel, with no length threshold. Checks the seven prohibitions plus a wider net (vague attributions, promotional language, `-ing` analyses, hedging, filler, false ranges, elegant variation, copula avoidance). **Fidelity guard**: form only, no claim added or removed, quotations and code and paths and numbers and proper nouns off limits, unresolvable passages left and reported. **Silent delivery**: returns the corrected text with no summary of changes.
- **`bin/register-check`** (Python, stdlib only, no network) — deterministic check of the four prohibitions with a syntactic signature: 3 negative parallelism (11 patterns across Italian and English, including the tailing `Y, not X` form), 4 em dash as a pause, 5 bold outside structural-label position, 6 rhythmic triads. Rules 4 and 5 report as `violation`, rules 3 and 6 as `candidate`. Skips YAML frontmatter, fenced blocks and blockquote lines; masks inline code, wikilinks, link targets and bare URLs before matching, preserving column numbers. Triad detection counts the whole enumeration run, so three consecutive items inside a longer list do not fire. `--skip N,M` suspends rules, `--json` emits machine-readable output, exit 0 clean / 1 findings / 2 usage error.
- **`tests/test_register_check.py`** — 54 tests, stdlib only, always run: `TestRule3NegativeParallelism`, `TestRule4EmDash`, `TestRule5Bold`, `TestRule6Triads`, `TestMasking`, `TestSkip`, `TestCli`. Run: `python3 -m unittest tests.test_register_check`.
- **`## Writing register` block in `preferences.example.md`** — optional per-instance exceptions: `suspended: [4, 6]` and `post_pass: on|off`. The section absent means the full register with the pass on, so `setup` writes nothing new.
- **`docs/shaping-writing-register.md`** — shaping doc for the grill session of 2026-08-14: the fourteen decisions, the two that moved during the session, the rejected alternatives.

### Changed

- **`.claude/agents/librarian.md`** — new `## Writing register` section. Binds the reports handed back to the orchestrator, because the synthesis inherits the shape of its source, and any `description` or body text written in the owner's territories.
- **`.claude/agents/scheduler.md`** — new `## Writing register` section, focused on the two prohibitions that bite on a structured list: meta-commentary and judgment as tone.
- **`.claude/skills/logbook/SKILL.md`** — new `## Writing register` section, plus the instruction to pass the finished note through the `writing-register` skill before writing it, and to confirm path and tags without narrating what the pass changed.
- **`CLAUDE.md` `## Tone`** — the "Direct, no fluff" bullet rewritten to drop an em dash used as a pause and a definition by negation.
- `maestro_version` bumped to `v2026.08.14.1` on: `CLAUDE.md`, `howto/10-writing-register.md`, `.claude/skills/writing-register/SKILL.md`, `.claude/skills/logbook/SKILL.md`, `.claude/agents/librarian.md`, `.claude/agents/scheduler.md`, `bin/register-check`.

### Why

- The seven prohibitions are a strict subset of the 29 patterns in the external `humanizer` skill. Three ways to get them into instances were on the table: depend on the external skill, vendor its `SKILL.md`, or inline its content. Skills load lazily and `CLAUDE.md` loads in full at every session start, so a Maestro-owned skill costs one `description` line per session while inlining 27 KB would have undone the compression release B of the spring upgrade paid for.
- The external skill stays out of the automatic flow on purpose. Its process is interactive (two prompts, three output blocks) and it carries no fidelity guard: its own canonical example removes a cited study, two named interviewees and a set of figures from the text it rewrites. On a Basecamp comment that is the difference between a post published and a post retracted.
- No length threshold, because the discriminant is reversibility rather than length. A two-line comment on a public channel is harder to take back than a thirty-line note that stays on disk.
- Existing template prose was left untouched. `CLAUDE.md` still contains 84 em dashes used as pauses inside the file that bans them, which works against prohibition 4 by imitation. Accepted knowingly: rewriting 84 sentences in a behavioral specification risks moving the meaning of instructions, and specification files sit outside the register's perimeter anyway.

### Migration

- Run `/maestro-sync`. `howto/10-writing-register.md` and `.claude/skills/writing-register/SKILL.md` arrive as new files through the reverse scan; `CLAUDE.md`, `logbook`, `librarian` and `scheduler` arrive as diffs.
- **`bin/register-check` needs a manual copy**, since `bin/*` is still outside sync scope: `cp ~/.maestro/bin/register-check bin/ && chmod +x bin/register-check`. Optionally `cp ~/.maestro/tests/test_register_check.py tests/`. Without the tool the skill still runs, doing the whole pass by reading.
- **`preferences.example.md` does not reach existing instances**, because `setup` removes the root templates after the first run. Instances that want the exceptions block add the section by hand, following `howto/10-writing-register.md` → "Per-instance exceptions". Instances that want the full register do nothing.
- Nothing to migrate in `memories.db`, and no change to any existing behavior beyond the shape of the prose.

---

## v2026.07.16.2 — 2026-07-16

**Theme**: Extend the semantic layer to the markdown **vault**, chunked by section — one fused recall over `memories.db` *and* the vault. Built on v2026.07.16.1 and fully additive: `log`/`log_vec` are untouched, and an instance that never supplies a vault root behaves exactly as before. Same model, dimensions, and vector format as `log_vec`, so the two indexes are co-queryable.

### Added

- **Markdown chunker in `bin/mem-vec`** (stdlib only — `re`, `fnmatch`, `hashlib`, `pathlib`): `parse_frontmatter`, `split_sections` (splits on `##`/`###`, ignores headings inside code fences, keeps the heading chain), `subsplit` (light overlap for oversized sections), `build_embed_text` (a **context sign** — file `description` + heading chain + `tags` — prepended to the chunk so cryptic headings still embed meaningfully), `make_snippet`, `compute_chunk_id`, `chunk_file`. No new dependency.
- **`vault_vec` table** — additive, self-creating alongside `log_vec` (PK = `sha256(rel_path | heading_path | sub_index)`; stores `rel_path`, `heading`/`anchor`, per-row `model`/`dims`, `content_hash`, `snippet`, `file_mtime`, and the float32-LE `embedding`). `rel_path` (relative, not absolute) keeps the index portable across machines.
- **Vault walk + `.mem-ignore`** — `walk_vault`/`load_ignore` iterate `*.md` under each root, honoring a `<vault_root>/.mem-ignore` (gitignore-style: comments, globs, `dir/`, `!negation`); dot-directories are always skipped. The ignore file lives in the vault (travels with it via iCloud/across machines), never in the template.
- **Root injection** — `bin/mem embed --root <path>` (repeatable) or env `MEM_VAULT_ROOTS` (`:`-separated). The engine stays preferences-agnostic; the orchestrator, which already reads `vault_path`, is the natural bridge. No root → `embed` does memories only, silently.
- **Incremental vault embed** — `scan_vault_state` classifies chunks as pending/stale/ok/orphan via an `mtime` pre-filter plus per-chunk `content_hash`: editing one section re-embeds only that section, deleting a file removes its chunks (orphan cleanup).
- **Fused search** — `search --semantic` merges `log_vec` + `vault_vec` in the data layer into a single ranking with a `source` field (`memory`/`vault`), a citable `ref` (`#id` or `rel_path#Section`, ready for an Obsidian `[[file#Section]]` wikilink), `score`, and `snippet`. Anti-flooding cap `--vault-frac` (default 0.6) and `--min-score` threshold; `--only memory|vault` restricts the source.
- **`tests/test_mem_vec.py`** — `TestChunker`, `TestIgnoreWalk` (stdlib, always run) plus `TestVaultEmbed`, `TestFusedSearch` (self-skip without sqlite-vec/Ollama). Full run green: 26 tests under `uv run --python 3.12 --with sqlite-vec python -m unittest tests.test_mem_vec`.

### Changed

- **`bin/mem` semantic output columns** — now `source | ref | title | score | snippet` (was `id | date | type | status | title | tags | score`). `search --semantic` forwards `--only`/`--vault-frac`; `embed` forwards `--root`.
- **`bin/mem-vec embed --status` shape** — now nested: `{"model", "memory": {…}, "vault"?: {…}}` (top-level `embedded`/`total`/`stale`/`missing` moved under `memory`). `bin/mem`'s human `--status` line was updated to read the nested shape and print a vault summary.
- **`CLAUDE.md` → `### Semantic layer (optional)`** — notes the layer now spans `log` + the markdown vault, `embed`'s `--root`/`MEM_VAULT_ROOTS`, and the `source`/`ref`/`--only` of fused search.
- **`howto/09-memoria-semantica.md`** — new "Vault index (chunked)" section (root injection, `.mem-ignore`, output columns, anti-flooding, degrade).
- `maestro_version` bumped to `v2026.07.16.2` on: `CLAUDE.md`, `howto/09-memoria-semantica.md`, `bin/mem`, `bin/mem-vec`.

### Why

- The richest context in an instance lives in the vault (logbooks especially), yet the semantic layer only saw `memories.db`. A real miss — a client whose context lived only in a logbook — was found by neither keyword nor `--semantic`, only a manual `rg`. Chunk-by-section indexing closes that gap while keeping the `.md` files the single source of truth: the db stores only vectors + a `path#anchor` pointer + a short snippet, never the prose (recovered on demand by opening the file).
- No new failure mode: same exit-3 degrade, same model/format, additive tables. Root absent → memories only. The engine never parses preferences; the vault root is declared once (in the instance) and injected by the caller.

### Migration

- Run `/maestro-sync`: `howto/09-memoria-semantica.md` arrives as a diff and `CLAUDE.md` gains the vault notes; copy `bin/mem` and `bin/mem-vec` from the mirror manually (`bin/*` stays outside sync's diff scope — `cp ~/.maestro/bin/mem bin/mem`, same for `mem-vec`).
- To index the vault on an instance: create `<vault_path>/.mem-ignore` (at least `Diario/` for privacy + noise globs like `*.excalidraw`), export `MEM_VAULT_ROOTS=<vault_path>` before `bin/mem embed` (e.g. in the session-start hook — today it runs rootless and would keep doing memories only), then `bin/mem embed --rebuild` once. Without a root, `bin/mem` is unchanged.
- **Contract change**: any consumer parsing `bin/mem embed --status` JSON must read `memory.*` (and optional `vault.*`) instead of the former top-level keys.

---

## v2026.07.16.1 — 2026-07-16

**Theme**: Optional semantic layer for `memories.db` — recall by meaning, duplicate detection, pattern discovery — built and calibrated on a real instance (Alfred), then upstreamed. Strictly opt-in per machine and fully additive: an instance without Ollama/uv behaves exactly as before.

### Added

- **`bin/mem-vec`** (new, PEP 723 script) — the data layer. Runs via `uv run --script`, declares its own dependency (`sqlite-vec`) inline, needs no project-level install. Talks to a local Ollama instance for embeddings (default model `bge-m3`, override via `MEM_EMBED_MODEL` or `--model`). Commands: `embed` (vectorize new/changed rows, `--rebuild`/`--status`), `search` (cosine similarity ranking), `similar` (rows close to a given id), `dupes` (candidate duplicate pairs). Vectors live in `log_vec`, a plain additive table that self-creates on first use — `log` and `memories.db.template` are untouched.
- **`bin/mem`** — thin delegation to `bin/mem-vec` via a new `_vec_run` helper (`uv run --script`, capturing stdout/stderr). New subcommands `embed`, `similar`, `dupes`; `search` gains `--semantic`, `--min-score`, `--model` and branches to `_cmd_search_semantic` in `cmd_search` when `--semantic` is set. `EXIT_SEM_UNAVAILABLE = 3` is returned (with a clear stderr message) whenever `uv` is missing or Ollama is unreachable — every other command is unaffected. Epilog documents exit code 3.
- **`tests/test_mem_vec.py`** (new, + `tests/__init__.py`) — stdlib-only unit tests (content hashing, pack/roundtrip, `log_vec` auto-creation, embed-state lifecycle) plus integration tests that self-skip when `sqlite-vec` or Ollama aren't available in the running interpreter. Full run: `uv run --with sqlite-vec python -m unittest tests.test_mem_vec -v`.
- **`howto/09-memoria-semantica.md`** (new, `origin: maestro`) — setup (`brew install ollama uv`, `ollama pull bge-m3`, `bin/mem embed --rebuild`), command reference, how embeddings are derived data (rebuildable from scratch, safe across machine changes), degradation behavior, and the evolution markers that signal a future move to vec0 KNN indexes (scale) or an FTS5 hybrid (exact-term recall).
- **`CLAUDE.md` → `## Memory`**: new `### Semantic layer (optional)` subsection (between `### Commands — via bin/mem` and `### Rules`) documenting the four commands, the anti-duplication rule (`--semantic --limit 3`, propose update on score ≥ 0.80 instead of inserting a duplicate), and the degradation rule (exit 3 → silent keyword fallback, never surfaced as an error).

### Why

- Keyword search on `log` misses paraphrases and near-duplicates by construction — the owner routinely thinks in concepts, not in the exact words a past entry used. A semantic layer closes that gap without touching the write path or the schema instances already depend on.
- Zero-risk by design: additive table, opt-in per machine (no Ollama/uv → identical behavior to today), derived data (embeddings are a pure function of text + model, always reconstructible via `--rebuild`), and delegated to a separate PEP-723 script so `bin/mem`'s own dependency surface stays at zero.
- `bge-m3` and the `0.80` anti-duplication threshold are concrete defaults calibrated against a real instance's data, not placeholders — instances can retune both without any code change.

### Migration

- Run `/maestro-sync`: `bin/mem`, `bin/mem-vec`, `tests/test_mem_vec.py`, `tests/__init__.py`, `howto/09-memoria-semantica.md` arrive as diffs/new files; the `CLAUDE.md` diff adds the `### Semantic layer (optional)` subsection. `bin/*` stays outside sync's diff scope for `maestro_version` bookkeeping — copy manually if the sync skill doesn't offer it (`cp ~/.maestro/bin/mem bin/mem` etc.).
- To activate on an instance: `brew install ollama uv && brew services start ollama && ollama pull bge-m3 && bin/mem embed --rebuild`. Without this setup, `bin/mem` is unchanged — semantic subcommands simply exit 3.

---

## v2026.07.15.2 — 2026-07-15

**Theme**: Slim `CLAUDE.md` from 489 to ~260 lines — second half of the "spring upgrade" (see `docs/shaping-spring-upgrade.md`). Behavioral rules stay resident and are rewritten tighter; reference material moves to canonical sources loaded on demand. **No rule was dropped** — only prose, examples, and duplicated reference were compressed or extracted.

### Added

- **`howto/08-markdown-discipline.md`** — new distributed reference file (`origin: maestro`, the first marked howto) carrying the full markdown discipline extracted from `CLAUDE.md`: frontmatter style (tags + description), YAML safety with examples, Obsidian wikilink rules. Delivered to instances by the reverse scan shipped in v2026.07.15.1.

### Changed

- **`CLAUDE.md`** — restructured (~-47%):
  - "Frontmatter and search discipline" + "YAML safety" + "Linking discipline" merged into one condensed **"Markdown discipline"** section (all rules kept) pointing to `howto/08` for details and examples.
  - **Memory section**: the SQL schema block is dropped (the schema ships in `memories.db.template`; type/status semantics stay inline); the full `bin/mem` command/report reference is replaced by a ~10-line cheatsheet plus `bin/mem --help` as the canonical reference.
  - Verbose behavioral sections (Session start step 4, Validation before touching a sub-app, Preferences evolution, Delegation, Handoff) rewritten tighter with every rule preserved.
- **`bin/mem`** — argparse help texts enriched so `--help` can serve as the canonical reference: top-level epilog documents relative dates, the early-morning rule, output modes, and `MEM_DB`; per-flag help added for `--date`, `--due`, `--status` (allowed values per type), `--bulk` (row keys), `marker`, and `search` filters. No behavior change.
- **`.claude/skills/logbook/SKILL.md`** — points to `howto/08-markdown-discipline.md` for the markdown discipline; the "retrieve today's entries" step uses `bin/mem today` (raw `sqlite3` kept as fallback).
- **`.claude/agents/librarian.md`** — frontmatter-discipline section points to `howto/08-markdown-discipline.md`.
- `maestro_version` bumped to `v2026.07.15.2` on: `CLAUDE.md`, `howto/08-markdown-discipline.md`, `.claude/skills/logbook/SKILL.md`, `.claude/agents/librarian.md`.

### Why

- ~40–45% of the old `CLAUDE.md` was reference material, not behavior. Loaded at every session start in every instance, it diluted the weight of the rules that matter (announce-every-write, access gate) and cost ~7–8k tokens per session. Reference belongs where it can't drift: the CLI documents itself via `--help`, the markdown discipline lives in one distributed file that skills and agents point to.
- Future SQLite work (FTS5, indexes, `sqlite-vec`) will land in `bin/mem` and its `--help` without touching `CLAUDE.md` again.

### Migration

- Instances that applied v2026.07.15.1 (reverse scan): run `/maestro-sync` — the slimmed `CLAUDE.md`, `logbook`, `librarian` arrive as diffs; `howto/08-markdown-discipline.md` is proposed as a new file. Copy `bin/mem` manually from the mirror (`cp ~/.maestro/bin/mem bin/mem`) — `bin/*` is still outside sync scope.
- Instances still on ≤ v2026.05.28.1: run `/maestro-sync` **twice** — the first run installs the reverse-scan-capable skill, the second delivers the new howto. The CLAUDE.md diff applies on the first run either way; the pointer to `howto/08` stays dangling until the second run (harmless: the condensed rules in CLAUDE.md are self-sufficient).
- Instances that hand-edited their `CLAUDE.md` despite the distribution rule: review the diff carefully per file — this release rewrites most lines.

---

## v2026.07.15.1 — 2026-07-15

**Theme**: Close the new-file delivery gap in `maestro-sync` — first half of the "spring upgrade" (see `docs/shaping-spring-upgrade.md`). Until now the skill only scanned the instance, so files created upstream after an instance was cloned (new skills, `bin/mem`, marked howtos) were never proposed and required manual copies.

### Added

- **`maestro-sync` → Phase 4b — Reverse scan**: after scanning the instance, the skill walks the mirror for `*.md` files marked `origin: maestro` whose path doesn't exist in the instance, and proposes each as a **new file** in the per-file confirmation flow (content preview instead of diff, same `a/s/A/n` prompt, `(new)` marker in the log, `Added:` line in the final summary). The reverse scan is glob-based over the whole mirror, so future distributed files are delivered regardless of where they live.

### Changed

- **`maestro-sync` → Memory log**: the post-sync memory entry now prefers `bin/mem save`, with raw `sqlite3` kept as fallback for instances that don't have the CLI yet.
- **`README.md`** — drift fixes: the roster ships with `librarian` and `scheduler` enrolled (was described as "empty at install"); the shipped skills/agents list and `bin/mem` are now stated; the howto index lists all seven guides (06 and 07 were missing); the Status section points at this CHANGELOG instead of "version 0.1.0".
- **`maestro-sync` frontmatter** — `maestro_version` bumped to `v2026.07.15.1`.

### Why

- The second half of the spring upgrade (planned as the next release) slims `CLAUDE.md` by extracting reference material into a **new** distributed file. Without the reverse scan, instances would sync the slimmed `CLAUDE.md` but never receive the file it points to. Shipping the sync fix **first** guarantees that by the time the refactor lands, every instance that syncs regularly already has the delivery mechanism.
- The manual-copy step documented for `bin/mem` in v2026.05.23.1 was a symptom of this gap. Note: `bin/mem` itself is still outside the scan scope (it carries a comment marker, not YAML frontmatter) — the reverse scan only covers `*.md` files for now.

### Migration

- Instances: run `/maestro-sync` and apply the `maestro-sync` skill diff. No data migration. From the **next** invocation onward, new upstream files will be proposed automatically.
- Instances that never copied `bin/mem` manually: the copy step from v2026.05.23.1 still applies (the reverse scan doesn't cover `bin/*` yet).

---

## v2026.05.28.1 — 2026-05-28

**Theme**: Promote two librarian disciplines proven in the Luigi instance into the base agent — tag parsimony and a symlink safety rail — generalized to be instance-agnostic.

### Changed

- **`.claude/agents/librarian.md`** gains two sections:
  - **`### Tag discipline — parsimony over creativity`** (under Frontmatter discipline): no orphan tags (a tag must be used by ≥2 files), reuse before inventing, prefer cross-cutting axes over content-descriptive adjectives, the orchestrator's controlled vocabulary wins on bulk catalog.
  - **`## Forbidden targets — symlinks to other repositories`** (after the catalog report format) + a matching `## Never` bullet: resolve `realpath` before any write, refuse to write if the real target sits outside the task's named territory (e.g. a symlink into an application code repo). Generic — names no specific repos.
- **`librarian.md` frontmatter** — `maestro_version` bumped to `v2026.05.28.1`.

### Why

Both patterns surfaced in the Luigi instance (Gestart) as hand-edits to the librarian: a tag-hygiene rule and a safety rail against writing through symlinks into application code. They are generic and benefit every instance, so they belong in the template rather than living as an instance fork.

### Migration

- Instances that had **not** customized `librarian.md`: pull via `maestro-sync` and apply the diff. No data migration.
- The Luigi instance carried these two sections as a local fork; after this promotion it re-aligns to the upstream (generalized) librarian and rejoins `maestro-sync` scope.

---

## v2026.05.23.2 — 2026-05-23

**Theme**: Extract the warm/cold/GC task pattern from instance-level boilerplate into a generic, opt-in Maestro feature. Instances declare a warm task channel in `preferences.md`; the orchestrator runs a lazy GC at session start. No hardcoded channel names in `CLAUDE.md`.

### Added

- **`howto/07-warm-task-channel.md`** — new how-to that describes the warm (external task system) / cold (`memories.db`) / GC (skill `<channel>-task-manager`) pattern, the skill contract, the archive-memory format, optional weekly trend, and reusability across instances. Includes worked examples for Slacky and Basecamp.
- **`preferences.example.md` → `## Warm task channel`** — new optional block with `channel`, `skill`, `archive_tag`, `marker_name`. Skip the block entirely (or set `channel: none`) to keep `memories.db` as the only task store.

### Changed

- **`CLAUDE.md` → `## Session start`** — added step 4 "Warm task channel — lazy GC" as an optional, channel-driven instruction. If `preferences.md` declares a warm task channel, the orchestrator invokes the named skill's `## Garbage Collector` section. Idempotency guard (1h), cross-week-boundary trend (if the skill defines it), non-blocking on errors, one-line announcement only when N > 0.
- **`CLAUDE.md` → `## Identity and customizations`** — added "Warm task channel" to the list of expected preferences blocks, marked optional.
- **`howto/README.md`** — added the new how-to to the index.
- **`CLAUDE.md` frontmatter** — `maestro_version` bumped to `v2026.05.23.2`.

### Why

- Pre-2026.05.23.2 instances that used a warm task channel (e.g. Alfred with Slacky) hardcoded the channel name in their own copy of `CLAUDE.md`, drifting from the template and making the same pattern hard to reuse on other instances (Pam with Basecamp, Claudio with Basecamp).
- Extracting the pattern lets every instance opt-in by editing `preferences.md` alone, without touching `CLAUDE.md`. New channels are added by writing a skill that conforms to the GC contract — the orchestrator's top-level behavior stays unchanged.
- The howto is the single source of truth for the contract, so each `<channel>-task-manager` skill (Slacky, Basecamp, etc.) can point at it instead of redefining the flow.

### Migration

- Instances with no warm task channel: **no action needed**. The new session-start step is a no-op when the preferences block is absent.
- Instances that already hardcoded a channel (e.g. Alfred): pull this version via `maestro-sync`, then move the channel declaration into a `## Warm task channel` block in `private/preferences.md` and delete any instance-level edits to `CLAUDE.md`'s session-start section. The existing `<channel>-task-manager` skill keeps working as-is — only the entry point moves from CLAUDE.md to preferences.

---

## v2026.05.23.1 — 2026-05-23

**Theme**: Ship `bin/mem` — a Python CLI wrapper for `memories.db` that replaces verbose raw SQL with a consistent, escape-safe, output-aware interface.

### Added

- **`bin/mem`** new executable Python script (stdlib only, no dependencies). Subcommands:
  - **Writes**: `save`, `task`, `idea`, `update`, `done`, `reopen`
  - **Reads**: `today`, `todo`, `overdue`, `search`, `show`, `stats`
  - **Bulk**: `save --bulk` reads a JSON array from stdin, inserts every row in a single SQLite transaction
  - **Markers**: `marker get|set <name>` for sync watermarks (upsert in-place on the `log` table — retro-compatible with marker rows created before the CLI existed)
- Cross-cutting features in the CLI:
  - Parameterized SQL — no more escape errors on apostrophes/accents/quotes
  - Relative dates: `today`, `yesterday`, `tomorrow`, `+Nd`, `-Nd`, `+Nw`, `+Nm`
  - Early-morning rule (00:00–06:00 → previous day) applied automatically when `--date` is omitted
  - Output: ASCII table on TTY, dense JSON on pipe; `--json` forces JSON
  - DB path resolution: env `MEM_DB` > `<repo-root>/private/memories.db` (auto-detected from the script's location)

### Changed

- **`CLAUDE.md` → `## Memory` → "Commands" / "Reports"** rewritten to promote `bin/mem` as the preferred access layer. Raw `sqlite3` is kept as a documented fallback for queries the CLI doesn't cover (custom joins, integrity checks, vacuum, `ALTER TABLE`).
- **`howto/04-memory-and-integrations.md`** new section "CLI helper — `bin/mem`" explaining the why and the surface.
- **`CLAUDE.md` frontmatter** — `maestro_version` bumped to `v2026.05.23.1`.

### Why

- Verbosity of raw SQL was the dominant token cost in the orchestrator's memory writes (~700–800 tokens per non-trivial save). The CLI cuts this by 30–40%.
- Escape of Italian (or any non-ASCII) text in raw SQL was a recurring source of silent INSERT failures. Parameterized SQL closes that.
- Bulk writes via single transaction unlock efficient flush flows (e.g., archiving an external task store's done items into the cold memory layer in one round-trip instead of N).
- Markers as named upsert give a clean replacement for the pattern of "row in `log` with a sentinel title".

### Migration note for instances

**`bin/mem` is not yet in `maestro-sync`'s scan scope.** The sync skill only walks Markdown files with `origin: maestro` frontmatter (CLAUDE.md, hub skills, base agents). Python files in `bin/` have an `# origin: maestro` comment marker but the parser doesn't read it yet.

At the next sync, after running `/maestro-sync` and applying the markdown diffs, **copy `bin/mem` manually** from the mirror:

```bash
mkdir -p bin
cp ~/.maestro/bin/mem bin/mem
chmod +x bin/mem
```

This is a one-shot step per instance (idempotent — running it again just overwrites with the current upstream version). A future Maestro release may extend `maestro-sync` to scan `bin/*` for comment-style frontmatter; until then, copy by hand.

### Roadmap (open)

The work behind this release is part of a larger shaping (see Alfred's `memories.db` idea #408). What's deferred for now:

- **FTS5 + indexes + views** — relevant when the row count grows past a few thousand
- **`sqlite-vec` + semantic similarity** — `bin/mem similar <id-or-query>` k-NN search (idea #407 in Alfred)
- **MCP server layer** — would eliminate the Bash round-trip the CLI still incurs; deferred because the dominant cost was verbosity (now solved) and an MCP server reopens the multi-instance isolation question (idea #455)
- **Scope extension of `maestro-sync`** to handle `bin/*` with comment-style markers — would remove the manual copy step above

### Commit

- (commit hash on this version)

---

## v2026.04.30.4 — 2026-04-30

**Theme**: Allow per-instance customization of the `tools:` frontmatter field on `origin: maestro` files.

### Changed

- **`CLAUDE.md` → "Distribution and modifications"** gets a new "Single exception" paragraph. Each instance can extend the `tools:` whitelist of a skill or agent marked `origin: maestro` with its own MCPs/tools, without violating the no-in-place-edits rule. This is necessary because MCP installations are per-instance: an agent that needs to call Slacky tools needs `mcp__slacky__*` in its `tools:`, but Slacky may not exist on every instance. The `maestro-sync` skill ignores diffs limited to the `tools:` field — only the body and other frontmatter keys are diffed for sync.

### Why

Without this exception, an instance that wants to use the base `scheduler` agent (Maestro-distributed) couldn't add its own MCP tools without forking the file or fighting the sync. The exception keeps the agent body as upstream's source of truth and lets the instance own its tool whitelist.

### Commit

- (commit hash on this version)

---

## v2026.04.30.3 — 2026-04-30

**Theme**: Introduce the `maestro-sync` skill — the actual sync engine.

### Added

- **`.claude/skills/maestro-sync/SKILL.md`** new hub skill. Implements the full sync flow:
  1. Locate mirror (`~/.maestro/`) and primary working tree (`~/Sites/me/maestro/`)
  2. Pre-sync check on the working tree (warn on uncommitted changes / unpushed commits)
  3. Refresh the read-only mirror with `git fetch origin && git reset --hard origin/main`
  4. Scan the instance for files marked `origin: maestro`, read each `maestro_version`
  5. Show the changelog delta from instance floor to mirror version
  6. Per-file diff and confirmation (`a` / `s` / `A` / `n`)
  7. Apply, log to `private/maestro-sync.log`, summarize, log a memory
- **`CLAUDE.md` → "Hub skills"** — new entry for `maestro-sync` so instances know the skill exists and how to trigger it.

### Bootstrap notes

- A brand new instance cloned from this template gets `maestro-sync` already installed.
- An old instance predating `origin: maestro` markers needs the owner to mark its inheritable files manually with `maestro_version: v2026.04.29.1` (the baseline) before the first sync — then the normal flow handles it.

### Self-update

`maestro-sync` is itself marked `origin: maestro`. When upstream ships a new version of the skill, instances pick it up like any other file in the scan.

### Commit

- (commit hash on this version)

---

## v2026.04.30.2 — 2026-04-30

**Theme**: Promote three patterns proven in the Alfred instance into the template.

### Added

- **`CLAUDE.md` → "Decide which `date:` to write — early-morning rule"** under the Memory section. New sub-section that codifies the rule: writes to `memories.db` between 00:00 and 06:00 local time are attributed to the previous day (`date('now','-1 day')`) unless the owner has explicitly closed it. Avoids fragmenting one lived session across two calendar days.
- **`CLAUDE.md` → "YAML safety in frontmatter values"** under "Frontmatter and search discipline". Lists the trigger characters (`: `, `# `, leading `[{>|*&!%@\``) that force a value to be quoted with double quotes, and the rule "when in doubt, quote".
- **`CLAUDE.md` → "Linking discipline (Obsidian wikilinks)"** new top-level section. When the vault is an Obsidian one, references to other vault files use `[[Filename]]` syntax (with optional `[[Filename|alias]]`). Lists what stays in monospace (folder paths, files outside the vault, code identifiers, URLs). Explains the graph-connectivity reason. Section is conditional: skipped when the vault is plain filesystem.

### Migration for existing instances

These three patterns may already exist in instance-level customizations of `CLAUDE.md` (instances that surfaced them earlier). On sync, prefer the template's wording for consistency unless the local version has owner-specific examples worth keeping.

### Commit

- (commit hash filled in by the commit itself — see git log on this version's commit)

---

## v2026.04.30.1 — 2026-04-30

**Theme**: Available apps moves out of `CLAUDE.md` into `preferences.md`; new distribution rule.

### Changed

- **`CLAUDE.md`** — the "Available apps" table no longer lives here. The section now points to `private/preferences.md`. Two cross-references updated:
  - In "Hub skills", the `add-external-app` entry now says it updates the section in preferences.
  - In "Validation before touching a sub-app", the access gate paragraph references the section in preferences instead of the table.
- **`preferences.example.md`** — introduces a new "Available apps" section with a 4-column table (Alias, Path, Purpose, Access) and a placeholder row. New instances get this template at setup time.
- **`.claude/skills/add-external-app/SKILL.md`** — Step 3 is rewritten to update `private/preferences.md` instead of `CLAUDE.md`. Frontmatter description, intro, Q3 of the Q&A flow, confirmation recap, Step 4 final summary, and the memory log line are all aligned to the new target.

### Added

- **`CLAUDE.md` → "Distribution and modifications"** new section. Forbids in-place edits of files marked `origin: maestro` in their frontmatter. Any change must go through Maestro origin and be reabsorbed via sync.

### Migration for existing instances

Instances on the previous version (or earlier) have the apps table living in their own `CLAUDE.md`. After a sync that applies this version:

1. The local `CLAUDE.md` "Available apps" section becomes a pointer to `preferences.md`.
2. The instance must move its existing apps table from `CLAUDE.md` into `private/preferences.md` (under a new "Available apps" section) — `maestro-sync` does not migrate data, only patterns.
3. The "Distribution and modifications" section is added to the local `CLAUDE.md`.

For instances bootstrapped from this version onward, the table lives in preferences from day one; no migration needed.

### Commit

- `f515fbf` (origin/main) — *V1.a → template: move "Available apps" out of CLAUDE.md into preferences*

---

## v2026.04.29.1 — 2026-04-29

**Theme**: Initial snapshot for changelog tracking.

This is the baseline version. Instances bootstrapped before this date may not declare `maestro_version` in their `origin: maestro` files; the first `maestro-sync` against `v2026.04.30.1` or later will treat them as `v2026.04.29.1` and propose all subsequent changes.

### State at this version

The template provides:

- Top-level `CLAUDE.md` describing the orchestrator role, session start, role rules, tone, repo structure, available apps (as table), hub skills, delegation/roster, routing, validation before touching sub-app, handoff between apps, file territories (vault root + three subfolder keys), frontmatter discipline, memory (SQLite at `private/memories.db`), preferences evolution, Basecamp scope, permissions/paths.
- Hub skills: `setup` (interactive first-launch configuration), `logbook` (daily logbook to `logbook_path`), `add-external-app` (registers an external project as a sub-app with a pointer skill, updates the apps table in `CLAUDE.md`), `guide` (answers questions about the orchestrator from `CLAUDE.md` and `howto/`).
- Craft agents: `librarian` (vault hygiene + research), `scheduler` (cold data layer for prospective/retrospective queries), `hr` (recruiter for the agent roster).
- Roster registry, `routines.example.yaml`, `memories.db.template` for setup seeding.
- `preferences.example.md` template (without "Available apps" section — that's introduced in v2026.04.30.1).
- `howto/` documentation set.

### Commit

- `c542a2e` (origin/main, parent of f515fbf) — *Install librarian + scheduler agents; rework setup with finalize.sh*
