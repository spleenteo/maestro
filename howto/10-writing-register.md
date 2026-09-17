---
origin: maestro
maestro_version: v2026.09.15.1
tags: [howto, writing-register, prose, style, register, domains, tone, translation, preferences, humanizer, unslop, orchestrator, discipline]
description: "Full reference for the writing register: rule zero, the seven prose prohibitions with bilingual examples, the perimeter that follows the reader, the three domains (communication, documentation, synthesis) with their tones, the lexical tells, the per-instance values in preferences and the questions setup and sync ask, the post-pass through the `writing-register` skill, the `bin/register-check` tool and its heuristics. The condensed rules live in CLAUDE.md."
---

# 10 — Writing register

This is the canonical reference for the shape of the prose an orchestrator produces. `CLAUDE.md` carries the condensed rules, the `writing-register` skill carries the working rules the orchestrator loads before writing, and this file carries the rationale, the bilingual examples and the per-instance values.

It is distributed by Maestro (`origin: maestro`): don't edit it in place. Changes go through the template and come back via `/maestro:maestro-sync`.

The register exists because a model writes fluently by default, and fluent default prose has a recognisable shape: it comments on itself, it agrees before arguing, it reaches for the em dash, it closes with encouragement. Each of the seven prohibitions removes one of those habits. One set of prohibitions was not enough, though: an email to a partner needs an opening line and a sign-off that a daily recap must not have, so the register also names the domain and the tone it is written in.

## Perimeter

The perimeter follows the reader. The register applies to text a person reads, wherever it lands:

- documents in the owner's vault (`documents_path`, `til_path`), dossiers, logbook entries
- posts and comments on external channels (Basecamp, Slack, anything the instance is wired to)
- emails, messages and translations written for someone other than the owner
- documents for people written to a repository: `README`, `CHANGELOG`, the howto guides, decision records, shaping and devflow documents
- internal reports from a craft agent to the orchestrator, because the synthesis inherits the shape of its source
- replies in chat to the owner, bound by the prohibitions and by `CLAUDE.md` → `## Tone`, with no domain and no post-pass; a text for someone else drafted in chat takes its domain

The register does not apply to files a model reads as instructions: `CLAUDE.md`, `SKILL.md` files, agent files, `preferences.md`. They are written for the agent that executes them, and emphasis or a contrast there has an operational job. The howto guides are read by people (the owner, whoever installs Maestro) and by the `guide` skill: they are inside, and rule zero protects the contrasts that carry an instruction.

Also outside: titles and descriptions in `memories.db`, too short for the prose patterns to appear; commit messages, which follow their own convention; code.

**Text the owner wrote** is never rewritten. When the owner hands over a draft and asks for it to be published, it goes out verbatim. Flagging a violation in one line before publishing is fine; the correction is the owner's call.

## Rule zero

Every rule below produces candidates. A pattern is corrected only when it is a confirmed defect in the text at hand:

- protect literal, domain-valid, quoted and attributed uses, genre-natural phrasing, and concrete calls to action (a call to action such as "reply here or grab a slot" stays, whatever the tool reports);
- never add a claim, advice or an anecdote; never drop a figure, date, name, URL, placeholder or condition;
- stripping warmth is a defect too: a message to a person that turns into telegraphese is wrong.

## The seven prohibitions

### 1 — Meta-commentary on the text itself

**Banned.** Sentences that describe the text's own structure or announce the weight of what follows.

**Why.** Weight comes from position in the list and from the facts carried. A sentence that says "this is the point that matters most" spends a line without adding one.

```
✗ It's worth noting that the parser has no timeout.
✗ The easy part is genuinely easy: the config is one file.
✗ This is the point that weighs most in the whole audit.
✓ The parser has no timeout.
✓ The config is one file.
```

### 2 — Sycophantic concessions

**Banned.** Agreeing out loud before making a point.

**Why.** If someone else's claim holds, use it as a premise and move on. The concession performs fairness instead of exercising it.

```
✗ This must be granted right away, because it's true: the API is slow.
✗ We have no reason to doubt the benchmark, and rightly so.
✓ The API is slow, so the cache earns its complexity.
✓ The benchmark puts it at 340ms.
```

### 3 — Negative parallelism

**Banned.** Defining something by first denying its opposite, in every variant, including the tailing form.

**Why.** The construction spends half a sentence on what the subject is not. Writing the affirmative half alone says the same thing and reads faster.

**Exception.** A factual contrast between two real alternatives stays: "Use the CMA, not the CDA", "40%, not 4%", "il file va in `private/`, non nel repo". The reader needs both halves to pick the right one. `bin/register-check` cannot tell the two apart, so its rule 3 findings stay candidates.

```
EN
✗ It's not a bug, it's a missing guard.
✗ The pass is not just cosmetic, but structural.
✗ It is not so much slow as unpredictable.
✗ More than a rewrite, a rethink.
✗ It searches by meaning, not just keywords.
✗ A refactor? No: a rewrite.
✓ A guard is missing.
✓ The pass changes the structure.
✓ It is unpredictable.
✓ It searches by meaning.
✓ Use the CMA for writes, not the CDA.

IT
✗ Non è un bug, è una guardia mancante.
✗ Non solo cosmetico, ma strutturale.
✗ Non si tratta di stile, ma di leggibilità.
✗ Non tanto lento quanto imprevedibile.
✗ Più che un refactor, una riscrittura.
✗ Cerca per significato, non solo per parole chiave.
✓ Manca una guardia.
✓ Cambia la struttura.
✓ È imprevedibile.
✓ Cerca per significato.
✓ Il costo è 40%, non 4%.
```

### 4 — Em dash as a pause

**Banned.** The em dash used to break a sentence.

**Why.** Comma, colon, parentheses and full stop each carry a different relation between the two halves. The em dash flattens all of them into one gesture, and the gesture repeats.

```
✗ The parser is slow — it reparses on every call.
✓ The parser is slow: it reparses on every call.
✓ The parser is slow, because it reparses on every call.
✓ The parser is slow. It reparses on every call.
```

The em dash stays available as a separator in headings and as a range marker, where it is not a pause.

### 5 — Bold as punctuation

**Banned.** Bold used for rhetorical emphasis inside a sentence.

**Allowed.** Bold as a structural label: keys in a list, section names, labels in a table. Never in an email body, where markdown has no reader.

**Why.** Emphasis that repeats stops being emphasis. If a sentence needs bold to land, the sentence needs rewriting.

```
✗ You must **never** write to that path.
✗ This is **the** decisive constraint.
✓ Writes to that path fail with EACCES.
✓ **Rules**: never write to that path.
✓ - **Identity** your name, the archetype, the adjectives
```

### 6 — Rhythmic triads

**Banned.** Three adjectives or three examples in a row where two suffice.

**Why.** The third item usually arrives for cadence rather than for content. A list of three real items is fine; a list of three where the third repeats the second is filler.

```
✗ The tool is fast, cheap, and reliable.
✗ It streamlines processes, enhances collaboration, and fosters alignment.
✓ The tool is fast and cheap.
✓ It cuts the review step from two days to one.
```

### 7 — Judgment as tone of voice

**Banned.** Evaluative stock phrases, decorative epithets, encouraging closings.

**Allowed.** Evaluation as content: a verdict, a risk, a recommendation, anchored to a criterion or a fact.

**The removal test.** Delete the phrase. If the reader loses nothing, it was tone and it goes. If the reader loses a fact, a risk or a recommendation, it was content and it stays.

```
✗ Solid work on the parser.            → nothing lost → cut
✗ A robust foundation to build on.     → nothing lost → cut
✗ The path is set, exciting times.     → nothing lost → cut
✓ The parser has no test for empty input.
✓ I would not ship it: the migration doubles the API calls.
✓ Module X has no permission tests.
```

When the owner asks for an opinion, the verdict is the answer and it gets given. The anchor stays mandatory:

```
✗ It doesn't quite convince me.
✓ It doesn't work: the opening promises one thing and the body does another.
```

Prohibition 7 bans judgment as decoration. It does not ban warmth in a message to a person: "thanks again for the call today" in an email is the communication domain doing its job, and rule zero protects it.

## The three domains

Every text for a reader belongs to one domain, and the domain gives it a shape. The orchestrator picks it from what the text is for; commits keep their own convention.

| Domain | For | Shape | Default tone |
|---|---|---|---|
| Communication | emails, letters, chat messages to people (customers, partners, colleagues), quick translations for chat | an opening line addressed to the person; one topic per paragraph; a close on a concrete next step with its object; the instance sign-off; contractions; at most one exclamation mark; no markdown in an email body | `tone_default.communication`, professional when unset |
| Documentation | dossiers, vault documents, logbook entries, README and howto guides, decision records, technical notes | start with the subject, no recap coda; headings, tables and bold labels welcome; every evaluation anchored to a fact | `tone_default.documentation`, neutral when unset |
| Synthesis | daily and weekly reports, recaps, status lines, task titles in reports and task managers | one line per fact; past participle first in Italian, past-tense verb first in English; no opening or closing; no adjectives, no adverbs; digits for numbers | neutral, always |

```
Communication, friendly
✓ Hi Alex, thanks again for the call today :)
  The export you asked about ships on Thursday; I'll ping you once it's live.
  Have a nice day,
  Sam

Communication, formal
✓ Dear Ms Rossi, thank you for your time today.
  The export ships on Thursday. I will confirm once it is live.
  Kind regards,
  Sam

Synthesis, IT
✓ Inviata la proposta ad Acme. Chiusi 3 to-do del roadshow. Rinviata la call con Rossi al 24.
✗ Oggi è stata una giornata produttiva: ho inviato la proposta ad Acme e chiuso ben tre to-do.

Synthesis, EN
✓ Sent the proposal to Acme. Closed 3 roadshow to-dos.
```

A skill that writes one domain may override its tone for the genre and says so in its own instructions: the `logbook` skill keeps the owner's first-person narrative and an evocative title inside the documentation domain. Task titles and status lines in reports and external task managers follow synthesis; rows of `memories.db` stay outside the register.

### Tone

Tone is a parameter separate from the domain. It changes delivery and leaves the facts as they are. The default comes from `tone_default` in preferences; the request overrides it ("formale", "neutral", "più professionale").

| Tone | Markers | Example |
|---|---|---|
| friendly | first name, contractions, a light personal line, one smiley at most | "Hi Alex, thanks again for the call today :)" |
| professional | first name, contractions, no jokes, no emoji | "Hi Alex, thanks for your time today." |
| formal | surname and title when the relationship calls for it, no contractions, no emoji | "Dear Ms Rossi, thank you for your time today." |
| neutral | no address, no warmth markers, facts only; the only tone for synthesis | "Call with Acme held on 16 September." |

The `voice` line in preferences ("warm, direct, dry humour; emoji from the source stay") shapes communication inside the chosen tone. Documentation and synthesis ignore it.

## Lexical tells and rhythm

Beyond the seven prohibitions, the `writing-register` skill carries a catalog of patterns that mark default model prose: throat-clearing openers ("Here's the thing:"), significance inflation ("stands as a testament to"), promotional words ("seamless", "robust"), business collocations ("leverage", "circle back"), superficial `-ing` tails (", highlighting…"), vague attributions ("studies show"), copula avoidance ("serves as"), AI vocabulary ("delve", "paramount", "moreover"), filler ("in order to"), hedge stacks ("could potentially"), generic positive endings, conclusion scaffolding, false ranges, elegant variation, chatbot artifacts ("I hope this email finds you well", "Let me know if you need anything else"). Each has a fix in the skill's table. Rule zero applies: a chatbot closing with a concrete object ("reply here or grab a slot") stays.

Calques from the source language are the usual translation risk. From Italian into English: "in order to" (per), "due to the fact that" (dato che), "could potentially" (potrebbe eventualmente), "aforementioned" (suddetto), "pertaining to" (in merito a), "henceforth" (d'ora in poi). An instance with another pair adds its own list to the `## Notes` section of `private/preferences.md`.

Rhythm is checked by reading: four sentences in a row of similar length, three or more fragments of five words or fewer, consecutive sentences opening with the same word, paragraphs opening with "Also,", "Moreover,", "However,", sentences ending with ", ensuring…", more than one exclamation mark in a short text.

## Per-instance values

The owner's values live in the `## Writing register` block of `private/preferences.md`, one fenced `yaml` block under the heading. Every key is optional and takes its default when missing; the block absent means the full register with the defaults.

```yaml
suspended: []                 # prohibitions to suspend, e.g. [4, 6]
post_pass: on                 # on | off
tone_default:
  communication: professional # friendly | professional | formal | neutral
  documentation: neutral
  synthesis: neutral          # always neutral
voice: ""                     # one line, e.g. "warm, direct, dry humour; emoji from the source stay"
communication:
  sign_off: ""                # e.g. "Have a nice day,\nAlex"
translation:
  enabled: false
  pair: ""                    # e.g. "it -> en"
  new_context_marker: ""      # e.g. "Ciao,"
  source_words_max: 1
  labels: [Translation, More polished version]
avoid_words: []               # e.g. [genuinely, leverage]
```

Keep the block fenced. A satellite session receives this section through the plugin's identity extract, which keeps fenced content intact and closes a section at any heading or setext underline: a bare sign-off line such as `--` would cut the block in half. Where the block overlaps `## Communication preferences` ("Tone with others", "Things to avoid"), the block wins.

`post_pass: off` keeps the rules active at writing time and skips the skill before each write or send. `suspended` reaches `bin/register-check` as `--skip`, passed by the skill.

### The questions setup and sync ask

`/maestro:new-instance` asks these after its ten questions, skippable with one answer; `/maestro:maestro-sync` asks once for the keys an instance lacks, proposing the owner's `## Communication preferences` lines where they overlap, and writes the answers after a backup of `preferences.md`. A skipped question writes its default with a `# default` comment.

| # | Question | Default | Example |
|---|---|---|---|
| 1 | Default tone for emails and messages to people? | professional | friendly "Hi Alex, thanks again for the call :)"; professional "Hi Alex, thanks for your time."; formal "Dear Ms Rossi, thank you for your time."; neutral "Call held on 16 September." |
| 2 | Default tone for documents and notes? | neutral | neutral suggested; friendly or professional adds an address and warmth markers to documents |
| 3 | Your voice in one line? | none | "warm, direct, dry humour; emoji from the source stay" |
| 4 | Sign-off for every email? | none | "Have a nice day,\nAlex" |
| 5 | Do you translate your drafts? If yes: language pair, source-language words allowed per text, labels | off | "it -> en", 1, [Translation, More polished version] |
| 6 | Words you never want to see? | none | [genuinely, leverage] |

## The post-pass

Every document destined for the vault, every post or comment on an external channel, and every `README`, `CHANGELOG` entry, howto guide or decision record written to a repository goes through the `writing-register` skill before delivery, on the finished text, aware of its domain. There is no length threshold: a two-line Basecamp comment goes through it, because what leaves the house is the hardest to retract.

Chat replies never go through the pass. Devflow work documents keep the mechanical check as their gate.

### What the pass may change

Form only. The pass may reformulate a sentence, swap punctuation, break a triad, remove an epithet.

The pass may not:

- add a claim the text did not make
- remove a claim the text made
- touch quoted material, whether it comes from an email or from a comment
- touch code, paths, wikilinks, numbers, proper nouns
- strip the warmth a message to a person carries

If a sentence cannot be corrected without moving its meaning, the pass leaves it and reports it. Delivery is silent: the orchestrator hands over the finished text without narrating what it changed.

### Coexistence with `humanizer` and `unslop`

Some instances have the external `humanizer` or `unslop` skills installed. The automatic flow always runs `writing-register`, the only one bound by the fidelity guard above and by the owner's values, and the only one that delivers silently. `humanizer` and `unslop` stay available when the owner calls them explicitly on a text they want worked over, with their own process and output. `unslop`'s contract ("a scanner match alone never authorizes an edit", protection of genre-natural uses and concrete calls to action, warmth stripped into telegraphese as a defect) is the source of rule zero. An instance that ran `humanizer` inside its own translation flow can replace that flow with the `translate` skill and the values above; nothing is removed from the instance.

## `bin/register-check`

Four of the seven prohibitions have a syntactic signature and are checked deterministically:

```bash
bin/register-check note.md                  # human-readable report
bin/register-check note.md --json           # machine-readable
bin/register-check - < draft.txt            # from stdin
bin/register-check note.md --skip 4,6       # suspend rules
```

Exit 0 means clean, 1 means findings, 2 means a usage error or an unreadable file.

Rules 4 and 5 are reported as `violation`: the match is the offence. Rules 3 and 6 are reported as `candidate`: the match is a probable offence that a reader confirms under rule zero. A three-item run inside a longer enumeration is not a triad, and the tool counts the whole run before reporting.

The tool skips YAML frontmatter, fenced code blocks and blockquote lines, and masks inline code, wikilinks, link targets, bare URLs and quoted spans in balanced double quotes (`"…"`, `“…”`, `«…»`) before matching, so a quoted example of a banned pattern raises nothing. Single quotes stay unmasked: they are apostrophes. A straight quote after a digit is an inch mark and never opens or closes a quotation. Headings skip rules 4 and 6. Without the Oxford comma, a run of three is reported only when its items are parallel: same length, no function word (`the`, `with`, `its`, `no`; `il`, `con`, `senza`); a comma followed by a pair (`for any question, reply here or book a slot`) is a clause, and a triad whose last item opens with a preposition (`chiaro, diretto e senza fronzoli`) is left to the reader. Prohibitions 1, 2 and 7 are semantic and stay with the skill.

The tool never reads `preferences.md`. Exceptions reach it as `--skip`, passed by the skill that read them.

## Reference

The seven prohibitions were formulated by the owner. The extended net draws on [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), maintained by WikiProject AI Cleanup, on the [`humanizer`](https://github.com/blader/humanizer) skill (MIT), which organises those observations into 29 patterns, and on the [`unslop`](https://github.com/sublayerapp/unslop) skill, whose contract on candidates and fidelity became rule zero. The domains and the tones come from a trial in one instance on five real texts (a recap, a call note, a follow-up email and two translations), 2026-09-16.
