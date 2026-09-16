"""tests/test_maestro_sync.py — the two literal shell commands the
maestro-sync skill uses for its reverse scan (Phase 4b) and its bin/* drift
check (Phase 5b) run as plain `git`/`shasum`/`awk`/`grep` pipelines, with no
`rg` (a shell function that exists only inside Claude Code sessions, per the
V3 slice packet's deviation note).

Extraction is text-only: find a known phase heading in the skill's Markdown,
then take the next fenced ```bash block after it. A rewritten heading text
changes the anchors below.

Both commands are run with `subprocess` from a temp working directory that
is neither the mirror nor the instance — the commands are meant to run from
wherever the skill happens to be invoked, so `cwd` must not matter — against
a temp git mirror built with `git init` + `git add` + `git commit` (local
`user.name`/`user.email`, so the test never touches global git config).

Run: python3 -m unittest tests.test_maestro_sync -v
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "plugins" / "maestro" / "skills" / "maestro-sync" / "SKILL.md"

# Anchors into the skill's Markdown. Each command is the first fenced
# ```bash block that follows its heading.
PHASE_4B_HEADING = "### Phase 4b — Reverse scan: new files from upstream"
PHASE_5B_HEADING = "### Phase 5b — Compare `bin/*` against the mirror"
PHASE_0_HEADING = "### Phase 0 — Check this is an instance"
PHASE_3_HEADING = "### Phase 3 — Refresh the read-only mirror, check the plugin"
PHASE_6B_HEADING = "### Phase 6b — Retired paths"

_BASH_FENCE_RE = re.compile(r"```bash\n(.*?)```", re.DOTALL)


def _first_bash_block_after(text: str, heading: str) -> str:
    idx = text.index(heading)  # raises ValueError -> test failure if absent
    m = _BASH_FENCE_RE.search(text, idx)
    if m is None:
        raise AssertionError(f"no fenced bash block found after heading {heading!r}")
    return m.group(1)


def _nth_bash_block_after(text: str, heading: str, n: int) -> str:
    idx = text.index(heading)
    for _ in range(n):
        m = _BASH_FENCE_RE.search(text, idx)
        if m is None:
            raise AssertionError(f"fewer than {n} bash blocks after {heading!r}")
        idx = m.end()
    return m.group(1)


def reverse_scan_command() -> str:
    return _first_bash_block_after(SKILL.read_text(), PHASE_4B_HEADING)


def bin_drift_command() -> str:
    return _first_bash_block_after(SKILL.read_text(), PHASE_5B_HEADING)


# ---------------------------------------------------------------------------
# Git fixture helpers
# ---------------------------------------------------------------------------

def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "sync-test@example.com"],
                    cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Sync Test"], cwd=path, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=path, check=True)


def _commit(path: Path, files: list[str], message: str = "seed") -> None:
    subprocess.run(["git", "add", *files], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=path, check=True)


def _marked_md(description: str = "test file") -> str:
    return (
        "---\n"
        "origin: maestro\n"
        "maestro_version: v2026.01.01.1\n"
        f"description: {description}\n"
        "---\n\n"
        "# Test\n\nBody.\n"
    )


def _unmarked_md(description: str = "not a maestro file") -> str:
    """Valid frontmatter, but no `origin: maestro` line — the negative
    twin of `_marked_md`."""
    return (
        "---\n"
        f"description: {description}\n"
        "---\n\n"
        "# Test\n\nBody.\n"
    )


def _run_shell(command: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", command], cwd=cwd,
                           capture_output=True, text=True)


def _output_lines(r: subprocess.CompletedProcess) -> list[str]:
    return [ln for ln in r.stdout.splitlines() if ln]


# ---------------------------------------------------------------------------
# Phase 4b — reverse scan, exclusion list
# ---------------------------------------------------------------------------

class TestReverseScanExclusions(unittest.TestCase):
    """Marked files under docs/, plugins/, .claude-plugin/ and user-skills/
    never reach the candidate list; marked files elsewhere do. An unmarked
    file (valid frontmatter, no `origin: maestro`) and a file with no
    frontmatter at all never reach it either, even when `origin: maestro`
    appears as plain text somewhere in their body — the awk extraction must
    stop reading once the real frontmatter block (or its absence) is
    settled, never fall through to matching body text."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.mirror = Path(self._tmp.name) / "mirror"
        self.cwd = Path(self._tmp.name) / "elsewhere"
        self.mirror.mkdir()
        self.cwd.mkdir()
        _init_git_repo(self.mirror)

        self._write(".claude/skills/x/SKILL.md", _marked_md())
        self._write(".claude/agents/y.md", _marked_md())
        self._write("howto/z.md", _marked_md())
        self._write("CLAUDE.md", _marked_md())
        self._write("docs/plan.md", _marked_md())
        self._write("plugins/maestro/skills/net/SKILL.md", _marked_md())
        self._write(".claude-plugin/notes.md", _marked_md())
        self._write("user-skills/foo/SKILL.md", _marked_md())
        # Valid frontmatter, but the `origin: maestro` line is absent.
        self._write("howto/unmarked.md", _unmarked_md())
        # No frontmatter at all (first line isn't `---`); the body still
        # happens to contain a line that reads exactly like the marker,
        # the way a howto explaining the marker itself might.
        self._write(
            "howto/no-frontmatter-mentions-origin.md",
            "# Not frontmatter\n\nThis file starts with a heading, not "
            "`---`. Its body happens to say:\n\norigin: maestro\n\n"
            "…as plain prose, which must not count.\n",
        )
        # Real frontmatter closes with the second `---`, closes WITHOUT
        # `origin: maestro`; a Markdown rule later in the body is followed
        # by a line that reads like the marker. A body containing its own
        # `---` must not trick the extraction into reading past the real
        # close and matching that later line.
        self._write(
            "howto/rule-then-origin-mention.md",
            _unmarked_md("looks unmarked, body is a trap")
            + "\n---\n\norigin: maestro\n",
        )
        _commit(self.mirror, ["."])

    def _write(self, rel: str, content: str) -> None:
        p = self.mirror / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)

    def _run(self) -> list[str]:
        cmd = reverse_scan_command().replace("<mirror-path>", str(self.mirror))
        r = _run_shell(cmd, self.cwd)
        self.assertEqual(r.returncode, 0, r.stderr)
        return _output_lines(r)

    def test_lists_marked_files_outside_excluded_folders(self):
        self.assertEqual(set(self._run()), {
            ".claude/skills/x/SKILL.md",
            ".claude/agents/y.md",
            "howto/z.md",
            "CLAUDE.md",
        })

    def test_excludes_docs(self):
        self.assertTrue(all(not f.startswith("docs/") for f in self._run()))

    def test_excludes_plugins(self):
        self.assertTrue(all(not f.startswith("plugins/") for f in self._run()))

    def test_excludes_claude_plugin(self):
        self.assertTrue(all(not f.startswith(".claude-plugin/") for f in self._run()))

    def test_excludes_user_skills(self):
        self.assertTrue(all(not f.startswith("user-skills/") for f in self._run()))

    def test_excludes_unmarked_file_with_valid_frontmatter(self):
        self.assertNotIn("howto/unmarked.md", self._run())

    def test_excludes_file_with_no_frontmatter_that_mentions_origin_in_body(self):
        self.assertNotIn("howto/no-frontmatter-mentions-origin.md", self._run())

    def test_body_rule_followed_by_origin_mention_does_not_trick_extraction(self):
        self.assertNotIn("howto/rule-then-origin-mention.md", self._run())


# ---------------------------------------------------------------------------
# Phase 4b / 5b — a `<mirror-path>` (or `<instance-path>`) that doesn't exist
# fails loudly instead of being swallowed by the `| while read` pipe
# ---------------------------------------------------------------------------

class TestGitFailurePropagates(unittest.TestCase):
    """Fix round 2, finding 1: `git -C "<mirror-path>"` on a path that
    doesn't exist fails, but the failure is the left side of a
    `| while read` pipe — without `set -o pipefail` the pipeline's exit
    status is the while loop's (0 on normal EOF), so Phase 4b reports no
    new files and Phase 5b no drift instead of erroring. The literal `~`
    the owner should never substitute for a placeholder is one way to reach
    a nonexistent path (double-quoted, `~` never expands); a plain typo or
    a mirror that hasn't been cloned yet is another. Both must fail loudly."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cwd = Path(self._tmp.name) / "elsewhere"
        self.cwd.mkdir()
        self.missing = Path(self._tmp.name) / "no-such-mirror"

    def test_reverse_scan_exits_nonzero_when_mirror_path_is_missing(self):
        cmd = reverse_scan_command().replace("<mirror-path>", str(self.missing))
        r = _run_shell(cmd, self.cwd)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(_output_lines(r), [])

    def test_bin_drift_exits_nonzero_when_mirror_path_is_missing(self):
        cmd = (bin_drift_command()
               .replace("<mirror-path>", str(self.missing))
               .replace("<instance-path>", str(self.cwd)))
        r = _run_shell(cmd, self.cwd)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(_output_lines(r), [])

    def test_reverse_scan_exits_nonzero_on_a_literal_tilde_path(self):
        # A literal `~` inside the double-quoted `"<mirror-path>"` slot
        # never expands — this is the regression itself, not a synthetic
        # case: the placeholder text must never be substituted this way,
        # and if it is, the command must fail loudly rather than silently
        # report "no new files".
        cmd = reverse_scan_command().replace(
            "<mirror-path>", "~/this-tilde-must-never-expand-here"
        )
        r = _run_shell(cmd, self.cwd)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(_output_lines(r), [])

    def test_bin_drift_exits_nonzero_on_a_literal_tilde_path(self):
        cmd = (bin_drift_command()
               .replace("<mirror-path>", "~/this-tilde-must-never-expand-here")
               .replace("<instance-path>", str(self.cwd)))
        r = _run_shell(cmd, self.cwd)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(_output_lines(r), [])


# ---------------------------------------------------------------------------
# Phase 5b — bin/* drift check
# ---------------------------------------------------------------------------

class TestBinDriftCheck(unittest.TestCase):
    """One changed, one missing, one identical file; an untracked
    bin/__pycache__/ in the mirror must never be listed."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.mirror = Path(self._tmp.name) / "mirror"
        self.instance = Path(self._tmp.name) / "instance"
        self.cwd = Path(self._tmp.name) / "elsewhere"
        self.mirror.mkdir()
        self.instance.mkdir()
        self.cwd.mkdir()
        _init_git_repo(self.mirror)

        (self.mirror / "bin").mkdir()
        (self.mirror / "bin" / "mem").write_text("content-mem-v2\n")
        (self.mirror / "bin" / "listen").write_text("content-listen-v1\n")
        (self.mirror / "bin" / "register-check").write_text("content-register-v1\n")
        # Untracked on purpose: git ls-files must not surface it.
        pycache = self.mirror / "bin" / "__pycache__"
        pycache.mkdir()
        (pycache / "mem.cpython-39.pyc").write_bytes(b"\x00\x01not-tracked")
        _commit(self.mirror, ["bin/mem", "bin/listen", "bin/register-check"])

        (self.instance / "bin").mkdir()
        (self.instance / "bin" / "mem").write_text("content-mem-v1\n")  # differs
        (self.instance / "bin" / "register-check").write_text("content-register-v1\n")  # identical
        # bin/listen intentionally absent from the instance -> missing

    def _run(self) -> list[str]:
        cmd = (bin_drift_command()
               .replace("<mirror-path>", str(self.mirror))
               .replace("<instance-path>", str(self.instance)))
        r = _run_shell(cmd, self.cwd)
        self.assertEqual(r.returncode, 0, r.stderr)
        return _output_lines(r)

    def test_reports_differs_missing_and_skips_identical(self):
        self.assertEqual(set(self._run()), {"differs bin/mem", "missing bin/listen"})

    def test_does_not_list_the_untracked_pycache_dir(self):
        self.assertTrue(all("__pycache__" not in ln for ln in self._run()))


# ---------------------------------------------------------------------------
# Regression — a mirror (or instance) path containing a space
# ---------------------------------------------------------------------------

class TestPathsWithSpaces(unittest.TestCase):
    """Fix round 1, Important 1: `git -C <mirror-path>` left the placeholder
    unquoted in both new blocks. With a space in the path (the skill's own
    `maestro_mirror_path:` preference, or an instance under `~/Library/Mobile
    Documents/…`), `git -C` fails to change directory, the failure is
    swallowed by the `| while read` pipe, and the pipeline exits 0 printing
    nothing — Phase 4b silently reports no new files, Phase 5b silently
    reports no drift. Both the mirror and the instance directory carry a
    space here, so a regression in either placeholder's quoting is caught."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.mirror = Path(self._tmp.name) / "my mirror"
        self.instance = Path(self._tmp.name) / "my instance"
        self.cwd = Path(self._tmp.name) / "elsewhere"
        self.mirror.mkdir()
        self.instance.mkdir()
        self.cwd.mkdir()
        _init_git_repo(self.mirror)

        self._write(".claude/skills/x/SKILL.md", _marked_md())
        _commit(self.mirror, ["."], "seed md")

        (self.mirror / "bin").mkdir()
        (self.mirror / "bin" / "mem").write_text("content-mem-v2\n")
        _commit(self.mirror, ["bin/mem"], "add bin")

        (self.instance / "bin").mkdir()
        (self.instance / "bin" / "mem").write_text("content-mem-v1\n")  # differs

    def _write(self, rel: str, content: str) -> None:
        p = self.mirror / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)

    def test_reverse_scan_lists_marked_file_when_mirror_path_has_a_space(self):
        cmd = reverse_scan_command().replace("<mirror-path>", str(self.mirror))
        r = _run_shell(cmd, self.cwd)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(_output_lines(r), [".claude/skills/x/SKILL.md"])

    def test_bin_drift_check_reports_when_mirror_path_has_a_space(self):
        cmd = (bin_drift_command()
               .replace("<mirror-path>", str(self.mirror))
               .replace("<instance-path>", str(self.instance)))
        r = _run_shell(cmd, self.cwd)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(_output_lines(r), ["differs bin/mem"])


# ---------------------------------------------------------------------------
# Phase 0, Phase 3, Phase 5b copy, Phase 6b — the blocks that decide or write
# ---------------------------------------------------------------------------

import json
import os
import sqlite3


class TestInstanceGuard(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(os.path.realpath(self._tmp.name))
        self.cmd = _nth_bash_block_after(SKILL.read_text(), PHASE_0_HEADING, 1)

    def test_stops_outside_an_instance(self):
        (self.root / "bin").mkdir()
        (self.root / "bin" / "mem").write_text("")
        r = _run_shell(self.cmd, self.root)
        self.assertEqual(r.returncode, 1)
        self.assertIn("not the root of a Maestro instance", r.stderr)

    def test_prints_the_instance_root(self):
        (self.root / "bin").mkdir()
        (self.root / "bin" / "mem").write_text("")
        (self.root / "private").mkdir()
        (self.root / "private" / "preferences.md").write_text("")
        r = _run_shell(self.cmd, self.root)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, str(self.root)), r.stderr)


class TestPluginBehindUpstream(unittest.TestCase):
    """Phase 3 clones or refreshes the mirror, then stops when upstream `main`
    has commits the installed plugin doesn't."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.work = root / "work"
        self.work.mkdir()
        _init_git_repo(self.work)
        subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=self.work, check=True)
        (self.work / "a.md").write_text("one\n")
        _commit(self.work, ["a.md"], "one")
        self.old = self._head()
        (self.work / "a.md").write_text("two\n")
        _commit(self.work, ["a.md"], "two")
        self.main = self._head()
        subprocess.run(["git", "checkout", "-q", "-b", "feature"], cwd=self.work, check=True)
        (self.work / "a.md").write_text("three\n")
        _commit(self.work, ["a.md"], "three")
        self.ahead = self._head()
        self.origin = root / "origin.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(self.work), str(self.origin)], check=True)
        self.plugin = root / "plugin"
        (self.plugin / ".claude-plugin").mkdir(parents=True)
        (self.plugin / ".claude-plugin" / "plugin.json").write_text(json.dumps({"repository": str(self.origin)}))
        self.bindir = root / "stub"
        self.bindir.mkdir()
        self.mirror = root / "mirror dir"
        self.cmd = _nth_bash_block_after(SKILL.read_text(), PHASE_3_HEADING, 1)

    def _head(self) -> str:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.work, capture_output=True,
                              text=True, check=True).stdout.strip()

    def _run(self, version: str, install_path=None) -> subprocess.CompletedProcess:
        claude = self.bindir / "claude"
        claude.write_text("#!/bin/sh\ncat <<'EOF'\n" + json.dumps([
            {"id": "maestro@maestro", "scope": "project", "version": "0000000"},
            {"id": "maestro@maestro", "scope": "user", "version": version[:12],
             "installPath": str(install_path or self.plugin)},
        ]) + "\nEOF\n")
        claude.chmod(0o755)
        env = {"PATH": f"{self.bindir}:/usr/bin:/bin", "HOME": self._tmp.name,
               "CLAUDE_PLUGIN_ROOT": str(self.plugin)}
        cmd = (self.cmd.replace("<mirror-path>", str(self.mirror))
               .replace("<instance-path>", self._tmp.name + "/instance").replace("<worktree-path>", "none"))
        return subprocess.run(["bash", "-c", cmd],
                              cwd=self._tmp.name, capture_output=True, text=True, env=env)

    def test_plugin_at_main_passes_and_clones_the_mirror(self):
        r = self._run(self.main)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"MIRROR_HEAD {self.main}", r.stdout)

    def test_plugin_ahead_on_a_branch_passes(self):
        self.assertEqual(self._run(self.ahead).returncode, 0)

    def test_loaded_plugin_other_than_installed_stops(self):
        other = Path(self._tmp.name) / "newer-install"
        other.mkdir()
        r = self._run(self.main, install_path=other)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Restart Claude Code", r.stderr)

    def test_stale_mirror_moves_forward_to_the_new_main(self):
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.mirror)], check=True)
        subprocess.run(["git", "-C", str(self.mirror), "reset", "-q", "--hard", self.old], check=True)
        r = self._run(self.main)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"MIRROR_HEAD {self.main}", r.stdout)

    def test_plugin_behind_main_stops(self):
        r = self._run(self.old)
        self.assertEqual(r.returncode, 1)
        self.assertIn("behind", r.stderr)


class TestBinCopy(unittest.TestCase):
    """Phase 5b's copy block backs up the db, then copies only drifted files."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.mirror = root / "mirror"
        self.instance = root / "my instance"
        self.mirror.mkdir()
        (self.instance / "bin").mkdir(parents=True)
        (self.instance / "private").mkdir()
        _init_git_repo(self.mirror)
        (self.mirror / "bin").mkdir()
        mem = self.mirror / "bin" / "mem"
        mem.write_text("#!/bin/sh\necho stats-v2\n")
        mem.chmod(0o755)
        (self.mirror / "bin" / "same").write_text("same\n")
        _commit(self.mirror, ["bin/mem", "bin/same"])
        (self.instance / "bin" / "mem").write_text("#!/bin/sh\necho stats-v1\n")
        (self.instance / "bin" / "same").write_text("same\n")
        con = sqlite3.connect(self.instance / "private" / "memories.db")
        con.execute("CREATE TABLE log (id INTEGER PRIMARY KEY, title TEXT)")
        con.execute("INSERT INTO log (title) VALUES ('kept')")
        con.commit()
        con.close()

    def test_backs_up_then_copies_only_drifted_files(self):
        cmd = (_nth_bash_block_after(SKILL.read_text(), PHASE_5B_HEADING, 2)
               .replace("<mirror-path>", str(self.mirror))
               .replace("<instance-path>", str(self.instance)))
        r = _run_shell(cmd, Path(self._tmp.name))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("copied bin/mem", r.stdout)
        self.assertNotIn("copied bin/same", r.stdout)
        self.assertIn("stats-v2", r.stdout)
        backups = list((self.instance / "private").glob("memories.db.bak.*-pre-sync"))
        self.assertEqual(len(backups), 1)
        con = sqlite3.connect(backups[0])
        self.assertEqual(con.execute("SELECT title FROM log").fetchall(), [("kept",)])
        con.close()

    def test_failed_stats_leaves_a_restorable_instance(self):
        (self.mirror / "bin" / "mem").write_text("#!/bin/sh\necho broken >&2\nexit 1\n")
        _commit(self.mirror, ["bin/mem"], "broken mem")
        text = SKILL.read_text()
        cmd = (_nth_bash_block_after(text, PHASE_5B_HEADING, 2)
               .replace("<mirror-path>", str(self.mirror)).replace("<instance-path>", str(self.instance)))
        r = _run_shell(cmd, Path(self._tmp.name))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("copied bin/mem", r.stdout)
        binbak = next(ln.split(" ", 2)[2] for ln in r.stdout.splitlines() if ln.startswith("old scripts "))
        backup = next(ln.split(" ", 1)[1] for ln in r.stdout.splitlines() if ln.startswith("backup "))
        restore = (_nth_bash_block_after(text, PHASE_5B_HEADING, 3)
                   .replace("<instance-path>", str(self.instance))
                   .replace("<old-scripts-path>", binbak).replace("<backup-path>", backup))
        r2 = _run_shell(restore, Path(self._tmp.name))
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertEqual((self.instance / "bin" / "mem").read_text(), "#!/bin/sh\necho stats-v1\n")


class TestRetiredPaths(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.inst = Path(self._tmp.name) / "my inst"
        (self.inst / "bin").mkdir(parents=True)
        (self.inst / "bin" / "mem").write_text("")
        (self.inst / "private").mkdir()
        (self.inst / "private" / "preferences.md").write_text("")
        for rel, marked in ((".claude/skills/maestro-sync", True), (".claude/skills/setup", False),
                            (".claude/skills/.disabled/setup", True), ("user-skills/maestro-net", True),
                            ("user-skills/mine", False)):
            d = self.inst / rel
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(_marked_md() if marked else _unmarked_md())
        text = SKILL.read_text()
        self.listing = _nth_bash_block_after(text, PHASE_6B_HEADING, 1)
        self.removal = _nth_bash_block_after(text, PHASE_6B_HEADING, 2)

    def remove(self, retired: str) -> subprocess.CompletedProcess:
        cmd = self.removal.replace("<instance-path>", str(self.inst)).replace("<retired-path>", retired)
        return _run_shell(cmd, Path(self._tmp.name))

    def test_lists_only_marked_retired_paths_and_removes_nothing(self):
        self.assertNotRegex(self.listing, r"\brm\b")
        r = _run_shell(self.listing.replace("<instance-path>", str(self.inst)), Path(self._tmp.name))
        self.assertEqual(r.returncode, 0, r.stderr)
        retired = [ln for ln in _output_lines(r) if ln.startswith("retired ")]
        self.assertEqual(retired, ["retired .claude/skills/maestro-sync",
                                   "retired .claude/skills/.disabled/setup",
                                   "retired user-skills/maestro-net"])
        self.assertIn("    .claude/skills/maestro-sync/SKILL.md", r.stdout)
        self.assertTrue((self.inst / ".claude" / "skills" / "maestro-sync").is_dir())

    def test_removal_refuses_anything_outside_the_allowlist(self):
        for bad in ("", ".", "private", "user-skills", "../x"):
            with self.subTest(path=bad):
                r = self.remove(bad)
                self.assertEqual(r.returncode, 2, r.stderr)
        self.assertTrue((self.inst / "private" / "preferences.md").is_file())
        self.assertTrue((self.inst / "user-skills" / "mine").is_dir())

    def test_removal_deletes_one_path_and_keeps_a_non_empty_user_skills(self):
        self.assertEqual(self.remove("user-skills/maestro-net").returncode, 0)
        self.assertFalse((self.inst / "user-skills" / "maestro-net").exists())
        self.assertTrue((self.inst / "user-skills" / "mine").is_dir())
        self.assertEqual(self.remove(".claude/skills/maestro-sync").returncode, 0)
        self.assertFalse((self.inst / ".claude" / "skills" / "maestro-sync").exists())


LISTEN_MEMBERS = (".claude/skills/listen", "bin/listen", "bin/listen-updates", "bin/audiowatch.swift")


class TestRetiredListen(unittest.TestCase):
    """`listen` moved into the plugin: Phase 6b retires the old copy as one
    unit, removes only the members that carry the marker (a script's own
    header, not a mention in its body), backs them up first, and waits while a
    capture runs, since an old `listen-updates` would print errors forever."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.inst = self.tmp / "my inst"
        (self.inst / "bin").mkdir(parents=True)
        (self.inst / "bin" / "mem").write_text("mem\n")
        (self.inst / "private").mkdir()
        (self.inst / "private" / "preferences.md").write_text("")
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.pid = None
        text = SKILL.read_text()
        self.listing = _nth_bash_block_after(text, PHASE_6B_HEADING, 1)
        self.removal = _nth_bash_block_after(text, PHASE_6B_HEADING, 2)

    def tearDown(self):
        if self.pid:
            try:
                os.kill(self.pid, signal.SIGKILL)
            except OSError:
                pass

    def seed(self, unmarked=()):
        skill = self.inst / ".claude" / "skills" / "listen"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            _unmarked_md() if ".claude/skills/listen" in unmarked else _marked_md())
        for name in ("listen", "listen-updates"):
            rel = f"bin/{name}"
            (self.inst / rel).write_text(
                "#!/bin/sh\necho mine\n" if rel in unmarked
                else "#!/usr/bin/env python3\n# origin: maestro\n# maestro_version: v2026.09.10.1\n")
        (self.inst / "bin" / "audiowatch.swift").write_text(
            "// mine\n" if "bin/audiowatch.swift" in unmarked
            else "// origin: maestro\n// maestro_version: v2026.09.10.1\n//\n")

    def capture_running(self):
        out = subprocess.run(["sh", "-c", "tail -f /dev/null >/dev/null 2>&1 </dev/null & echo $!"],
                             capture_output=True, text=True, check=True)
        self.pid = int(out.stdout.strip())
        state = self.home / ".local" / "state" / "listen"
        state.mkdir(parents=True)
        (state / "current.json").write_text(json.dumps({"supervisor_pid": self.pid}))

    def run_block(self, block: str) -> subprocess.CompletedProcess:
        cmd = block.replace("<instance-path>", str(self.inst)).replace("<retired-path>", "listen")
        env = dict(os.environ, HOME=str(self.home))
        return subprocess.run(["bash", "-c", cmd], cwd=self.tmp, env=env,
                              capture_output=True, text=True)

    def test_lists_marked_members_and_names_the_kept_ones(self):
        self.seed(unmarked=("bin/listen",))
        r = self.run_block(self.listing)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = _output_lines(r)
        start = lines.index("retired listen")
        self.assertEqual(lines[start + 1:start + 5], [
            "    .claude/skills/listen (marked)",
            "    bin/listen (not marked, kept)",
            "    bin/listen-updates (marked)",
            "    bin/audiowatch.swift (marked)",
        ])

    def test_a_marker_in_the_body_is_not_a_mark(self):
        (self.inst / "bin" / "listen").write_text("#!/bin/sh\necho a\necho b\n# origin: maestro\n")
        r = self.run_block(self.listing)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("listen", r.stdout)

    def test_no_marked_member_lists_nothing(self):
        self.seed(unmarked=LISTEN_MEMBERS)
        self.assertNotIn("listen", self.run_block(self.listing).stdout)

    def test_a_running_capture_postpones_the_unit(self):
        self.seed()
        self.capture_running()
        r = self.run_block(self.listing)
        self.assertIn("postponed listen: a capture is running", r.stdout)
        self.assertNotIn("retired listen", r.stdout)

    def test_removal_backs_up_and_removes_marked_members_only(self):
        self.seed(unmarked=("bin/listen",))
        r = self.run_block(self.removal)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for rel in (".claude/skills/listen", "bin/listen-updates", "bin/audiowatch.swift"):
            self.assertFalse((self.inst / rel).exists(), rel)
            self.assertIn(f"removed {rel}", r.stdout)
        self.assertEqual((self.inst / "bin" / "listen").read_text(), "#!/bin/sh\necho mine\n")
        self.assertIn("kept bin/listen", r.stdout)
        self.assertEqual((self.inst / "bin" / "mem").read_text(), "mem\n")
        backups = list((self.inst / "private").glob("retired.bak.*-listen"))
        self.assertEqual(len(backups), 1)
        self.assertTrue((backups[0] / ".claude" / "skills" / "listen" / "SKILL.md").is_file())
        self.assertTrue((backups[0] / "bin" / "listen-updates").is_file())
        self.assertTrue((backups[0] / "bin" / "audiowatch.swift").is_file())
        self.assertFalse((backups[0] / "bin" / "listen").exists())

    def test_removal_waits_for_a_running_capture(self):
        self.seed()
        self.capture_running()
        r = self.run_block(self.removal)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        for rel in LISTEN_MEMBERS:
            self.assertTrue((self.inst / rel).exists(), rel)

    def test_listing_and_removal_name_the_same_paths(self):
        loop = re.search(r"for p in (.*?); do", self.listing).group(1).split()
        case = re.search(r"^\s*([^\s()]+)\) ;;", self.removal, re.M).group(1).split("|")
        self.assertEqual(set(loop) | {"listen"}, set(case))
        members = [re.search(r"for m in (.*?); do", block).group(1).split()
                   for block in (self.listing, self.removal)]
        self.assertEqual(members[0], list(LISTEN_MEMBERS))
        self.assertEqual(members[1], list(LISTEN_MEMBERS))


if __name__ == "__main__":
    unittest.main()
