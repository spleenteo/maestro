"""tests/test_plugin_layout.py — structure of the `maestro` Claude Code
plugin and marketplace (V3 slice, Task 2): `.claude-plugin/marketplace.json`
at the repo root, `plugins/maestro/.claude-plugin/plugin.json`, and
`maestro-net` moved in from `user-skills/maestro-net/`.

Static, file-content checks only. `claude plugin validate` is a separate
gate step, run outside this file — no `claude` binary assumed in a test
environment. No network, no real instance.

Run: python3 -m unittest tests.test_plugin_layout -v
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN_DIR = ROOT / "plugins" / "maestro"
PLUGIN_MANIFEST = PLUGIN_DIR / ".claude-plugin" / "plugin.json"
SCRIPT = PLUGIN_DIR / "bin" / "maestro-net"
SKILL = PLUGIN_DIR / "skills" / "maestro-net" / "SKILL.md"
NEW_INSTANCE_SKILL = PLUGIN_DIR / "skills" / "new-instance" / "SKILL.md"
NEW_INSTANCE_FINALIZE = PLUGIN_DIR / "skills" / "new-instance" / "finalize.sh"


class TestMarketplaceJson(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))

    def test_parses_as_an_object(self):
        self.assertIsInstance(self.data, dict)

    def test_required_fields(self):
        self.assertEqual(self.data["name"], "maestro")
        self.assertIn("owner", self.data)
        self.assertIsInstance(self.data["owner"], dict)
        self.assertTrue(self.data["owner"].get("name"))
        self.assertIsInstance(self.data["plugins"], list)

    def test_top_level_description(self):
        self.assertIsInstance(self.data.get("description"), str)
        self.assertTrue(self.data["description"].strip())

    def test_lists_the_maestro_plugin_entry(self):
        entries = {e["name"]: e for e in self.data["plugins"]}
        self.assertIn("maestro", entries)
        entry = entries["maestro"]
        self.assertEqual(entry["source"], "./plugins/maestro")
        self.assertIsInstance(entry.get("description"), str)
        self.assertTrue(entry["description"].strip())

    def test_declares_no_version(self):
        self.assertNotIn("version", self.data)


class TestPluginJson(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))

    def test_parses_as_an_object(self):
        self.assertIsInstance(self.data, dict)

    def test_required_fields(self):
        self.assertEqual(self.data["name"], "maestro")
        self.assertIsInstance(self.data.get("description"), str)
        self.assertTrue(self.data["description"].strip())
        self.assertIsInstance(self.data.get("author"), dict)
        self.assertTrue(self.data["author"].get("name"))
        self.assertEqual(self.data["repository"], "https://github.com/spleenteo/maestro")

    def test_declares_no_version(self):
        self.assertNotIn("version", self.data)


class TestNoOriginMarker(unittest.TestCase):
    """Plugin files carry no `origin: maestro` marker (Task 2 brief): the
    plugin distributes them, and an instance still running an old
    `maestro-sync`, without the reverse-scan exclusion list, would otherwise
    propose them as new upstream files."""

    def test_no_file_under_plugins_or_dot_claude_plugin_carries_the_marker(self):
        offenders = []
        for base in (ROOT / "plugins", ROOT / ".claude-plugin"):
            if not base.is_dir():
                continue
            for path in base.rglob("*"):
                if not path.is_file():
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                if "origin: maestro" in text or "maestro_version:" in text:
                    offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])


class TestMaestroNetScriptPlacement(unittest.TestCase):
    def test_script_exists_and_is_executable(self):
        self.assertTrue(SCRIPT.is_file())
        self.assertTrue(os.access(SCRIPT, os.X_OK))

    def test_script_has_no_origin_header(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("# origin: maestro", text)
        self.assertNotIn("# maestro_version:", text)


class TestMaestroNetSkillPlacement(unittest.TestCase):
    def test_skill_exists(self):
        self.assertTrue(SKILL.is_file())

    def test_skill_frontmatter_has_no_origin_marker(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertNotIn("origin: maestro", text)
        self.assertNotIn("maestro_version:", text)

    def test_skill_calls_the_command_bare_not_by_home_path(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertNotIn("~/.claude/skills", text)

    def test_skill_name_field_unchanged(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("name: maestro-net", text)

    def test_skill_description_says_it_ships_in_the_plugin(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertNotIn("Installed user-level", text)


class TestUserSkillsGone(unittest.TestCase):
    def test_user_skills_directory_no_longer_exists(self):
        self.assertFalse((ROOT / "user-skills").exists())


class TestNewInstanceSkillPlacement(unittest.TestCase):
    """`setup` moved from `.claude/skills/setup/` into the plugin as
    `new-instance` (V4 plan, Task 3): triggered only on explicit request,
    never automatically — a user-scope plugin loads its skills in every
    session, and the interview should not start on its own."""

    def test_skill_exists(self):
        self.assertTrue(NEW_INSTANCE_SKILL.is_file())

    def test_finalize_script_exists_and_is_readable(self):
        self.assertTrue(NEW_INSTANCE_FINALIZE.is_file())

    def test_skill_frontmatter_has_no_origin_marker(self):
        text = NEW_INSTANCE_SKILL.read_text(encoding="utf-8")
        self.assertNotIn("origin: maestro", text)
        self.assertNotIn("maestro_version:", text)

    def test_skill_name_field_is_new_instance(self):
        text = NEW_INSTANCE_SKILL.read_text(encoding="utf-8")
        self.assertIn("name: new-instance", text)

    def test_skill_disables_automatic_model_invocation(self):
        text = NEW_INSTANCE_SKILL.read_text(encoding="utf-8")
        self.assertIn("disable-model-invocation: true", text)


class TestOldSetupSkillGone(unittest.TestCase):
    def test_setup_skill_directory_no_longer_exists_under_dot_claude(self):
        self.assertFalse((ROOT / ".claude" / "skills" / "setup").exists())


if __name__ == "__main__":
    unittest.main()
