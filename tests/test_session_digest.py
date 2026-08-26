"""Tests for bin/session-digest — stdlib only, no network, no real transcripts."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "bin" / "session-digest"

WORK_DIR = "/tmp/maestro-test-project"


def human(text, ts, sidechain=False):
    return {
        "type": "user",
        "isSidechain": sidechain,
        "origin": {"kind": "human"},
        "timestamp": ts,
        "cwd": WORK_DIR,
        "message": {"content": text},
    }


def tool_result(ts):
    return {
        "type": "user",
        "isSidechain": False,
        "timestamp": ts,
        "cwd": WORK_DIR,
        "message": {"content": [{"type": "tool_result", "content": "ok"}]},
    }


def assistant(ts):
    return {"type": "assistant", "timestamp": ts, "message": {"content": "risposta lunga"}}


class DigestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # slug della cwd, come lo costruisce Claude Code
        self.project = self.root / "-tmp-maestro-test-project"
        self.project.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def write_session(self, session_id, records):
        path = self.project / f"{session_id}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return path

    def run_digest(self, *args, expect_code=0):
        env = dict(os.environ, CLAUDE_PROJECTS_ROOT=str(self.root), TZ="UTC")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--cwd", WORK_DIR, *args],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(proc.returncode, expect_code, proc.stderr)
        return proc.stdout

    def json_digest(self, *args):
        return json.loads(self.run_digest("--json", *args))


class TestExtraction(DigestCase):
    def test_keeps_only_human_messages(self):
        self.write_session("aaaa1111-0000-0000-0000-000000000000", [
            {"type": "custom-title", "customTitle": "bicicletta"},
            human("prima domanda", "2026-08-25T08:00:00.000Z"),
            tool_result("2026-08-25T08:00:05.000Z"),
            assistant("2026-08-25T08:00:10.000Z"),
            human("seconda domanda", "2026-08-25T09:30:00.000Z"),
        ])
        data = self.json_digest("--date", "2026-08-25")
        self.assertEqual(len(data["sessions"]), 1)
        session = data["sessions"][0]
        self.assertEqual(session["name"], "bicicletta")
        self.assertEqual(session["count"], 2)
        self.assertEqual([m["text"] for m in session["messages"]],
                         ["prima domanda", "seconda domanda"])

    def test_skips_sidechain_subagent_messages(self):
        self.write_session("bbbb2222-0000-0000-0000-000000000000", [
            human("dell'owner", "2026-08-25T08:00:00.000Z"),
            human("di un subagente", "2026-08-25T08:01:00.000Z", sidechain=True),
        ])
        session = self.json_digest("--date", "2026-08-25")["sessions"][0]
        self.assertEqual(session["count"], 1)

    def test_skips_harness_noise(self):
        self.write_session("cccc3333-0000-0000-0000-000000000000", [
            human("<local-command-caveat>Caveat: ...</local-command-caveat>", "2026-08-25T08:00:00.000Z"),
            human("<system-reminder>ricorda</system-reminder>", "2026-08-25T08:01:00.000Z"),
            human('The user named this session "x".', "2026-08-25T08:02:00.000Z"),
            human("messaggio vero", "2026-08-25T08:03:00.000Z"),
        ])
        session = self.json_digest("--date", "2026-08-25")["sessions"][0]
        self.assertEqual([m["text"] for m in session["messages"]], ["messaggio vero"])

    def test_falls_back_to_ai_title(self):
        self.write_session("dddd4444-0000-0000-0000-000000000000", [
            {"type": "ai-title", "aiTitle": "Ruota della graziella"},
            human("ciao", "2026-08-25T08:00:00.000Z"),
        ])
        session = self.json_digest("--date", "2026-08-25")["sessions"][0]
        self.assertIsNone(session["name"])
        self.assertEqual(session["ai_title"], "Ruota della graziella")

    def test_last_custom_title_wins_after_rename(self):
        self.write_session("eeee5555-0000-0000-0000-000000000000", [
            {"type": "custom-title", "customTitle": "primo-nome"},
            human("ciao", "2026-08-25T08:00:00.000Z"),
            {"type": "custom-title", "customTitle": "secondo-nome"},
        ])
        session = self.json_digest("--date", "2026-08-25")["sessions"][0]
        self.assertEqual(session["name"], "secondo-nome")

    def test_truncates_long_messages(self):
        self.write_session("ffff6666-0000-0000-0000-000000000000", [
            human("x" * 500, "2026-08-25T08:00:00.000Z"),
        ])
        session = self.json_digest("--date", "2026-08-25", "--max-chars", "100")["sessions"][0]
        self.assertTrue(session["messages"][0]["text"].endswith("[…]"))
        self.assertLess(len(session["messages"][0]["text"]), 120)

    def test_survives_malformed_lines(self):
        path = self.project / "9999aaaa-0000-0000-0000-000000000000.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            fh.write("non è json\n")
            fh.write("\n")
            fh.write(json.dumps(human("sopravvissuto", "2026-08-25T08:00:00.000Z")) + "\n")
        session = self.json_digest("--date", "2026-08-25")["sessions"][0]
        self.assertEqual(session["messages"][0]["text"], "sopravvissuto")


class TestDayBoundary(DigestCase):
    def setUp(self):
        super().setUp()
        self.write_session("aaaa1111-0000-0000-0000-000000000000", [
            human("del 24", "2026-08-24T10:00:00.000Z"),
            human("del 25 mattina", "2026-08-25T08:00:00.000Z"),
            human("del 25 sera", "2026-08-25T20:00:00.000Z"),
        ])

    def test_filters_by_day_not_by_file(self):
        session = self.json_digest("--date", "2026-08-25")["sessions"][0]
        self.assertEqual([m["text"] for m in session["messages"]],
                         ["del 25 mattina", "del 25 sera"])

    def test_empty_day_is_not_an_error(self):
        data = self.json_digest("--date", "2026-08-23")
        self.assertEqual(data["sessions"], [])

    def test_relative_dates_resolve(self):
        for spec in ("today", "oggi", "yesterday", "ieri", "3d"):
            self.json_digest("--date", spec)
        self.json_digest("--date=-3d")

    def test_bad_date_is_rejected(self):
        self.run_digest("--date", "25 agosto", expect_code=1)


class TestShadowSessions(DigestCase):
    def setUp(self):
        super().setUp()
        # il transcript "ombra" del parent conserva solo il primo messaggio
        self.write_session("aaaa1111-0000-0000-0000-000000000000", [
            {"type": "ai-title", "aiTitle": "Stesso filo"},
            human("apertura", "2026-08-25T08:00:00.000Z"),
        ])
        self.write_session("bbbb2222-0000-0000-0000-000000000000", [
            {"type": "ai-title", "aiTitle": "Stesso filo"},
            human("apertura", "2026-08-25T08:00:00.000Z"),
            human("seguito", "2026-08-25T08:10:00.000Z"),
        ])

    def test_shadow_transcript_is_dropped(self):
        data = self.json_digest("--date", "2026-08-25")
        self.assertEqual(len(data["sessions"]), 1)
        self.assertEqual(data["sessions"][0]["count"], 2)

    def test_no_dedup_keeps_both(self):
        data = self.json_digest("--date", "2026-08-25", "--no-dedup")
        self.assertEqual(len(data["sessions"]), 2)

    def test_identical_sessions_are_both_kept(self):
        # sottoinsieme stretto, non uguaglianza: due sessioni identiche restano due
        self.write_session("cccc3333-0000-0000-0000-000000000000", [
            human("apertura", "2026-08-25T08:00:00.000Z"),
            human("seguito", "2026-08-25T08:10:00.000Z"),
        ])
        data = self.json_digest("--date", "2026-08-25")
        self.assertEqual(len(data["sessions"]), 2)


class TestSelection(DigestCase):
    def setUp(self):
        super().setUp()
        self.write_session("aaaa1111-0000-0000-0000-000000000000", [
            {"type": "custom-title", "customTitle": "bicicletta"},
            human("della bici", "2026-08-25T08:00:00.000Z"),
        ])
        self.write_session("bbbb2222-0000-0000-0000-000000000000", [
            {"type": "custom-title", "customTitle": "piscina"},
            human("della piscina", "2026-08-25T09:00:00.000Z"),
        ])

    def test_sessions_are_sorted_by_first_message(self):
        data = self.json_digest("--date", "2026-08-25")
        self.assertEqual([s["name"] for s in data["sessions"]], ["bicicletta", "piscina"])

    def test_filter_by_name(self):
        data = self.json_digest("--date", "2026-08-25", "--session", "pisc")
        self.assertEqual([s["name"] for s in data["sessions"]], ["piscina"])

    def test_filter_by_session_id_prefix(self):
        data = self.json_digest("--date", "2026-08-25", "--session", "aaaa1111")
        self.assertEqual([s["name"] for s in data["sessions"]], ["bicicletta"])

    def test_exclude_session(self):
        data = self.json_digest("--date", "2026-08-25", "--exclude-session", "aaaa1111")
        self.assertEqual([s["name"] for s in data["sessions"]], ["piscina"])


class TestCli(DigestCase):
    def test_text_output_carries_names_and_times(self):
        self.write_session("aaaa1111-0000-0000-0000-000000000000", [
            {"type": "custom-title", "customTitle": "bicicletta"},
            human("la ruota è sbagliata", "2026-08-25T08:00:00.000Z"),
        ])
        out = self.run_digest("--date", "2026-08-25")
        self.assertIn("bicicletta", out)
        self.assertIn("aaaa1111", out)
        self.assertIn("08:00", out)
        self.assertIn("la ruota è sbagliata", out)
        self.assertIn("1 sessione,", out)

    def test_unknown_project_exits_2(self):
        env = dict(os.environ, CLAUDE_PROJECTS_ROOT=str(self.root))
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--cwd", "/tmp/nessun-progetto-qui"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(proc.returncode, 2)

    def test_finds_project_by_scanning_when_slug_differs(self):
        # cartella con nome non derivabile dallo slug: si risale dal campo cwd
        odd = self.root / "cartella-con-nome-inatteso"
        odd.mkdir()
        with (odd / "aaaa1111-0000-0000-0000-000000000000.jsonl").open("w", encoding="utf-8") as fh:
            fh.write(json.dumps(human("trovato per scansione", "2026-08-25T08:00:00.000Z")) + "\n")
        env = dict(os.environ, CLAUDE_PROJECTS_ROOT=str(self.root))
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--cwd", WORK_DIR, "--date", "2026-08-25", "--json"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("trovato per scansione", proc.stdout)


if __name__ == "__main__":
    unittest.main()
