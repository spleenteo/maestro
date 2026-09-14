"""Characterization tests for bin/mem — pin today's behaviour before schema/scope changes.

Black-box, stdlib-only tests: every command runs through subprocess against the
real `bin/mem` script, on a temporary db seeded with the legacy (pre-scope) `log`
schema. Both MEM_DB and MEM_SCOPE are stripped from the parent environment before
each run and MEM_DB is repointed at the temp db, so a real instance (or a
satellite session) can never leak in. TestScope sets MEM_SCOPE per run to play a
satellite session.

Run: python3 -m unittest tests.test_mem -v
"""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "mem"

# Same text as LOG_SCHEMA in tests/test_mem_vec.py: the schema bin/mem runs on
# today, before the scope column exists.
LOG_SCHEMA = """
CREATE TABLE log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  tags TEXT,
  type TEXT NOT NULL CHECK(type IN ('memory', 'task', 'idea')),
  status TEXT,
  due_date TEXT,
  completed_date TEXT,
  priority TEXT DEFAULT 'normal'
);
"""


def effective_today() -> str:
    """Mirrors bin/mem's early-morning rule (00:00-06:00 counts as yesterday)."""
    now = datetime.now()
    if now.hour < 6:
        return (now.date() - timedelta(days=1)).isoformat()
    return now.date().isoformat()


# Whole-hour Etc/GMT zones tzdata actually ships (Etc/GMT-14..Etc/GMT+12,
# sign reversed per POSIX): the range of UTC offsets, in hours, available to
# force a local wall-clock hour deterministically.
_ETC_GMT_OFFSET_RANGE = range(-12, 15)


def _etc_gmt_zone(offset_hours: int) -> str:
    """The Etc/GMT zone name for a UTC offset in whole hours. POSIX reverses
    the sign: Etc/GMT-N is UTC+N, Etc/GMT+N is UTC-N."""
    if offset_hours == 0:
        return "Etc/GMT"
    if offset_hours > 0:
        return f"Etc/GMT-{offset_hours}"
    return f"Etc/GMT+{-offset_hours}"


def _pick_early_morning_tz() -> "tuple[str, int] | tuple[None, None]":
    """An (Etc/GMT zone, UTC offset in hours) whose local time is between
    00:00 and 06:00 right now, computed from the current UTC hour so the
    choice is deterministic at any time of day the gate happens to run.
    Among the offsets that land in the window, the one closest to its middle
    (03:00) is preferred, to absorb the gap between picking the zone here and
    the subprocess under test reading its own clock a moment later.
    (None, None) when no whole-hour Etc/GMT offset lands in the window —
    doesn't happen in practice (every UTC hour has an exact 03:00 match
    within -12..+14), but callers skip rather than assume it can't."""
    utc_hour = datetime.now(timezone.utc).hour
    best = None  # (distance from 03:00, offset)
    for offset in _ETC_GMT_OFFSET_RANGE:
        local_hour = (utc_hour + offset) % 24
        if 0 <= local_hour < 6:
            dist = abs(local_hour - 3)
            if best is None or dist < best[0]:
                best = (dist, offset)
    if best is None:
        return None, None
    offset = best[1]
    return _etc_gmt_zone(offset), offset


class TempDbCase(unittest.TestCase):
    """Fixture: temp db with the legacy log schema, empty, plus run/read helpers."""

    def setUp(self):
        os.environ.pop("MEM_DB", None)
        os.environ.pop("MEM_SCOPE", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db = Path(self._tmp.name) / "test.db"
        con = sqlite3.connect(self.db)
        con.executescript(LOG_SCHEMA)
        con.commit()
        con.close()

    def run_mem(self, *args, env=None, stdin=None):
        base = dict(os.environ)
        base.pop("MEM_DB", None)
        base.pop("MEM_SCOPE", None)
        base["MEM_DB"] = str(self.db)
        if env:
            base.update(env)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True, env=base, input=stdin,
        )

    def ok_json(self, *args, stdin=None, env=None):
        """Run a write command with --json appended, assert success, return the payload."""
        r = self.run_mem(*args, "--json", stdin=stdin, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def read_json(self, *args, env=None):
        """Run a read command (JSON is automatic off a TTY) and return the payload."""
        r = self.run_mem(*args, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def db_rows(self, where="1=1", params=()):
        con = sqlite3.connect(self.db)
        con.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in con.execute(
                f"SELECT * FROM log WHERE {where}", params).fetchall()]
        finally:
            con.close()

    def db_row(self, rid):
        rows = self.db_rows("id=?", (rid,))
        self.assertEqual(len(rows), 1, f"expected exactly one row with id {rid}, got {rows}")
        return rows[0]


class TestSave(TempDbCase):
    def test_single_save_writes_row_and_prints_json(self):
        payload = self.ok_json("save", "server riavviato", "-d", "manutenzione notturna",
                                "-t", "infra,server")
        self.assertEqual(payload["title"], "server riavviato")
        self.assertEqual(payload["description"], "manutenzione notturna")
        self.assertEqual(payload["tags"], "infra,server")
        self.assertEqual(payload["type"], "memory")
        self.assertEqual(payload["date"], effective_today())
        row = self.db_row(payload["id"])
        self.assertEqual(row["type"], "memory")
        self.assertIsNone(row["status"])
        self.assertEqual(row["tags"], "infra,server")

    def test_save_without_json_announces_and_still_writes(self):
        r = self.run_mem("save", "nota rapida")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("saved", r.stdout)
        self.assertIn("nota rapida", r.stdout)
        rows = self.db_rows("title=?", ("nota rapida",))
        self.assertEqual(len(rows), 1)

    def test_explicit_date_overrides_today(self):
        payload = self.ok_json("save", "vecchio ricordo", "--date", "2020-01-01")
        self.assertEqual(payload["date"], "2020-01-01")

    def test_bulk_inserts_all_rows_in_one_transaction(self):
        items = [
            {"title": "nota bulk", "type": "memory", "tags": "x,y",
             "status": "open"},  # memory: status must be forced to NULL
            {"title": "task bulk", "type": "task", "status": "todo",
             "priority": "high", "due_date": "2026-12-31"},
        ]
        payload = self.ok_json("save", "--bulk", stdin=json.dumps(items))
        self.assertEqual(payload["count"], 2)
        ids = [row["id"] for row in payload["inserted"]]
        self.assertEqual(len(ids), 2)
        memory_row = self.db_row(ids[0])
        self.assertEqual(memory_row["type"], "memory")
        self.assertIsNone(memory_row["status"])  # forced NULL despite input
        task_row = self.db_row(ids[1])
        self.assertEqual(task_row["status"], "todo")
        self.assertEqual(task_row["priority"], "high")
        self.assertEqual(task_row["due_date"], "2026-12-31")

    def test_bulk_defaults_date_type_and_priority_when_missing(self):
        payload = self.ok_json("save", "--bulk", stdin=json.dumps([{"title": "senza data"}]))
        row = self.db_row(payload["inserted"][0]["id"])
        self.assertEqual(row["date"], effective_today())
        self.assertEqual(row["type"], "memory")
        self.assertEqual(row["priority"], "normal")

    def test_bulk_invalid_json_exits_2(self):
        r = self.run_mem("save", "--bulk", stdin="not json")
        self.assertEqual(r.returncode, 2)
        self.assertIn("invalid JSON", r.stderr)

    def test_bulk_non_list_exits_2(self):
        r = self.run_mem("save", "--bulk", stdin=json.dumps({"a": 1}))
        self.assertEqual(r.returncode, 2)
        self.assertIn("array", r.stderr)


class TestTask(TempDbCase):
    def test_creates_todo_row_with_defaults(self):
        payload = self.ok_json("task", "compra latte")
        self.assertEqual(payload["status"], "todo")
        self.assertEqual(payload["priority"], "normal")
        self.assertIsNone(payload["due_date"])
        row = self.db_row(payload["id"])
        self.assertEqual(row["type"], "task")
        self.assertEqual(row["status"], "todo")

    def test_creates_with_due_date_priority_and_tags(self):
        payload = self.ok_json("task", "rinnovare assicurazione", "--due", "2026-12-31",
                                "--priority", "high", "-t", "casa,scadenze")
        self.assertEqual(payload["due_date"], "2026-12-31")
        self.assertEqual(payload["priority"], "high")
        row = self.db_row(payload["id"])
        self.assertEqual(row["tags"], "casa,scadenze")
        self.assertEqual(row["due_date"], "2026-12-31")


class TestIdea(TempDbCase):
    def test_creates_open_row(self):
        payload = self.ok_json("idea", "indice semantico del vault", "-t", "mem,idee")
        self.assertEqual(payload["type"], "idea")
        self.assertEqual(payload["status"], "open")
        row = self.db_row(payload["id"])
        self.assertEqual(row["type"], "idea")
        self.assertEqual(row["status"], "open")
        self.assertEqual(row["tags"], "mem,idee")


class TestUpdate(TempDbCase):
    def setUp(self):
        super().setUp()
        self.rid = self.ok_json("task", "rivedere contratto")["id"]

    def test_updates_multiple_fields_at_once(self):
        payload = self.ok_json(
            "update", str(self.rid),
            "--title", "rivedere contratto affitto",
            "--status", "in_progress",
            "--due", "2026-11-01",
            "--priority", "low",
            "--tags", "casa,legale",
            "--date", "2026-01-05",
        )
        self.assertEqual(payload["id"], self.rid)
        row = self.db_row(self.rid)
        self.assertEqual(row["title"], "rivedere contratto affitto")
        self.assertEqual(row["status"], "in_progress")
        self.assertEqual(row["due_date"], "2026-11-01")
        self.assertEqual(row["priority"], "low")
        self.assertEqual(row["tags"], "casa,legale")
        self.assertEqual(row["date"], "2026-01-05")

    def test_no_fields_exits_1(self):
        r = self.run_mem("update", str(self.rid))
        self.assertEqual(r.returncode, 1)
        self.assertIn("nothing to update", r.stderr)

    def test_unknown_id_exits_1(self):
        r = self.run_mem("update", "999999", "--title", "x")
        self.assertEqual(r.returncode, 1)
        self.assertIn("999999", r.stderr)


class TestDone(TempDbCase):
    def setUp(self):
        super().setUp()
        self.t1 = self.ok_json("task", "task uno")["id"]
        self.t2 = self.ok_json("task", "task due")["id"]

    def test_marks_task_done_with_completed_date(self):
        payload = self.ok_json("done", str(self.t1))
        self.assertEqual(payload["done"], [self.t1])
        self.assertEqual(payload["completed_date"], effective_today())
        row = self.db_row(self.t1)
        self.assertEqual(row["status"], "done")
        self.assertEqual(row["completed_date"], effective_today())

    def test_marks_several_ids_in_one_call(self):
        self.ok_json("done", str(self.t1), str(self.t2))
        self.assertEqual(self.db_row(self.t1)["status"], "done")
        self.assertEqual(self.db_row(self.t2)["status"], "done")

    def test_unknown_id_exits_1(self):
        r = self.run_mem("done", "999999")
        self.assertEqual(r.returncode, 1)
        self.assertIn("999999", r.stderr)

    def test_a_bad_id_after_a_good_one_still_commits_the_good_one(self):
        """Characterization: cmd_done commits on `return 1` from inside the
        `with connect()` block, so a good id processed before a failing one
        in the same call is already persisted done. A future scope-refusal
        must not silently change this partial-commit behaviour. Task 5: the
        committed id is announced on stdout before the stderr refusal."""
        r = self.run_mem("done", str(self.t1), "999999")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.db_row(self.t1)["status"], "done")
        self.assertIn(f"✅ done #{self.t1}", r.stdout)
        self.assertIn("999999", r.stderr)

    def test_bad_id_after_good_one_in_json_mode_emits_committed_ids_then_exits_1(self):
        r = self.run_mem("done", str(self.t1), "999999", "--json")
        self.assertEqual(r.returncode, 1)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["done"], [self.t1])
        self.assertEqual(payload["completed_date"], effective_today())
        self.assertIn("999999", r.stderr)
        self.assertEqual(self.db_row(self.t1)["status"], "done")

    def test_first_id_refused_announces_nothing_and_json_mode_reports_empty_done(self):
        """No id committed before the refusal: no announcement, and --json
        still emits a well-formed payload with an empty `done` list."""
        r = self.run_mem("done", "999999", str(self.t1))
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "")
        self.assertIsNone(self.db_row(self.t1)["completed_date"])
        payload = self.run_mem("done", "999999", str(self.t1), "--json")
        self.assertEqual(payload.returncode, 1)
        self.assertEqual(json.loads(payload.stdout),
                         {"done": [], "completed_date": effective_today()})


class TestReopen(TempDbCase):
    def setUp(self):
        super().setUp()
        self.rid = self.ok_json("task", "task chiuso")["id"]
        self.run_mem("done", str(self.rid))

    def test_reopen_clears_completed_date_and_sets_todo(self):
        payload = self.ok_json("reopen", str(self.rid))
        self.assertEqual(payload["reopened"], self.rid)
        row = self.db_row(self.rid)
        self.assertEqual(row["status"], "todo")
        self.assertIsNone(row["completed_date"])

    def test_unknown_id_exits_1(self):
        r = self.run_mem("reopen", "999999")
        self.assertEqual(r.returncode, 1)
        self.assertIn("999999", r.stderr)


class TestMarker(TempDbCase):
    def test_set_then_get_round_trips(self):
        set_payload = self.ok_json("marker", "set", "last-flush", "2026-09-14T08:00:00")
        self.assertEqual(set_payload["action"], "created")
        get_payload = self.ok_json("marker", "get", "last-flush")
        self.assertEqual(get_payload["value"], "2026-09-14T08:00:00")
        self.assertEqual(get_payload["id"], set_payload["id"])

    def test_get_without_json_prints_the_raw_value(self):
        self.run_mem("marker", "set", "last-flush", "hello")
        r = self.run_mem("marker", "get", "last-flush")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "hello")

    def test_set_again_updates_the_same_row_not_a_new_one(self):
        first = self.ok_json("marker", "set", "last-flush", "v1")
        second = self.ok_json("marker", "set", "last-flush", "v2")
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(second["action"], "updated")
        rows = self.db_rows("title=?", ("last-flush",))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["description"], "v2")

    def test_get_missing_marker_returns_null_value(self):
        payload = self.ok_json("marker", "get", "never-set")
        self.assertIsNone(payload["value"])

    def test_get_falls_back_to_any_row_with_matching_title(self):
        """Retrocompat (bin/mem:343-349): a pre-CLI marker row has no
        tags='marker' — the title-only fallback must still find it."""
        con = sqlite3.connect(self.db)
        con.execute(
            "INSERT INTO log (date, title, description, type) VALUES (?,?,?,?)",
            (effective_today(), "old-flush", "legacy-value", "memory"),
        )
        con.commit()
        con.close()
        payload = self.ok_json("marker", "get", "old-flush")
        self.assertEqual(payload["value"], "legacy-value")


class TestToday(TempDbCase):
    def test_returns_only_rows_dated_today_in_id_order(self):
        self.run_mem("save", "vecchia nota", "--date", "2020-01-01")
        first = self.ok_json("save", "nota di oggi uno")
        second = self.ok_json("save", "nota di oggi due")
        rows = self.read_json("today")
        ids = [row["id"] for row in rows]
        self.assertEqual(ids, [first["id"], second["id"]])
        titles = {row["title"] for row in rows}
        self.assertNotIn("vecchia nota", titles)


class TestTodo(TempDbCase):
    def test_orders_by_priority_then_due_date_then_id(self):
        low = self.ok_json("task", "bassa priorita", "--priority", "low")
        high_later = self.ok_json("task", "alta con scadenza lontana",
                                   "--priority", "high", "--due", "2026-12-31")
        high_sooner = self.ok_json("task", "alta con scadenza vicina",
                                    "--priority", "high", "--due", "2026-10-01")
        normal_no_due = self.ok_json("task", "normale senza scadenza", "--priority", "normal")
        rows = self.read_json("todo")
        ids = [row["id"] for row in rows]
        self.assertEqual(ids, [high_sooner["id"], high_later["id"],
                                normal_no_due["id"], low["id"]])

    def test_excludes_done_cancelled_tasks_and_non_task_rows(self):
        todo_task = self.ok_json("task", "task aperto")
        done_task = self.ok_json("task", "task chiuso")
        self.run_mem("done", str(done_task["id"]))
        cancelled_task = self.ok_json("task", "task annullato")
        self.run_mem("update", str(cancelled_task["id"]), "--status", "cancelled")
        self.ok_json("idea", "una idea aperta")
        self.ok_json("save", "una memoria")
        rows = self.read_json("todo")
        ids = [row["id"] for row in rows]
        self.assertEqual(ids, [todo_task["id"]])


class TestOverdue(TempDbCase):
    def test_returns_only_overdue_open_tasks_ordered_by_due_date(self):
        far_past = self.ok_json("task", "scaduto da molto", "--due", "2020-01-01")
        near_past = self.ok_json("task", "scaduto da poco", "--due", "2020-06-01")
        self.ok_json("task", "non ancora scaduto", "--due", "2099-01-01")
        self.ok_json("task", "senza scadenza")
        done_overdue = self.ok_json("task", "scaduto ma chiuso", "--due", "2020-01-01")
        self.run_mem("done", str(done_overdue["id"]))
        rows = self.read_json("overdue")
        ids = [row["id"] for row in rows]
        self.assertEqual(ids, [far_past["id"], near_past["id"]])


class TestSearch(TempDbCase):
    def setUp(self):
        super().setUp()
        self.a = self.ok_json("save", "lavatrice rumorosa", "-d", "vibra in centrifuga",
                               "-t", "casa,elettrodomestici", "--date", "2026-01-10")
        self.b = self.ok_json("task", "chiamare tecnico caldaia", "-t", "casa",
                               "--date", "2026-02-01")
        self.c = self.ok_json("idea", "indice semantico vault", "-t", "mem",
                               "--date", "2026-03-01")

    def test_query_matches_title_or_description(self):
        rows = self.read_json("search", "lavatrice")
        self.assertEqual([x["id"] for x in rows], [self.a["id"]])

    def test_filters_by_tag(self):
        rows = self.read_json("search", "--tag", "casa")
        self.assertEqual({x["id"] for x in rows}, {self.a["id"], self.b["id"]})

    def test_filters_by_type(self):
        rows = self.read_json("search", "--type", "idea")
        self.assertEqual([x["id"] for x in rows], [self.c["id"]])

    def test_filters_by_status(self):
        rows = self.read_json("search", "--status", "todo")
        self.assertEqual([x["id"] for x in rows], [self.b["id"]])

    def test_filters_by_since_and_until(self):
        rows = self.read_json("search", "--since", "2026-02-01", "--until", "2026-02-28")
        self.assertEqual([x["id"] for x in rows], [self.b["id"]])

    def test_limit_caps_result_count(self):
        rows = self.read_json("search", "--limit", "1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], self.c["id"])  # date DESC: most recent first


class TestShow(TempDbCase):
    def test_returns_full_row(self):
        saved = self.ok_json("save", "nota completa", "-d", "dettaglio", "-t", "x")
        row = self.read_json("show", str(saved["id"]))
        self.assertEqual(row["id"], saved["id"])
        self.assertEqual(row["title"], "nota completa")
        self.assertEqual(row["description"], "dettaglio")

    def test_missing_id_exits_1(self):
        r = self.run_mem("show", "999999")
        self.assertEqual(r.returncode, 1)
        self.assertIn("999999", r.stderr)


class TestStats(TempDbCase):
    def test_aggregates_counts_and_date_range(self):
        self.ok_json("save", "memoria uno", "--date", "2026-01-01")
        self.ok_json("save", "memoria due", "--date", "2026-01-05")
        done_task = self.ok_json("task", "task chiuso", "--date", "2026-02-10")
        self.ok_json("task", "task aperto", "--date", "2026-02-01")
        self.run_mem("done", str(done_task["id"]))
        self.ok_json("idea", "idea aperta", "--date", "2026-03-01")
        payload = self.read_json("stats")
        self.assertEqual(payload["total"], 5)
        self.assertEqual(payload["by_type"], {"memory": 2, "task": 2, "idea": 1})
        self.assertEqual(payload["open_tasks"], 1)
        self.assertEqual(payload["open_ideas"], 1)
        self.assertEqual(payload["first_date"], "2026-01-01")
        self.assertEqual(payload["last_date"], "2026-03-01")


SAT = {"MEM_SCOPE": "acme"}
OTHER = {"MEM_SCOPE": "other"}


class TestScope(TempDbCase):
    """MEM_SCOPE rules: a satellite (MEM_SCOPE set) writes and reads only its
    scope; the mother (MEM_SCOPE unset) writes null and reads null unless
    --scope/--all-scopes open the others, and todo/overdue show every scope."""

    READS_WITH_FLAGS = ("today", "search", "stats", "todo", "overdue")

    def ids(self, rows):
        return sorted(row["id"] for row in rows)

    def run_mem_tty(self, *args, env=None):
        """Run bin/mem with stdout on a pseudo-terminal, to read its table output."""
        import pty
        master, slave = pty.openpty()
        base = dict(os.environ)
        base.pop("MEM_SCOPE", None)
        base["MEM_DB"] = str(self.db)
        base.update(env or {})
        try:
            proc = subprocess.Popen([sys.executable, str(SCRIPT), *args], stdout=slave,
                                    stderr=subprocess.PIPE, text=True, env=base)
        finally:
            os.close(slave)
        # Read before waiting: macOS drops what is left in the pty once the
        # child has exited and the reader arrives late.
        chunks = []
        while True:
            try:
                data = os.read(master, 4096)
            except OSError:  # Linux signals the closed slave with EIO
                break
            if not data:
                break
            chunks.append(data)
        os.close(master)
        stderr = proc.stderr.read()
        proc.stderr.close()
        self.assertEqual(proc.wait(), 0, stderr)
        return b"".join(chunks).decode()

    def header(self, table):
        return [c.strip() for c in table.splitlines()[0].split("|")]

    # --- writes -----------------------------------------------------------

    def test_save_in_a_satellite_stores_its_scope(self):
        payload = self.ok_json("save", "nota satellite", env=SAT)
        self.assertEqual(payload["scope"], "acme")
        self.assertEqual(self.db_row(payload["id"])["scope"], "acme")

    def test_save_in_the_mother_leaves_scope_null(self):
        payload = self.ok_json("save", "nota madre")
        self.assertIsNone(self.db_row(payload["id"])["scope"])

    def test_task_and_idea_in_a_satellite_store_its_scope(self):
        task = self.ok_json("task", "task satellite", env=SAT)
        idea = self.ok_json("idea", "idea satellite", env=SAT)
        self.assertEqual(self.db_row(task["id"])["scope"], "acme")
        self.assertEqual(self.db_row(idea["id"])["scope"], "acme")

    def test_bulk_stores_the_session_scope_over_a_scope_key(self):
        items = json.dumps([{"title": "bulk uno", "scope": "other"},
                            {"title": "bulk due", "type": "task", "status": "todo"}])
        sat = self.ok_json("save", "--bulk", stdin=items, env=SAT)
        mother = self.ok_json("save", "--bulk", stdin=items)
        for row in sat["inserted"]:
            self.assertEqual(self.db_row(row["id"])["scope"], "acme")
        for row in mother["inserted"]:
            self.assertIsNone(self.db_row(row["id"])["scope"])

    def test_invalid_mem_scope_exits_6_and_writes_nothing(self):
        r = self.run_mem("save", "probe", env={"MEM_SCOPE": "Acme!"})
        self.assertEqual(r.returncode, 6)
        self.assertIn("MEM_SCOPE", r.stderr)
        r = self.run_mem("search", "probe", env={"MEM_SCOPE": "Acme!"})
        self.assertEqual(r.returncode, 6)
        self.assertEqual(self.db_rows(), [])

    # --- the V1 Done probe ------------------------------------------------

    def test_probe_saved_in_a_satellite_is_hidden_from_the_mother_search(self):
        probe = self.ok_json("save", "probe", env=SAT)
        self.assertEqual(self.read_json("search", "probe"), [])
        self.assertEqual(self.ids(self.read_json("search", "probe", "--scope", "acme")),
                         [probe["id"]])
        self.assertEqual(self.ids(self.read_json("search", "probe", env=SAT)), [probe["id"]])

    # --- reads: today, search, stats --------------------------------------

    def seed_three_scopes(self, *args):
        """The same write in the mother, in acme and in other; returns their ids."""
        return (self.ok_json(*args)["id"],
                self.ok_json(*args, env=SAT)["id"],
                self.ok_json(*args, env=OTHER)["id"])

    def test_today_reads_the_current_scope_unless_a_mother_flag_opens_others(self):
        mother, sat, other = self.seed_three_scopes("save", "nota di oggi")
        self.assertEqual(self.ids(self.read_json("today")), [mother])
        self.assertEqual(self.ids(self.read_json("today", env=SAT)), [sat])
        self.assertEqual(self.ids(self.read_json("today", "--scope", "acme")), [sat])
        self.assertEqual(self.ids(self.read_json("today", "--all-scopes")),
                         sorted([mother, sat, other]))

    def test_search_reads_the_current_scope_unless_a_mother_flag_opens_others(self):
        mother, sat, other = self.seed_three_scopes("save", "lavatrice")
        self.assertEqual(self.ids(self.read_json("search", "lavatrice")), [mother])
        self.assertEqual(self.ids(self.read_json("search", "lavatrice", env=SAT)), [sat])
        self.assertEqual(self.ids(self.read_json("search", "--all-scopes")),
                         sorted([mother, sat, other]))

    def test_stats_count_only_the_current_scope(self):
        self.ok_json("save", "memoria madre", "--date", "2026-01-01")
        self.ok_json("idea", "idea madre", "--date", "2026-01-02")
        self.ok_json("task", "task satellite", "--date", "2026-02-01", env=SAT)
        self.ok_json("save", "memoria satellite", "--date", "2026-02-05", env=SAT)
        self.ok_json("save", "memoria other", "--date", "2026-03-01", env=OTHER)
        mother = self.read_json("stats")
        self.assertEqual(mother, {"total": 2, "by_type": {"memory": 1, "idea": 1},
                                  "open_tasks": 0, "open_ideas": 1,
                                  "first_date": "2026-01-01", "last_date": "2026-01-02"})
        sat = self.read_json("stats", env=SAT)
        self.assertEqual(sat, {"total": 2, "by_type": {"memory": 1, "task": 1},
                               "open_tasks": 1, "open_ideas": 0,
                               "first_date": "2026-02-01", "last_date": "2026-02-05"})
        self.assertEqual(self.read_json("stats", "--scope", "acme"), sat)
        everything = self.read_json("stats", "--all-scopes")
        self.assertEqual(everything["total"], 5)
        self.assertEqual(everything["last_date"], "2026-03-01")

    # --- reads: todo, overdue ---------------------------------------------

    def test_todo_in_the_mother_shows_every_scope(self):
        ids = self.seed_three_scopes("task", "task aperto")
        self.assertEqual(self.ids(self.read_json("todo")), sorted(ids))
        self.assertEqual(self.ids(self.read_json("todo", "--all-scopes")), sorted(ids))

    def test_todo_in_a_satellite_or_with_scope_shows_that_scope_only(self):
        _, sat, _ = self.seed_three_scopes("task", "task aperto")
        self.assertEqual(self.ids(self.read_json("todo", env=SAT)), [sat])
        self.assertEqual(self.ids(self.read_json("todo", "--scope", "acme")), [sat])

    def test_overdue_in_the_mother_shows_every_scope(self):
        ids = self.seed_three_scopes("task", "scaduto", "--due", "2020-01-01")
        self.assertEqual(self.ids(self.read_json("overdue")), sorted(ids))
        self.assertEqual(self.ids(self.read_json("overdue", "--all-scopes")), sorted(ids))

    def test_overdue_in_a_satellite_or_with_scope_shows_that_scope_only(self):
        _, sat, _ = self.seed_three_scopes("task", "scaduto", "--due", "2020-01-01")
        self.assertEqual(self.ids(self.read_json("overdue", env=SAT)), [sat])
        self.assertEqual(self.ids(self.read_json("overdue", "--scope", "acme")), [sat])

    def test_todo_and_overdue_tables_carry_a_scope_column_in_the_mother_only(self):
        self.ok_json("task", "scaduto", "--due", "2020-01-01", env=SAT)
        for cmd in ("todo", "overdue"):
            with self.subTest(cmd=cmd):
                mother = self.run_mem_tty(cmd)
                self.assertIn("scope", self.header(mother))
                self.assertIn("acme", mother)
                self.assertNotIn("scope", self.header(self.run_mem_tty(cmd, env=SAT)))

    # --- the mother flags -------------------------------------------------

    def test_mother_flags_are_refused_in_a_satellite_with_exit_4(self):
        for cmd in self.READS_WITH_FLAGS:
            for flag in (["--scope", "other"], ["--all-scopes"]):
                with self.subTest(cmd=cmd, flag=flag):
                    r = self.run_mem(cmd, *flag, env=SAT)
                    self.assertEqual(r.returncode, 4, r.stderr)
                    self.assertIn("acme", r.stderr)
                    self.assertEqual(r.stdout, "")

    def test_invalid_scope_flag_exits_6(self):
        for cmd in self.READS_WITH_FLAGS:
            with self.subTest(cmd=cmd):
                r = self.run_mem(cmd, "--scope", "Not_A_Slug")
                self.assertEqual(r.returncode, 6, r.stderr)
                self.assertIn("--scope", r.stderr)

    def test_scope_and_all_scopes_together_are_a_usage_error(self):
        for cmd in self.READS_WITH_FLAGS:
            with self.subTest(cmd=cmd):
                r = self.run_mem(cmd, "--scope", "acme", "--all-scopes")
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertIn("not allowed with argument", r.stderr)

    # --- markers ----------------------------------------------------------

    def test_mother_and_satellite_hold_separate_markers_with_the_same_name(self):
        mother_set = self.ok_json("marker", "set", "last-flush", "madre")
        sat_set = self.ok_json("marker", "set", "last-flush", "satellite", env=SAT)
        self.assertEqual(sat_set["action"], "created")
        self.assertNotEqual(mother_set["id"], sat_set["id"])
        self.assertEqual(self.db_row(sat_set["id"])["scope"], "acme")
        self.assertEqual(self.ok_json("marker", "get", "last-flush")["value"], "madre")
        self.assertEqual(self.ok_json("marker", "get", "last-flush", env=SAT)["value"],
                         "satellite")

    def test_marker_lookups_skip_a_legacy_row_of_another_scope(self):
        """Both the tagged query and the title fallback of `get`, and the lookup
        of `set`, stay inside the scope."""
        con = sqlite3.connect(self.db)
        legacy_id = con.execute(
            "INSERT INTO log (date, title, description, type) VALUES (?,?,?,?)",
            (effective_today(), "old-flush", "legacy-value", "memory")).lastrowid
        con.commit()
        con.close()
        self.assertIsNone(self.ok_json("marker", "get", "old-flush", env=SAT)["value"])
        sat_set = self.ok_json("marker", "set", "old-flush", "nuovo", env=SAT)
        self.assertEqual(sat_set["action"], "created")
        self.assertEqual(self.db_row(legacy_id)["description"], "legacy-value")
        self.assertEqual(self.ok_json("marker", "get", "old-flush")["value"], "legacy-value")

    # --- id commands ------------------------------------------------------

    def assert_refused(self, r, rid):
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"no row with id {rid} in scope acme", r.stderr)

    def test_show_in_a_satellite_refuses_a_row_of_another_scope(self):
        mother = self.ok_json("save", "nota madre")["id"]
        own = self.ok_json("save", "nota satellite", env=SAT)["id"]
        self.assert_refused(self.run_mem("show", str(mother), env=SAT), mother)
        self.assertEqual(self.read_json("show", str(own), env=SAT)["id"], own)

    def test_update_in_a_satellite_refuses_a_row_of_another_scope(self):
        mother = self.ok_json("task", "task madre")["id"]
        self.assert_refused(self.run_mem("update", str(mother), "--title", "x", env=SAT), mother)
        self.assertEqual(self.db_row(mother)["title"], "task madre")

    def test_update_in_a_satellite_keeps_its_own_row_in_scope(self):
        own = self.ok_json("task", "task satellite", env=SAT)["id"]
        self.ok_json("update", str(own), "--title", "rinominato", "--status", "done", env=SAT)
        row = self.db_row(own)
        self.assertEqual(row["title"], "rinominato")
        self.assertEqual(row["scope"], "acme")

    def test_done_in_a_satellite_refuses_a_task_of_another_scope(self):
        mother = self.ok_json("task", "task madre")["id"]
        self.assert_refused(self.run_mem("done", str(mother), env=SAT), mother)
        self.assertEqual(self.db_row(mother)["status"], "todo")

    def test_done_in_a_satellite_announces_the_owned_id_before_the_refusal(self):
        """Task 5 resolution: `done <own> <other-scope>` commits and announces
        the owned id on stdout before the stderr refusal for the other one."""
        own = self.ok_json("task", "task satellite", env=SAT)["id"]
        mother = self.ok_json("task", "task madre")["id"]
        r = self.run_mem("done", str(own), str(mother), env=SAT)
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"✅ done #{own}", r.stdout)
        self.assertIn(f"no row with id {mother} in scope acme", r.stderr)
        self.assertEqual(self.db_row(own)["status"], "done")
        self.assertEqual(self.db_row(mother)["status"], "todo")

    def test_done_in_a_satellite_json_mode_reports_the_owned_id_before_the_refusal(self):
        own = self.ok_json("task", "task satellite", env=SAT)["id"]
        mother = self.ok_json("task", "task madre")["id"]
        r = self.run_mem("done", str(own), str(mother), "--json", env=SAT)
        self.assertEqual(r.returncode, 1)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["done"], [own])
        self.assertEqual(payload["completed_date"], effective_today())
        self.assertIn(f"no row with id {mother} in scope acme", r.stderr)

    def test_done_in_a_satellite_on_its_own_memory_still_says_no_task(self):
        own = self.ok_json("save", "memoria satellite", env=SAT)["id"]
        r = self.run_mem("done", str(own), env=SAT)
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"no task with id {own}", r.stderr)

    def test_reopen_in_a_satellite_refuses_a_task_of_another_scope(self):
        mother = self.ok_json("task", "task madre")["id"]
        self.ok_json("done", str(mother))
        self.assert_refused(self.run_mem("reopen", str(mother), env=SAT), mother)
        self.assertEqual(self.db_row(mother)["status"], "done")

    def test_id_commands_in_the_mother_act_on_any_scope(self):
        sat = self.ok_json("task", "task satellite", env=SAT)["id"]
        self.assertEqual(self.read_json("show", str(sat))["scope"], "acme")
        self.ok_json("update", str(sat), "--priority", "high")
        self.ok_json("done", str(sat))
        self.assertEqual(self.db_row(sat)["status"], "done")
        self.ok_json("reopen", str(sat))
        row = self.db_row(sat)
        self.assertEqual((row["status"], row["priority"], row["scope"]),
                         ("todo", "high", "acme"))

    # --- the semantic layer: --semantic, similar, dupes, embed ------------

    def test_embed_is_refused_in_a_satellite_and_leaves_the_db_untouched(self):
        before = self.db.read_bytes()
        r = self.run_mem("embed", env=SAT)
        self.assertEqual(r.returncode, 4, r.stderr)
        self.assertIn("acme", r.stderr)
        self.assertEqual(r.stdout, "")
        self.assertEqual(self.db.read_bytes(), before)

    def test_similar_and_dupes_refuse_scope_flags_in_a_satellite(self):
        for cmd, extra in (("similar", ["1"]), ("dupes", [])):
            for flag in (["--scope", "other"], ["--all-scopes"]):
                with self.subTest(cmd=cmd, flag=flag):
                    r = self.run_mem(cmd, *extra, *flag, env=SAT)
                    self.assertEqual(r.returncode, 4, r.stderr)
                    self.assertTrue(r.stderr.startswith("mem:"), r.stderr)
                    self.assertIn("acme", r.stderr)

    def test_search_semantic_refuses_scope_flags_in_a_satellite(self):
        for flag in (["--scope", "other"], ["--all-scopes"]):
            with self.subTest(flag=flag):
                r = self.run_mem("search", "q", "--semantic", *flag, env=SAT)
                self.assertEqual(r.returncode, 4, r.stderr)
                self.assertTrue(r.stderr.startswith("mem:"), r.stderr)
                self.assertIn("acme", r.stderr)

    def test_semantic_refusals_run_before_uv_and_before_the_db(self):
        """PATH without uv: exit 4 instead of 3 ("uv non installato") shows the
        refusal runs before _vec_run looks for uv; the legacy db file stays
        byte-identical, so nothing opened or migrated it."""
        before = self.db.read_bytes()
        no_uv_env = {**SAT, "PATH": ""}
        for args in (["search", "q", "--semantic", "--scope", "other"],
                     ["similar", "1", "--all-scopes"],
                     ["dupes", "--scope", "other"],
                     ["embed"]):
            with self.subTest(args=args):
                r = self.run_mem(*args, env=no_uv_env)
                self.assertEqual(r.returncode, 4, r.stderr)
        self.assertEqual(self.db.read_bytes(), before)

    def _fake_uv(self, tmpdir):
        """A recorder standing in for `uv`: writes its argv and the MEM_SCOPE it
        inherited to call.json, and prints an empty JSON list (a valid, empty
        `mem-vec` answer for every subcommand `bin/mem` parses)."""
        uv_path = Path(tmpdir) / "uv"
        log_path = Path(tmpdir) / "call.json"
        uv_path.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            f"open({str(log_path)!r}, 'w').write(json.dumps("
            "{'argv': sys.argv[1:], 'mem_scope': os.environ.get('MEM_SCOPE')}))\n"
            "print('[]')\n")
        uv_path.chmod(0o755)
        return log_path

    def _vec_call(self, *args, env):
        """Run bin/mem with the fake uv first on PATH; return what uv received."""
        with tempfile.TemporaryDirectory() as fakebin:
            log_path = self._fake_uv(fakebin)
            r = self.run_mem(*args, env={**env, "PATH": fakebin})
            self.assertEqual(r.returncode, 0, r.stderr)
            return json.loads(log_path.read_text())

    def assert_flag(self, argv, flag, value=None):
        self.assertIn(flag, argv)
        if value is not None:
            self.assertEqual(argv[argv.index(flag) + 1], value)

    def test_mother_forwards_scope_flags_to_mem_vec(self):
        for args in (["search", "q", "--semantic"], ["similar", "1"], ["dupes"]):
            with self.subTest(args=args):
                call = self._vec_call(*args, "--scope", "acme", env={})
                self.assert_flag(call["argv"], "--scope", "acme")
                self.assertNotIn("--all-scopes", call["argv"])
                call = self._vec_call(*args, "--all-scopes", env={})
                self.assert_flag(call["argv"], "--all-scopes")
                self.assertNotIn("--scope", call["argv"])

    def test_satellite_reaches_mem_vec_through_mem_scope_without_flags(self):
        for args in (["search", "q", "--semantic"], ["similar", "1"], ["dupes"]):
            with self.subTest(args=args):
                call = self._vec_call(*args, env=SAT)
                self.assertEqual(call["mem_scope"], "acme")
                self.assertNotIn("--scope", call["argv"])
                self.assertNotIn("--all-scopes", call["argv"])

    def test_similar_table_shows_the_row_columns_mem_vec_similar_returns(self):
        """`bin/mem-vec similar` returns rows shaped like a search hit (id,
        date, type, status, title, tags, score) — not like `search
        --semantic`'s (source, ref, snippet). The table header must name the
        keys the row actually has."""
        row = {"id": 7, "date": "2026-03-01", "type": "memory", "status": None,
               "title": "affine", "tags": "x,y", "score": 0.87}
        with tempfile.TemporaryDirectory() as fakebin:
            uv_path = Path(fakebin) / "uv"
            uv_path.write_text(
                f"#!{sys.executable}\n"
                "import json, sys\n"
                f"print(json.dumps([{row!r}]))\n")
            uv_path.chmod(0o755)
            table = self.run_mem_tty("similar", "7", env={"PATH": fakebin})
        self.assertEqual(self.header(table),
                         ["id", "date", "type", "status", "title", "tags", "score"])
        self.assertIn("affine", table)
        self.assertIn("0.87", table)

    # --- help -------------------------------------------------------------

    def test_help_documents_scope_flags_defaults_and_exit_codes(self):
        r = self.run_mem("--help")
        self.assertEqual(r.returncode, 0, r.stderr)
        for text in ("MEM_SCOPE", "--scope", "--all-scopes", "todo and overdue",
                     "similar", "dupes", "embed",
                     "Exit code 4", "Exit code 5", "Exit code 6"):
            with self.subTest(text=text):
                self.assertIn(text, r.stdout)


D1, D2, D3 = "2026-03-01", "2026-03-02", "2026-03-03"


class TestReadOptions(TempDbCase):
    """The read options skills use in place of raw sqlite3 on `log`:
    today --date/--to, todo --due-until, search --completed-since/-until and
    --limit 0. Fixture: rows in the null scope and in acme across three days,
    the mother's rows inserted before the satellite's, so id order and date
    order disagree across scopes."""

    MOTHER = [
        ("m1", {"title": "memoria madre uno", "date": D1}),
        ("m_task_done", {"title": "task madre chiuso", "type": "task", "status": "done",
                         "date": D1, "completed_date": D2}),
        ("m_task_due2", {"title": "task madre scade D2", "type": "task", "status": "todo",
                         "date": D1, "due_date": D2, "priority": "low"}),
        ("m2", {"title": "memoria madre due", "date": D2}),
        ("m_task_nodue", {"title": "task madre senza scadenza", "type": "task",
                          "status": "in_progress", "date": D2}),
        ("m_idea", {"title": "idea madre", "type": "idea", "status": "open", "date": D2}),
        ("m3", {"title": "memoria madre tre", "date": D3}),
        ("m_task_due3", {"title": "task madre scade D3", "type": "task", "status": "todo",
                         "date": D3, "due_date": D3, "priority": "high"}),
        ("m_task_far", {"title": "task madre lontano", "type": "task", "status": "todo",
                        "date": D3, "due_date": "2099-01-01"}),
    ]
    SATELLITE = [
        ("s1", {"title": "memoria acme uno", "date": D1}),
        ("s_task_due1", {"title": "task acme scade D1", "type": "task", "status": "todo",
                         "date": D1, "due_date": D1, "priority": "high"}),
        ("s2", {"title": "memoria acme due", "date": D2}),
        ("s_task_done", {"title": "task acme chiuso", "type": "task", "status": "done",
                         "date": D2, "completed_date": D3}),
        ("s3", {"title": "memoria acme tre", "date": D3}),
        ("s_idea", {"title": "idea acme", "type": "idea", "status": "open", "date": D3}),
        ("s_idea_closed", {"title": "idea acme scartata", "type": "idea",
                           "status": "dismissed", "date": D3}),
    ]

    def setUp(self):
        super().setUp()
        self.id = {}
        for rows, env in ((self.MOTHER, None), (self.SATELLITE, SAT)):
            payload = self.ok_json("save", "--bulk", stdin=json.dumps([r for _, r in rows]),
                                   env=env)
            for (key, _), inserted in zip(rows, payload["inserted"]):
                self.id[key] = inserted["id"]

    def ids(self, *keys):
        return [self.id[k] for k in keys]

    def got(self, *args, env=None):
        return [row["id"] for row in self.read_json(*args, env=env)]

    def raw(self, sql, params=()):
        """The ids a skill's raw sqlite3 query returned before V2."""
        con = sqlite3.connect(self.db)
        try:
            return [r[0] for r in con.execute(sql, params).fetchall()]
        finally:
            con.close()

    def seed_dates(self, *days):
        """One mother memory per day, returned as {day: id}."""
        return {d: self.ok_json("save", f"nota {d}", "--date", d)["id"] for d in days}

    # --- today --date / --to ----------------------------------------------

    def test_today_date_reads_that_day_in_the_current_scope(self):
        self.assertEqual(self.got("today", "--date", D2),
                         self.ids("m2", "m_task_nodue", "m_idea"))
        self.assertEqual(self.got("today", "--date", D2, env=SAT),
                         self.ids("s2", "s_task_done"))

    def test_today_date_with_all_scopes_in_the_mother_reads_every_scope(self):
        self.assertEqual(self.got("today", "--date", D2, "--all-scopes"),
                         self.ids("m2", "m_task_nodue", "m_idea", "s2", "s_task_done"))
        self.assertEqual(self.got("today", "--date", D2, "--scope", "acme"),
                         self.ids("s2", "s_task_done"))

    def test_today_to_reads_an_inclusive_range_ordered_by_date_then_id(self):
        self.assertEqual(self.got("today", "--date", D1, "--to", D2, "--all-scopes"),
                         self.ids("m1", "m_task_done", "m_task_due2", "s1", "s_task_due1",
                                  "m2", "m_task_nodue", "m_idea", "s2", "s_task_done"))
        self.assertEqual(self.got("today", "--date", D2, "--to", D3, env=SAT),
                         self.ids("s2", "s_task_done", "s3", "s_idea", "s_idea_closed"))

    def test_today_to_equal_to_date_reads_one_day(self):
        self.assertEqual(self.got("today", "--date", D3, "--to", D3),
                         self.ids("m3", "m_task_due3", "m_task_far"))

    def test_today_to_before_date_is_a_usage_error(self):
        r = self.run_mem("today", "--date", D3, "--to", D1)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertTrue(r.stderr.startswith("mem:"), r.stderr)  # not argparse's usage
        self.assertIn("--to", r.stderr)
        self.assertEqual(r.stdout, "")

    def test_today_to_before_effective_today_without_date_is_a_usage_error(self):
        r = self.run_mem("today", "--to", "2020-01-01")
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertTrue(r.stderr.startswith("mem:"), r.stderr)
        self.assertIn("--to", r.stderr)

    def test_today_without_date_starts_from_the_early_morning_today(self):
        today = datetime.strptime(effective_today(), "%Y-%m-%d").date()
        before, day, after = (str(today + timedelta(days=n)) for n in (-1, 0, 1))
        seeded = self.seed_dates(before, day, after)
        self.assertEqual(self.got("today"), [seeded[day]])
        self.assertEqual(self.got("today", "--to", after), [seeded[day], seeded[after]])

    def test_today_without_date_uses_the_lived_day_before_6am_in_a_chosen_tz(self):
        """The branch above (hour < 6) is otherwise only exercised when the
        suite happens to run between 00:00 and 06:00 local. A TZ chosen from
        the current UTC hour forces it deterministically, at any hour."""
        tz, offset = _pick_early_morning_tz()
        if tz is None:
            self.skipTest("no Etc/GMT offset puts local time in 00:00-06:00 right now")
        local_now = (datetime.now(timezone.utc) + timedelta(hours=offset)).replace(tzinfo=None)
        self.assertLess(local_now.hour, 6,
                        "clock crossed the window while picking the TZ; rerun")
        lived_day = (local_now.date() - timedelta(days=1)).isoformat()
        calendar_day = local_now.date().isoformat()
        seeded = self.seed_dates(lived_day, calendar_day)
        self.assertEqual(self.got("today", env={"TZ": tz}), [seeded[lived_day]])

    def test_today_date_and_to_accept_relative_dates(self):
        today = datetime.now().date()
        days = [str(today + timedelta(days=n)) for n in (-2, -1, 0)]
        seeded = self.seed_dates(*days)
        self.assertEqual(self.got("today", "--date", "yesterday", "--to", "today"),
                         [seeded[days[1]], seeded[days[2]]])
        # argparse reads a bare "-2d" as an option: negative offsets need "=".
        self.assertEqual(self.got("today", "--date=-2d"), [seeded[days[0]]])

    # --- todo --due-until -------------------------------------------------

    def test_todo_due_until_keeps_null_due_dates_and_drops_later_ones(self):
        self.assertEqual(sorted(self.got("todo", "--due-until", D2)),
                         sorted(self.ids("m_task_due2", "m_task_nodue", "s_task_due1")))
        self.assertEqual(self.got("todo", "--due-until", D2, env=SAT),
                         self.ids("s_task_due1"))

    def test_todo_due_until_keeps_the_todo_order(self):
        wanted = set(self.got("todo", "--due-until", D3))
        self.assertEqual(wanted, set(self.ids("m_task_due2", "m_task_nodue", "m_task_due3",
                                              "s_task_due1")))
        self.assertEqual(self.got("todo", "--due-until", D3),
                         [i for i in self.got("todo") if i in wanted])

    # --- search --completed-since / --completed-until ---------------------

    def test_search_completed_range_filters_completed_date(self):
        self.assertEqual(self.got("search", "--completed-since", D2,
                                  "--completed-until", D2, "--all-scopes"),
                         self.ids("m_task_done"))
        self.assertEqual(self.got("search", "--completed-since", D3, "--all-scopes"),
                         self.ids("s_task_done"))
        self.assertEqual(self.got("search", "--completed-since", D2, env=SAT),
                         self.ids("s_task_done"))

    def test_search_completed_bound_excludes_rows_without_completed_date(self):
        self.assertEqual(sorted(self.got("search", "--completed-until", D3, "--all-scopes")),
                         sorted(self.ids("m_task_done", "s_task_done")))

    def test_search_semantic_refuses_completed_bounds_before_uv(self):
        for flag in ("--completed-since", "--completed-until"):
            with self.subTest(flag=flag):
                r = self.run_mem("search", "q", "--semantic", flag, D2, env={"PATH": ""})
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertTrue(r.stderr.startswith("mem:"), r.stderr)
                self.assertIn(flag, r.stderr)

    # --- search --limit 0 -------------------------------------------------

    def test_search_limit_0_returns_every_row(self):
        items = [{"title": f"riga {n}", "tags": "sessanta", "date": D1} for n in range(60)]
        self.ok_json("save", "--bulk", stdin=json.dumps(items))
        self.assertEqual(len(self.got("search", "--tag", "sessanta")), 50)
        self.assertEqual(len(self.got("search", "--tag", "sessanta", "--limit", "0")), 60)

    def test_search_semantic_with_limit_0_is_a_usage_error_before_uv(self):
        """PATH without uv: exit 2 instead of 3 shows the refusal runs before
        _vec_run looks for uv."""
        r = self.run_mem("search", "q", "--semantic", "--limit", "0", env={"PATH": ""})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("--limit 0", r.stderr)
        self.assertEqual(r.stdout, "")

    # --- the skills' pre-V2 queries have a bin/mem equivalent -------------

    def test_logbook_day_query_equivalent(self):
        """logbook/SKILL.md:102, target day D2: every scope, as the raw query had
        no scope filter."""
        raw = self.raw("SELECT id FROM log WHERE date = ? ORDER BY id", (D2,))
        self.assertEqual(self.got("today", "--date", D2, "--all-scopes"), raw)

    def test_logbook_early_morning_query_equivalent(self):
        """logbook/SKILL.md:108, the previous day D2 plus the night of D3."""
        raw = self.raw("SELECT id FROM log WHERE date IN (?, ?) ORDER BY date, id", (D2, D3))
        self.assertEqual(self.got("today", "--date", D2, "--to", D3, "--all-scopes"), raw)

    def test_scheduler_open_tasks_query_equivalent(self):
        """scheduler.md:60 with <end> = D2; todo reads every scope in the mother."""
        raw = self.raw(
            "SELECT id FROM log WHERE type='task' AND status IN ('todo','in_progress') "
            "AND (due_date IS NULL OR due_date <= ?)", (D2,))
        self.assertEqual(sorted(self.got("todo", "--due-until", D2)), sorted(raw))

    def test_scheduler_done_in_window_query_equivalent(self):
        """scheduler.md:66 with <start> = D2, <end> = D3, as two searches."""
        raw = self.raw(
            "SELECT id FROM log WHERE (type='memory' AND date BETWEEN ? AND ?) "
            "OR (type='task' AND status='done' AND completed_date BETWEEN ? AND ?)",
            (D2, D3, D2, D3))
        memories = self.got("search", "--type", "memory", "--since", D2, "--until", D3,
                            "--limit", "0", "--all-scopes")
        tasks = self.got("search", "--type", "task", "--status", "done",
                         "--completed-since", D2, "--completed-until", D3,
                         "--limit", "0", "--all-scopes")
        self.assertEqual(sorted(memories + tasks), sorted(raw))
        self.assertEqual(len(raw), 6)

    def test_scheduler_open_ideas_query_equivalent(self):
        """scheduler.md:72."""
        raw = self.raw("SELECT id FROM log WHERE type='idea' AND status='open'")
        self.assertEqual(sorted(self.got("search", "--type", "idea", "--status", "open",
                                         "--limit", "0", "--all-scopes")), sorted(raw))
        self.assertEqual(len(raw), 2)

    # --- help -------------------------------------------------------------

    def test_help_documents_the_read_options(self):
        for args, texts in ((["today", "--help"], ["--date", "--to"]),
                            (["todo", "--help"], ["--due-until"]),
                            (["search", "--help"], ["--completed-since", "--completed-until",
                                                    "0 = no limit"]),
                            (["--help"], ["--due-until", "--completed-since", "--limit 0",
                                          "Exit code 2"])):
            r = self.run_mem(*args)
            self.assertEqual(r.returncode, 0, r.stderr)
            for text in texts:
                with self.subTest(args=args, text=text):
                    self.assertIn(text, r.stdout)


class TestHelpText(TempDbCase):
    """Task 5 carried findings: wording fixes to `bin/mem`'s own help/epilog
    text, with no change to any exit code or read behaviour."""

    def test_today_date_help_names_calendar_keywords_and_the_lived_day_default(self):
        """today --date: a keyword (today/yesterday/tomorrow) resolves to that
        calendar day; omitting --date entirely is the only case that applies
        the early-morning rule and lands on the lived day."""
        r = self.run_mem("today", "--help")
        self.assertEqual(r.returncode, 0, r.stderr)
        # argparse wraps long help lines, so check the words rather than an
        # exact phrase that might fall across a line break.
        self.assertIn("calendar", r.stdout)
        self.assertIn("lived day", r.stdout)
        self.assertIn("early-morning rule", r.stdout)

    def test_date_help_examples_use_the_equals_form_for_negative_offsets(self):
        """A bare -2d after --date argparse-errors as an unknown flag: every
        per-command --date help text shows the --date=-2d form instead."""
        for cmd in ("save", "task", "idea", "update"):
            with self.subTest(cmd=cmd):
                r = self.run_mem(cmd, "--help")
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIn("--date=-2d", r.stdout)
                self.assertNotIn("yesterday, -2d", r.stdout)

    def test_invalid_date_exits_1_not_2(self):
        """Characterization: parse_date's SystemExit carries a string message,
        which Python turns into exit code 1 — not the usage-error 2."""
        r = self.run_mem("save", "x", "--date", "not-a-date")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("invalid date", r.stderr)

    def test_epilog_documents_exit_code_1_separately_from_the_usage_error_2(self):
        r = self.run_mem("--help")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Exit code 1", r.stdout)
        self.assertIn("Exit code 2", r.stdout)
        exit1_at = r.stdout.index("Exit code 1")
        exit2_at = r.stdout.index("Exit code 2")
        self.assertLess(exit1_at, exit2_at)
        # The invalid-date case is named under exit 1, not folded into the
        # usage-error list under exit 2.
        exit2_section = r.stdout[exit2_at:r.stdout.index("Exit code 3")]
        self.assertNotIn("date", exit2_section)
        exit1_section = r.stdout[exit1_at:exit2_at]
        self.assertIn("date", exit1_section)


class TestSatellite(TempDbCase):
    """`bin/mem satellite add|list|show`: the registry the mother keeps of the
    repos it lends its memory to."""

    def satellite_rows(self):
        """None when the `satellites` table doesn't exist (so a caller can
        assert `add` never ran and left no table behind)."""
        con = sqlite3.connect(self.db)
        try:
            if con.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' "
                    "AND name='satellites'").fetchone() is None:
                return None
            con.row_factory = sqlite3.Row
            return [dict(r) for r in con.execute("SELECT * FROM satellites").fetchall()]
        finally:
            con.close()

    def repo(self, name):
        d = Path(self._tmp.name) / name
        d.mkdir()
        return d

    # --- add: happy path ---------------------------------------------------

    def test_add_stores_the_resolved_repo_path_and_announces(self):
        real = self.repo("real-repo")
        link = Path(self._tmp.name) / "linked-repo"
        link.symlink_to(real)
        r = self.run_mem("satellite", "add", "acme", "--repo", str(link),
                         "--type", "development")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("🛰️ satellite added: acme", r.stdout)
        self.assertIn(str(real.resolve()), r.stdout)
        rows = self.satellite_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["scope"], "acme")
        self.assertEqual(rows[0]["repo_path"], str(real.resolve()))
        self.assertEqual(rows[0]["project_type"], "development")
        self.assertIsNotNone(rows[0]["created"])
        for col in ("mandate", "method", "constraints", "language", "vault_folder"):
            self.assertIsNone(rows[0][col])

    def test_add_with_json_emits_the_stored_row(self):
        real = self.repo("repo2")
        payload = self.ok_json(
            "satellite", "add", "acme", "--repo", str(real), "--type", "ux",
            "--mandate", "design review", "--method", "shaping",
            "--constraints", "no production code", "--language", "en",
            "--vault", "/abs/vault")
        self.assertEqual(payload["scope"], "acme")
        self.assertEqual(payload["repo_path"], str(real.resolve()))
        self.assertEqual(payload["project_type"], "ux")
        self.assertEqual(payload["mandate"], "design review")
        self.assertEqual(payload["method"], "shaping")
        self.assertEqual(payload["constraints"], "no production code")
        self.assertEqual(payload["language"], "en")
        self.assertEqual(payload["vault_folder"], "/abs/vault")
        self.assertIn("created", payload)

    def test_list_and_show_round_trip(self):
        real = self.repo("repo3")
        added = self.ok_json("satellite", "add", "acme", "--repo", str(real),
                             "--type", "development")
        listing = self.read_json("satellite", "list")
        self.assertEqual(len(listing), 1)
        self.assertEqual(listing[0]["scope"], "acme")
        shown = self.read_json("satellite", "show", "acme")
        self.assertEqual(shown, added)

    # --- list/show on a legacy db without the table -----------------------

    def test_list_on_a_db_without_the_table_returns_empty_and_creates_nothing(self):
        self.assertEqual(self.read_json("satellite", "list"), [])
        self.assertIsNone(self.satellite_rows())

    def test_show_of_an_unknown_slug_exits_1_and_creates_nothing(self):
        r = self.run_mem("satellite", "show", "ghost")
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("ghost", r.stderr)
        self.assertIsNone(self.satellite_rows())

    # --- duplicates: exit 8 -------------------------------------------------

    def test_duplicate_slug_exits_8_and_names_it(self):
        self.ok_json("satellite", "add", "acme", "--repo", str(self.repo("repoA")),
                     "--type", "development")
        r = self.run_mem("satellite", "add", "acme", "--repo", str(self.repo("repoB")),
                         "--type", "development")
        self.assertEqual(r.returncode, 8, r.stderr)
        # The explicit slug check, not the sqlite3.IntegrityError fallback:
        # that message would also mention the (different) repoB path.
        self.assertEqual(r.stderr, "mem: satellite 'acme' already exists\n")
        self.assertEqual(len(self.satellite_rows()), 1)

    def test_duplicate_repo_exits_8_and_names_it(self):
        real = self.repo("repoC")
        self.ok_json("satellite", "add", "acme", "--repo", str(real), "--type", "development")
        r = self.run_mem("satellite", "add", "other", "--repo", str(real), "--type", "development")
        self.assertEqual(r.returncode, 8, r.stderr)
        # The explicit repo check, naming the satellite that already holds
        # it, not the sqlite3.IntegrityError fallback (which would name
        # "other", the slug of *this* call, instead of "acme").
        self.assertEqual(
            r.stderr,
            f"mem: repo {real.resolve()} is already registered as satellite 'acme'\n")
        self.assertEqual(len(self.satellite_rows()), 1)

    # --- invalid --type: exit 2 (argparse choices, no DB-level CHECK) -------

    def test_invalid_type_exits_2_and_writes_nothing(self):
        """project_type has no CHECK in the schema (SQLite can't ALTER one
        later, and no db has the table yet): argparse's --type choices is
        the only validation, refused before the db is ever touched."""
        r = self.run_mem("satellite", "add", "acme", "--repo", str(self.repo("repoTypeBogus")),
                         "--type", "bogus")
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIsNone(self.satellite_rows())

    # --- invalid slug: exit 6 -----------------------------------------------

    def test_invalid_slug_exits_6_and_writes_nothing(self):
        r = self.run_mem("satellite", "add", "Not_A_Slug", "--repo", str(self.repo("repoD")),
                         "--type", "development")
        self.assertEqual(r.returncode, 6, r.stderr)
        self.assertIn("slug", r.stderr)
        self.assertIsNone(self.satellite_rows())

    # --- bad paths: exit 7 --------------------------------------------------

    def test_relative_repo_exits_7_and_writes_nothing(self):
        r = self.run_mem("satellite", "add", "acme", "--repo", "relative/path",
                         "--type", "development")
        self.assertEqual(r.returncode, 7, r.stderr)
        self.assertIsNone(self.satellite_rows())

    def test_relative_repo_that_happens_to_exist_still_exits_7(self):
        """A relative --repo that resolves to a real directory (unlike the
        test above, where "relative/path" doesn't exist relative to the
        process cwd) must still be refused on the absolute-path check
        alone, not on the exists() check."""
        r = self.run_mem("satellite", "add", "acme", "--repo", ".",
                         "--type", "development")
        self.assertEqual(r.returncode, 7, r.stderr)
        self.assertIn("absolute", r.stderr)
        self.assertIsNone(self.satellite_rows())

    def test_missing_repo_exits_7_and_writes_nothing(self):
        missing = Path(self._tmp.name) / "does-not-exist"
        r = self.run_mem("satellite", "add", "acme", "--repo", str(missing),
                         "--type", "development")
        self.assertEqual(r.returncode, 7, r.stderr)
        self.assertIsNone(self.satellite_rows())

    def test_repo_that_is_a_file_exits_7_like_a_missing_path(self):
        """--repo must be an existing directory: a file at that path is
        refused the same way a missing path is, not accepted as a repo."""
        a_file = Path(self._tmp.name) / "not-a-directory"
        a_file.write_text("not a repo")
        r = self.run_mem("satellite", "add", "acme", "--repo", str(a_file),
                         "--type", "development")
        self.assertEqual(r.returncode, 7, r.stderr)
        self.assertIsNone(self.satellite_rows())

    def test_relative_vault_exits_7_and_writes_nothing(self):
        real = self.repo("repoE")
        r = self.run_mem("satellite", "add", "acme", "--repo", str(real),
                         "--type", "development", "--vault", "relative/vault")
        self.assertEqual(r.returncode, 7, r.stderr)
        self.assertIsNone(self.satellite_rows())

    def test_vault_is_stored_resolved(self):
        """--vault is stored through Path(vault).resolve(): a messy absolute
        path (a `..` segment here) is normalized before it hits the db, the
        way --repo already is. Not required to exist."""
        real = self.repo("repoVault")
        messy = Path(self._tmp.name) / "vault-dir" / ".." / "vault-notes"
        self.assertIn("..", str(messy))  # sanity: the input really is messy
        payload = self.ok_json("satellite", "add", "acme", "--repo", str(real),
                               "--type", "development", "--vault", str(messy))
        self.assertEqual(payload["vault_folder"], str(messy.resolve()))
        self.assertNotIn("..", payload["vault_folder"])

    # --- mother-only: exit 4 -------------------------------------------------

    def test_all_three_are_refused_in_a_satellite_with_exit_4(self):
        real = self.repo("repoF")
        for args in (["satellite", "add", "other", "--repo", str(real), "--type", "development"],
                     ["satellite", "list"],
                     ["satellite", "show", "other"]):
            with self.subTest(args=args):
                r = self.run_mem(*args, env=SAT)
                self.assertEqual(r.returncode, 4, r.stderr)
                self.assertIn("acme", r.stderr)
        self.assertIsNone(self.satellite_rows())

    # --- help ----------------------------------------------------------------

    def test_help_documents_satellite_commands_and_the_new_exit_codes(self):
        r = self.run_mem("--help")
        self.assertEqual(r.returncode, 0, r.stderr)
        for text in ("satellite", "Exit code 7", "Exit code 8"):
            with self.subTest(text=text):
                self.assertIn(text, r.stdout)


if __name__ == "__main__":
    unittest.main()
