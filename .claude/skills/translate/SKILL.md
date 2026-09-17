---
origin: maestro
maestro_version: v2026.09.16.1
name: translate
description: Translate a draft the owner wrote, in two labeled versions, under the writing register. Runs only in an instance whose `## Writing register` block sets `translation.enabled` to true; elsewhere it hands the request back to ordinary chat. Use when the owner pastes a draft in the source language of `translation.pair` (an email, a message, a reply) and asks to translate it, or when a draft opens with `translation.new_context_marker`. Also translates a text someone else wrote that the owner wants to read in the target language, revises a draft already written in the target language ("Revised") and cleans transcribed speech. Interface strings, code and files of a software project are never its business.
---

# Translate

Two versions of the owner's draft in the target language, and nothing else. The first keeps the source's form; the second is what a native speaker would write with the same voice and facts.

## Step 0: is translation on?

Read `translation` in the `## Writing register` block: `private/preferences.md` in an instance, the `# Satellite session` context (under `## Identity (from the mother instance)`) in a satellite. A request about interface strings, code or the files of a software project is not a draft: answer it as ordinary chat without loading anything else here. If `enabled` is missing or false, say in one line that translation is off in this instance (`translation.enabled` in the `## Writing register` block turns it on) and answer the request as ordinary chat. Nothing below applies.

Keys and defaults:

```yaml
translation:
  enabled: false
  pair: ""                    # e.g. "it -> en": source language -> target language
  new_context_marker: ""      # e.g. "Ciao,": a draft opening with it starts a fresh translation
  source_words_max: 1         # source-language words allowed per text, only when they add warmth
  labels: [Translation, More polished version]
communication:
  sign_off: ""                # appended to both versions only when set
```

## Rules

The writing register applies: rule zero, the seven prohibitions with the rule 3 exception, the lexical tells and the calques of `.claude/skills/writing-register/SKILL.md` (load it if it isn't in context), in the communication domain. The tone is the draft's own: the owner chose it when writing.

- Names, prices, plan names, ids, dates, URLs, emoji, smileys and placeholders exactly as in the source.
- Names the source lacks are never added; when a greeting or a closing needs one, flag it in the `Note:` line.
- A draft that opens with `new_context_marker` is a fresh translation: earlier drafts in the session don't shape it. The marker is part of the text and gets translated ("Ciao," becomes "Hi,").
- If something in the source looks wrong (a price, a date, a missing link, a sentence that reads two ways), one line after both versions, prefixed `Note:`. Never fix it silently.
- Idioms are rendered with an idiom of similar weight in the target language, never word for word.
- Up to `source_words_max` words of the source language may stay, only when they add warmth ("Fantastico to hear that"). Zero is fine.
- Calques from the source language are the defect to watch (`in order to`, `due to the fact that`, `could potentially`, `aforementioned`).

## Output

Two labeled blocks, the labels from `translation.labels`, a line of `+` under each label, and nothing before or after them except the optional `Note:` line. No preamble, no explanation of choices, no list of changes.

```
<labels[0]>
+++++++++++++++++++++++++
<version 1>

<labels[1]>
+++++++++++++++++++++++++
<version 2>
```

When `communication.sign_off` is set, it closes both versions, after a blank line, translated if it is in the source language. When it is empty, the versions end where the draft ends: most owners sign their own emails.

**Version 1**, the first label: keeps the source's form (paragraph order, lists, line breaks, sentence boundaries wherever the target language allows), lets go on register (informal where the source is), idioms rendered with idioms.

**Version 2**, the second label: the same voice, tone and facts, written as a native speaker would. Grammar corrected; sentences split, merged or reordered inside a paragraph when that makes them clearer; paragraph order kept. A source-language word from version 1 stays only if it still works.

## Variants

- **Input already in the target language**: the same two blocks, the first labeled `Revised` (the owner's text with grammar and calques fixed, form kept), the second with the second label.
- **Transcribed speech** (a dictation, a voice note transcript): filler words, false starts and repetitions removed first, then the two blocks. No translation when source and target coincide.
- **A request to translate a text the owner didn't write** (a partner's email, a document): translate it faithfully in one block labeled `Translation`; register rules don't apply to someone else's text, only fidelity does.

## What this skill is not

It doesn't write the email: the draft is the owner's. It doesn't add links, calls to action or personal lines the source lacks (a `Note:` may suggest one). It doesn't run the `humanizer` or `unslop` skills, whatever the instance has installed.
