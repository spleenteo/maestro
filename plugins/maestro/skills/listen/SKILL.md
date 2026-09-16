---
name: listen
description: Live listening on a call in progress, from any Claude Code session (a Maestro instance, a satellite repo, or a plain folder). Captures system audio plus microphone with `yap`, keeps a growing transcript on disk, answers the owner's questions about what has been said so far, and on close files a note plus the raw transcript where the owner confirms. Ships in the Maestro plugin. Use when the owner types /listen, or says "listen to this call", "start listening", "ascolta questa call", "registra l'intervista", or asks what was said during a call that is currently running.
allowed-tools: Bash(maestro-listen *)
---

# listen

Turns a call into something the session can consult **while it is still
happening**. `yap` transcribes system audio and microphone on-device, the
transcript grows on disk, and the session reads it on demand.

Built for interviews, discovery calls and client meetings, where the owner is
talking and needs an answer in two lines, not a report.

The skill ships in the Maestro plugin, so it runs in every session on the
machine. A bare `/listen` reaches it wherever no other skill holds the name. An
instance that still carries its old local copy (`.claude/skills/listen/`) runs
that copy on `/listen` until `/maestro:maestro-sync` retires it; `/maestro:listen`
always reaches this one.

## Prerequisites

- **`yap`** — `brew install yap`. On-device transcription through the Speech
  framework. Nothing leaves the machine.
- **macOS 26 or later** — the framework `yap` relies on ships with 26.
- **Permissions** — Microphone and Screen Recording, granted to the terminal
  that runs the capture. macOS asks once.

`maestro-listen start` checks both and stops with a clear message when one is
missing (exit 4). Never improvise a fallback: no other tool, no partial capture.
Report what is missing and the command that installs it.

## Command surface

`/listen help` prints this list, verbatim, translated into the owner's language:

```
/listen                     start in the owner's language; the context comes
                            from calendar, memory and vault, and is stated
                            back in one line
/listen <language>          start in another language (en, en-gb, fr, de, es,
                            or a full code such as en-US)
/listen <one line of why>   start with the objective stated, when guessing
                            is not good enough
/listen them-only           close the microphone and transcribe the far side
                            only: no echo, and the owner is not recorded
/listen status              how long it has been running, how many exchanges,
                            the last line heard
/listen update me every N   turn on automatic updates every N minutes
/listen stop updating       turn them off
/listen close               stop the capture and propose where to file the note
/listen help                this list
```

`maestro-listen` backs it, from the plugin's `bin/` on the `PATH`: `start`,
`status`, `text`, `stop`, `updates`, JSON when piped, exit codes in
`maestro-listen --help`. State and the growing transcript live in
`~/.local/state/listen/`, outside every worktree and outside the vault.

**Every call is one simple command**: `maestro-listen <verb> [flags] --project "${CLAUDE_PROJECT_DIR}"`,
with no `cd`, no `&&`, no pipe and no `set` in front. `--project` carries this
session's project folder, filled in when the skill loads, so a `cd` into a
subfolder or an app between two calls never makes the capture look like
another folder's.

The `allowed-tools` rule of this skill covers only the turn that invokes it; a
question asked later in the call runs in a later turn, where the owner's
permission settings decide. A compound command never matches the owner's rule
and prompts while they are talking. When a prompt does interrupt the call,
answer first, then say once that adding `Bash(maestro-listen *)` to
`permissions.allow` in `~/.claude/settings.json` stops them. Never edit
settings yourself.

**The lock is machine-wide, and a capture belongs to its folder.** One capture
runs on the machine at a time. It belongs to the folder that started it: the
main checkout of the git repository the session runs in (a subfolder or a
worktree counts as the repository), or the folder itself outside a repository.
From another folder, `maestro-listen` reports who holds the lock and since
when, and refuses `text`, `stop` and `updates` with exit 3; every refusal
carries the `project` it resolved for the caller. The boundary keeps sessions
from stepping on each other's calls. It is no access control, so never read
the files under `~/.local/state/listen/` directly.

## Context

Before the first action, work out which of three contexts this session is. Decide
once per capture.

1. **Satellite**: the session context carries a `# Satellite session: <scope>`
   block from the Maestro plugin. It names the mother instance's path, the
   memory command (`MEM_SCOPE=<scope> "<mother>/bin/mem" …`), the role
   (mandate, constraints, language), the identity extract and, when there is
   one, the linked vault folder.
2. **Instance**: otherwise, run `maestro-listen status --project "${CLAUDE_PROJECT_DIR}"`
   and read `project`, then
   `ls "<project>/private/preferences.md" "<project>/bin/mem"`. Both present:
   this is a Maestro instance rooted at `<project>`, also when the session runs
   in a worktree or a subfolder of it. Read `<project>/private/preferences.md`
   when it isn't already in context.
3. **Plain folder**: anything else.

| | Instance | Satellite | Plain folder |
|---|---|---|---|
| Context at opening | calendar, `"<project>/bin/mem" search`, the vault territories in preferences | calendar, the scope's memory (`MEM_SCOPE=<scope> "<mother>/bin/mem" search`), the vault folder | calendar, when a calendar tool is available |
| Language | the owner's language from preferences | the role's `Language`; when empty, the default language in the identity extract | the language of the conversation |
| `--mic-label` | the owner's nick from preferences | the owner's nick from the identity extract; ask when it isn't there | ask |
| Destination proposed at close | a vault folder chosen from people and topic | the vault folder, or a subfolder of it; without one, ask | ask |
| Memory at close | `"<project>/bin/mem" save` | `MEM_SCOPE=<scope> "<mother>/bin/mem" save` | none |
| Register pass on the note | the `writing-register` skill | the rules in `<mother>/CLAUDE.md`, section `## Writing register`, adjusted by the `Writing register` block of the identity extract when there is one, then `"<mother>/bin/register-check" <note>` | none |

- In an instance, call the root's `bin/mem` by absolute path: a worktree has no
  `private/`, so its own copy finds no memory.
- A satellite's constraints say what must not happen, and they hold: when one
  rules out storing the call, say so at close and write nothing. They never
  name a destination.
- In a satellite without a vault folder, when the owner names a path inside
  the repository, say once that the repository may be shared with others, then
  do what they say.

## Segments and device changes

A capture is a sequence of **segments**, not a single process. Each segment is
one `yap` run with its own file and a known offset from the start of the call;
reads merge them back into one timeline, so the owner sees continuous
timestamps and one transcript.

This exists because `yap` binds to the input device it finds at launch. Plugging
in headphones mid-call switches the system's default input, `yap` stays on the
old device, and the microphone channel dies with no error at all. A detached
supervisor watches the default input through `audiowatch`, a small CoreAudio
listener that costs nothing while idle, and rotates the segment when the device
changes: it closes the current `yap`, opens a new one on the new device, and
records the offset.

Two things worth saying out loud:

- Each boundary drops a second or two, the time of the restart. Far less than
  what a dead channel costs, and not zero.
- Without `swiftc` the watcher cannot be built. The capture still runs, with a
  single segment and no rotation, and `status` reports `rotation: off`. Say so
  when it happens rather than letting the owner assume they are covered.

## Opening

On `/listen`, in this order:

1. **Work out what this call is.** Look at the clock against the calendar, then
   at the memory and the vault the context gives (see **Context**). State the
   conclusion in one line ("the Sam call, still open: the framing document and
   the role-play videos"). The owner corrects it in a few words or says
   nothing. Ask only when nothing in the sources points anywhere.
2. **Pick the language.** One locale per capture, no auto-detection. Default to
   the language the context gives; `maestro-listen` itself defaults to `en-US`.
   English terms inside another language come through fine, so pick the
   language of the conversation, not of the jargon.
3. **Pick the labels.** `--mic-label` comes from the context. `--system-label`
   is the other party's name when known, otherwise a generic one. Pass
   `--title` and `--context` so the state carries them.
4. **Start**, as one command:

   ```
   maestro-listen start --locale it-IT --mic-label "Ada" --system-label "Sam" --title "Sam call" --context "framing document and role-play videos" --project "${CLAUDE_PROJECT_DIR}"
   ```

   Add `--them-only` for `/listen them-only`.
5. **When `start` refuses with exit 3**, read `already_running`. With
   `same_folder: true` the capture was opened from this folder: say who opened
   it and since when, and offer to attach to it (go on with `status` and `text`)
   instead of opening another. With `same_folder: false` say who holds the lock
   and since when, and stop: nothing about that capture is available from here.
6. **Say two things, one line each.** That the capture is open, and that the
   owner should tell whoever is on the call that it is being transcribed.
   Recording someone without telling them is not something this skill helps
   with, and macOS shows no visible indicator for system-audio capture.

Then go quiet. No confirmations, no progress notes.

## While the call runs

The owner is speaking to someone else. Every answer is **two or three lines**.
No headers, no bullet lists, no preamble.

- Read with `maestro-listen text --since <last second already read> --project "${CLAUDE_PROJECT_DIR}"`
  and keep the watermark, so a long call is never re-read from the top.
- Answer **only** from the transcript. When something was not said, say it was
  not said. Never fill a gap with what was probably meant.
- Writing lands on disk in blocks and `yap` only emits finalized segments, so
  the last five seconds or so are missing. When it matters, say how far the
  transcript reaches.
- Transcription degrades on technical terms and proper nouns. Reconstruct the
  sense, and treat verbatim quotes of technical material as unreliable.
- Without headphones the far side's voice leaves the speakers and re-enters the
  microphone. `maestro-listen` drops what it can (see **De-echoing** below);
  some gets through, so a microphone line that reads like the other person
  probably is.

### Automatic updates

Off by default. The owner turns them on during the call ("update me every ten
minutes") and off the same way.

Start `maestro-listen updates <minutes> --project "${CLAUDE_PROJECT_DIR}"` as a background command (the Monitor
tool when the session has it, otherwise a background Bash call). It prints
`UPDATE: …` whenever new cues have landed, which wakes the session; read only
what is new and comment. It prints `CAPTURE CLOSED` and exits on its own when
the capture stops. To turn updates off, stop that background command.

An update is worth sending when it says something the owner could act on before
the call ends: a theme from the objective still untouched, a claim left hanging,
a contradiction with what was said earlier, a number mentioned once and never
returned to. A running summary is the least useful thing to send, because the
owner can ask for that whenever they want.

## De-echoing

Two mechanisms, deliberately different in cost.

**During the call**, `maestro-listen` applies a mechanical filter: a microphone
cue is dropped when a system cue starting shortly before it reads similarly, or
when it sits almost entirely inside the far side's speech. Both thresholds were
tuned on a real call. It is instant and approximate.

**At close**, do the attribution by reading. The mechanical filter compares
strings; the two channels segment the same words differently, so one channel's
cue is often a fragment or a merge of the other's, which no ratio can pair.
Reading the raw two-channel transcript with `text --raw` settles
those cases, and it costs nothing extra because the whole transcript has to be
read anyway to write the note.

## Closing

On "we're done" or `/listen close`:

1. `maestro-listen stop --project "${CLAUDE_PROJECT_DIR}"`, which returns the
   segments with their offsets and input devices, the speakers heard, and a
   word count.
2. **When the capture is empty** (the result says so, or there is no exchange to
   speak of), stop here. Say what was captured, leave the working files in
   place, and write nothing. A call that never happened is not a note.
3. Read the whole transcript with `maestro-listen text --raw --project "${CLAUDE_PROJECT_DIR}"`
   and settle the attribution by reading. After `stop`, `text` reads the
   capture this folder just closed, segments merged at their offsets.
4. **Propose a destination folder** as the context says (see **Context**). There
   is no default path: the owner confirms or corrects, and usually names the
   place themselves. Never write before the confirmation.
5. Write **two files** side by side in the confirmed folder:
   - `YYYY-MM-DD - <Title>.md` — the note.
   - `YYYY-MM-DD - <Title> - transcript.md` — the transcript, echo removed,
     timestamps and speaker labels kept.
   - Each links the other with a wikilink.
6. **Save a memory of the call** with the command the context gives, and
   announce the write. A plain folder saves none.

### The note

Sections, in order, dropping any that has nothing in it:

- **Summary** — three to five lines. What the call was for and where it landed.
- **What came up** — what was said that matters, attributed to who said it.
- **Decisions** — what was settled.
- **Open questions** — what stayed unresolved.
- **Next steps** — who does what.

Quote verbatim when the exact wording carries weight, and mark it as a quote.
The transcript is right next door, so the note does not need to carry
everything.

## Rules

- **Write in the owner's language**, as the context gives it. This file is in
  English because it travels with the plugin; what reaches the owner follows
  their language.
- **Frontmatter on both files**: `tags:` in flow form, multi-dimensional
  (people, areas, subjects), and a one-line `description:`. Quote any value
  containing `: ` or starting with a YAML-sensitive character.
- **The note goes through the register pass of its context** before delivery,
  on the finished text. The transcript never does: those are other people's
  words and they go out untouched.
- **Never invent a speaker.** When a line's attribution is unclear, leave it
  unattributed.
- **One capture at a time on the machine.** Attach only to a capture opened
  from the same folder; from anywhere else, report who holds the lock and since
  when, nothing more.
- **The transcript stays next to the note**, permanently. The working copy
  under `~/.local/state/listen/` can be removed once both files are written.
