# `.claude/agents/data/` — Runtime config for craft agents

This folder holds **data/schema files** read by craft agents at runtime.
Not code, not agent definitions — just inputs.

## Config map

Where every piece of config the orchestrator depends on actually lives:

| File | Role | Nature | Gitignored |
|------|------|--------|:---:|
| `.claude/agents/data/channels.yaml` | Channel map + `question_types` routing. Read by `scheduler` (Cal) at every invocation. | Shared, versioned | no |
| `.claude/agents/*.md` | Agent definitions (hr, librarian, scheduler, …) | Shared, versioned | no |
| `.claude/roster.yaml` | Active agent registry — source of truth for delegation | Shared, versioned | no |
| `.claude/skills/*/SKILL.md` | Skill definitions | Shared, versioned | no |
| `private/preferences.md` | Owner profile: identity, territories, timezone, integrations | Private | **yes** |
| `private/memories.db` | SQLite log of memories, tasks, ideas | Private | **yes** |
| `private/routines.yaml` | Recurring routines read by Cal when the question type requests them | Private | **yes** |

Tool-specific configs live where the tool expects them. Examples:

- A Basecamp CLI typically reads from `.basecamp/config.json` (bucket IDs, card table IDs, owner user id, …). Channels referencing Basecamp use `access.config_refs` to point at those keys — never hardcode IDs in the agent prompt or the channel YAML.
- MCP servers resolve their own credentials via Claude Code's MCP config. Channels referencing an MCP declare the tool name under `access.mcp` and rely on the MCP's own plumbing.

## Why configs are "scattered"

Not everything lives here, for three reasons:

- **External tool convention** — CLI wrappers (`.basecamp/config.json`, etc.) live where the tool looks for them, not where we'd prefer.
- **Privacy** — owner-specific data (routines, preferences, memory db) lives in `private/`, gitignored; can't mix with versioned files.
- **Claude Code convention** — `.claude/agents/*.md`, `.claude/roster.yaml`, `.claude/skills/` have fixed positions the runtime expects.

What belongs here is **shared runtime config read by one or more craft agents** — today just `channels.yaml`; tomorrow potentially other schemas (output templates, glossaries, …).

## Rule for evolution

When you add a shared config file that one or more agents read at runtime, put it here. Update the Config map above with its role, nature, and gitignore status. Keep the table short and the file names self-explanatory.
