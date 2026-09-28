"""tests/test_template_archive.py — `git archive` drops template-only paths
from a fresh instance (V4 plan, Task 1): `docs/`, `plugins/`,
`.claude-plugin/`, `.devflow.yml`, `.gitattributes` itself, and the tests
that only make sense inside the template repo.

`new-instance` builds an instance with `git archive <sha> | tar -x`, not
`git clone` + delete: nothing is removed after extraction, so the archive
itself has to come out clean. `.gitattributes` `export-ignore` marks the
excluded paths; this file exercises the real `git` binary against it.

Exercises a throwaway local clone of the *committed* branch — never the
working tree's uncommitted state, never the network (`git clone` on a local
path copies refs and objects only). This file is itself `export-ignore`:
it needs the template's own `.git` to clone from, which an archived
instance never has.

Run: python3 -m unittest tests.test_template_archive -v
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Paths that must never reach an archived instance.
TEMPLATE_ONLY_PATHS = (
    "docs",
    "plugins",
    ".claude-plugin",
    ".devflow.yml",
    ".gitattributes",
    ".version",
)

# Paths every archived instance must carry.
INSTANCE_PATHS = (
    "CLAUDE.md",
    "bin/mem",
    "bin/mem_schema.py",
    "memories.db.template",
    "preferences.example.md",
    "routines.example.yaml",
    ".claude/skills/logbook/SKILL.md",
    ".gitignore",
)

# Test files that reference template-only paths: export-ignored, so a
# freshly archived instance never carries them.
EXPORT_IGNORED_TEST_FILES = (
    "test_plugin_layout.py",
    "test_maestro_net.py",
    "test_maestro_sync.py",
    "test_maestro_versions.py",
    "test_template_archive.py",
    "test_finalize.py",
    "test_new_instance.py",
    "test_claude_md_refs.py",
)

# A sample of test files that have nothing to do with the template and
# must survive the archive untouched — guards against a `.gitattributes`
# pattern broad enough to drop `tests/` wholesale.
KEPT_TEST_FILES = (
    "__init__.py",
    "test_mem.py",
    "test_mem_schema.py",
    "test_mem_vec.py",
    "test_register_check.py",
    "test_session_digest.py",
    "test_skill_queries.py",
)

# Substrings that would tie a test to the template repo's own layout.
TEMPLATE_ONLY_TOKENS = ("plugins/", "docs/", ".claude-plugin")


def _git_env():
    """Explicit subprocess environment: no inherited PATH, only what git
    (and tar) need to run a local clone and archive."""
    env = {"PATH": "/usr/bin:/bin"}
    home = os.environ.get("HOME")
    if home:
        env["HOME"] = home
    return env


def _run(args, cwd=None, **kwargs):
    return subprocess.run(args, cwd=cwd, env=_git_env(), check=True, **kwargs)


class TestTemplateArchive(unittest.TestCase):
    """From a temp clone of the committed branch, `git archive HEAD | tar -x`
    into a temp dir must produce a clean instance skeleton."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="maestro-archive-test-")
        cls.clone = os.path.join(cls.tmp, "clone")
        cls.out = os.path.join(cls.tmp, "out")
        os.makedirs(cls.out, exist_ok=True)

        _run(["git", "clone", "--quiet", str(REPO), cls.clone])

        archive = _run(
            ["git", "-C", cls.clone, "archive", "HEAD"],
            stdout=subprocess.PIPE,
        )
        _run(["tar", "-x", "-C", cls.out], input=archive.stdout)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_template_only_paths_are_absent(self):
        for rel in TEMPLATE_ONLY_PATHS:
            with self.subTest(path=rel):
                self.assertFalse(
                    (Path(self.out) / rel).exists(),
                    f"{rel} leaked into the archive",
                )

    def test_instance_files_are_present(self):
        for rel in INSTANCE_PATHS:
            with self.subTest(path=rel):
                self.assertTrue(
                    (Path(self.out) / rel).exists(),
                    f"{rel} missing from the archive",
                )

    def test_bin_mem_is_executable(self):
        mem = Path(self.out) / "bin" / "mem"
        self.assertTrue(os.access(mem, os.X_OK), "bin/mem lost its executable bit")

    def test_template_only_test_files_are_absent(self):
        tests_dir = Path(self.out) / "tests"
        for name in EXPORT_IGNORED_TEST_FILES:
            with self.subTest(name=name):
                self.assertFalse((tests_dir / name).exists())

    def test_other_test_files_survive(self):
        tests_dir = Path(self.out) / "tests"
        for name in KEPT_TEST_FILES:
            with self.subTest(name=name):
                self.assertTrue((tests_dir / name).exists())

    def test_archived_tests_do_not_mention_template_only_paths(self):
        tests_dir = Path(self.out) / "tests"
        self.assertTrue(tests_dir.is_dir())
        offenders = []
        for path in sorted(tests_dir.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for token in TEMPLATE_ONLY_TOKENS:
                if token in text:
                    offenders.append(f"{path.name}: {token!r}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
