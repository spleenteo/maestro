"""Tests for plugins/maestro/bin/maestro_versions.py — the vYYYY.MM.DD.N
version scheme, the changelog's top version, and the `origin: maestro`
marker rules shared by `maestro-sync` and, in V3, by the update-check hook.

The module lives under plugins/maestro/bin/, not on sys.path by package
name, so it is loaded from its file with SourceFileLoader, as
tests/test_mem_schema.py loads bin/mem_schema.py. Pure text/path logic: no
subprocess, no network, no temporary git repos needed.

Run: python3 -m unittest tests.test_maestro_versions -v
"""

from __future__ import annotations

import importlib.util
import re
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "plugins" / "maestro" / "bin" / "maestro_versions.py"
CHANGELOG = ROOT / "CHANGELOG.md"


def _load(name, path):
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


maestro_versions = _load("maestro_versions", MODULE_PATH)


class TestParseVersion(unittest.TestCase):
    def test_parses_a_well_formed_version(self):
        self.assertEqual(maestro_versions.parse_version("v2026.09.27.1"), (2026, 9, 27, 1))

    def test_parses_a_multi_digit_release_number(self):
        self.assertEqual(maestro_versions.parse_version("v2026.01.02.13"), (2026, 1, 2, 13))

    def test_rejects_a_missing_v_prefix(self):
        with self.assertRaises(ValueError):
            maestro_versions.parse_version("2026.09.27.1")

    def test_rejects_a_two_digit_year(self):
        with self.assertRaises(ValueError):
            maestro_versions.parse_version("v26.09.27.1")

    def test_rejects_trailing_garbage(self):
        with self.assertRaises(ValueError):
            maestro_versions.parse_version("v2026.09.27.1-beta")

    def test_rejects_an_empty_string(self):
        with self.assertRaises(ValueError):
            maestro_versions.parse_version("")


class TestIsNewer(unittest.TestCase):
    def test_a_later_date_is_newer(self):
        self.assertTrue(maestro_versions.is_newer("v2026.09.27.1", "v2026.09.24.1"))

    def test_an_earlier_date_is_not_newer(self):
        self.assertFalse(maestro_versions.is_newer("v2026.09.24.1", "v2026.09.27.1"))

    def test_equal_versions_are_not_newer(self):
        self.assertFalse(maestro_versions.is_newer("v2026.09.27.1", "v2026.09.27.1"))

    def test_the_release_counter_breaks_a_tie_on_the_same_day(self):
        self.assertTrue(maestro_versions.is_newer("v2026.09.27.2", "v2026.09.27.1"))

    def test_compares_as_integers_not_as_text(self):
        # A text comparison would put ".10" before ".9".
        self.assertTrue(maestro_versions.is_newer("v2026.09.27.10", "v2026.09.27.9"))


class TestChangelogTopVersion(unittest.TestCase):
    def test_matches_the_repos_own_first_heading(self):
        text = CHANGELOG.read_text(encoding="utf-8")
        m = re.search(r"^##\s+(v\d{4}\.\d{2}\.\d{2}\.\d+)\b", text, re.MULTILINE)
        self.assertIsNotNone(m, "CHANGELOG.md has no `## v...` heading to compare against")
        self.assertEqual(maestro_versions.changelog_top_version(CHANGELOG), m.group(1))

    def test_returns_the_first_of_several_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "CHANGELOG.md"
            path.write_text(
                "# CHANGELOG\n\nIntro text.\n\n"
                "## v2026.09.27.1 — 2026-09-27\n\nLatest.\n\n"
                "## v2026.09.24.1 — 2026-09-24\n\nOlder.\n",
                encoding="utf-8",
            )
            self.assertEqual(maestro_versions.changelog_top_version(path), "v2026.09.27.1")

    def test_none_when_no_heading_is_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "CHANGELOG.md"
            path.write_text("# CHANGELOG\n\nNo versions yet.\n", encoding="utf-8")
            self.assertIsNone(maestro_versions.changelog_top_version(path))


class TestReadMarker(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _write(self, name, text, newline=None):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline=newline) as fh:
            fh.write(text)
        return path

    def test_marked_markdown_with_version(self):
        path = self._write(
            "CLAUDE.md",
            "---\ntags: [x]\norigin: maestro\nmaestro_version: v2026.04.29.1\n---\n\n# Title\n",
        )
        marked, version = maestro_versions.read_marker(path)
        self.assertTrue(marked)
        self.assertEqual(version, "v2026.04.29.1")

    def test_marked_markdown_without_version_reads_none_and_the_baseline_is_documented(self):
        path = self._write("CLAUDE.md", "---\ntags: [x]\norigin: maestro\n---\n\n# Title\n")
        marked, version = maestro_versions.read_marker(path)
        self.assertTrue(marked)
        self.assertIsNone(version)
        self.assertEqual(maestro_versions.BASELINE_VERSION, "v2026.04.29.1")
        self.assertEqual(maestro_versions.parse_version(maestro_versions.BASELINE_VERSION), (2026, 4, 29, 1))

    def test_unmarked_valid_frontmatter(self):
        path = self._write("CLAUDE.md", "---\ntags: [x]\n---\n\n# Title\n")
        marked, version = maestro_versions.read_marker(path)
        self.assertFalse(marked)
        self.assertIsNone(version)

    def test_no_frontmatter_at_all(self):
        path = self._write("CLAUDE.md", "# Title\n\norigin: maestro\n")
        marked, version = maestro_versions.read_marker(path)
        self.assertFalse(marked)
        self.assertIsNone(version)

    def test_frontmatter_never_closed_is_not_marked(self):
        path = self._write("CLAUDE.md", "---\norigin: maestro\n\n# no closing rule\n")
        marked, version = maestro_versions.read_marker(path)
        self.assertFalse(marked)

    def test_a_body_line_that_mentions_the_marker_after_the_rule_is_never_a_mark(self):
        path = self._write(
            "CLAUDE.md",
            "---\ntags: [x]\n---\n\nSee `origin: maestro` in the marker rules.\n",
        )
        marked, version = maestro_versions.read_marker(path)
        self.assertFalse(marked)

    def test_an_inexact_frontmatter_line_is_not_a_mark(self):
        path = self._write("CLAUDE.md", "---\ntags: [x]\norigin: maestro-fork\n---\n\n# Title\n")
        marked, version = maestro_versions.read_marker(path)
        self.assertFalse(marked)

    def test_crlf_line_endings_are_still_read(self):
        path = self._write(
            "CLAUDE.md",
            "---\r\ntags: [x]\r\norigin: maestro\r\nmaestro_version: v2026.09.01.1\r\n---\r\n\r\n# Title\r\n",
            newline="",
        )
        marked, version = maestro_versions.read_marker(path)
        self.assertTrue(marked)
        self.assertEqual(version, "v2026.09.01.1")

    def test_a_utf8_bom_does_not_hide_the_first_dashes_line(self):
        path = self.root / "CLAUDE.md"
        path.write_bytes("﻿---\ntags: [x]\norigin: maestro\n---\n\n# Title\n".encode("utf-8"))
        marked, version = maestro_versions.read_marker(path)
        self.assertTrue(marked)

    def test_marked_script_in_first_three_lines(self):
        path = self._write(
            "bin/tool",
            "#!/usr/bin/env python3\n# origin: maestro\n# maestro_version: v2026.05.01.1\n\nprint('hi')\n",
        )
        marked, version = maestro_versions.read_marker(path)
        self.assertTrue(marked)

    def test_marked_script_with_the_c_style_comment(self):
        path = self._write("bin/tool.swift", "// origin: maestro\n// a swift script\n\nprint(1)\n")
        marked, version = maestro_versions.read_marker(path)
        self.assertTrue(marked)

    def test_a_script_marker_past_the_first_three_lines_is_not_a_mark(self):
        path = self._write(
            "bin/tool",
            "#!/usr/bin/env python3\n# a plain comment\n# another plain comment\n# origin: maestro\n",
        )
        marked, version = maestro_versions.read_marker(path)
        self.assertFalse(marked)

    def test_a_script_body_mention_is_never_a_mark(self):
        path = self._write(
            "bin/tool",
            "#!/usr/bin/env python3\n\"\"\"docstring\n\nmentions origin: maestro in prose.\n\"\"\"\nprint(1)\n",
        )
        marked, version = maestro_versions.read_marker(path)
        self.assertFalse(marked)


class TestConstants(unittest.TestCase):
    def test_baseline_version_matches_the_documented_value(self):
        self.assertEqual(maestro_versions.BASELINE_VERSION, "v2026.04.29.1")

    def test_markdown_globs_are_the_four_scanned_by_plan(self):
        self.assertEqual(
            maestro_versions.MARKDOWN_GLOBS,
            ("CLAUDE.md", ".claude/skills/*/SKILL.md", ".claude/agents/*.md", "howto/*.md"),
        )


if __name__ == "__main__":
    unittest.main()
