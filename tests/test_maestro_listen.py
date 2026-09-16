"""tests/test_maestro_listen.py — the folder boundary of `maestro-listen`.

The capture lock is machine-wide, so every Claude Code session on the machine
can reach a running capture: an instance, a satellite, any folder. These tests
pin what another folder gets back (the holder's name and start time, never the
title, the context or the transcript) and how a folder is resolved: a subfolder
or a worktree of a repository is that repository's main checkout, anything
else is the folder itself.

No `yap` and no audio: the test writes the state file, with a throwaway `cat`
process as the supervisor, so the lock reads as live. Never the test process
itself: a `stop` that crossed the boundary would signal it.

Run: python3 -m unittest tests.test_maestro_listen -v
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "plugins" / "maestro" / "bin" / "maestro-listen"
BASE_PATH = "/usr/bin:/bin"
EXIT_BUSY = 3
SECRET = "SECRET"


class ListenCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(os.path.realpath(self._tmp.name))
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.repo = self.tmp / "acme"
        (self.repo / "src").mkdir(parents=True)
        self.git("init", "-q")
        self.other = self.tmp / "elsewhere"
        self.other.mkdir()
        self.state_file = self.home / ".local" / "state" / "listen" / "current.json"
        self.supervisor = subprocess.Popen(["cat"], stdin=subprocess.PIPE,
                                           stdout=subprocess.DEVNULL)

    def tearDown(self):
        if self.supervisor.poll() is None:
            self.supervisor.kill()
        self.supervisor.wait()
        self.supervisor.stdin.close()
        self._tmp.cleanup()

    def env(self):
        return {"PATH": BASE_PATH, "HOME": str(self.home)}

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.repo), *args], check=True,
                       capture_output=True, text=True, env=self.env())

    def write_state(self, project: Path | None):
        state = {
            "supervisor_pid": self.supervisor.pid,
            "started_at": "2026-09-16T10:00:00",
            "stem": "2026-09-16-1000-call",
            "locale": "en-US",
            "mic_label": "Me",
            "system_label": "Them",
            "them_only": False,
            "max_length": 200,
            "title": f"{SECRET} title",
            "context": f"{SECRET} context",
            "instance": "acme",
            "rotation": "on",
            "segments": [],
        }
        if project is not None:
            state["project"] = str(project)
        self.state_file.parent.mkdir(parents=True)
        self.state_file.write_text(json.dumps(state))

    def listen(self, *args, cwd: Path):
        return subprocess.run([str(SCRIPT), *args], cwd=cwd, capture_output=True,
                              text=True, env=self.env(), timeout=30)

    def payload(self, r):
        return json.loads(r.stdout)


class TestAnotherFolder(ListenCase):
    def test_start_names_the_holder_without_title_or_context(self):
        self.write_state(self.repo)
        r = self.listen("start", cwd=self.other)
        self.assertEqual(r.returncode, EXIT_BUSY, r.stderr)
        held = self.payload(r)["already_running"]
        self.assertEqual(held["instance"], "acme")
        self.assertEqual(held["started_at"], "2026-09-16T10:00:00")
        self.assertFalse(held["same_folder"])
        self.assertNotIn(SECRET, r.stdout + r.stderr)

    def test_status_hides_context_and_last_line(self):
        self.write_state(self.repo)
        r = self.listen("status", cwd=self.other)
        self.assertEqual(r.returncode, 0, r.stderr)
        data = self.payload(r)
        self.assertTrue(data["running"])
        self.assertFalse(data["same_folder"])
        self.assertNotIn("last_text", data)
        self.assertNotIn(SECRET, r.stdout + r.stderr)

    def test_text_stop_and_updates_are_refused_and_the_capture_survives(self):
        self.write_state(self.repo)
        for args in (("text",), ("stop",), ("updates", "1")):
            with self.subTest(args=args):
                r = self.listen(*args, cwd=self.other)
                self.assertEqual(r.returncode, EXIT_BUSY, r.stdout + r.stderr)
                self.assertNotIn(SECRET, r.stdout + r.stderr)
                self.assertTrue(self.state_file.exists())
                self.assertIsNone(self.supervisor.poll())

    def test_a_state_without_project_counts_as_another_folder(self):
        self.write_state(None)
        r = self.listen("status", cwd=self.repo)
        self.assertFalse(self.payload(r)["same_folder"])
        self.assertNotIn(SECRET, r.stdout)


class TestSameFolder(ListenCase):
    def test_a_subfolder_of_the_repo_gets_the_full_refusal(self):
        self.write_state(self.repo)
        r = self.listen("start", cwd=self.repo / "src")
        self.assertEqual(r.returncode, EXIT_BUSY, r.stderr)
        held = self.payload(r)["already_running"]
        self.assertTrue(held["same_folder"])
        self.assertEqual(held["context"], f"{SECRET} context")

    def test_status_carries_the_context(self):
        self.write_state(self.repo)
        data = self.payload(self.listen("status", cwd=self.repo))
        self.assertTrue(data["same_folder"])
        self.assertEqual(data["context"], f"{SECRET} context")


class TestProjectResolution(ListenCase):
    def test_nothing_running_reports_the_repo_from_a_subfolder(self):
        data = self.payload(self.listen("status", cwd=self.repo / "src"))
        self.assertFalse(data["running"])
        self.assertEqual(data["project"], str(self.repo))

    def test_a_worktree_resolves_to_the_main_checkout(self):
        self.git("-c", "user.name=t", "-c", "user.email=t@example.com",
                 "commit", "-q", "--allow-empty", "-m", "init")
        worktree = self.repo / ".claude" / "worktrees" / "w"
        self.git("worktree", "add", "-q", str(worktree))
        data = self.payload(self.listen("status", cwd=worktree))
        self.assertEqual(data["project"], str(self.repo))

    def test_a_plain_folder_is_itself(self):
        data = self.payload(self.listen("status", cwd=self.other))
        self.assertEqual(data["project"], str(self.other))


if __name__ == "__main__":
    unittest.main()
