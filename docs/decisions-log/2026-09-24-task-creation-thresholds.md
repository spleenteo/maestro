---
work: task-creation-thresholds
status: active
superseded_by: null
tags: [decision, tasks, warm-channel, thresholds, steward, memory, claude-md, howto-07]
description: "Task creation thresholds live in CLAUDE.md and in every channel skill's Creation section, for every store; the steward agent reviews the backlog against them. Read before changing where tasks are created or adding a channel skill."
---

# Task creation thresholds live in `CLAUDE.md` and in the channel skill

**Date**: 2026-09-24 · **Work**: `task-creation-thresholds` · **Status**: active

## Context

Two instances drifted in opposite directions from the same template.

In the first, preferences declared a warm channel, and the rule that tasks live there sat in the channel skill, loaded only on request. The proactive trigger in `CLAUDE.md` ("The owner lists things to do → `task` with `status: todo`") was read at every session and wrote to `memories.db` whenever the skill wasn't loaded. Between April and September 2026 it produced 161 task rows, 45 still open, next to the warm channel: the two-writers anti-pattern of `howto/07`.

The second instance already routed the trigger to its warm channel and held no open task in `memories.db`. Its monthly task creations still grew from 7 in July to 25 in August and 31 in September; of 46 closed tasks, 15 were closed within one day and 22 within three. They were next steps of a conversation ("send the deck", "check the reply", "brief them before the call").

Routing the trigger to the right store fixes the first case and leaves the second as it was.

## Decision

1. `CLAUDE.md` → `## Memory` gains `### Task creation thresholds`, read at every session and valid for every store. A task is created on a direct request, a date by which the action has to happen, or evident urgency; with none of the three it stays an idea or the orchestrator asks once. A step toward an outcome already tracked goes into that task's notes. Search before creating, neutral priority by default, no numeric cap per area.
2. The proactive trigger applies the thresholds and then creates the task through the warm channel's skill when one is declared, in `memories.db` otherwise.
3. The channel skill contract in `howto/07` requires a `## Creation` section that maps each rule onto the channel (where a step goes, which read call finds related tasks, the neutral priority value) and adds no rule of its own.
4. An instance may tighten or loosen the rules in preferences, under `## Warm task channel` → `### Task creation thresholds`; the instance block wins.
5. The `steward` agent (alias Della) ships in the template: a weekly review that proposes closures, parent ideas, duplicates and moves against the thresholds, and writes nothing.

## Alternatives considered

- **Thresholds in preferences only.** The first instance did this on 2026-09-19. It fixes one instance and leaves the template contradicting itself; every new instance would rediscover the drift.
- **Thresholds in the channel skill only.** The skill is loaded on request, so sessions that never load it follow `CLAUDE.md` alone. This is how the first instance drifted.
- **An agent that also creates tasks.** Rejected: the conversation's context sits with the orchestrator, and an agent receiving a summary judges the thresholds with less than the orchestrator has.
- **A scheduled routine for the review.** Deferred: cloud routines can't reach a local `memories.db` or a local stdio MCP, so it needs a local LaunchAgent running `claude -p`, still to be spiked.

## Consequences

- Every existing channel skill needs a `## Creation` section; instances write it after the sync, since Maestro ships no channel skill.
- An instance that wrote its own thresholds in preferences can keep them as the override block or delete them in favour of `CLAUDE.md`.
- The steward's first pass on an instance with a legacy backlog can exceed 20 proposals; it stops and reports the unreviewed rows.
