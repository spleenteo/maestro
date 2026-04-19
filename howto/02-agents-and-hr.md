---
tags: [howto, agents, hr, roster, claude-code, orchestrator, delegation]
description: How to hire, use, and retire craft agents via the HR agent. Agents are subagents with their own identity and isolated context, registered in `.claude/roster.yaml`.
---

# How to add agents and use HR

An **agent** is a subagent of the orchestrator with its own identity, scope, and isolated context. Agents are invoked via the `Task` tool with `subagent_type: <name>`. They return their output to the orchestrator, which filters and presents it to the owner. Agents never speak directly to the owner.

Agents are the right abstraction when:

- Work is long-running and would pollute the orchestrator's context if inlined
- A distinct identity helps reasoning (e.g., an "HR" agent that evaluates candidates, a "maintenance" agent that handles appliances)
- A scope is worth enforcing: the agent only touches a specific domain, registry, or folder

If any of those doesn't apply, a skill is probably enough (see `01-skills.md`).

## Where agents live

```
.claude/
├── agents/
│   ├── hr.md                  ← the HR agent itself (ships with the template)
│   ├── <name>.md              ← other craft agents, one file each
│   └── data/
│       └── <registry>.yml     ← optional data the agent needs (registries, maps)
└── roster.yaml                ← the registry of active and retired agents
```

The **roster** is the source of truth for the orchestrator: before invoking an agent, the orchestrator confirms it's listed in `active`.

`.claude/roster.yaml`:

```yaml
version: 1
active:
  - name: <technical-name>
    alias: <optional human name>
    installed_at: YYYY-MM-DD
    version: 1.0.0
retired: []
```

## The HR agent

HR is **recruiter + onboarding + offboarding**. You don't install or retire craft agents by hand — you ask the orchestrator, which invokes HR.

HR's responsibilities:

- Search in cascade for candidates: local filesystem → Anthropic marketplace → third-party GitHub → custom creation
- Evaluate scope, identity, source quality
- Propose with explicit pros/cons to the orchestrator
- On confirmation, install (write the agent file + update the roster) or retire (move to `.retired/`)

HR never talks to the owner. It reports back to the orchestrator, which surfaces the proposal.

## Hiring an agent

Tell the orchestrator what you need:

> "I'd like an agent that handles my home appliances — manuals, warranties, service history."

The orchestrator will invoke HR. HR searches and proposes something like:

> **Option 1**: `appliances` (custom). Scope: manage a registry of home appliances in `.claude/agents/data/appliances.yml` with manuals on Dropbox and service notes in an Obsidian folder. Pros: clear perimeter, tailored to your request. Cons: needs to be written from scratch. Recommendation: proceed.

If you say yes:

1. HR creates `.claude/agents/appliances.md` with frontmatter (`name`, `description`, `tools`) plus operating principles, territory rules, and workflow.
2. HR adds an entry to `roster.yaml` (`active`).
3. HR reports back: *"Agent `appliances` hired."*

The orchestrator can now delegate to it with `Task(subagent_type=appliances)`.

## Using an agent once hired

You never invoke the agent directly. You ask the orchestrator something that matches its scope:

> "How old is my dishwasher?"

The orchestrator reads the roster, sees `appliances` is active, opens its file to confirm the match, then runs `Task(subagent_type=appliances, prompt="...")`. The agent does its thing and returns a result. The orchestrator synthesizes and replies to you.

### Aliases

In the roster, an agent can have an `alias` (a human name):

```yaml
- name: appliances
  alias: Amerigo
  installed_at: 2026-04-18
  version: 1.0.0
```

You can refer to the agent by alias in conversation (*"ask Amerigo what's up with the dryer"*). The orchestrator resolves to the technical `name` when invoking the Task tool. When the orchestrator mentions the agent back to you, it uses the alias.

## Agent structure — what lives in `<name>.md`

Frontmatter:

```markdown
---
name: <technical-name>
description: <one line: what the agent does — also shown in subagent listings>
tools: Read, Write, Edit, Bash, Glob, Grep
---
```

Body, typically:

- **Operating principles** (3–5 bullets: how the agent works, when it asks for confirmation, how it communicates)
- **Scope** (what's in, what's out)
- **Authorized territories** (paths where the agent can read/write, each with rules)
- **Workflow** (numbered steps for the typical task)
- **Data sources** (pointers to registries in `.claude/agents/data/`)
- **Communication rules** (always returns to the orchestrator, never speaks to the owner)

The `hr.md` file that ships with the template is a working example — read it when drafting a new one.

## Retiring an agent

Tell the orchestrator you want to retire an agent. It invokes HR; HR:

1. Asks for confirmation.
2. Moves the roster entry from `active` to `retired`, with `retired_at: YYYY-MM-DD`.
3. Moves the file from `.claude/agents/<name>.md` to `.claude/agents/.retired/<name>.md`.
4. Reports back.

**Retirement never deletes.** History is preserved. You can un-retire by moving files and roster entries back.

## Common patterns

- **Narrow scope, narrow registry**: an agent backed by a YAML map in `.claude/agents/data/` (e.g., a list of appliances, a list of clients, a list of recurring reports). Keeps the agent self-contained.
- **Output always through the orchestrator**: never let an agent compose a final response to the owner. The orchestrator filters and frames.
- **One agent per domain, not per task**: don't spawn a new agent every time you need something. If a skill can do it, use a skill.

## Tips on HR's cascade

HR's default is to look locally first — a skill you already have might be promoted to an agent with minor edits. Only when nothing local fits does it go further afield. If you've built a skill and want to convert it to an agent, tell HR; it'll propose the promotion rather than creating something new.
