"""tests/test_maestro_listen.py — the folder boundary and the lock of
`maestro-listen`.

The capture lock is machine-wide, so every Claude Code session on the machine
can reach a running capture: an instance, a satellite, any folder. These tests
pin what another folder gets back (the holder's name and start time, never the
title, the context or the transcript), how a folder is resolved (a subfolder or
a worktree of a repository is that repository's main checkout, `--project`
wins over the working directory, anything else is the folder itself), and that
a closed capture stays readable from its own folder.

No `yap` and no audio: the test writes the state file and the VTT segments,
with a detached `tail -f /dev/null` as the supervisor, so the lock reads as
live. Never the test process or one of its children: a `stop` signals the
supervisor and waits for it to disappear, and a child would linger as a zombie.

Run: python3 -m unittest tests.test_maestro_listen -v
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "plugins" / "maestro" / "bin" / "maestro-listen"
BASE_PATH = "/usr/bin:/bin"
EXIT_BUSY = 3
EXIT_NOT_RUNNING = 5
SECRET = "SECRET"


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


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
        self.state_dir = self.home / ".local" / "state" / "listen"
        self.state_file = self.state_dir / "current.json"
        out = subprocess.run(["sh", "-c", "tail -f /dev/null >/dev/null 2>&1 </dev/null & echo $!"],
                             capture_output=True, text=True, check=True)
        self.supervisor = int(out.stdout.strip())

    def tearDown(self):
        try:
            os.kill(self.supervisor, signal.SIGKILL)
        except OSError:
            pass
        self._tmp.cleanup()

    def env(self):
        return {"PATH": BASE_PATH, "HOME": str(self.home),
                "GIT_CEILING_DIRECTORIES": str(self.tmp), "GIT_CONFIG_NOSYSTEM": "1"}

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.repo), *args], check=True,
                       capture_output=True, text=True, env=self.env())

    def write_state(self, project: Path | None, segments: list | None = None, pid: int | None = None):
        state = {
            "supervisor_pid": self.supervisor if pid is None else pid,
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
            "segments": segments or [],
        }
        if project is not None:
            state["project"] = str(project)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state))

    def segment(self, index: int, offset: float, start: str, words: str) -> dict:
        path = self.state_dir / "transcripts" / f"2026-09-16-1000-call-{index:02d}.vtt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"WEBVTT\n\n{start}.000 --> {start}.900\n<v Them>{words}\n")
        return {"file": str(path), "offset": offset, "device": "mic", "pid": 0}

    def listen(self, *args, cwd: Path):
        return subprocess.run([str(SCRIPT), *args], cwd=cwd, capture_output=True,
                              text=True, env=self.env(), timeout=60)

    def payload(self, r):
        return json.loads(r.stdout)


class TestAnotherFolder(ListenCase):
    def test_start_names_the_holder_without_title_or_context(self):
        self.write_state(self.repo)
        r = self.listen("start", cwd=self.other)
        self.assertEqual(r.returncode, EXIT_BUSY, r.stderr)
        data = self.payload(r)
        held = data["already_running"]
        self.assertEqual(held["instance"], "acme")
        self.assertEqual(held["started_at"], "2026-09-16T10:00:00")
        self.assertFalse(held["same_folder"])
        self.assertEqual(data["project"], str(self.other))
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
                self.assertEqual(self.payload(r)["project"], str(self.other))
                self.assertNotIn(SECRET, r.stdout + r.stderr)
                self.assertTrue(self.state_file.exists())
                self.assertTrue(alive(self.supervisor))

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


class TestClosedCapture(ListenCase):
    def setUp(self):
        super().setUp()
        self.write_state(self.repo, segments=[
            self.segment(1, 0.0, "00:00:05", "first words"),
            self.segment(2, 100.0, "00:00:02", "after the headphones"),
        ])

    def test_text_after_stop_reads_every_segment_at_its_offset(self):
        r = self.listen("stop", cwd=self.repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(alive(self.supervisor))
        r = self.listen("text", "--raw", cwd=self.repo)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        text = self.payload(r)["text"]
        self.assertIn("[00:05] Them: first words", text)
        self.assertIn("[01:42] Them: after the headphones", text)

    def test_a_closed_capture_is_invisible_from_another_folder(self):
        self.listen("stop", cwd=self.repo)
        r = self.listen("text", "--raw", cwd=self.other)
        self.assertEqual(r.returncode, EXIT_NOT_RUNNING, r.stdout + r.stderr)
        self.assertNotIn("words", r.stdout + r.stderr)
        self.assertNotIn(SECRET, r.stdout + r.stderr)


class TestLock(ListenCase):
    def test_a_supervisor_pid_of_zero_reads_as_not_running(self):
        self.write_state(self.repo, pid=0)
        data = self.payload(self.listen("status", cwd=self.repo))
        self.assertFalse(data["running"])


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

    def test_the_project_flag_wins_over_the_working_directory(self):
        self.write_state(self.repo)
        data = self.payload(self.listen("status", "--project", str(self.repo / "src"), cwd=self.other))
        self.assertTrue(data["same_folder"])
        self.assertEqual(data["project"], str(self.repo))

    def test_an_empty_project_flag_falls_back_to_the_working_directory(self):
        data = self.payload(self.listen("status", "--project", "", cwd=self.other))
        self.assertEqual(data["project"], str(self.other))


if __name__ == "__main__":
    unittest.main()
