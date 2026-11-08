---
tags: [maintenance, template, ci, dependencies, claude-code, runbook]
description: Routine maintenance of the template repository, with the checks the /maintenance skill runs, what each finding means, the standard remedy and the decisions deferred on purpose; relevant after an update of Claude Code, once a month, or before a release.
---

# Maintenance

The template is skills, agents, markdown and a few Python scripts, so there is no lockfile to refresh. What ages is around the code: Claude Code, which runs the hooks and the mod and parses the manifests; the GitHub Actions of the Pages workflow; `sqlite-vec`, fetched by uv at run time; the external tools the optional features call. This document is the runbook. The `/maintenance` skill of this repository runs the report at `.claude/skills/maintenance/check` and applies the remedies below on the owner's yes. Both live only here: `docs/` and `.claude/skills/maintenance/` are `export-ignore` in `.gitattributes` and outside the sync mirror, so an instance never sees them.

## When

- After an update of Claude Code: the hook events, the skill frontmatter keys, the `claude plugin` subcommands and the mod API (`$.clock`, `$.ui`, `$.store`, `claude-code/testing`) are the template's real dependency and can change under it.
- Once a month, for the Actions and the branches.
- Before a release, with the full report.

## The checks

| Check | A finding means | Remedy |
|---|---|---|
| Working tree | Uncommitted changes while the report runs | Commit or stash first; the archive test reads the last commit |
| Scripts start | A distributed script fails `--help` under the Python on PATH | The script uses something newer than the README's promise (Python 3, stdlib); fix the script or raise the promise in README → Requirements |
| Python suite | `python3 -m unittest discover -s tests -t .` fails | Read the failing test; a failure right after a Claude Code update usually sits in `tests/test_plugin_layout.py` or `tests/test_maestro_sync.py` |
| Plugin manifests | `claude plugin validate` reports errors or new warnings | Errors: fix the manifest. Warnings: compare with the deferred decisions below before acting |
| Mod tests | `claude plugin test plugins/agenda` fails | The mod API moved; read the failing test and `plugins/agenda/hooks/register.tsx`. `bun test` alone cannot run them: `claude-code/testing` comes from the runner |
| GitHub Actions | An action in `.github/workflows/*.yml` is behind its latest major | Bump the `@vN` pin; the next push to `main` touching `site/`, `CHANGELOG.md` or the workflow runs it. Dependabot (`.github/dependabot.yml`, monthly, grouped) opens the PR when nobody does it by hand |
| Pages workflow | The last run failed or carries a deprecation notice (Node runtime, retired action) | Same bump as above; check the annotations with `gh run view <id>` |
| Dependabot PRs | An open PR from Dependabot | `gh pr diff <n>`, then merge on yes |
| Merged branches | Local or remote branches already merged into `main` | `git branch -d <name>`; `git push origin --delete <name>`, only the ones listed |
| Tools (brew) | yap, uv, ollama, sqlite or ripgrep outdated on this machine | The owner's machine, not the repo: `brew upgrade <tool>` is theirs to run |
| sqlite-vec pin | Informational: the pin in `bin/mem-vec` and the latest on PyPI | Nothing, unless a release breaks `bin/mem embed`; then add an upper bound |
| Plugin cache | An installed `maestro@maestro` or `agenda@maestro` is behind `main` | `claude plugin update <name>@maestro`, then restart Claude Code. Stale cached versions are harmless |

## Deferred decisions

- `version` in the two `plugin.json`. `claude plugin validate` warns that it is missing. The plugins are versioned by commit (`docs/development-guidelines.md` → `## Mods`), and the instances see the git sha as the version. Adding a semver next to the `vYYYY.MM.DD.N` scheme is a separate decision; until it is taken, the warning is expected and the skill reports it as open.
- Continuous integration. The Python suite could run on every push with a ten-line workflow; `claude plugin test` would need Claude Code installed in the runner. Not set up as of 2026-11-08.

## Baseline

2026-11-08: `unittest` ran 853 tests, OK, 8 skipped, under the system Python 3.9.6 (pytest counts the same run as 845 passed plus 8 skipped); mod tests 65 pass; Actions at checkout v7, configure-pages v6, upload-pages-artifact v5, deploy-pages v5; Dependabot added; 11 merged branches deleted.
