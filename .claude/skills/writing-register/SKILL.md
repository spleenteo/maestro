---
origin: maestro
maestro_version: v2026.08.14.1
name: writing-register
description: The writing register in full, for two moments. Load it before drafting any text for a person other than the owner (an email, a message, a post, a comment, a quick translation) or a document for the vault or a repository, so the text is written under the rules of its domain (communication, documentation, synthesis) in the owner's tone and voice; and run it as the post-pass on the finished text before a vault write, an external post, or a README, CHANGELOG, howto or decision record written to a repository. Chat replies to the owner load nothing.
---

# Writing register

Two moments, one set of rules. At writing time the skill is the reference you write under; at delivery it is the second reading. Loaded once, it stays in context for the session.

Condensed rules: `CLAUDE.md` → `## Writing register`. Human reference with bilingual examples: `howto/10-writing-register.md`.

## Where the values come from

The owner's values live in the `## Writing register` block of `private/preferences.md`, a fenced `yaml` block. Every key is optional; a missing key takes the default below.

```yaml
suspended: []                 # prohibitions to suspend, e.g. [4, 6]
post_pass: on                 # on | off
tone_default:
  communication: professional # friendly | professional | formal | neutral
  documentation: neutral
  synthesis: neutral          # synthesis is always neutral
voice: ""                     # one line on how the owner sounds, e.g. "warm, direct, dry humour"
communication:
  sign_off: ""                # closing lines of every email, e.g. "Have a nice day,\nAlex"
translation:
  enabled: false              # the translate skill runs only when true
  pair: ""                    # e.g. "it -> en"
  new_context_marker: ""      # a draft opening with it starts a fresh translation
  source_words_max: 1         # source-language words allowed per text
  labels: [Translation, More polished version]
avoid_words: []               # words the owner never wants to see
```

- In an instance: read the block from `private/preferences.md`. A block still written as bare lines (`suspended: [4, 6]`, `post_pass: off`) is honoured for those two keys until `/maestro:maestro-sync` converts it.
- In a satellite: the block arrives inside the `# Satellite session` context, under `## Identity (from the mother instance)`. Read it there; the repo has no preferences of its own.
- `post_pass: off` means the delivery pass does not run; the writing-time rules still apply.
- Where the block overlaps `## Communication preferences` ("Tone with others", "Things to avoid"), the block wins.

`bin/register-check` runs from the instance root. In a satellite, the `# Satellite session` block names the mother's copy by absolute path: use that.

## How to apply, at writing time

1. Pick the domain from what the text is for (table below). Commits keep their own convention. A reply in chat to the owner has no domain: the prohibitions and `CLAUDE.md` → `## Tone` bind it. A text for someone else drafted in chat takes its domain.
2. Pick the tone: `tone_default` for that domain, unless the request names another ("formale", "neutral", "più professionale").
3. Write under rule zero, the seven prohibitions, the domain rules and the tone markers. Keep the `voice` line in mind for communication; `avoid_words` never appear.
4. Read the finished text once against the lexical tells and the rhythm checks. For anything longer than a chat line, run `bin/register-check` on it (`printf '%s' "$text" | bin/register-check - --json`).
5. Deliver the text only. No list of what you avoided.

## Rule zero

- Correct a pattern only when it is a confirmed defect in context. A match with a list is a candidate, never a reason by itself.
- Protect literal, domain-valid, quoted and attributed uses, genre-natural phrasing, and concrete calls to action.
- Never add a claim, advice or an anecdote. Never drop a figure, date, name, URL, placeholder (`XXX`) or condition.
- Stripping warmth is a defect too: a message to a person that turns into telegraphese is wrong.

## The seven prohibitions

| # | Banned | Fix |
|---|---|---|
| 1 | Meta-commentary on the text itself ("it's worth noting", "this is the point that matters most", "vale la pena notare") | Cut. Weight comes from position and facts |
| 2 | Sycophantic concessions ("rightly so", "this must be granted", "we have no reason to doubt") | Use the other party's claim as a premise and move on |
| 3 | Negative parallelism, every variant: "not X, but Y", "not only X but also Y", "more than X, Y", "X isn't A, it's B", the tailing "Y, not X"; "non è X, è Y", "non solo X, ma Y" | Write the affirmative half alone. Exception: a factual contrast between two real alternatives stays ("Use the CMA, not the CDA", "40%, not 4%") |
| 4 | Em dash as a pause | Comma, colon, semicolon, parentheses, full stop |
| 5 | Bold as emphasis inside a sentence | Rewrite the sentence. Bold stays for structural labels, and never appears in an email body |
| 6 | Rhythmic triads: three adjectives or examples where two carry the content | Keep the two |
| 7 | Judgment as tone of voice ("solid work", "a robust foundation", "the path is set") | Removal test: delete the phrase; if the reader loses nothing, it was tone. "The parser has no test for empty input" stays |

## Lexical tells

| Pattern | Examples | Fix |
|---|---|---|
| Throat-clearing openers | "Here's the thing:", "The truth is,", "Let me be clear", "Let's dive in" | Start with the point |
| Emphasis crutches | "Full stop.", "Let that sink in.", "Make no mistake" | Cut |
| Significance inflation | "stands as a testament to", "pivotal moment", "cornerstone of", "plays a crucial role", "underscore the importance" | Say what it does or what changed |
| Promotional | "world-class", "state-of-the-art", "seamless", "game-changer", "synergy", "robust", "powerful" | State what it does. "Scalable" and "ecosystem" stay when literal for the product |
| Business collocations | "leverage our platform", "navigate the complex landscape", "harness the power of AI", "circle back", "touch base" | Plain verb |
| Superficial -ing tails | ", highlighting…", ", showcasing…", ", fostering…", ", paving the way for…", ", ensuring…" | Cut, or make it a main clause with a subject |
| Vague attribution | "Experts argue", "Studies show", "Many believe", "it is widely held" | Name the source or drop it |
| Copula avoidance | "serves as a testament", "stands as a cornerstone", "functions as" | is, are, has |
| AI vocabulary | "delve", "garner", "paramount", "meticulous", "moreover", "furthermore", "myriad" | Plain word |
| Filler | "It's worth noting", "When it comes to", "In order to", "Due to the fact that", "In terms of", "at the end of the day", "at its core" | Delete or shorten |
| Hedge stacks | "could potentially", "may possibly", "(arguably …)" | One hedge or none |
| Generic positive endings | "The future looks bright", "Exciting times lie ahead", "Looking forward to our continued success" | End on the concrete next step, or stop |
| Conclusion scaffolding | "In conclusion", "In summary", "Ultimately," as an opener, "Firstly / Secondly" | Cut. Numbered steps of a procedure stay |
| Rhetorical question openers | "What does this mean for…", "Why should you care?" | State it |
| Colon reveal | "The answer is: …" | Plain sentence |
| False agency | "the numbers speak for themselves", "the data tells a clear story" | Name who concludes what |
| False ranges | "from X to Y, from A to B" | One accurate span |
| Elegant variation | agency, studio, partner, firm for the same subject | Same word each time |
| Chatbot artifacts | "I hope this helps", "Great question!", "Certainly!", "Let me know if you need anything else", "I'd be happy to", "at your convenience", "I hope this email finds you well" | See the communication domain: a closing with a concrete object stays |
| Knowledge-cutoff hedges | "based on available information", "as of my last" | Cut |

Calques from the source language are the usual translation risk. From Italian into English: "in order to" (per), "due to the fact that" (dato che), "could potentially" (potrebbe eventualmente), "aforementioned" (suddetto), "pertaining to" (in merito a), "henceforth" (d'ora in poi). Another language pair gets its own list in the `## Notes` section of `private/preferences.md`.

## Rhythm, by eye

- Four sentences in a row of similar length
- Three or more fragments of five words or fewer in a row
- Consecutive sentences opening with the same word ("I… I… I…", "We… We…")
- Paragraphs opening one after another with "Also,", "Moreover,", "However,", "Finally,"
- Sentences ending with ", ensuring…", ", allowing…", ", enabling…"
- More than one exclamation mark in a short text

## Domains

| Domain | For | Default tone |
|---|---|---|
| Communication | emails, letters, chat messages to people (customers, partners, colleagues), quick translations for chat; a draft to translate in two versions goes to the `translate` skill where translation is enabled | `tone_default.communication` (professional) |
| Documentation | dossiers, vault documents, logbook entries, README and howto guides, decision records, technical notes | `tone_default.documentation` (neutral) |
| Synthesis | daily and weekly reports, recaps, status lines, task titles in reports and task managers | neutral, always |

### Communication

- Open with one line addressed to the person: a greeting and, when natural, a short personal line tied to them or to the thread ("All good thanks, hope you're doing well too!"). The canned "I hope this email finds you well" goes.
- One topic per paragraph. Lists only for steps or options the reader acts on.
- Close on a concrete next step with its object ("grab a slot here", "I'll ping you once it's fixed"). A generic offer with no object goes ("Let me know if you need anything else").
- End with `communication.sign_off` when it is set, in every email, translated or written directly.
- Contractions yes. At most one exclamation mark. Emoji and smileys only when the source or the `voice` line has them.
- No bold, no headers, no markdown in an email body. Full URLs, no tracking parameters.
- Names, prices, plan names, ids, dates and placeholders exactly as given.

### Documentation

- Start with the subject, no preamble. End when the content ends, no recap coda.
- Structure is welcome: headings, tables, bold as labels.
- Every evaluation anchored to a fact or a criterion.
- A skill that writes documentation may override the neutral tone for its genre (the logbook keeps the owner's first-person narrative); it says so in its own instructions.

### Synthesis

- One line per fact. No opening, no closing, no transitions.
- Italian: past participle first ("Inviata la proposta ad Acme", "Chiusi 3 to-do del roadshow"). English: past-tense verb first ("Sent the proposal to Acme").
- What, who, outcome. A reason only when it changes a decision. No adjectives, no adverbs.
- Numbers as digits, names as the reader knows them.

Task titles and status lines in reports and external task managers follow synthesis. Rows of `memories.db` stay outside the register.

## Tone

Tone changes delivery and leaves the facts as they are. The default comes from `tone_default`; the request can override it.

| Tone | Markers | Example |
|---|---|---|
| friendly | first name, contractions, a light personal line, one smiley at most | "Hi Alex, thanks again for the call today :)" |
| professional | first name, contractions, no jokes, no emoji | "Hi Alex, thanks for your time today." |
| formal | surname and title when the relationship calls for it, no contractions, no emoji | "Dear Ms Rossi, thank you for your time today." |
| neutral | no address, no warmth markers, facts only; the only tone for synthesis | "Call with Acme held on 16 September." |

## The post-pass, at delivery

Runs on the finished text, right before it is written or sent, when `post_pass` is on:

- a document about to be written to the owner's vault (`documents_path`, `til_path`), a logbook entry
- a post or a comment about to go out to an external channel
- a `README`, a `CHANGELOG` entry, a howto guide or a decision record about to be written to a repository

No length threshold: a two-line comment goes through it. Chat replies, devflow work documents (their gate is `bin/register-check`), specification files (`CLAUDE.md`, `SKILL.md`, agent files, `preferences.md`), `memories.db` rows, commit messages, code and any text the owner wrote do not.

### Step 1: deterministic check

```bash
bin/register-check <file> --json
bin/register-check <file> --json --skip 4,6      # when preferences suspend some
printf '%s' "$text" | bin/register-check - --json
```

Findings carry `rule`, `domain`, `line`, `col` and `match`. `violation` (rules 4 and 5): fix it. `candidate` (rules 3 and 6): judge it under rule zero. The tool needs no network; if it is missing, do the whole pass by reading and say so in the unresolved notes.

### Step 2: the seven prohibitions and the lexical tells

Verify all seven, including the three the tool cannot see, then the lexical tells and the rhythm checks, on the domain the text belongs to: an email keeps its opening line and its sign-off, a synthesis keeps its one-line-per-fact shape, a document keeps its labels.

### The fidelity guard

Form only. This is the hard boundary of the pass.

You may reformulate a sentence, swap punctuation, break a triad, remove an epithet, replace a vague attribution with the source already present in the text.

You may not add a claim the text did not make; remove a claim the text made, including figures, dates, names, URLs and citations; touch quoted material; touch code, fenced blocks, paths, wikilinks, numbers, proper nouns; touch frontmatter; strip the warmth a message to a person carries (rule zero).

If a passage cannot be corrected without moving its meaning, leave it as it stands and record it in the unresolved notes.

### Output contract

Return the corrected text and nothing else, ready to be written or sent. No preamble, no summary of changes. Delivery to the owner is silent.

If something was left uncorrected, append after the text a block the orchestrator keeps to itself:

```
UNRESOLVED
- line 12: negative parallelism, rewriting it would change the claim about the API limit
```

The orchestrator surfaces that block only when the residual risk is material, or when the owner asks.

## What this skill is not

It does not rewrite for personality beyond the `voice` line: a logbook note and a Basecamp comment gain nothing from a livelier register, and prohibition 7 exists to keep that out.

External skills such as `humanizer` and `unslop` stay available for the owner to call explicitly on a text they want worked over. They never run in the automatic flow: neither is bound by the fidelity guard above, and their process is interactive or script-driven.
