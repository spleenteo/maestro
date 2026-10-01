"""The plugin's satellite hooks: `hooks/satellite-hook` and `hooks/satellite-guard`.

Both run in every Claude Code session on the machine, so the tests pin two
things: outside a satellite they do nothing (no output, no env write, no
Python for the guard), and inside one they hand the session its scope, its
role and only the whitelisted part of the mother's preferences.

`TestUpdateCheck` covers the hook's other job, the update notice in an
instance root. Every hook test runs with `MAESTRO_VERSION_URL` pointing at a
`file://` URL inside the temp dir and a large `MAESTRO_UPDATE_INTERVAL`, so
no test reaches the network.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / "plugins" / "maestro" / "hooks"
HOOK = HOOKS / "satellite-hook"
GUARD = HOOKS / "satellite-guard"
SESSION = "s1"
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
        # The update check's files: the cache, and the upstream `.version` the
        # fetcher reads. The version file doesn't exist until a test writes it,
        # so a fetcher spawned by any test fails fast and writes nothing.
        self.cache = self.tmp / "cache dir" / "maestro-update-check.json"
        self.version_file = self.tmp / "upstream.version"

    def tearDown(self):
        self._tmp.cleanup()

    def add_satellite_row(self, mandate="Ship the acme app"):
        cmd = [str(self.mother / "bin" / "mem"), "satellite", "add", "acme",
               "--repo", str(self.repo), "--type", "development", "--vault", str(self.vault)]
        if mandate is not None:
            cmd += ["--mandate", mandate]
        r = subprocess.run(cmd, capture_output=True, text=True, env=self.env())
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
               "CLAUDE_PROJECT_DIR": str(self.repo),
               "MAESTRO_UPDATE_CACHE": str(self.cache),
               "MAESTRO_UPDATE_INTERVAL": "999999",
               "MAESTRO_VERSION_URL": self.version_file.as_uri()}
        env.update(extra)
        return env

    def session_start(self, cwd, **extra):
        r = subprocess.run(["python3", str(HOOK), "session-start"],
                           input=json.dumps({"cwd": str(cwd), "hook_event_name": "SessionStart",
                                             "session_id": SESSION}),
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

    def test_memory_criterion_comes_from_the_mother_with_type_examples(self):
        self.write_registry()
        self.add_satellite_row()
        (self.mother / "CLAUDE.md").write_text(
            "## Memory\n\n### Writing to the log\n\nWrite when the moon is full.\n"
            "Second line of the same paragraph.\n\nNot this paragraph.\n")
        ctx = self.context(self.session_start(self.repo))
        self.assertIn("When to write: Write when the moon is full. Second line of the same paragraph.", ctx)
        self.assertNotIn("Not this paragraph", ctx)
        self.assertIn("a merge or push to main", ctx)

    def test_memory_criterion_falls_back_without_the_section(self):
        self.write_registry()
        self.add_satellite_row()
        (self.mother / "CLAUDE.md").write_text("## Memory\n\nNothing here.\n")
        ctx = self.context(self.session_start(self.repo))
        self.assertIn("When to write: Write proactively, without being asked", ctx)

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

    def test_translate_flag_must_be_a_direct_child(self):
        self.write_registry()
        self.add_satellite_row()
        skill = self.mother / ".claude" / "skills" / "translate" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("# Translate\n")
        prefs = self.mother / "private" / "preferences.md"
        prefs.write_text(prefs.read_text().replace(
            "communication:\n  sign_off: |", "translation:\n  flags:\n    enabled: true\ncommunication:\n  sign_off: |"))
        self.assertNotIn(str(skill), self.context(self.session_start(self.repo)))

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

    def test_the_context_says_the_mandate_anchors_the_mothers_answers(self):
        self.write_registry()
        self.add_satellite_row()
        ctx = self.context(self.session_start(self.repo))
        self.assertIn("serves this satellite's mandate", ctx)
        self.assertNotIn("has no mandate", ctx)

    def test_without_a_mandate_the_context_says_the_folder_perimeter_holds(self):
        self.write_registry()
        self.add_satellite_row(mandate=None)
        ctx = self.context(self.session_start(self.repo))
        self.assertIn("has no mandate", ctx)
        self.assertNotIn("serves this satellite's mandate", ctx)

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


class TestUpdateCheck(HookCase):
    """The update notice at session start, in an instance root only. The
    mother folder of HookCase (preferences.md, bin/mem) stands in for the
    instance; its CLAUDE.md carries the local version."""

    LOCAL = "v2026.09.17.1"
    NEWER = "v2026.09.27.1"

    def setUp(self):
        super().setUp()
        (self.mother / "CLAUDE.md").write_text(
            f"---\norigin: maestro\nmaestro_version: {self.LOCAL}\ntags: [orchestrator]\n---\n\n# Orchestrator\n")

    def write_cache(self, upstream, age=timedelta(0)):
        checked_at = (datetime.now(timezone.utc).replace(microsecond=0) - age).isoformat()
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        self.cache.write_text(json.dumps({"upstream": upstream, "checked_at": checked_at}))

    def read_cache(self):
        return json.loads(self.cache.read_text())

    def fetch(self, **extra):
        """The fetcher mode, run synchronously with the same environment the hook hands it."""
        r = subprocess.run(["python3", str(HOOK), "update-fetch"], capture_output=True, text=True,
                           env=self.env(**extra), timeout=30)
        self.assertEqual((r.returncode, r.stdout), (0, ""), r.stderr)

    def test_outside_an_instance_nothing_is_printed_and_no_cache_appears(self):
        # A plain folder, no cache (stale by definition) and a zero interval:
        # only the instance gate keeps the hook from stamping and spawning.
        r = self.session_start(self.repo, MAESTRO_UPDATE_INTERVAL="0")
        self.assertEqual(r.stdout, "")
        self.assertFalse(self.cache.exists())

    def test_a_fresh_cache_at_the_same_version_prints_nothing(self):
        self.write_cache(self.LOCAL)
        before = self.cache.read_bytes()
        r = self.session_start(self.mother)
        self.assertEqual(r.stdout, "")
        self.assertEqual(self.cache.read_bytes(), before)

    def test_a_fresh_cache_with_a_newer_version_prints_the_one_line_notice(self):
        self.write_cache(self.NEWER)
        r = self.session_start(self.mother)
        self.assertEqual(r.stdout.count("\n"), 1)
        self.assertEqual(self.context(r), f"Maestro {self.NEWER} is available "
                                          f"(this instance is on {self.LOCAL}): run /maestro:maestro-sync.")

    def test_the_instance_stamp_decides_when_newer_than_claude_md(self):
        self.write_cache(self.NEWER)
        stamp = self.mother / "private" / ".version"
        stamp.write_text(self.NEWER + "\n")
        self.assertEqual(self.session_start(self.mother).stdout, "")
        stamp.write_text("garbage\n")
        self.assertIn(f"this instance is on {self.LOCAL}", self.context(self.session_start(self.mother)))

    def test_a_missing_cache_is_stamped_and_the_fetcher_writes_it_from_a_file_url(self):
        """The hook stamps `checked_at` alone (no upstream known yet) and
        spawns the fetcher detached. The fetcher is then run synchronously
        here rather than waited for: a detached process can only be observed
        by polling with sleeps, and the version file appears only after the
        hook returned, so the spawned copy either failed fast on the missing
        file or wrote, atomically, the same content the synchronous run
        asserts below."""
        start = datetime.now(timezone.utc).replace(microsecond=0)
        r = self.session_start(self.mother)
        self.assertEqual(r.stdout, "")
        stamped = self.read_cache()
        self.assertNotIn("upstream", stamped)
        self.assertGreaterEqual(datetime.fromisoformat(stamped["checked_at"]), start)
        self.version_file.write_text(f"{self.NEWER}\n")
        self.fetch()
        refreshed = self.read_cache()
        self.assertEqual(refreshed["upstream"], self.NEWER)
        self.assertGreaterEqual(datetime.fromisoformat(refreshed["checked_at"]), start)

    def test_an_unreachable_url_leaves_the_cache_untouched(self):
        # A cache older than the (large) test interval: the hook stamps `checked_at`
        # and keeps `upstream`; the fetcher, spawned and then run synchronously
        # against a refused port, writes nothing.
        start = datetime.now(timezone.utc).replace(microsecond=0)
        self.write_cache(self.LOCAL, age=timedelta(days=30))
        r = self.session_start(self.mother, MAESTRO_VERSION_URL="http://127.0.0.1:1/")
        self.assertEqual(r.stdout, "")
        stamped = self.cache.read_bytes()
        self.assertEqual(json.loads(stamped)["upstream"], self.LOCAL)
        self.assertGreaterEqual(datetime.fromisoformat(json.loads(stamped)["checked_at"]), start)
        self.fetch(MAESTRO_VERSION_URL="http://127.0.0.1:1/")
        self.assertEqual(self.cache.read_bytes(), stamped)


class TestVaultGuard(HookCase):
    def guard(self, target, path=BASE_PATH, tool="Read", **extra):
        key = "file_path" if tool == "Read" else "path"
        payload = {"tool_name": tool, "tool_input": {key: str(target), **extra}}
        return subprocess.run(["sh", str(GUARD), "pre-tool-use"],
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



class TestNudges(HookCase):
    """UserPromptSubmit and Stop, through the guard, with the session's active
    time set by writing its state file."""

    def setUp(self):
        super().setUp()
        self.write_registry()
        self.add_satellite_row()
        self.session_start(self.repo)
        self.state = self.plugin_data / "satellites" / "state" / f"{SESSION}.json"

    def set_active(self, seconds):
        state = json.loads(self.state.read_text())
        state.update(active=seconds, last=int(datetime.now(timezone.utc).timestamp()))
        self.state.write_text(json.dumps(state))

    def turn(self, mode, **payload):
        r = subprocess.run(["sh", str(GUARD), mode],
                           input=json.dumps({"session_id": SESSION, **payload}),
                           capture_output=True, text=True, env=self.env(), timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_closing_word_after_work_adds_context_and_a_long_prompt_does_not(self):
        self.set_active(700)
        self.assertEqual(self.turn("user-prompt-submit",
                                   prompt="ok, now rewrite the hero section with the copy the client sent us this morning"), "")
        out = json.loads(self.turn("user-prompt-submit", prompt="Perfetto, grazie!"))
        self.assertIn("closing signal", out["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(self.turn("user-prompt-submit", prompt="ok"), "")

    def test_stop_blocks_once_after_an_hour_without_a_memory(self):
        self.set_active(3600)
        out = json.loads(self.turn("stop"))
        self.assertEqual(out["decision"], "block")
        self.assertIn("MEM_SCOPE=acme", out["reason"])
        self.assertEqual(self.turn("stop"), "")

    def test_stop_lets_go_when_a_memory_was_saved(self):
        self.set_active(3600)
        r = subprocess.run([str(self.mother / "bin" / "mem"), "save", "Hero shipped", "-t", "acme"],
                           capture_output=True, text=True, env=self.env(MEM_SCOPE="acme"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.turn("stop"), "")
        self.assertEqual(json.loads(self.state.read_text())["active"], 0)

    def test_a_long_pause_before_a_prompt_adds_nothing(self):
        state = json.loads(self.state.read_text())
        state.update(active=3000, last=int(datetime.now(timezone.utc).timestamp()) - 7200)
        self.state.write_text(json.dumps(state))
        self.turn("user-prompt-submit", prompt="back to the form validation now")
        self.assertEqual(json.loads(self.state.read_text())["active"], 3000)

    def test_stop_never_blocks_a_stop_it_already_blocked(self):
        self.set_active(3600)
        self.assertEqual(self.turn("stop", stop_hook_active=True), "")


if __name__ == "__main__":
    unittest.main()
