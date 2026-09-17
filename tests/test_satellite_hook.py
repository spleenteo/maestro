"""The plugin's satellite hooks: `hooks/satellite-hook` and `hooks/vault-guard`.

Both run in every Claude Code session on the machine, so the tests pin two
things: outside a satellite they do nothing (no output, no env write, no
Python for the guard), and inside one they hand the session its scope, its
role and only the whitelisted part of the mother's preferences.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / "plugins" / "maestro" / "hooks"
HOOK = HOOKS / "satellite-hook"
GUARD = HOOKS / "vault-guard"
BASE_PATH = "/usr/bin:/bin"

PREFERENCES = """---
setup_completed: true
---

# Preferences

## Identity (the orchestrator)

- Name: Ada

## Owner — basics

- Nick: you

## People

- A private contact that must not leave the mother

## Communication preferences

- Short answers

## Notes

```
## Identity
- LEAK inside a fence
```

- LEAK after the fence

## Identity theft notes

- LEAK prefix match

## Owner — basics (private)

- Kept: a parenthetical suffix is allowed
   ## LEAK indented heading closes the section
- LEAK under the indented heading

## Writing register

```yaml
tone_default:
  communication: friendly
communication:
  sign_off: |
    Have a nice day,
    --
    Ada
```

Setext heading LEAK
-------------------

- LEAK under the setext heading
"""


class HookCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(os.path.realpath(self._tmp.name))
        self.mother = self.tmp / "home"
        (self.mother / "bin").mkdir(parents=True)
        (self.mother / "private").mkdir()
        for name in ("mem", "mem_schema.py"):
            shutil.copy2(ROOT / "bin" / name, self.mother / "bin" / name)
        shutil.copy2(ROOT / "memories.db.template", self.mother / "private" / "memories.db")
        (self.mother / "private" / "preferences.md").write_text(PREFERENCES)
        self.repo = self.tmp / "acme"
        (self.repo / "src").mkdir(parents=True)
        self.vault = self.tmp / "vault" / "acme"
        self.vault.mkdir(parents=True)
        self.registry = self.tmp / "maestro-instances.yaml"
        self.plugin_data = self.tmp / "plugin-data"
        self.env_file = self.tmp / "env"
        self.env_file.write_text("")

    def tearDown(self):
        self._tmp.cleanup()

    def add_satellite_row(self):
        r = subprocess.run(
            [str(self.mother / "bin" / "mem"), "satellite", "add", "acme",
             "--repo", str(self.repo), "--type", "development",
             "--mandate", "Ship the acme app", "--vault", str(self.vault)],
            capture_output=True, text=True, env=self.env())
        self.assertEqual(r.returncode, 0, r.stderr)

    def write_registry(self, satellites=True, accepts="recap, ask"):
        text = f"version: 1\ninstances:\n  home:\n    path: {self.mother}\n    accepts: [{accepts}]\n"
        if satellites:
            text += f"satellites:\n  acme:\n    repo: {self.repo}\n    mother: home\n"
        self.registry.write_text(text)

    def env(self, **extra):
        env = {"PATH": BASE_PATH, "HOME": str(self.tmp),
               "MAESTRO_INSTANCES": str(self.registry),
               "CLAUDE_PLUGIN_DATA": str(self.plugin_data),
               "CLAUDE_ENV_FILE": str(self.env_file),
               "CLAUDE_PROJECT_DIR": str(self.repo)}
        env.update(extra)
        return env

    def session_start(self, cwd, **extra):
        r = subprocess.run(["python3", str(HOOK), "session-start"],
                           input=json.dumps({"cwd": str(cwd), "hook_event_name": "SessionStart"}),
                           capture_output=True, text=True, env=self.env(**extra), timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def context(self, r):
        return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]

    def marker(self):
        return self.plugin_data / "satellites" / str(self.repo).replace("%", "%25").replace("/", "%2F")


class TestSessionStart(HookCase):
    def test_no_registry_is_silent(self):
        r = self.session_start(self.repo)
        self.assertEqual(r.stdout, "")
        self.assertEqual(self.env_file.read_text(), "")

    def test_folder_outside_every_satellite_is_silent_and_drops_a_stale_marker(self):
        self.write_registry()
        self.marker().parent.mkdir(parents=True)
        self.marker().write_text("{}")
        other = self.tmp / "other"
        other.mkdir()
        r = self.session_start(other, CLAUDE_PROJECT_DIR=str(self.repo))
        self.assertEqual(r.stdout, "")
        self.assertEqual(self.env_file.read_text(), "")
        self.assertFalse(self.marker().exists())

    def test_subfolder_gets_scope_role_and_whitelisted_identity(self):
        self.write_registry()
        self.add_satellite_row()
        r = self.session_start(self.repo / "src")
        self.assertEqual(self.env_file.read_text(), "export MEM_SCOPE=acme\n")
        ctx = self.context(r)
        self.assertIn("Ship the acme app", ctx)
        self.assertIn("Name: Ada", ctx)
        self.assertIn("Short answers", ctx)
        self.assertIn(str(self.mother / "bin" / "mem"), ctx)
        self.assertIn(f'`"{self.mother / "bin" / "register-check"}" <file>`', ctx)
        self.assertNotIn("private contact", ctx)
        self.assertNotIn("LEAK", ctx)
        self.assertIn("Kept: a parenthetical suffix is allowed", ctx)
        self.assertIn(f'MEM_SCOPE=acme "{self.mother / "bin" / "mem"}"', ctx)
        self.assertEqual(json.loads(self.marker().read_text())["vault"], str(self.vault))
        self.assertNotIn("maestro-net request", ctx)
        self.assertIn("/maestro:listen", ctx)

    def test_identity_extract_keeps_a_fenced_register_block(self):
        self.write_registry()
        self.add_satellite_row()
        ctx = self.context(self.session_start(self.repo))
        self.assertIn("    --\n    Ada", ctx)
        self.assertIn("communication: friendly", ctx)
        self.assertNotIn("LEAK", ctx)

    def test_translate_pointer_needs_the_skill_and_the_flag(self):
        self.write_registry()
        self.add_satellite_row()
        skill = self.mother / ".claude" / "skills" / "translate" / "SKILL.md"
        self.assertNotIn("translate", self.context(self.session_start(self.repo)))
        skill.parent.mkdir(parents=True)
        skill.write_text("# Translate\n")
        self.assertNotIn(str(skill), self.context(self.session_start(self.repo)))
        prefs = self.mother / "private" / "preferences.md"
        prefs.write_text(prefs.read_text().replace(
            "communication:\n  sign_off: |", "translation:\n  enabled: true\n  pair: it -> en\ncommunication:\n  sign_off: |"))
        ctx = self.context(self.session_start(self.repo))
        self.assertIn(f"read `{skill}`", ctx)
        self.assertIn("pair: it -> en", ctx)

    def test_register_skill_pointer_only_when_the_mother_has_the_skill(self):
        self.write_registry()
        self.add_satellite_row()
        skill = self.mother / ".claude" / "skills" / "writing-register" / "SKILL.md"
        self.assertNotIn(str(skill), self.context(self.session_start(self.repo)))
        skill.parent.mkdir(parents=True)
        skill.write_text("# Writing register\n")
        ctx = self.context(self.session_start(self.repo))
        self.assertIn(f"read `{skill}`", ctx)

    def test_plugin_skills_line_stays_when_request_is_granted(self):
        self.write_registry(accepts="recap, ask, request")
        self.add_satellite_row()
        ctx = self.context(self.session_start(self.repo))
        self.assertIn("maestro-net request", ctx)
        self.assertIn("/maestro:listen", ctx)

    def test_without_env_file_the_context_says_scope_is_not_exported(self):
        self.write_registry()
        self.add_satellite_row()
        env = self.env()
        del env["CLAUDE_ENV_FILE"]
        r = subprocess.run(["python3", str(HOOK), "session-start"], input=json.dumps({"cwd": str(self.repo)}),
                           capture_output=True, text=True, env=env, timeout=30)
        ctx = self.context(r)
        self.assertIn("not exported", ctx)
        self.assertNotIn("is also exported", ctx)

    def test_instance_inside_a_satellite_repo_stays_silent(self):
        inner = self.repo / "tools" / "inner"
        inner.mkdir(parents=True)
        self.write_registry()
        self.registry.write_text(self.registry.read_text().replace(
            "satellites:", f"  inner:\n    path: {inner}\n    accepts: [recap]\nsatellites:"))
        self.add_satellite_row()
        r = self.session_start(inner)
        self.assertEqual(r.stdout, "")
        self.assertEqual(self.env_file.read_text(), "")

    def test_symlinked_repo_path_matches(self):
        self.write_registry()
        self.add_satellite_row()
        link = self.tmp / "link-to-acme"
        link.symlink_to(self.repo)
        r = self.session_start(link / "src")
        self.assertIn("Satellite session: acme", self.context(r))

    def test_old_mother_warns_sets_nothing_and_drops_the_marker(self):
        self.write_registry()
        self.marker().parent.mkdir(parents=True)
        self.marker().write_text("{}")
        schema = self.mother / "bin" / "mem_schema.py"
        schema.write_text("SCHEMA_API = 1\n")
        r = self.session_start(self.repo)
        self.assertIn("too old", self.context(r))
        self.assertEqual(self.env_file.read_text(), "")
        self.assertFalse(self.marker().exists())


class TestVaultGuard(HookCase):
    def guard(self, target, path=BASE_PATH, tool="Read", **extra):
        key = "file_path" if tool == "Read" else "path"
        payload = {"tool_name": tool, "tool_input": {key: str(target), **extra}}
        return subprocess.run(["sh", str(GUARD)],
                              input=json.dumps(payload),
                              capture_output=True, text=True, env=self.env(PATH=path), timeout=30)

    def test_without_marker_runs_no_python(self):
        stub = self.tmp / "stub"
        stub.mkdir()
        sentinel = self.tmp / "python-ran"
        (stub / "python3").write_text(f"#!/bin/sh\ntouch {sentinel}\n")
        (stub / "python3").chmod(0o755)
        r = self.guard(self.vault / "note.md", path=f"{stub}:{BASE_PATH}")
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertFalse(sentinel.exists())

    def test_allows_inside_the_vault_only(self):
        self.write_registry()
        self.add_satellite_row()
        self.session_start(self.repo)
        inside = json.loads(self.guard(self.vault / "notes" / "a.md").stdout)
        self.assertEqual(inside["hookSpecificOutput"]["permissionDecision"], "allow")
        for outside in (self.tmp / "vault" / "other.md", self.vault / ".." / "other.md",
                        Path(str(self.vault) + "-evil") / "a.md"):
            r = self.guard(outside)
            self.assertEqual((r.returncode, r.stdout), (0, ""), outside)
        r = self.guard(self.vault, tool="Glob", pattern="../../**")
        self.assertEqual(r.stdout, "")


if __name__ == "__main__":
    unittest.main()
