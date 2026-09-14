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

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "maestro-sync" / "SKILL.md"

# Anchors into the skill's Markdown. Each command is the first fenced
# ```bash block that follows its heading.
PHASE_4B_HEADING = "### Phase 4b — Reverse scan: new files from upstream"
PHASE_5B_HEADING = "### Phase 5b — Compare `bin/*` against the mirror"

_BASH_FENCE_RE = re.compile(r"```bash\n(.*?)```", re.DOTALL)


def _first_bash_block_after(text: str, heading: str) -> str:
    idx = text.index(heading)  # raises ValueError -> test failure if absent
    m = _BASH_FENCE_RE.search(text, idx)
    if m is None:
        raise AssertionError(f"no fenced bash block found after heading {heading!r}")
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


if __name__ == "__main__":
    unittest.main()
