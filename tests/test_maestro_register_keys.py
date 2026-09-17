"""tests/test_maestro_register_keys.py — the plugin command that renders and
writes the `## Writing register` block of an instance's preferences, shared by
new-instance's finalize.sh and maestro-sync's register phase.

Black box through subprocess against temp preferences files. Reads the
command out of plugins/, absent from an archived instance, so this file is
export-ignored.

Run: python3 -m unittest tests.test_maestro_register_keys -v
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "plugins" / "maestro" / "bin" / "maestro-register-keys"

PREFS_WITHOUT_BLOCK = """---
setup_completed: true
---

# Preferences

## Communication preferences

- **Tone with you**: direct
- **Tone with others (when writing on your behalf)**: warmer with agency contacts
- **Things to avoid**: genuinely, leverage

---

## Notes

Free text.
"""

PREFS_BARE = PREFS_WITHOUT_BLOCK.replace("## Notes", "## Writing register\nsuspended: [4, 6]\npost_pass: off\n\n---\n\n## Notes")

PREFS_FENCED = PREFS_WITHOUT_BLOCK.replace("## Notes", """## Writing register

```yaml
suspended: []
post_pass: on
tone_default:
  communication: friendly
voice: "dry humour"
```

---

## Notes""")


def run(*args, env=None, cwd=None):
    full = {"PATH": "/usr/bin:/bin", "HOME": cwd or "/tmp"}
    full.update(env or {})
    return subprocess.run(["python3", str(TOOL), *args], capture_output=True, text=True, env=full, cwd=cwd)


class TestRender(unittest.TestCase):
    def test_defaults_carry_the_default_comment(self):
        r = run("render")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.startswith("```yaml\n"))
        self.assertIn("communication: professional", r.stdout)
        self.assertRegex(r.stdout, r"communication: professional\s+# default")
        self.assertIn("enabled: false", r.stdout)
        self.assertIn("labels: [Translation, More polished version]", r.stdout)

    def test_values_from_env_replace_defaults_without_the_comment(self):
        r = run("render", env={"MAESTRO_TONE_COMMUNICATION": "friendly", "MAESTRO_SIGN_OFF": 'Have a nice day,\n"Alex"',
                               "MAESTRO_TRANSLATION": "on", "MAESTRO_TRANSLATION_PAIR": "it -> en",
                               "MAESTRO_AVOID_WORDS": "genuinely, leverage", "MAESTRO_SUSPENDED": "4,6"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout, r"communication: friendly\s+# friendly")
        self.assertNotRegex(r.stdout, r"communication: friendly\s+# default")
        self.assertIn('sign_off: "Have a nice day,\\n\\"Alex\\""', r.stdout)
        self.assertIn("enabled: true", r.stdout)
        self.assertIn('pair: "it -> en"', r.stdout)
        self.assertIn("post_pass: on ", r.stdout)
        self.assertIn("avoid_words: [genuinely, leverage]", r.stdout)
        self.assertIn("suspended: [4, 6]", r.stdout)

    def test_invalid_tone_exits_two(self):
        r = run("render", env={"MAESTRO_TONE_COMMUNICATION": "chatty"})
        self.assertEqual(r.returncode, 2)
        self.assertIn("tone", r.stderr)

    def test_synthesis_is_always_neutral(self):
        r = run("render", env={"MAESTRO_TONE_DOCUMENTATION": "friendly"})
        self.assertIn("documentation: friendly", r.stdout)
        self.assertRegex(r.stdout, r"synthesis: neutral\s+# default; always neutral")


class TestReport(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.prefs = Path(self._tmp.name) / "preferences.md"

    def report(self, text):
        self.prefs.write_text(text)
        r = run("report", str(self.prefs))
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_absent_block_lists_every_key_and_the_hints(self):
        rep = self.report(PREFS_WITHOUT_BLOCK)
        self.assertEqual(rep["block"], "absent")
        self.assertEqual(rep["present"], [])
        self.assertIn("tone_default.communication", rep["missing"])
        self.assertEqual(rep["hints"], {"tone_default.communication": "warmer with agency contacts",
                                        "avoid_words": "genuinely, leverage"})

    def test_bare_block_keeps_its_two_keys(self):
        rep = self.report(PREFS_BARE)
        self.assertEqual(rep["block"], "bare")
        self.assertEqual(rep["present"], ["suspended", "post_pass"])

    def test_fenced_block_reports_present_and_missing(self):
        rep = self.report(PREFS_FENCED)
        self.assertEqual(rep["block"], "fenced")
        self.assertEqual(rep["present"], ["suspended", "post_pass", "tone_default.communication", "voice"])
        self.assertIn("communication.sign_off", rep["missing"])

    def test_placeholder_hints_are_ignored(self):
        text = PREFS_WITHOUT_BLOCK.replace("warmer with agency contacts", "<e.g. warmer with agency contacts>")
        self.assertNotIn("tone_default.communication", self.report(text)["hints"])

    def test_missing_file_exits_seven(self):
        r = run("report", str(self.prefs))
        self.assertEqual(r.returncode, 7)


class TestWrite(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.prefs = Path(self._tmp.name) / "preferences.md"

    def write(self, text, env=None):
        self.prefs.write_text(text)
        r = run("write", str(self.prefs), env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r, self.prefs.read_text()

    def backups(self):
        return sorted(Path(self._tmp.name).glob("preferences.md.bak.*-register"))

    def test_absent_block_is_inserted_before_notes_with_a_backup(self):
        r, out = self.write(PREFS_WITHOUT_BLOCK, env={"MAESTRO_TONE_COMMUNICATION": "formal"})
        self.assertEqual(len(self.backups()), 1)
        self.assertEqual(self.backups()[0].read_text(), PREFS_WITHOUT_BLOCK)
        self.assertIn("backup ", r.stdout)
        self.assertLess(out.index("## Writing register"), out.index("## Notes"))
        self.assertGreater(out.index("## Writing register"), out.index("## Communication preferences"))
        self.assertIn("```yaml\n", out)
        self.assertIn("communication: formal", out)
        self.assertIn("Free text.", out)
        self.assertEqual(out.count("## Notes"), 1)

    def test_bare_block_is_converted_and_its_values_kept(self):
        r, out = self.write(PREFS_BARE, env={"MAESTRO_POST_PASS": "on", "MAESTRO_SUSPENDED": "1"})
        self.assertIn("suspended: [4, 6]", out)
        self.assertIn("post_pass: off", out)
        self.assertNotIn("suspended: [1]", out)
        self.assertIn("block converted", r.stdout)
        self.assertEqual(out.count("## Writing register"), 1)
        self.assertIn("## Notes", out)

    def test_fenced_block_gains_missing_keys_only(self):
        r, out = self.write(PREFS_FENCED, env={"MAESTRO_TONE_COMMUNICATION": "formal", "MAESTRO_SIGN_OFF": "Bye,\nAlex"})
        self.assertIn("communication: friendly", out)
        self.assertNotIn("communication: formal", out)
        self.assertIn('voice: "dry humour"', out)
        self.assertIn('sign_off: "Bye,\\nAlex"', out)
        self.assertRegex(out, r"documentation: neutral\s+# default")
        self.assertIn("communication.sign_off", r.stdout)

    def test_second_write_changes_nothing_and_makes_no_backup(self):
        self.write(PREFS_WITHOUT_BLOCK)
        first = self.prefs.read_text()
        r = run("write", str(self.prefs))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("unchanged", r.stdout)
        self.assertEqual(self.prefs.read_text(), first)
        self.assertEqual(len(self.backups()), 1)

    def test_written_block_reads_back_with_the_same_values(self):
        env = {"MAESTRO_SIGN_OFF": 'Have a nice day,\n--\n"Alex"', "MAESTRO_VOICE": "warm: direct",
               "MAESTRO_TRANSLATION": "on", "MAESTRO_TRANSLATION_MARKER": "Ciao,"}
        self.write(PREFS_WITHOUT_BLOCK, env=env)
        r = run("report", str(self.prefs))
        rep = json.loads(r.stdout)
        self.assertEqual(rep["block"], "fenced")
        self.assertEqual(rep["missing"], [])
        text = self.prefs.read_text()
        self.assertIn('sign_off: "Have a nice day,\\n--\\n\\"Alex\\""', text)
        self.assertIn('voice: "warm: direct"', text)
        self.assertIn('new_context_marker: "Ciao,"', text)
        self.assertNotIn("\n--\n", text.split("```yaml")[1].split("```")[0])

    def test_a_hash_inside_a_quoted_value_survives_a_rewrite(self):
        _, out = self.write(PREFS_WITHOUT_BLOCK, env={"MAESTRO_VOICE": "dry, #1 fan of colons"})
        r = run("write", str(self.prefs), env={"MAESTRO_TONE_COMMUNICATION": "formal"})
        self.assertIn("unchanged", r.stdout)
        text = self.prefs.write_text(self.prefs.read_text().replace("avoid_words: []", "# avoid_words removed"))
        run("write", str(self.prefs))
        self.assertIn('voice: "dry, #1 fan of colons"', self.prefs.read_text())

    def test_owner_prose_and_unknown_keys_in_the_section_survive(self):
        text = PREFS_FENCED.replace("## Writing register\n", "## Writing register\n\nI keep documents cold.\n")
        text = text.replace('voice: "dry humour"', 'voice: "dry humour"\ncommunication:\n  opening: "Ciao"\nmy_custom: 3')
        text = text.replace("```\n\n---\n\n## Notes", "```\n\n### My notes on tone\n\nNever sign emails to Marco.\n\n---\n\n## Notes")
        _, out = self.write(text, env={"MAESTRO_SIGN_OFF": "Bye"})
        for kept in ("I keep documents cold.", "### My notes on tone", "Never sign emails to Marco.",
                     '  opening: "Ciao"', "my_custom: 3", 'voice: "dry humour"'):
            self.assertIn(kept, out)
        self.assertRegex(out, r"communication:\n  opening: \"Ciao\"\n  sign_off: Bye")
        self.assertEqual(out.count("```"), 2)
        self.assertEqual(json.loads(run("report", str(self.prefs)).stdout)["missing"], [])

    def test_block_scalar_sign_off_is_kept_verbatim(self):
        text = PREFS_FENCED.replace('voice: "dry humour"', 'communication:\n  sign_off: |\n    Have a nice day,\n    --\n    Ada')
        _, out = self.write(text)
        self.assertIn("  sign_off: |\n    Have a nice day,\n    --\n    Ada\n", out)
        self.assertNotIn('sign_off: "|"', out)

    def test_inserted_section_keeps_one_rule_and_a_blank_line_before_its_heading(self):
        _, out = self.write(PREFS_WITHOUT_BLOCK)
        self.assertIn("agency contacts\n- **Things to avoid**: genuinely, leverage\n\n## Writing register\n", out)
        self.assertEqual(out.count("\n---\n"), 2)
        self.assertIn("```\n\n---\n\n## Notes", out)

    def test_crlf_file_keeps_crlf(self):
        self.write(PREFS_WITHOUT_BLOCK.replace("\n", "\r\n"))
        raw = self.prefs.read_bytes().decode()
        self.assertNotIn("\n", raw.replace("\r\n", ""))
        self.assertIn("communication: professional", raw)

    def test_capitalised_or_level_three_heading_is_the_section(self):
        for heading in ("## Writing Register", "### Writing register"):
            with self.subTest(heading=heading):
                _, out = self.write(PREFS_FENCED.replace("## Writing register", heading))
                self.assertEqual(out.lower().count("writing register\n"), 1)

    def test_quoted_list_item_with_a_comma_is_read_back(self):
        self.prefs.write_text(PREFS_FENCED.replace('voice: "dry humour"', 'avoid_words: ["a, b", c]'))
        r = run("report", str(self.prefs))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("avoid_words", json.loads(r.stdout)["present"])

    def test_no_section_and_no_notes_appends_at_the_end(self):
        text = "---\nsetup_completed: true\n---\n\n# Preferences\n\n## Identity\n\n- Name: Ada\n"
        _, out = self.write(text)
        self.assertTrue(out.rstrip().endswith("```"))
        self.assertIn("- Name: Ada", out)


if __name__ == "__main__":
    unittest.main()
