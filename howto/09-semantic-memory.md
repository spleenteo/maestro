---
origin: maestro
maestro_version: v2026.10.01.1
tags: [maestro, memory, semantic-search, sqlite-vec, ollama, vault, chunking, scope, satellites, exit-codes, pattern]
description: "Optional semantic layer for memories.db and the chunked markdown vault: setup (Ollama + uv), commands, vault index, scope rules for satellites and exit codes, graceful degradation, rebuild, machine-change notes, and the markers that signal when to evolve the architecture."
---

# 09 — Semantic memory (optional layer)

`bin/mem` can search `memories.db` by meaning as well as by keyword: recall by affinity, duplicate detection, pattern discovery. The layer is strictly optional and additive: an instance without it behaves exactly as before.

## Setup (per machine)

```bash
brew install ollama uv
brew services start ollama        # starts at login from now on
ollama pull bge-m3                # the embedding model (multilingual)
bin/mem embed --rebuild           # vectorize the whole db (minutes)
```

## How it works

- Vectors live in `log_vec`, a plain additive table inside `memories.db`, self-creating on first use. `log` itself carries a `scope` column (see Scope below), migrated in by `bin/mem_schema.py` and already present in `memories.db.template`.
- A row needs (re)embedding when its content hash no longer matches: inserts and updates are picked up automatically by the next `bin/mem embed`.
- Embeddings are **derived data**: a pure function of (text, model). They travel inside the .db file, and can always be rebuilt from scratch with `bin/mem embed --rebuild`. Changing machine loses nothing: reinstall Ollama, re-pull the model, done.
- Writes never wait for embeddings. Run `bin/mem embed` opportunistically (session start, alongside the warm-channel GC).

## Commands

```bash
bin/mem embed [--rebuild|--status]        # vectorize / coverage report
bin/mem search "text" --semantic          # meaning-based recall (+ usual filters)
bin/mem similar <id>                      # rows close to a given one
bin/mem dupes [--min-score 0.85]          # duplicate candidates for hygiene
```

## Vault index (chunked)

Besides `memories.db`, the layer indexes the markdown vault, split by section (`##`/`###` headings). The vectors live in `vault_vec` (additive, self-creating like `log_vec`); the `.md` files stay the only source of truth: the db holds the vector, `path#anchor` and a snippet.

```bash
# the root comes from --root (repeatable) or env MEM_VAULT_ROOTS
MEM_VAULT_ROOTS="$VAULT" bin/mem embed          # memories + vault, incremental
bin/mem embed --root "$VAULT"                   # the same, explicit
bin/mem search "…" --semantic                   # one ranking, memories + vault
bin/mem search "…" --semantic --only vault      # the vault only
```

- **Exclusions:** `<vault_root>/.mem-ignore`, `.gitignore` style (one pattern per line; `Journal/`, `*.excalidraw`, `!exception`). Dot-folders are always skipped, and symlinks are never followed. The file belongs to the instance, never to the template. Every folder in File territories → `off_limits` belongs in it too; the archive root never does, since archived notes stay searchable.
- **Several roots:** `--root` repeats; each chunk is keyed by its root, so two vaults holding a note at the same relative path don't collide.
- **Output columns:** `source` (`memory`/`vault`), `ref` (`#id` or `path#section`), `title`/heading, `score`, `snippet`.
- **Flood control:** `--vault-frac` (default 0.6) caps the share of vault hits; `--min-score` drops the weak neighbours.
- **Degradation:** unchanged (exit 3). Without a root, `embed` vectorizes the memories only.

## Scope (satellites)

A satellite session exports `MEM_SCOPE=<slug>`, a slug matching `^[a-z0-9][a-z0-9-]*$`. Every `log` row carries a `scope` column: null for the mother instance, the slug for a satellite. `bin/mem` and `bin/mem-vec` add the column when they first open an older db, through `bin/mem_schema.py`. The semantic layer follows the rule of keyword search:

- `search --semantic`: a satellite ranks only the memories of its own scope. The mother ranks the null scope; `--scope <slug>` narrows the ranking to one scope and `--all-scopes` opens every scope. Vault hits are the same in every session.
- `similar <id>`: a satellite accepts an anchor id of its own scope only, and exits 1 on any other id. The mother accepts any anchor, and its hits follow the same flags as `search`.
- `dupes`: a pair shows up only when both of its rows are in scope.
- `embed`: a satellite gets exit 4 before the db is opened. `embed` deletes from `vault_vec` every chunk outside the roots it receives, so only the mother runs it.
- In a satellite, `--scope` and `--all-scopes` exit 4 on `search --semantic`, `similar` and `dupes`, before `uv` or Ollama start.

`bin/mem` passes the flags on to `bin/mem-vec`, and `MEM_SCOPE` reaches it through the environment. Called directly, `bin/mem-vec` applies the same checks.

| Exit code | Meaning |
|---|---|
| 3 | semantic layer unavailable (see Degradation) |
| 4 | `--scope` or `--all-scopes` in a satellite, or `embed` with `MEM_SCOPE` set |
| 5 | `bin/mem_schema.py` missing or incompatible (`SCHEMA_API` mismatch) next to `bin/mem` or `bin/mem-vec`: copy `bin/mem`, `bin/mem-vec` and `bin/mem_schema.py` together from `~/.maestro/bin/` |
| 6 | invalid slug in `MEM_SCOPE` or `--scope` |

## Degradation

No Ollama or no uv → semantic commands exit with code 3 and a clear message; everything else works as always. The orchestrator falls back to keyword search silently.

## Service management

Ollama runs as a per-user brew service (label `homebrew.mxcl.ollama`, plist in `~/Library/LaunchAgents/`). It starts automatically at login: a machine reboot needs no action.

```bash
brew services list                  # all brew services; look for "ollama  started"
brew services info ollama           # detail: Running, PID
brew services restart ollama        # restart after an upgrade or a hang
brew services stop ollama           # stop it — semantic commands degrade to exit 3, nothing breaks
curl -s localhost:11434/api/version # one-shot health check
```

## Evolution markers

Watch for these:

- **To vec0 KNN indexes** (scale): semantic search repeatedly >~500ms warm, or corpus >~30-50k rows, or full rebuild >~15 min.
- **To FTS5 hybrid** (quality): systematic misses on exact terms (codes, serials, proper nouns) or recurring "exact word + concept" queries.
- **Model change**: poor Italian recall despite calibrated thresholds → re-test models, `bin/mem embed --rebuild` (minutes).
