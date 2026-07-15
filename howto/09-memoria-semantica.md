---
origin: maestro
tags: [maestro, memory, semantic-search, sqlite-vec, ollama, pattern]
description: "Optional semantic layer for memories.db: setup (Ollama + uv), commands, graceful degradation, rebuild, machine-change notes, and the markers that signal when to evolve the architecture."
---

# 09 — Semantic memory (optional layer)

`bin/mem` can search `memories.db` by meaning, not just keywords: recall by affinity, duplicate detection, pattern discovery. The layer is **strictly optional and additive** — an instance without it behaves exactly as before.

## Setup (per machine)

```bash
brew install ollama uv
brew services start ollama        # starts at login from now on
ollama pull bge-m3                # the embedding model (multilingual)
bin/mem embed --rebuild           # vectorize the whole db (minutes)
```

## How it works

- Vectors live in `log_vec`, a plain additive table inside `memories.db` — `log` is never touched. The table self-creates on first use; `memories.db.template` needs no change.
- A row needs (re)embedding when its content hash no longer matches — inserts and updates are picked up automatically by the next `bin/mem embed`.
- Embeddings are **derived data**: a pure function of (text, model). They travel inside the .db file, and can always be rebuilt from scratch with `bin/mem embed --rebuild`. Changing machine loses nothing: reinstall Ollama, re-pull the model, done.
- Writes never wait for embeddings. Run `bin/mem embed` opportunistically (session start, alongside the warm-channel GC).

## Commands

```bash
bin/mem embed [--rebuild|--status]        # vectorize / coverage report
bin/mem search "text" --semantic          # meaning-based recall (+ usual filters)
bin/mem similar <id>                      # rows close to a given one
bin/mem dupes [--min-score 0.85]          # duplicate candidates for hygiene
```

## Degradation

No Ollama or no uv → semantic commands exit with code **3** and a clear message; everything else works as always. The orchestrator falls back to keyword search silently.

## Evolution markers

Watch for these; full rationale in the design doc (instance vault, Progetti/Maestro):

- **To vec0 KNN indexes** (scale): semantic search repeatedly >~500ms warm, or corpus >~30-50k rows, or full rebuild >~15 min.
- **To FTS5 hybrid** (quality): systematic misses on exact terms (codes, serials, proper nouns) or recurring "exact word + concept" queries.
- **Model change**: poor Italian recall despite calibrated thresholds → re-test models, `bin/mem embed --rebuild` (minutes).
