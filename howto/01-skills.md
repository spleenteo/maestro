---
tags: [howto, skills, claude-code, orchestrator, customization]
description: How to add, invoke, write, and retire skills in your orchestrator. Skills are lightweight capabilities loaded in the root context.
---

# How to add and use skills

A **skill** is a small capability the orchestrator can invoke. Skills live in `.claude/skills/<name>/SKILL.md` and are surfaced to Claude Code at session start. The orchestrator decides when to invoke them (based on their `description`), or you can invoke one explicitly with `/<skill-name>`.

Skills are the right abstraction when:

- The behavior is short-running and needs the orchestrator's context to be useful
- You want a reusable recipe that can be triggered by a keyword or a pattern in the conversation
- The capability doesn't need its own identity or isolated context

If any of those fail — especially the last one — you probably want an **agent** instead (see `02-agents-and-hr.md`).

## Anatomy of a skill

Minimum structure:

```
.claude/skills/<name>/
└── SKILL.md
```

Some skills need sidecar files (templates, scripts, data). Put them alongside `SKILL.md`.

`SKILL.md` starts with a frontmatter block:

```markdown
---
name: <skill-name>
description: <one-line: what it does and when to use it — this is the trigger signal for the orchestrator>
---

# <Skill title>

<Body of instructions — what the skill does, step by step.>
```

Two fields are critical:

- **`name`** must match the folder name and be valid for `/<name>` invocation.
- **`description`** is the trigger. It's what the orchestrator reads at session start to decide whether a request matches. Write it like you'd write a commit subject: concrete, action-oriented, mentioning the real triggers ("Use when the user asks for X, Y, or Z").

## How invocation works

When Claude Code starts a session in your repo, it loads all skills' names and descriptions into the orchestrator's context. The orchestrator then:

1. **Auto-invokes** a skill when it detects a clear match with its description (e.g., user says "recap of today" and the `logbook` skill matches).
2. **Explicit invocation** happens when the user types `/<skill-name>`.

If auto-invocation doesn't fire when you expected it to, sharpen the description or use the explicit `/<name>` form.

## Writing a new skill

Minimum viable skill — let's call it `weekly-report`:

```markdown
---
name: weekly-report
description: Generate a weekly summary of completed tasks and noteworthy memories from `private/memories.db`, formatted for sharing with stakeholders. Use when the user asks for "weekly report", "weekly summary", or "Friday wrap-up".
---

# Weekly report

Generate a summary of the last 7 days.

## Steps

1. Query the log:
   ```bash
   sqlite3 -header -column private/memories.db "SELECT date, title, type, tags FROM log WHERE date >= date('now','-7 days') ORDER BY date, id;"
   ```
2. Group entries by tag cluster (customize for your domain).
3. Write the report as Markdown, sections per cluster.
4. Ask the user whether to save it to `<documents_path>/weekly/YYYY-WW.md`.
```

Put this at `.claude/skills/weekly-report/SKILL.md`. Restart the Claude Code session (or type `/weekly-report`) to verify it's picked up.

## Testing a skill

- `/weekly-report` should surface it in the completion menu.
- Ask the orchestrator something that triggers it ("give me the weekly report") and see if it auto-invokes.
- If not, read the description: it should leave no ambiguity about when to fire.

## Retiring a skill

Move the skill folder to `.claude/skills/.disabled/<name>/`. It's preserved but no longer available to the orchestrator. Restore by moving it back.

The `setup` skill uses this pattern after first launch — it self-disables but stays recoverable.

## Skill vs agent — quick heuristic

| If you want... | Use a... |
|---|---|
| A reusable recipe the orchestrator runs in its own context | Skill |
| An identity with its own scope and operating principles | Agent |
| Fast, conversational help (short tool call chains) | Skill |
| Long-running work with many tool calls and isolated context | Agent |
| Something the orchestrator proposes to the user ("should we run /weekly-report?") | Skill |
| Something the orchestrator delegates to by name ("let me ask HR") | Agent |

Most of the time: start with a skill. Convert to agent when the skill starts needing its own personality or when its context pollutes the orchestrator's window.
