---
name: maintenance
description: Routine maintenance of the Maestro template repository, run from the repository itself and never from an instance. Runs the read-only report `.claude/skills/maintenance/check` (Python suite, mod tests, plugin manifests, GitHub Actions pins, Pages run, Dependabot PRs, merged branches, brew tools, sqlite-vec pin, installed plugin cache), explains each finding in plain words and applies the standard remedy from `docs/maintenance.md` on the owner's yes. Use when the owner types /maintenance, says "manutenzione", "facciamo manutenzione", "è tutto aggiornato?", "maintenance", "is everything up to date", or after an update of Claude Code.
user-invocable: true
---

# Maintenance

The template repository has no lockfile. Its dependencies are Claude Code (hook events, skill frontmatter, `claude plugin` commands, the mod API), the GitHub Actions of `pages.yml`, `sqlite-vec` through uv, and the external tools (yap, ollama, sqlite3, rg). This skill checks all of them in one pass and keeps the remedies in `docs/maintenance.md`, so the procedure is never rebuilt from scratch.

## Where it runs

Only in the template repository: `plugins/maestro/` present at the root. In an instance or a satellite, say in one sentence that maintenance belongs to the template repository and stop.

## 1. Run the report

```bash
.claude/skills/maintenance/check              # full: the Python suite takes about four minutes
.claude/skills/maintenance/check --no-tests   # when the owner asks for a quick look
```

Default is the full report. "veloce", "quick", "solo un'occhiata" means `--no-tests`; say so in the report. Run it in one Bash call with a timeout of at least 600000 ms. Exit 1 means at least one ATTENTION line, exit 0 none.

## 2. Read the remedies

Read `docs/maintenance.md`: the table says what each check means, the standard remedy, and which decisions the owner has deferred on purpose (those are reported as open, never "fixed"). Check the auto-memory for a maintenance entry of the last month, so a decision taken then is not asked again.

## 3. Report to the owner

In chat, in the owner's language, grouped in three blocks: healthy, needs attention, skipped (with the reason). Plain words, no internal jargon: "the deploy workflow uses versions GitHub is retiring" rather than the raw line. Figures stay (test counts, versions, branch names). For each ATTENTION line, state the remedy from `docs/maintenance.md` and whether it is a repo change, a machine change (the owner's brew), or a decision.

## 4. Apply on yes

Each remedy waits for the owner's yes; one yes covers the remedies named in the same question. Rules:

- Repo changes follow `docs/development-guidelines.md`: explicit `git add` on the touched files, one commit per kind (`chore(ci): …`, `chore(repo): …`), English imperative message. Commit on a branch when on `main`, unless the owner says otherwise. Never push, merge or delete remote branches without an explicit request.
- Actions bump: edit the `@vN` pins in `.github/workflows/*.yml` to the latest major the report names; the workflow verifies itself at the next push to `main` that touches `site/`, `CHANGELOG.md` or the workflow.
- Dependabot PR: read its diff with `gh pr diff <n>` before proposing the merge; merge only on yes.
- Merged branches: `git branch -d` for local, `git push origin --delete` for remote, only the ones the report lists.
- Brew tools: never run `brew upgrade`; give the command to the owner.
- Plugin behind `main`: `claude plugin update <name>@maestro` runs on yes; stale cached versions need nothing.
- `version` in `plugin.json`: a deferred decision, see `docs/maintenance.md`; never add it inside this skill.

## 5. Close

After the remedies, rerun `check --no-tests` and show the summary line. When the test count changed, update the baseline line in `docs/maintenance.md` and in `docs/development-guidelines.md` → `## Gate`. Write one auto-memory with the date, what was found and what was done.
