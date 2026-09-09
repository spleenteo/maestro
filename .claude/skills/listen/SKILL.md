---
origin: maestro
maestro_version: v2026.09.10.1
name: listen
description: Live listening on a call in progress. Captures system audio plus microphone with `yap`, keeps a growing transcript on disk, answers the owner's questions about what has been said so far, and on close writes a note plus the raw transcript into the vault. Use when the owner types /listen, or says "listen to this call", "start listening", "ascolta questa call", "registra l'intervista", or asks what was said during a call that is currently running.
---

# listen

Turns a call into something the orchestrator can consult **while it is still
happening**. `yap` transcribes system audio and microphone on-device, the
transcript grows on disk, and the orchestrator reads it on demand.

Built for interviews, discovery calls and client meetings, where the owner is
talking and needs an answer in two lines, not a report.

## Prerequisites

- **`yap`** — `brew install yap`. On-device transcription through the Speech
  framework. Nothing leaves the machine.
- **macOS 26 or later** — the framework `yap` relies on ships with 26.
- **Permissions** — Microphone and Screen Recording, granted to the terminal
  that runs the capture. macOS asks once.

`bin/listen` checks both and stops with a clear message when one is missing.
Never improvise a fallback: no other tool, no partial capture. Report what is
missing and the command that installs it.

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

`bin/listen` backs it: `start`, `status`, `text`, `stop`, JSON when piped. State
and the growing transcript live in `~/.local/state/listen/`, outside every
worktree and outside the vault. The lock is machine-wide, so a second `/listen`
from another instance or another session is refused with the details of the one
already running.

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
   at memory and the vault for the project and the people involved. State the
   conclusion in one line ("the Simone call, still open: the framing document
   and the role-play videos"). The owner corrects it in a few words or says
   nothing. Ask only when nothing in the sources points anywhere.
2. **Pick the language.** One locale per capture, no auto-detection. Default to
   the owner's language from preferences; `bin/listen` itself defaults to
   `en-US`. English terms inside another language come through fine, so pick the
   language of the conversation, not of the jargon.
3. **Pick the labels.** `--mic-label` is the owner's nick from preferences.
   `--system-label` is the other party's name when known, otherwise a generic
   one. Pass `--title` and `--context` so the state carries them.
4. **Say two things, one line each.** That the capture is open, and that the
   owner should tell whoever is on the call that it is being transcribed.
   Recording someone without telling them is not something this skill helps
   with, and macOS shows no visible indicator for system-audio capture.

Then go quiet. No confirmations, no progress notes.

## While the call runs

The owner is speaking to someone else. Every answer is **two or three lines**.
No headers, no bullet lists, no preamble.

- Read with `bin/listen text --since <last second already read>` and keep the
  watermark, so a long call is never re-read from the top.
- Answer **only** from the transcript. When something was not said, say it was
  not said. Never fill a gap with what was probably meant.
- Writing lands on disk in blocks and `yap` only emits finalized segments, so
  the last five seconds or so are missing. When it matters, say how far the
  transcript reaches.
- Transcription degrades on technical terms and proper nouns. Reconstruct the
  sense, and treat verbatim quotes of technical material as unreliable.
- Without headphones the far side's voice leaves the speakers and re-enters the
  microphone. `bin/listen` drops what it can (see **De-echoing** below); some
  gets through, so a microphone line that reads like the other person probably
  is.

### Automatic updates

Off by default. The owner turns them on during the call ("update me every ten
minutes") and off the same way.

Start `bin/listen-updates <minutes>` as a background monitor. It prints one line
whenever new cues have landed, which wakes the orchestrator; read only what is
new and comment. It exits on its own when the capture stops.

An update is worth sending when it says something the owner could act on before
the call ends: a theme from the objective still untouched, a claim left hanging,
a contradiction with what was said earlier, a number mentioned once and never
returned to. A running summary is the least useful thing to send, because the
owner can ask for that whenever they want.

## De-echoing

Two mechanisms, deliberately different in cost.

**During the call**, `bin/listen` applies a mechanical filter: a microphone cue
is dropped when a system cue starting shortly before it reads similarly, or when
it sits almost entirely inside the far side's speech. Both thresholds were tuned
on a real call. It is instant and approximate.

**At close**, do the attribution by reading. The mechanical filter compares
strings; the two channels segment the same words differently, so one channel's
cue is often a fragment or a merge of the other's, which no ratio can pair.
Reading the raw two-channel transcript with `--raw` settles those cases, and it
costs nothing extra because the whole transcript has to be read anyway to write
the note.

## Closing

On "we're done" or `/listen close`:

1. `bin/listen stop`, which returns the segments with their offsets and input
   devices, the speakers heard, and a word count.
2. **When the capture is empty** (the result says so, or there is no exchange to
   speak of), stop here. Say what was captured, leave the working file in place,
   and write nothing to the vault. A call that never happened is not a note.
3. Read the whole transcript with `--raw` and settle the attribution by reading.
4. **Propose a destination folder** in the vault, chosen from who was on the
   call and what it was about. There is no default path: the owner confirms or
   corrects. Never write before the confirmation.
5. Write **two files** side by side in the confirmed folder:
   - `YYYY-MM-DD - <Title>.md` — the note.
   - `YYYY-MM-DD - <Title> - transcript.md` — the transcript, echo removed,
     timestamps and speaker labels kept.
   - Each links the other with a wikilink.
6. Save a memory of the call with `bin/mem save`, and announce the write.

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

- **Write in the owner's language.** This file is in English because it travels
  between instances; what reaches the owner follows their preferences.
- **Frontmatter on both files**: `tags:` in flow form, multi-dimensional
  (people, areas, subjects), and a one-line `description:`. Quote any value
  containing `: ` or starting with a YAML-sensitive character.
- **The note goes through the `writing-register` skill** before delivery, on the
  finished text. The transcript does not: those are other people's words and
  they go out untouched.
- **Never invent a speaker.** When a line's attribution is unclear, leave it
  unattributed.
- **One capture at a time on the machine.** When `start` refuses, report who
  holds the lock and since when, and offer to attach to that capture instead of
  opening another.
- **The transcript stays in the vault** alongside the note, permanently. The
  working copy under `~/.local/state/listen/` can be removed once both files are
  written.
