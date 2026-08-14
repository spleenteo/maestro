---
origin: maestro
maestro_version: v2026.08.14.1
name: writing-register
description: Post-pass over finished text before delivery, to enforce the writing register. Runs on every document destined for the owner's vault and on every post or comment going out to an external channel (Basecamp, Slack, anything the instance is wired to). Checks the seven prohibitions plus a wider net of AI-writing patterns, changing form only and never content. Chat replies do not go through it.
---

# Writing register — post-pass

This skill is the second reading. The seven prohibitions apply while the text is being written; this pass runs on the finished text, right before it is written to disk or sent out.

Full reference for the register: `howto/10-writing-register.md`.

## When the orchestrator invokes it

- A document about to be written to the owner's vault (`documents_path`, `til_path`)
- A logbook entry about to be written
- A post or a comment about to go out to an external channel

No length threshold. A two-line comment goes through it, because what leaves the house is the hardest to retract.

It is not invoked on: chat replies, specification files (`CLAUDE.md`, `SKILL.md`, agent files, `preferences.md`, howto guides), `memories.db` writes, commit messages, code, and any text the owner wrote themselves.

## Read the exceptions first

If `private/preferences.md` declares a `## Writing register` block, honour it:

```markdown
## Writing register
suspended: [4, 6]
post_pass: on
```

- `post_pass: off` means this skill does not run at all
- `suspended: [...]` lists prohibitions to leave alone, and the numbers are passed straight to the tool as `--skip`

Block absent means the full register with the pass on.

## Step 1 — deterministic check

Four prohibitions have a syntactic signature. Run the tool before reading, from the repo root:

```bash
bin/register-check <file> --json
bin/register-check <file> --json --skip 4,6      # if preferences suspend some
printf '%s' "$text" | bin/register-check - --json
```

Findings come back with `rule`, `kind`, `line`, `col` and `match`:

- `kind: violation` (rules 4 and 5) means the match is the offence. Fix it.
- `kind: candidate` (rules 3 and 6) means a probable offence. Read it and judge: a list of three real items is legitimate, three adjectives for cadence are not.

Exit code 3 does not exist here; the tool needs no Ollama and no network. If the tool is missing, do the whole pass by reading and say so in the unresolved notes.

## Step 2 — the seven prohibitions

Verify all seven, including the three the tool cannot see:

| # | Prohibition | Fix |
|---|---|---|
| 1 | Meta-commentary on the text itself | Cut the sentence. Weight comes from position and facts |
| 2 | Sycophantic concessions | Use the other party's claim as a premise and move on |
| 3 | Negative parallelism, every variant | Write the affirmative half alone |
| 4 | Em dash as a pause | Comma, colon, parentheses, full stop |
| 5 | Bold as rhetorical emphasis | Rewrite the sentence. Bold stays for structural labels |
| 6 | Rhythmic triads | Keep the two that carry content |
| 7 | Judgment as tone of voice | Apply the removal test |

**The removal test** for prohibition 7: delete the phrase. If the reader loses nothing, it was tone and it goes. If the reader loses a fact, a risk or a recommendation, it was content and it stays. "Solid work on the parser" goes. "The parser has no test for empty input" stays.

## Step 3 — the extended net

Beyond the seven, correct these on the text you are passing over:

| Pattern | Signature | Fix |
|---|---|---|
| Vague attributions | "many observers note", "it is widely held", "studies show" | Name the source or drop the claim |
| Promotional language | "powerful", "groundbreaking", "seamless", "robust" | State what it does |
| Superficial `-ing` analyses | "underscoring its role", "highlighting the interplay" | Cut, or turn into a main clause with a subject |
| Excessive hedging | "it could potentially be argued that", "may perhaps" | Say it, or say you don't know |
| Filler phrases | "in order to", "at its core", "it is important to note" | Delete |
| False ranges | "from hobbyists to enterprises, from solo devs to teams" | One accurate span |
| Elegant variation | the same subject renamed three ways in a paragraph | Use the same word each time |
| Copula avoidance | "serves as", "functions as", "stands as" | "is", "are", "has" |

## The fidelity guard

Form only. This is the hard boundary of the pass.

**You may**: reformulate a sentence, swap punctuation, break a triad, remove an epithet, replace a vague attribution with the source already present in the text.

**You may not**:

- add a claim the text did not make
- remove a claim the text made, including figures, dates, names and citations
- touch quoted material, whether it comes from an email or from a comment
- touch code, fenced blocks, paths, wikilinks, numbers, proper nouns
- touch frontmatter

If a passage cannot be corrected without moving its meaning, leave it as it stands and record it in the unresolved notes.

## Output contract

Return the corrected text and nothing else, ready to be written or sent. No preamble, no summary of changes, no list of what was found. Delivery to the owner is silent.

If something was left uncorrected, append after the text a block the orchestrator keeps to itself:

```
UNRESOLVED
- line 12: negative parallelism, rewriting it would change the claim about the API limit
```

The orchestrator surfaces that block only when the residual risk is material, or when the owner asks.

## What this skill is not

It does not rewrite for voice or personality. A logbook note and a Basecamp comment gain nothing from a livelier register, and prohibition 7 exists to keep that out.

If the instance also has the external `humanizer` skill installed, that one stays available for the owner to call explicitly on a text they want worked over. It never runs in the automatic flow: it is not bound by the fidelity guard above, and its process is interactive.
