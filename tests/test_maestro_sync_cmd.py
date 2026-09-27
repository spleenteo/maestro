"""tests/test_maestro_sync_cmd.py — black-box tests of the plugin command
`plugins/maestro/bin/maestro-sync`, run through `subprocess` against a
temporary instance and a temporary mirror (a git repo with a bare
`origin.git` standing in for GitHub), never a real instance, never the
network.

Fixtures every task of the V1 slice reuses: `make_instance`, `make_mirror`,
`make_plugin_root`, `recorder_claude`, `run_sync`. Every fixture path carries
a space (iCloud folders do), `HOME` sits inside the temp dir, and the
temporary git repos use a local `user.name`/`user.email` with
`commit.gpgsign false`, so no test touches the global git config.

This file keeps its name until V2 deletes `tests/test_maestro_sync.py` (the
extraction tests on the skill's bash blocks) and renames it.

Run: python3 -m unittest tests.test_maestro_sync_cmd -v
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = ROOT / "plugins" / "maestro"
SCRIPT = PLUGIN_ROOT / "bin" / "maestro-sync"
TEMPLATE_DB = ROOT / "memories.db.template"

OK = 0
E_USAGE = 2
E_NOT_INSTANCE = 3
E_MIRROR = 4
E_PLUGIN = 5

LISTEN_MEMBERS = (".claude/skills/listen", "bin/listen", "bin/listen-updates",
                  "bin/audiowatch.swift")
PLAN_FILE = "private/maestro-sync.plan.json"

OLD_VERSION = "v2026.01.01.1"
NEW_VERSION = "v2026.02.01.1"

# The instance's four scanned globs, one file each, at relative paths.
MARKED_PATHS = (
    "CLAUDE.md",
    ".claude/skills/logbook/SKILL.md",
    ".claude/agents/librarian.md",
    "howto/01-first-steps.md",
)

_GIT_BIN = str(Path(shutil.which("git") or "/usr/bin/git").parent)
SYSTEM_PATH = f"{_GIT_BIN}:/usr/bin:/bin"


# ---------------------------------------------------------------------------
# Git and file helpers
# ---------------------------------------------------------------------------

def init_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "sync-test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Sync Test"], cwd=path, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=path, check=True)


def commit(path: Path, files: list[str], message: str = "seed") -> str:
    subprocess.run(["git", "add", *files], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=path, check=True)
    return git_out(path, "rev-parse", "HEAD")


def git_out(path: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=path, capture_output=True, text=True,
                          check=True).stdout.strip()


def marked_md(version: str, description: str = "a marked file", body: str = "Body.\n",
              tools: str | None = None) -> str:
    front = ["---", "origin: maestro", f"maestro_version: {version}",
             f"description: {description}"]
    if tools is not None:
        front.append(f"tools: {tools}")
    front.append("---")
    return "\n".join(front) + "\n\n# Title\n\n" + body


def write(path: Path, text: str, mode: int | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if mode is not None:
        path.chmod(mode)
    return path


def changelog(*versions: str) -> str:
    parts = ["---", "tags: [changelog]", "description: test changelog", "---", "", "# Changelog", ""]
    for v in versions:
        parts += [f"## {v} — 2026-01-01", "", f"- entry for {v}", ""]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_instance(root: Path, version: str, mirror: Path | str | None = None,
                  worktree: Path | str | None = None, shape: str = "bold",
                  name: str = "inst ance") -> Path:
    """A Maestro instance: the four globs with marked files at `version`,
    `bin/mem` and `bin/mem_schema.py` copied from the repo, `memories.db`
    from the template, `private/preferences.md` carrying the two path keys
    in the `- **key**: value` shape (`shape="bold"`) or `key: value`
    (`shape="plain"`). A key whose value is None is left out."""
    inst = root / name
    for rel in MARKED_PATHS:
        write(inst / rel, marked_md(version, description=rel))
    (inst / "bin").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "bin" / "mem", inst / "bin" / "mem")
    shutil.copy2(ROOT / "bin" / "mem_schema.py", inst / "bin" / "mem_schema.py")
    (inst / "private").mkdir(exist_ok=True)
    shutil.copy2(TEMPLATE_DB, inst / "private" / "memories.db")
    write(inst / "private" / "preferences.md", preferences_text(mirror, worktree, shape))
    return inst


def preferences_text(mirror, worktree, shape: str = "bold") -> str:
    def line(key: str, value) -> str:
        if value is None:
            return ""
        if shape == "bold":
            return f"- **{key}**: {value}\n"
        return f"{key}: {value}\n"

    return (
        "---\nsetup_completed: true\ntags: [preferences]\ndescription: test preferences\n---\n\n"
        "## Identity\n\n- **Name**: Tester\n\n"
        "## Integrations\n\n"
        + line("maestro_mirror_path", mirror)
        + line("maestro_worktree_path", worktree)
        + "\n## Notes\n"
    )


def make_mirror(root: Path) -> SimpleNamespace:
    """A template repo on `main` with marked files, `bin/`, a `CHANGELOG.md`
    with two entries, plus a bare `origin.git` clone the command fetches
    from. Returns `work`, `origin`, `old` (first commit), `main` (tip of
    main), `ahead` (a commit on a `feature` branch)."""
    work = root / "mirror src"
    init_git_repo(work)
    for rel in MARKED_PATHS:
        write(work / rel, marked_md(OLD_VERSION, description=rel))
    (work / "bin").mkdir()
    shutil.copy2(ROOT / "bin" / "mem", work / "bin" / "mem")
    shutil.copy2(ROOT / "bin" / "mem_schema.py", work / "bin" / "mem_schema.py")
    write(work / "CHANGELOG.md", changelog(OLD_VERSION))
    old = commit(work, ["."], f"{OLD_VERSION}: seed")
    for rel in MARKED_PATHS:
        write(work / rel, marked_md(NEW_VERSION, description=rel, body="New body.\n"))
    write(work / "CHANGELOG.md", changelog(NEW_VERSION, OLD_VERSION))
    main = commit(work, ["."], f"{NEW_VERSION}: bump")
    subprocess.run(["git", "checkout", "-q", "-b", "feature"], cwd=work, check=True)
    write(work / "howto/02-feature.md", marked_md(NEW_VERSION, description="feature"))
    ahead = commit(work, ["."], "feature work")
    subprocess.run(["git", "checkout", "-q", "main"], cwd=work, check=True)
    origin = root / "origin.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(work), str(origin)], check=True)
    return SimpleNamespace(work=work, origin=origin, old=old, main=main, ahead=ahead)


def make_plugin_root(root: Path, repo_url: str, name: str = "plugin root") -> Path:
    plugin = root / name
    write(plugin / ".claude-plugin" / "plugin.json", json.dumps({"repository": repo_url}))
    return plugin


def recorder_claude(bindir: Path, version: str, install_path: Path | str) -> Path:
    """A `claude` on PATH answering `plugin list --json` with a project-scope
    row to ignore and the user-scope maestro row, and logging its argv."""
    bindir.mkdir(parents=True, exist_ok=True)
    rows = [
        {"id": "maestro@maestro", "scope": "project", "version": "0000000"},
        {"id": "maestro@maestro", "scope": "user", "version": version[:12],
         "installPath": str(install_path)},
    ]
    script = bindir / "claude"
    script.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$*\" >> \"{bindir / 'claude.log'}\"\n"
        "cat <<'EOF'\n" + json.dumps(rows) + "\nEOF\n"
    )
    script.chmod(0o755)
    return script


def unmarked_md(description: str = "an unmarked file", body: str = "Body.\n") -> str:
    return f"---\ndescription: {description}\n---\n\n# Title\n\n{body}"


def marked_script(version: str = OLD_VERSION, comment: str = "#") -> str:
    """A marked script: a Python one under `#`, a Swift one under `//`."""
    if comment == "#":
        return f"#!/usr/bin/env python3\n# origin: maestro\n# maestro_version: {version}\n"
    return f"{comment} origin: maestro\n{comment} maestro_version: {version}\n{comment}\n"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recorder_procs(bindir: Path, ps_command: str | None = None,
                   pgrep_pid: int | None = None) -> None:
    """A `ps` and a `pgrep` on PATH, each logging its argv: `ps` prints
    `ps_command` (exit 1 with nothing when None, the way a dead pid reads),
    `pgrep` prints `pgrep_pid` (exit 1 when None: no process matched)."""
    bindir.mkdir(parents=True, exist_ok=True)
    for name, value in (("ps", ps_command), ("pgrep", pgrep_pid)):
        script = bindir / name
        body = "#!/bin/sh\n" + f"printf '%s\\n' \"$*\" >> \"{bindir / (name + '.log')}\"\n"
        body += f"printf '%s\\n' '{value}'\nexit 0\n" if value is not None else "exit 1\n"
        script.write_text(body)
        script.chmod(0o755)


def seed_listen(inst: Path, unmarked: tuple[str, ...] = ()) -> None:
    """The four members of the retired listen unit, each marked unless
    named in `unmarked` (the owner's own copy of that member)."""
    write(inst / ".claude" / "skills" / "listen" / "SKILL.md",
          unmarked_md("mine") if ".claude/skills/listen" in unmarked
          else marked_md(OLD_VERSION, description="listen"))
    for name in ("listen", "listen-updates"):
        rel = f"bin/{name}"
        write(inst / rel, "#!/bin/sh\necho mine\n" if rel in unmarked else marked_script(), mode=0o755)
    write(inst / "bin" / "audiowatch.swift",
          "// mine\n" if "bin/audiowatch.swift" in unmarked else marked_script(comment="//"))


def write_listen_state(home: Path, pid: int) -> Path:
    state = home / ".local" / "state" / "listen"
    state.mkdir(parents=True, exist_ok=True)
    return write(state / "current.json", json.dumps({"supervisor_pid": pid}))


def push_main(mirror_src: SimpleNamespace, files: dict, message: str = "more upstream") -> str:
    """Commit `files` on the mirror source's main and push it to the bare origin."""
    for rel, text in files.items():
        if text is None:
            (mirror_src.work / rel).unlink()
        else:
            write(mirror_src.work / rel, text)
    sha = commit(mirror_src.work, ["."], message)
    subprocess.run(["git", "push", "-q", str(mirror_src.origin), "main"],
                   cwd=mirror_src.work, check=True)
    return sha


def run_sync(*args: str, env: dict | None = None, cwd: Path | str | None = None,
             script: Path = SCRIPT) -> subprocess.CompletedProcess:
    """Run maestro-sync with a minimal environment: PATH and HOME come from
    `env`, never from the test process. A value of None unsets a key."""
    base = {"PATH": SYSTEM_PATH, "LANG": os.environ.get("LANG", "en_US.UTF-8")}
    for key, value in (env or {}).items():
        if value is None:
            base.pop(key, None)
        else:
            base[key] = value
    return subprocess.run([sys.executable, str(script), *args], capture_output=True,
                          text=True, env=base, cwd=str(cwd) if cwd else None)


class SyncFixture(unittest.TestCase):
    """A mirror source, its bare origin, a plugin root whose manifest points
    at that origin, a recorder `claude` at the tip of main, and an instance
    at the old version pointing at an absent `mirror dir`."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "temp root"
        self.root.mkdir()
        self.home = self.root / "home dir"
        self.home.mkdir()
        self.mirror_src = make_mirror(self.root)
        self.plugin = make_plugin_root(self.root, str(self.mirror_src.origin))
        self.bindir = self.root / "stub bin"
        recorder_claude(self.bindir, self.mirror_src.main, self.plugin)
        self.mirror = self.root / "mirror dir"
        self.instance = make_instance(self.root, OLD_VERSION, mirror=self.mirror)
        self.env = {"PATH": f"{self.bindir}:{SYSTEM_PATH}", "HOME": str(self.home)}

    def plan(self, *args: str, instance: Path | None = None, plugin_root: Path | None = None,
             env: dict | None = None, cwd=None) -> subprocess.CompletedProcess:
        full = ["plan", "--instance", str(instance or self.instance)]
        if plugin_root is not False:
            full += ["--plugin-root", str(plugin_root or self.plugin)]
        return run_sync(*full, *args, env={**self.env, **(env or {})}, cwd=cwd or self.root)

    def plan_json(self, *args, **kw) -> dict:
        r = self.plan("--json", *args, **kw)
        self.assertEqual(r.returncode, OK, r.stderr)
        return json.loads(r.stdout)

    def items(self, kind: str | None = None, **kw) -> list:
        plan = self.plan_json(**kw)
        return [it for it in plan["items"] if kind is None or it["kind"] == kind]

    def push_main(self, files: dict, message: str = "more upstream") -> str:
        """Move upstream main forward and re-record the plugin at the new tip,
        the way a plugin updated after the release reads."""
        sha = push_main(self.mirror_src, files, message)
        recorder_claude(self.bindir, sha, self.plugin)
        return sha

    def set_prefs(self, mirror=None, worktree=None, shape="bold") -> None:
        write(self.instance / "private" / "preferences.md",
              preferences_text(mirror, worktree, shape))

    def clone_worktree(self, name: str = "work tree") -> Path:
        wt = self.root / name
        subprocess.run(["git", "clone", "-q", str(self.mirror_src.origin), str(wt)], check=True)
        subprocess.run(["git", "config", "user.email", "sync-test@example.com"], cwd=wt, check=True)
        subprocess.run(["git", "config", "user.name", "Sync Test"], cwd=wt, check=True)
        subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=wt, check=True)
        return wt


# ---------------------------------------------------------------------------
# The command itself
# ---------------------------------------------------------------------------

class TestCommandShape(SyncFixture):
    def test_script_is_executable_with_a_python_shebang(self):
        self.assertTrue(os.access(SCRIPT, os.X_OK))
        self.assertEqual(SCRIPT.read_text().splitlines()[0], "#!/usr/bin/env python3")

    def test_help_lists_the_verbs_and_the_named_exit_codes(self):
        r = run_sync("--help", env=self.env)
        self.assertEqual(r.returncode, OK)
        for verb in ("plan", "apply", "note", "rollback", "backups"):
            self.assertIn(verb, r.stdout)
        for name, code in (("E_USAGE", 2), ("E_NOT_INSTANCE", 3), ("E_MIRROR", 4),
                           ("E_PLUGIN", 5), ("E_STALE", 6), ("E_ITEM", 7),
                           ("E_PARTIAL", 8), ("E_LOCKED", 9), ("POSTPONED", 10)):
            self.assertRegex(r.stdout, rf"{code}\s+{name}")

    def test_no_verb_is_a_usage_error(self):
        r = run_sync(env=self.env)
        self.assertEqual(r.returncode, E_USAGE)
        self.assertIn("plan", r.stderr)

    def test_later_verbs_are_registered_but_not_implemented_yet(self):
        for verb in ("apply", "note", "rollback", "backups"):
            with self.subTest(verb=verb):
                r = run_sync(verb, env=self.env, cwd=self.instance)
                self.assertEqual(r.returncode, E_USAGE)
                self.assertIn("not implemented yet", r.stderr)


# ---------------------------------------------------------------------------
# Phase 0 — the instance root
# ---------------------------------------------------------------------------

class TestInstanceRoot(SyncFixture):
    def test_the_template_repo_is_refused(self):
        (self.instance / "plugins" / "maestro").mkdir(parents=True)
        r = self.plan()
        self.assertEqual(r.returncode, E_NOT_INSTANCE)
        self.assertIn("template repository", r.stderr)

    def test_a_folder_without_bin_mem_is_refused(self):
        (self.instance / "bin" / "mem").unlink()
        r = self.plan()
        self.assertEqual(r.returncode, E_NOT_INSTANCE)
        self.assertIn("not the root of a Maestro instance", r.stderr)

    def test_the_instance_defaults_to_the_current_directory(self):
        r = run_sync("plan", "--plugin-root", str(self.plugin), "--json", env=self.env,
                     cwd=self.instance)
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertEqual(json.loads(r.stdout)["instance"], str(self.instance.resolve()))

    def test_a_plain_folder_as_current_directory_is_refused(self):
        r = run_sync("plan", "--plugin-root", str(self.plugin), env=self.env, cwd=self.root)
        self.assertEqual(r.returncode, E_NOT_INSTANCE)

    def test_the_instance_path_is_its_real_path(self):
        link = self.root / "link dir"
        link.symlink_to(self.instance)
        plan = self.plan_json(instance=link)
        self.assertEqual(plan["instance"], str(self.instance.resolve()))


# ---------------------------------------------------------------------------
# Phase 1 — the two paths from preferences
# ---------------------------------------------------------------------------

class TestPreferenceKeys(SyncFixture):
    def test_bold_list_shape_is_read(self):
        plan = self.plan_json()
        self.assertEqual(plan["mirror"], str(self.mirror))
        self.assertTrue((self.mirror / ".git").is_dir())

    def test_plain_key_shape_is_read(self):
        other = self.root / "other mirror"
        self.set_prefs(mirror=other, shape="plain")
        plan = self.plan_json()
        self.assertEqual(plan["mirror"], str(other))
        self.assertTrue((other / ".git").is_dir())

    def test_tilde_expands_to_the_temp_home(self):
        self.set_prefs(mirror="~/tilde mirror")
        plan = self.plan_json()
        self.assertEqual(plan["mirror"], str(self.home / "tilde mirror"))
        self.assertTrue((self.home / "tilde mirror" / ".git").is_dir())

    def test_default_mirror_is_dot_maestro_under_home(self):
        self.set_prefs(mirror=None)
        plan = self.plan_json()
        self.assertEqual(plan["mirror"], str(self.home / ".maestro"))
        self.assertTrue((self.home / ".maestro" / ".git").is_dir())

    def test_first_match_wins(self):
        first = self.root / "first mirror"
        text = preferences_text(first, None) + f"\nmaestro_mirror_path: {self.root / 'second'}\n"
        write(self.instance / "private" / "preferences.md", text)
        plan = self.plan_json()
        self.assertEqual(plan["mirror"], str(first))

    def test_a_backticked_value_is_read_bare(self):
        write(self.instance / "private" / "preferences.md",
              preferences_text(f"`{self.mirror}`", None))
        plan = self.plan_json()
        self.assertEqual(plan["mirror"], str(self.mirror))


# ---------------------------------------------------------------------------
# Phase 2 — the working tree, reported as data
# ---------------------------------------------------------------------------

class TestWorktreeStatus(SyncFixture):
    def test_undeclared_worktree_is_absent(self):
        plan = self.plan_json()
        self.assertEqual(plan["worktree"]["state"], "absent")
        self.assertIsNone(plan["worktree"]["path"])

    def test_declared_but_missing_worktree_is_absent(self):
        missing = self.root / "no such tree"
        self.set_prefs(mirror=self.mirror, worktree=missing)
        plan = self.plan_json()
        self.assertEqual(plan["worktree"], {"path": str(missing), "state": "absent",
                                            "files": [], "commits": []})

    def test_clean_worktree(self):
        wt = self.clone_worktree()
        self.set_prefs(mirror=self.mirror, worktree=wt)
        plan = self.plan_json()
        self.assertEqual(plan["worktree"]["state"], "clean")

    def test_uncommitted_edits_are_listed(self):
        wt = self.clone_worktree()
        write(wt / "CLAUDE.md", "edited\n")
        write(wt / "new file.md", "untracked\n")
        self.set_prefs(mirror=self.mirror, worktree=wt)
        plan = self.plan_json()
        self.assertEqual(plan["worktree"]["state"], "uncommitted")
        # Porcelain lines verbatim: git quotes a path with a space.
        self.assertEqual(sorted(plan["worktree"]["files"]), [" M CLAUDE.md", '?? "new file.md"'])

    def test_unpushed_commits_are_listed(self):
        wt = self.clone_worktree()
        write(wt / "CLAUDE.md", "edited\n")
        commit(wt, ["CLAUDE.md"], "local work")
        self.set_prefs(mirror=self.mirror, worktree=wt)
        plan = self.plan_json()
        self.assertEqual(plan["worktree"]["state"], "unpushed")
        self.assertEqual(len(plan["worktree"]["commits"]), 1)
        self.assertIn("local work", plan["worktree"]["commits"][0])

    def test_uncommitted_wins_over_unpushed(self):
        wt = self.clone_worktree()
        write(wt / "CLAUDE.md", "edited\n")
        commit(wt, ["CLAUDE.md"], "local work")
        write(wt / "CLAUDE.md", "edited again\n")
        self.set_prefs(mirror=self.mirror, worktree=wt)
        plan = self.plan_json()
        self.assertEqual(plan["worktree"]["state"], "uncommitted")
        self.assertEqual(len(plan["worktree"]["commits"]), 1)

    def test_the_worktree_is_never_touched(self):
        wt = self.clone_worktree()
        write(wt / "CLAUDE.md", "edited\n")
        self.set_prefs(mirror=self.mirror, worktree=wt)
        self.plan_json()
        self.assertEqual((wt / "CLAUDE.md").read_text(), "edited\n")

    def test_summary_names_the_worktree_state(self):
        wt = self.clone_worktree()
        write(wt / "CLAUDE.md", "edited\n")
        self.set_prefs(mirror=self.mirror, worktree=wt)
        r = self.plan()
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("WORKTREE uncommitted", r.stdout)
        self.assertIn(" M CLAUDE.md", r.stdout)


# ---------------------------------------------------------------------------
# Phase 3 — the mirror
# ---------------------------------------------------------------------------

class TestMirrorRefresh(SyncFixture):
    def test_a_missing_mirror_is_cloned_and_the_head_printed(self):
        r = self.plan()
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn(f"MIRROR_HEAD {self.mirror_src.main}", r.stdout)
        self.assertEqual(git_out(self.mirror, "rev-parse", "HEAD"), self.mirror_src.main)

    def test_a_stale_mirror_moves_forward_to_the_new_main(self):
        subprocess.run(["git", "clone", "-q", str(self.mirror_src.origin), str(self.mirror)], check=True)
        subprocess.run(["git", "reset", "-q", "--hard", self.mirror_src.old], cwd=self.mirror, check=True)
        plan = self.plan_json()
        self.assertEqual(plan["mirror_head"], self.mirror_src.main)
        self.assertEqual(git_out(self.mirror, "rev-parse", "HEAD"), self.mirror_src.main)

    def test_a_detached_mirror_is_reset_to_origin_main(self):
        subprocess.run(["git", "clone", "-q", str(self.mirror_src.origin), str(self.mirror)], check=True)
        subprocess.run(["git", "checkout", "-q", "--detach", self.mirror_src.old], cwd=self.mirror, check=True)
        plan = self.plan_json()
        self.assertEqual(plan["mirror_head"], self.mirror_src.main)
        self.assertEqual(git_out(self.mirror, "rev-parse", "HEAD"), self.mirror_src.main)
        self.assertEqual((self.mirror / "CLAUDE.md").read_text(),
                         marked_md(NEW_VERSION, description="CLAUDE.md", body="New body.\n"))

    def test_the_fetch_takes_every_branch(self):
        self.plan_json()
        self.assertEqual(git_out(self.mirror, "rev-parse", "origin/feature"), self.mirror_src.ahead)

    def test_a_mirror_with_local_edits_is_refused(self):
        subprocess.run(["git", "clone", "-q", str(self.mirror_src.origin), str(self.mirror)], check=True)
        write(self.mirror / "CLAUDE.md", "hand edit\n")
        r = self.plan()
        self.assertEqual(r.returncode, E_MIRROR)
        self.assertIn("local edits", r.stderr)
        self.assertEqual((self.mirror / "CLAUDE.md").read_text(), "hand edit\n")

    def test_a_mirror_equal_to_the_instance_is_refused(self):
        self.set_prefs(mirror=self.instance)
        r = self.plan()
        self.assertEqual(r.returncode, E_MIRROR)
        self.assertIn("refusing to reset", r.stderr)

    def test_a_mirror_equal_to_the_worktree_is_refused(self):
        wt = self.clone_worktree()
        self.set_prefs(mirror=wt, worktree=wt)
        r = self.plan()
        self.assertEqual(r.returncode, E_MIRROR)
        self.assertIn("refusing to reset", r.stderr)

    def test_a_bad_mirror_path_is_an_error_with_a_message(self):
        bad = write(self.root / "a file", "not a folder\n")
        self.set_prefs(mirror=bad)
        r = self.plan()
        self.assertEqual(r.returncode, E_MIRROR)
        self.assertTrue(r.stderr.strip())
        self.assertNotIn("MIRROR_HEAD", r.stdout)

    def test_a_dead_repository_url_is_an_error_with_a_message(self):
        plugin = make_plugin_root(self.root, str(self.root / "no such origin.git"), name="dead plugin")
        recorder_claude(self.bindir, self.mirror_src.main, plugin)
        r = self.plan(plugin_root=plugin)
        self.assertEqual(r.returncode, E_MIRROR)
        self.assertIn("clone", r.stderr)


# ---------------------------------------------------------------------------
# Phase 3 — the plugin check
# ---------------------------------------------------------------------------

class TestPluginCheck(SyncFixture):
    def test_plugin_at_main_passes(self):
        r = self.plan()
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn(f"PLUGIN {self.mirror_src.main[:12]}", r.stdout)

    def test_claude_is_asked_for_the_plugin_list_as_json(self):
        self.plan_json()
        self.assertEqual((self.bindir / "claude.log").read_text().splitlines(), ["plugin list --json"])

    def test_plugin_ahead_on_a_branch_passes(self):
        recorder_claude(self.bindir, self.mirror_src.ahead, self.plugin)
        r = self.plan()
        self.assertEqual(r.returncode, OK, r.stderr)

    def test_plugin_behind_main_is_refused(self):
        recorder_claude(self.bindir, self.mirror_src.old, self.plugin)
        r = self.plan()
        self.assertEqual(r.returncode, E_PLUGIN)
        self.assertIn("behind", r.stderr)

    def test_a_commit_unknown_to_the_mirror_is_refused(self):
        recorder_claude(self.bindir, "deadbeefdeadbeefdeadbeef", self.plugin)
        r = self.plan()
        self.assertEqual(r.returncode, E_PLUGIN)
        self.assertIn("behind", r.stderr)

    def test_loaded_plugin_other_than_installed_is_refused(self):
        other = self.root / "newer install"
        other.mkdir()
        recorder_claude(self.bindir, self.mirror_src.main, other)
        r = self.plan()
        self.assertEqual(r.returncode, E_PLUGIN)
        self.assertIn("Restart Claude Code", r.stderr)

    def test_a_non_sha_version_means_not_installed_from_the_marketplace(self):
        recorder_claude(self.bindir, "1.2.3", self.plugin)
        r = self.plan()
        self.assertEqual(r.returncode, E_PLUGIN)
        self.assertIn("user scope", r.stderr)

    def test_claude_absent_from_path_is_refused(self):
        r = self.plan(env={"PATH": SYSTEM_PATH})
        self.assertEqual(r.returncode, E_PLUGIN)
        self.assertIn("claude", r.stderr)

    def test_a_missing_plugin_manifest_is_refused(self):
        bare = self.root / "bare plugin"
        bare.mkdir()
        recorder_claude(self.bindir, self.mirror_src.main, bare)
        r = self.plan(plugin_root=bare)
        self.assertEqual(r.returncode, E_PLUGIN)
        self.assertIn("plugin.json", r.stderr)

    def test_without_plugin_root_the_path_check_is_skipped_with_a_warning(self):
        copy = self.root / "plugin copy"
        for name in ("maestro-sync", "maestro_registry.py", "maestro_versions.py",
                     "maestro-register-keys"):
            shutil.copy2(PLUGIN_ROOT / "bin" / name, write(copy / "bin" / name, ""))
        write(copy / ".claude-plugin" / "plugin.json",
              json.dumps({"repository": str(self.mirror_src.origin)}))
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        recorder_claude(self.bindir, self.mirror_src.main, elsewhere)
        r = run_sync("plan", "--instance", str(self.instance), "--json", env=self.env,
                     cwd=self.root, script=copy / "bin" / "maestro-sync")
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("--plugin-root", r.stderr)
        plan = json.loads(r.stdout)
        self.assertEqual(plan["mirror_head"], self.mirror_src.main)
        self.assertTrue(any("--plugin-root" in w for w in plan["warnings"]))


# ---------------------------------------------------------------------------
# Phase 4 — the instance scan and the version floor
# ---------------------------------------------------------------------------

class TestInstanceScan(SyncFixture):
    def test_every_marked_file_of_the_four_globs_is_an_update(self):
        items = self.items("update")
        self.assertEqual(sorted(it["path"] for it in items), sorted(MARKED_PATHS))
        for it in items:
            self.assertEqual((it["from"], it["to"]), (OLD_VERSION, NEW_VERSION))
            self.assertEqual(it["checksum"], sha256_of(self.instance / it["path"]))
            self.assertIn("+New body.", it["diff"])

    def test_item_ids_are_numbered_per_kind(self):
        items = self.items("update")
        self.assertEqual([it["id"] for it in items], [f"u{i}" for i in range(1, len(items) + 1)])

    def test_a_marked_file_under_a_symlinked_app_is_never_listed(self):
        other = make_instance(self.root, OLD_VERSION, name="other inst")
        (self.instance / "apps").mkdir()
        (self.instance / "apps" / "x").symlink_to(other)
        paths = [it["path"] for it in self.items()]
        self.assertFalse(any(p.startswith("apps/") for p in paths), paths)

    def test_a_symlinked_skill_folder_is_not_followed(self):
        elsewhere = self.root / "elsewhere skill"
        write(elsewhere / "SKILL.md", marked_md(OLD_VERSION, description="linked"))
        (self.instance / ".claude" / "skills" / "linked").symlink_to(elsewhere)
        paths = [it["path"] for it in self.items()]
        self.assertNotIn(".claude/skills/linked/SKILL.md", paths)

    def test_a_marked_file_outside_the_globs_is_ignored(self):
        write(self.instance / "howto" / "deep" / "nested.md", marked_md(OLD_VERSION))
        write(self.instance / "notes.md", marked_md(OLD_VERSION))
        paths = [it["path"] for it in self.items()]
        self.assertNotIn("howto/deep/nested.md", paths)
        self.assertNotIn("notes.md", paths)

    def test_an_unmarked_instance_file_is_ignored(self):
        write(self.instance / "howto" / "01-first-steps.md", unmarked_md("the owner rewrote it"))
        paths = [it["path"] for it in self.items()]
        self.assertNotIn("howto/01-first-steps.md", paths)

    def test_the_floor_is_the_lowest_version_across_scanned_files(self):
        write(self.instance / "howto" / "01-first-steps.md",
              marked_md("v2025.12.01.1", description="howto/01-first-steps.md"))
        plan = self.plan_json()
        self.assertEqual(plan["versions"], {"floor": "v2025.12.01.1", "upstream": NEW_VERSION})

    def test_a_marked_file_without_version_reads_as_the_baseline(self):
        write(self.instance / "howto" / "01-first-steps.md",
              "---\norigin: maestro\ndescription: old\n---\n\nBody.\n")
        plan = self.plan_json()
        self.assertEqual(plan["versions"]["floor"], OLD_VERSION)
        item = next(it for it in plan["items"] if it["path"] == "howto/01-first-steps.md")
        self.assertEqual(item["from"], "v2026.04.29.1")

    def test_a_retired_path_never_lowers_the_floor(self):
        write(self.instance / ".claude" / "skills" / "setup" / "SKILL.md",
              marked_md("v2025.01.01.1", description="setup"))
        plan = self.plan_json()
        self.assertEqual(plan["versions"]["floor"], OLD_VERSION)
        self.assertNotIn(".claude/skills/setup/SKILL.md",
                         [it["path"] for it in plan["items"] if it["kind"] != "retired"])

    def test_an_identical_file_is_no_item(self):
        write(self.instance / "CLAUDE.md",
              marked_md(NEW_VERSION, description="CLAUDE.md", body="New body.\n"))
        self.assertNotIn("CLAUDE.md", [it["path"] for it in self.items()])


# ---------------------------------------------------------------------------
# Phase 4b — the reverse scan
# ---------------------------------------------------------------------------

class TestReverseScan(SyncFixture):
    def test_a_marked_upstream_file_absent_from_the_instance_is_new(self):
        self.push_main({"howto/08-markdown-discipline.md": marked_md(
            NEW_VERSION, description="markdown discipline", body="Rules.\n")})
        items = self.items("new")
        self.assertEqual([it["path"] for it in items], ["howto/08-markdown-discipline.md"])
        item = items[0]
        self.assertEqual((item["id"], item["from"], item["to"]), ("n1", None, NEW_VERSION))
        self.assertIsNone(item["checksum"])
        self.assertIn("Rules.", item["preview"])

    def test_excluded_folders_never_yield_new_items(self):
        self.push_main({
            "docs/plan.md": marked_md(NEW_VERSION),
            "plugins/maestro/skills/net/SKILL.md": marked_md(NEW_VERSION),
            ".claude-plugin/notes.md": marked_md(NEW_VERSION),
            "user-skills/foo/SKILL.md": marked_md(NEW_VERSION),
            ".claude/skills/maestro-sync/SKILL.md": marked_md(NEW_VERSION),
            "howto/07-new.md": marked_md(NEW_VERSION),
        })
        self.assertEqual([it["path"] for it in self.items("new")], ["howto/07-new.md"])

    def test_the_three_marker_edge_cases_are_not_new_files(self):
        self.push_main({
            "howto/unmarked.md": unmarked_md("valid frontmatter, no marker"),
            "howto/no-frontmatter.md": "# Heading\n\nThe body says:\n\norigin: maestro\n\nas prose.\n",
            "howto/rule-then-mention.md": unmarked_md("a trap") + "\n---\n\norigin: maestro\n",
        })
        self.assertEqual(self.items("new"), [])

    def test_a_new_file_present_in_the_instance_is_not_new(self):
        self.push_main({"howto/07-new.md": marked_md(NEW_VERSION, description="howto/07-new.md")})
        write(self.instance / "howto" / "07-new.md", marked_md(OLD_VERSION, description="howto/07-new.md"))
        self.assertEqual(self.items("new"), [])


# ---------------------------------------------------------------------------
# Phase 5 — the changelog slice
# ---------------------------------------------------------------------------

class TestChangelogSlice(SyncFixture):
    def test_the_slice_runs_from_the_floor_excluded_to_upstream_included(self):
        plan = self.plan_json()
        self.assertIn(f"## {NEW_VERSION}", plan["changelog"])
        self.assertNotIn(f"## {OLD_VERSION}", plan["changelog"])

    def test_an_instance_at_upstream_has_an_empty_slice(self):
        for rel in MARKED_PATHS:
            write(self.instance / rel, marked_md(NEW_VERSION, description=rel, body="New body.\n"))
        plan = self.plan_json()
        self.assertEqual(plan["changelog"], "")
        self.assertEqual(plan["versions"]["floor"], NEW_VERSION)

    def test_the_summary_prints_the_slice_and_one_line_per_item(self):
        r = self.plan()
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn(f"## {NEW_VERSION}", r.stdout)
        self.assertIn(f"VERSIONS {OLD_VERSION} -> {NEW_VERSION}", r.stdout)
        for rel in MARKED_PATHS:
            self.assertRegex(r.stdout, rf"(?m)^u\d+ +update +{re.escape(rel)} ")
        self.assertIn("WORKTREE absent", r.stdout)

    def test_a_mirror_without_changelog_is_a_warning_not_an_error(self):
        self.push_main({"CHANGELOG.md": None}, "drop the changelog")
        plan = self.plan_json()
        self.assertEqual(plan["changelog"], "")
        self.assertIsNone(plan["versions"]["upstream"])
        self.assertTrue(any("CHANGELOG" in w for w in plan["warnings"]))


# ---------------------------------------------------------------------------
# Phase 5b — bin drift
# ---------------------------------------------------------------------------

class TestBinDrift(SyncFixture):
    def test_an_aligned_bin_is_no_item(self):
        self.assertEqual(self.items("bin"), [])

    def test_a_differing_and_a_missing_script_are_one_item(self):
        write(self.instance / "bin" / "mem", "#!/bin/sh\necho old\n", mode=0o755)
        (self.instance / "bin" / "mem_schema.py").unlink()
        items = self.items("bin")
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual((item["id"], item["path"], item["checksum"]), ("b1", "bin", None))
        files = {f["path"]: f for f in item["files"]}
        self.assertEqual(files["bin/mem"]["state"], "differs")
        self.assertEqual(files["bin/mem"]["checksum"], sha256_of(self.instance / "bin" / "mem"))
        self.assertEqual(files["bin/mem_schema.py"]["state"], "missing")
        self.assertIsNone(files["bin/mem_schema.py"]["checksum"])

    def test_a_pycache_folder_in_the_mirror_is_never_listed(self):
        subprocess.run(["git", "clone", "-q", str(self.mirror_src.origin), str(self.mirror)], check=True)
        write(self.mirror / "bin" / "__pycache__" / "mem.cpython-39.pyc", "not tracked")
        write(self.instance / "bin" / "mem", "#!/bin/sh\necho old\n", mode=0o755)
        files = [f["path"] for f in self.items("bin")[0]["files"]]
        self.assertEqual(files, ["bin/mem"])

    def test_a_script_upstream_deleted_is_not_drift(self):
        write(self.instance / "bin" / "mine", "#!/bin/sh\n", mode=0o755)
        self.assertEqual(self.items("bin"), [])


# ---------------------------------------------------------------------------
# Phase 6 — diffs, the tools: exemption, locally_modified
# ---------------------------------------------------------------------------

class TestDiffs(SyncFixture):
    REL = ".claude/agents/librarian.md"

    def test_only_tools_differing_means_no_item(self):
        self.push_main({self.REL: marked_md(
            NEW_VERSION, description=self.REL, body="New body.\n", tools="Read, Grep")})
        write(self.instance / self.REL, marked_md(
            NEW_VERSION, description=self.REL, body="New body.\n", tools="Read, Grep, mcp__acme__*"))
        self.assertNotIn(self.REL, [it["path"] for it in self.items()])

    def test_the_diff_keeps_the_instance_tools_line(self):
        self.push_main({self.REL: marked_md(
            NEW_VERSION, description=self.REL, body="New body.\n", tools="Read, Grep")})
        write(self.instance / self.REL, marked_md(OLD_VERSION, description=self.REL, tools="Read, mcp__acme__*"))
        item = next(it for it in self.items("update") if it["path"] == self.REL)
        self.assertNotRegex(item["diff"], r"(?m)^[-+]tools:")
        self.assertIn(" tools: Read, mcp__acme__*", item["diff"])
        self.assertIn("+New body.", item["diff"])

    def test_a_tools_line_added_upstream_reaches_the_instance(self):
        self.push_main({self.REL: marked_md(
            NEW_VERSION, description=self.REL, body="New body.\n", tools="Read")})
        item = next(it for it in self.items("update") if it["path"] == self.REL)
        self.assertIn("+tools: Read", item["diff"])

    def test_a_file_equal_to_an_older_mirror_commit_is_not_locally_modified(self):
        for it in self.items("update"):
            self.assertFalse(it["locally_modified"], it["path"])

    def test_an_edited_body_is_locally_modified(self):
        write(self.instance / "CLAUDE.md", marked_md(
            OLD_VERSION, description="CLAUDE.md", body="Body, with my own rule.\n"))
        item = next(it for it in self.items("update") if it["path"] == "CLAUDE.md")
        self.assertTrue(item["locally_modified"])

    def test_a_tools_extension_alone_is_not_a_local_modification(self):
        # Upstream shipped the file with `tools: Read` at the old version, then
        # changed its body; the instance extended `tools:` and nothing else.
        self.push_main({self.REL: marked_md(OLD_VERSION, description=self.REL, tools="Read")},
                       "tools at the old version")
        self.push_main({self.REL: marked_md(
            NEW_VERSION, description=self.REL, body="New body.\n", tools="Read")})
        write(self.instance / self.REL, marked_md(OLD_VERSION, description=self.REL, tools="Read, mcp__acme__*"))
        item = next(it for it in self.items("update") if it["path"] == self.REL)
        self.assertFalse(item["locally_modified"])

    def test_a_manifest_naming_an_unknown_head_does_not_break_the_search(self):
        write(self.instance / "private" / "backups" / "20260101-000000-sync" / "manifest.json",
              json.dumps({"mirror_head": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"}))
        for it in self.items("update"):
            self.assertFalse(it["locally_modified"], it["path"])

    def test_the_last_manifest_head_is_tried_first(self):
        write(self.instance / "private" / "backups" / "20260101-000000-sync" / "manifest.json",
              json.dumps({"mirror_head": self.mirror_src.old}))
        for it in self.items("update"):
            self.assertFalse(it["locally_modified"], it["path"])


# ---------------------------------------------------------------------------
# Phase 6b — retired paths and the listen unit
# ---------------------------------------------------------------------------

class TestRetired(SyncFixture):
    def setUp(self):
        super().setUp()
        recorder_procs(self.bindir)

    def retired(self, path: str) -> dict | None:
        return next((it for it in self.items("retired") if it["path"] == path), None)

    def test_a_marked_retired_howto_is_listed_with_its_checksum(self):
        rel = "howto/09-memoria-semantica.md"
        write(self.instance / rel, marked_md(OLD_VERSION, description="old howto"))
        item = self.retired(rel)
        self.assertIsNotNone(item)
        self.assertEqual((item["id"], item["state"]), ("r1", "listed"))
        self.assertEqual(item["members"], [{"path": rel, "marked": True,
                                           "checksum": sha256_of(self.instance / rel)}])
        self.assertEqual(item["files"], [rel])

    def test_a_marked_retired_skill_is_listed_with_its_files(self):
        write(self.instance / ".claude" / "skills" / "setup" / "SKILL.md", marked_md(OLD_VERSION))
        write(self.instance / ".claude" / "skills" / "setup" / "finalize.sh", "#!/bin/sh\n")
        item = self.retired(".claude/skills/setup")
        self.assertEqual(item["state"], "listed")
        self.assertEqual(sorted(item["files"]),
                         [".claude/skills/setup/SKILL.md", ".claude/skills/setup/finalize.sh"])

    def test_an_unmarked_skill_sharing_a_retired_name_is_not_listed(self):
        write(self.instance / ".claude" / "skills" / "setup" / "SKILL.md", unmarked_md("mine"))
        self.assertIsNone(self.retired(".claude/skills/setup"))

    def test_nothing_retired_means_no_retired_item(self):
        self.assertEqual(self.items("retired"), [])

    def test_the_listen_unit_is_listed_when_one_member_is_marked(self):
        seed_listen(self.instance, unmarked=("bin/listen",))
        item = self.retired("listen")
        self.assertEqual(item["state"], "listed")
        members = {m["path"]: m for m in item["members"]}
        self.assertEqual(sorted(members), sorted(LISTEN_MEMBERS))
        self.assertFalse(members["bin/listen"]["marked"])
        self.assertTrue(members["bin/audiowatch.swift"]["marked"])
        self.assertEqual(members[".claude/skills/listen"]["checksum"],
                         sha256_of(self.instance / ".claude/skills/listen/SKILL.md"))
        self.assertIn(".claude/skills/listen/SKILL.md", item["files"])

    def test_an_absent_member_is_not_listed(self):
        seed_listen(self.instance)
        (self.instance / "bin" / "audiowatch.swift").unlink()
        self.assertNotIn("bin/audiowatch.swift", [m["path"] for m in self.retired("listen")["members"]])

    def test_a_marker_in_a_script_body_is_not_a_mark(self):
        write(self.instance / "bin" / "listen", "#!/bin/sh\necho a\necho b\n# origin: maestro\n")
        self.assertIsNone(self.retired("listen"))

    def test_no_marked_member_lists_nothing(self):
        seed_listen(self.instance, unmarked=LISTEN_MEMBERS)
        self.assertIsNone(self.retired("listen"))

    def test_an_unmarked_skill_keeps_the_unit(self):
        seed_listen(self.instance, unmarked=(".claude/skills/listen",))
        item = self.retired("listen")
        self.assertEqual(item["state"], "kept")

    def test_a_running_capture_postpones_the_unit(self):
        seed_listen(self.instance)
        write_listen_state(self.home, os.getpid())
        recorder_procs(self.bindir, ps_command="/usr/bin/python3 /x/maestro-listen _supervise 42")
        item = self.retired("listen")
        self.assertEqual(item["state"], "postponed")
        self.assertIn(f"capture supervisor pid {os.getpid()}", item["reason"])
        self.assertEqual((self.bindir / "ps.log").read_text().splitlines(),
                         [f"-o command= -p {os.getpid()}"])

    def test_an_old_updates_monitor_postpones_the_unit(self):
        seed_listen(self.instance)
        recorder_procs(self.bindir, pgrep_pid=4242)
        item = self.retired("listen")
        self.assertEqual(item["state"], "postponed")
        self.assertIn("old listen-updates monitor pid 4242", item["reason"])
        self.assertEqual((self.bindir / "pgrep.log").read_text().splitlines(),
                         [f"-o -u {os.getuid()} -f /bin/listen-update[s]( |$)"])

    def test_a_reused_pid_with_another_command_line_is_not_a_capture(self):
        seed_listen(self.instance)
        write_listen_state(self.home, os.getpid())
        recorder_procs(self.bindir, ps_command="/usr/bin/tail -f /dev/null")
        self.assertEqual(self.retired("listen")["state"], "listed")

    def test_a_dead_supervisor_pid_is_not_a_capture(self):
        seed_listen(self.instance)
        write_listen_state(self.home, 2 ** 22 - 1)
        recorder_procs(self.bindir, ps_command="/x/maestro-listen _supervise")
        self.assertEqual(self.retired("listen")["state"], "listed")
        self.assertFalse((self.bindir / "ps.log").exists())

    def test_an_unrelated_listen_folder_at_the_root_is_untouched(self):
        seed_listen(self.instance)
        write(self.instance / "listen" / "keep.md", "mine\n")
        item = self.retired("listen")
        self.assertNotIn("listen/keep.md", item["files"])
        self.assertEqual((self.instance / "listen" / "keep.md").read_text(), "mine\n")

    def test_plan_removes_nothing(self):
        seed_listen(self.instance)
        write(self.instance / ".claude" / "skills" / "setup" / "SKILL.md", marked_md(OLD_VERSION))
        self.plan_json()
        for rel in LISTEN_MEMBERS + (".claude/skills/setup/SKILL.md",):
            self.assertTrue((self.instance / rel).exists(), rel)


# ---------------------------------------------------------------------------
# Phase 6c — the writing register keys
# ---------------------------------------------------------------------------

class TestRegisterItem(SyncFixture):
    def test_missing_keys_are_one_register_item(self):
        items = self.items("register")
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual((item["id"], item["path"], item["block"]),
                         ("g1", "private/preferences.md", "absent"))
        self.assertIn("tone_default.communication", item["missing"])
        self.assertEqual(item["checksum"], sha256_of(self.instance / "private" / "preferences.md"))
        self.assertIsInstance(item["hints"], dict)

    def test_a_complete_block_means_no_register_item(self):
        prefs = self.instance / "private" / "preferences.md"
        r = subprocess.run([sys.executable, str(PLUGIN_ROOT / "bin" / "maestro-register-keys"),
                            "write", str(prefs)], capture_output=True, text=True,
                           env={"PATH": SYSTEM_PATH})
        self.assertEqual(r.returncode, 0, r.stderr)
        for bak in prefs.parent.glob("preferences.md.bak.*"):
            bak.unlink()
        self.assertEqual(self.items("register"), [])

    def test_hints_carry_the_owner_lines(self):
        prefs = self.instance / "private" / "preferences.md"
        write(prefs, prefs.read_text().replace(
            "## Notes\n",
            "## Communication preferences\n\n- **Tone with others**: warmer with agency contacts\n\n## Notes\n"))
        item = self.items("register")[0]
        self.assertEqual(item["hints"].get("tone_default.communication"), "warmer with agency contacts")


# ---------------------------------------------------------------------------
# Orphans, the plan file and the JSON output
# ---------------------------------------------------------------------------

class TestPlanOutput(SyncFixture):
    def test_a_marked_file_absent_upstream_is_an_orphan(self):
        write(self.instance / "howto" / "99-mine.md", marked_md(OLD_VERSION, description="gone upstream"))
        items = self.items("orphan")
        self.assertEqual([(it["id"], it["path"], it["from"]) for it in items],
                         [("o1", "howto/99-mine.md", OLD_VERSION)])
        self.assertEqual(items[0]["checksum"], sha256_of(self.instance / "howto" / "99-mine.md"))
        self.assertTrue((self.instance / "howto" / "99-mine.md").exists())

    def test_the_plan_file_is_written_and_equal_to_the_json_output(self):
        plan = self.plan_json()
        self.assertEqual(json.loads((self.instance / PLAN_FILE).read_text()), plan)

    def test_the_summary_run_writes_the_same_plan_file(self):
        r = self.plan()
        self.assertEqual(r.returncode, OK, r.stderr)
        on_disk = json.loads((self.instance / PLAN_FILE).read_text())
        self.assertEqual(on_disk["mirror_head"], self.mirror_src.main)
        self.assertIn(PLAN_FILE, r.stdout)

    def test_the_plan_carries_its_creation_time_and_stamp(self):
        plan = self.plan_json()
        self.assertRegex(plan["created_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$")
        self.assertEqual(plan["stamp"], plan["created_at"][:10].replace("-", "") + "-"
                         + plan["created_at"][11:19].replace(":", ""))

    def test_the_plan_names_the_instance_by_its_real_path(self):
        link = self.root / "link dir"
        link.symlink_to(self.instance)
        plan = self.plan_json(instance=link)
        self.assertEqual(plan["instance"], str(self.instance.resolve()))
        self.assertEqual(json.loads((self.instance / PLAN_FILE).read_text())["instance"], plan["instance"])

    def test_a_new_plan_overwrites_the_previous_one(self):
        first = self.plan_json()
        write(self.instance / "howto" / "99-mine.md", marked_md(OLD_VERSION))
        second = self.plan_json()
        self.assertNotEqual([it["path"] for it in first["items"]], [it["path"] for it in second["items"]])
        self.assertEqual(json.loads((self.instance / PLAN_FILE).read_text())["items"], second["items"])

    def test_every_item_kind_appears_on_the_fixtures(self):
        recorder_procs(self.bindir)
        self.push_main({"howto/07-new.md": marked_md(NEW_VERSION, description="new")})
        write(self.instance / "bin" / "mem", "#!/bin/sh\necho old\n", mode=0o755)
        seed_listen(self.instance)
        write(self.instance / "howto" / "99-mine.md", marked_md(OLD_VERSION))
        kinds = {it["kind"] for it in self.items()}
        self.assertEqual(kinds, {"update", "new", "bin", "retired", "register", "orphan"})
        r = self.plan()
        for prefix in ("u1 ", "n1 ", "b1 ", "r1 ", "g1 ", "o1 "):
            self.assertIn(f"\n{prefix}", "\n" + r.stdout)


if __name__ == "__main__":
    unittest.main()
