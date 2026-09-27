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

import json
import os
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
        for name in ("maestro-sync", "maestro_registry.py", "maestro_versions.py"):
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


if __name__ == "__main__":
    unittest.main()
