"""tests/test_finalize.py — `finalize.sh`, moved from `.claude/skills/setup/`
into the plugin at `plugins/maestro/skills/new-instance/` (V4 plan, Task 3).

Two behaviour changes exercised here:
- Step 6 (moving the skill into `.claude/skills/.disabled/`) is gone: the
  interview skill lives in the plugin now, never in the instance's own
  `.claude/skills/`, so there is nothing left to self-disable.
- The first memory row is written through the instance's own `bin/mem save`
  instead of a raw `sqlite3 INSERT INTO log`, and the script refuses to run
  a second time — both when `private/preferences.md` already exists (the
  original refusal) and, new here, when `private/memories.db` already
  exists.

Builds a temp instance skeleton with `git archive HEAD` from a throwaway
local clone of the *committed* branch — never the working tree's
uncommitted state, never the network — the same pattern as
test_template_archive.py. `finalize.sh` itself is read from that same
clone's committed `plugins/maestro/skills/new-instance/finalize.sh`, so a
GREEN run needs the move and the script fix committed first.

`plugins/` is `export-ignore`d (see `.gitattributes`) — this file needs the
template's own `.git` to clone from and a `plugins/` tree to read
`finalize.sh` out of, neither of which an archived instance ever has, so
this file is `export-ignore`d too.

Every subprocess runs under an explicit, minimal `PATH` — never the
inherited one — and one run additionally sets `MEM_DB`/`MEM_SCOPE` to decoy
values to prove `finalize.sh`'s `env -u MEM_DB -u MEM_SCOPE` actually
strips them before calling `bin/mem`.

Run: python3 -m unittest tests.test_finalize -v
"""

from __future__ import annotations

import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

REQUIRED_VARS = (
    "MAESTRO_LANGUAGE",
    "MAESTRO_PROJECT_NAME",
    "MAESTRO_PROJECT_SLUG",
    "MAESTRO_ORCHESTRATOR_NAME",
    "MAESTRO_OWNER_NICK",
    "MAESTRO_OWNER_FULL_NAME",
    "MAESTRO_OWNER_ROLE",
    "MAESTRO_CONTEXT",
)

REQUIRED_ENV = {
    "MAESTRO_LANGUAGE": "english",
    "MAESTRO_PROJECT_NAME": "Acme partnership",
    "MAESTRO_PROJECT_SLUG": "acme-partnership",
    "MAESTRO_ORCHESTRATOR_NAME": "Jarvis",
    "MAESTRO_OWNER_NICK": "Jane",
    "MAESTRO_OWNER_FULL_NAME": "Jane Doe",
    "MAESTRO_OWNER_ROLE": "Partnership Manager",
    "MAESTRO_CONTEXT": "Work: manage partner relationships across time zones.",
}

TEMPLATE_ROOT_FILES = (
    "memories.db.template",
    "preferences.example.md",
    "routines.example.yaml",
)


def _tool_dir(name: str) -> str:
    """Directory holding `name`, for a `PATH` that never inherits the
    caller's — only /usr/bin:/bin plus whatever a tool needs beyond that."""
    found = shutil.which(name)
    if found is None:
        raise RuntimeError(f"{name} not found on this machine")
    return str(Path(found).resolve().parent)


def _base_path() -> str:
    dirs = ["/usr/bin", "/bin"]
    for tool in ("sqlite3", "python3", "git", "tar"):
        d = _tool_dir(tool)
        if d not in dirs:
            dirs.append(d)
    return ":".join(dirs)


BASE_PATH = _base_path()


class TestFinalize(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="maestro-finalize-test-")
        cls.clone = os.path.join(cls.tmp, "clone")
        subprocess.run(
            ["git", "clone", "--quiet", str(REPO), cls.clone],
            check=True, env=cls._git_env(),
        )
        cls.script = (
            Path(cls.clone) / "plugins" / "maestro" / "skills" / "new-instance" / "finalize.sh"
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @staticmethod
    def _git_env() -> dict:
        env = {"PATH": BASE_PATH}
        home = os.environ.get("HOME")
        if home:
            env["HOME"] = home
        return env

    # -- fixtures ------------------------------------------------------

    def _fresh_instance(self) -> Path:
        """A new instance skeleton, archived from the clone's committed
        HEAD, in its own throwaway directory."""
        out = Path(tempfile.mkdtemp(prefix="maestro-instance-", dir=self.tmp))
        archive = subprocess.run(
            ["git", "-C", self.clone, "archive", "HEAD"],
            stdout=subprocess.PIPE, check=True, env=self._git_env(),
        )
        subprocess.run(
            ["tar", "-x", "-C", str(out)], input=archive.stdout,
            check=True, env=self._git_env(),
        )
        return out

    def _decoy_db(self) -> Path:
        """A real, readable memories.db in a path outside the instance —
        `env -u MEM_DB` must keep finalize.sh from ever opening it."""
        decoy = Path(tempfile.mkdtemp(prefix="maestro-decoy-", dir=self.tmp)) / "decoy.db"
        shutil.copyfile(REPO / "memories.db.template", decoy)
        return decoy

    def _env(self, *, decoy_db: Path | None = None, **overrides) -> dict:
        env = {"PATH": BASE_PATH}
        home = os.environ.get("HOME")
        if home:
            env["HOME"] = home
        env.update(REQUIRED_ENV)
        if decoy_db is not None:
            env["MEM_DB"] = str(decoy_db)
            env["MEM_SCOPE"] = "decoy"
        env.update(overrides)
        return env

    def _run(self, instance: Path, env: dict) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["/bin/bash", str(self.script)], cwd=str(instance), env=env,
            capture_output=True, text=True,
        )

    # -- tests -----------------------------------------------------------

    def test_finalizes_a_fresh_instance_and_leaves_the_decoy_db_untouched(self):
        instance = self._fresh_instance()
        decoy = self._decoy_db()
        env = self._env(decoy_db=decoy)

        r = self._run(instance, env)
        self.assertEqual(r.returncode, 0, r.stderr)

        prefs = (instance / "private" / "preferences.md").read_text()
        self.assertIn("setup_completed: true", prefs)

        db = instance / "private" / "memories.db"
        self.assertTrue(db.exists())
        con = sqlite3.connect(str(db))
        try:
            cols = {row[1] for row in con.execute("PRAGMA table_info(log)")}
            self.assertIn("scope", cols)
            rows = con.execute("SELECT title, tags, scope FROM log").fetchall()
        finally:
            con.close()
        self.assertEqual(len(rows), 1, rows)
        title, tags, scope = rows[0]
        self.assertEqual(title, "Orchestrator setup completed")
        self.assertEqual(tags, "setup,bootstrap,meta")
        self.assertIsNone(scope)

        self.assertTrue((instance / "private" / "routines.yaml").exists())

        for name in TEMPLATE_ROOT_FILES:
            self.assertFalse((instance / name).exists(), name)

        self.assertFalse((instance / ".claude" / "skills" / ".disabled").exists())

        self.assertRegex(r.stdout, r"OK: first memory logged \(id=\d+\)")

        # The decoy carries its own template's empty log — MEM_DB/MEM_SCOPE
        # from the caller's environment must never reach bin/mem.
        decoy_con = sqlite3.connect(str(decoy))
        try:
            decoy_rows = decoy_con.execute("SELECT COUNT(*) FROM log").fetchone()[0]
        finally:
            decoy_con.close()
        self.assertEqual(decoy_rows, 0)

    def test_writes_the_register_block_from_answers_and_defaults(self):
        instance = self._fresh_instance()
        r = self._run(instance, self._env(MAESTRO_TONE_COMMUNICATION="friendly",
                                          MAESTRO_SIGN_OFF='Have a nice day,\n"Jane"'))
        self.assertEqual(r.returncode, 0, r.stderr)
        prefs = (instance / "private" / "preferences.md").read_text()
        self.assertIn("## Writing register", prefs)
        self.assertLess(prefs.index("## Writing register"), prefs.index("## Notes"))
        self.assertIn("```yaml\n", prefs)
        self.assertIn("communication: friendly", prefs)
        self.assertIn('sign_off: "Have a nice day,\\n\\"Jane\\""', prefs)
        self.assertRegex(prefs, r"documentation: neutral\s+# default")
        self.assertIn("enabled: false", prefs)

    def test_invalid_tone_exits_before_writing(self):
        instance = self._fresh_instance()
        r = self._run(instance, self._env(MAESTRO_TONE_COMMUNICATION="chatty"))
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((instance / "private" / "preferences.md").exists())

    def test_second_run_refuses_and_changes_nothing(self):
        instance = self._fresh_instance()
        env = self._env(decoy_db=self._decoy_db())

        r1 = self._run(instance, env)
        self.assertEqual(r1.returncode, 0, r1.stderr)

        prefs_before = (instance / "private" / "preferences.md").read_text()
        db_before = (instance / "private" / "memories.db").read_bytes()

        r2 = self._run(instance, env)
        self.assertNotEqual(r2.returncode, 0)
        self.assertIn("preferences.md", r2.stderr)

        self.assertEqual((instance / "private" / "preferences.md").read_text(), prefs_before)
        self.assertEqual((instance / "private" / "memories.db").read_bytes(), db_before)

    def test_refuses_when_memories_db_already_exists(self):
        instance = self._fresh_instance()
        (instance / "private").mkdir(parents=True, exist_ok=True)
        sentinel = b"not a real memories.db"
        (instance / "private" / "memories.db").write_bytes(sentinel)
        env = self._env(decoy_db=self._decoy_db())

        r = self._run(instance, env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("memories.db", r.stderr)

        self.assertFalse((instance / "private" / "preferences.md").exists())
        self.assertEqual((instance / "private" / "memories.db").read_bytes(), sentinel)

    def test_missing_required_var_exits_before_writing(self):
        for missing in REQUIRED_VARS:
            with self.subTest(missing=missing):
                instance = self._fresh_instance()
                env = self._env(decoy_db=self._decoy_db())
                del env[missing]

                r = self._run(instance, env)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn(missing, r.stderr)

                self.assertFalse((instance / "private" / "preferences.md").exists())
                self.assertFalse((instance / "private" / "memories.db").exists())


if __name__ == "__main__":
    unittest.main()
