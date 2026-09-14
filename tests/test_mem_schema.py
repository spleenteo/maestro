"""Tests for bin/mem_schema.py — the scope migration and the scope rules.

`ensure_scope` and the scope helpers are exercised in-process on temporary dbs
built from the legacy (pre-scope) `log` schema; `bin/mem` and `bin/mem-vec` are
exercised as they run for real: `bin/mem` through subprocess, `bin/mem-vec`
loaded from its file as tests/test_mem_vec.py does. MEM_DB and MEM_SCOPE are
removed from the environment in setUp and from every subprocess environment.

Run: python3 -m unittest tests.test_mem_schema -v
"""

import contextlib
import importlib.util
import io
import os
import re
import select
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin"
MEM = BIN / "mem"
MEM_VEC = BIN / "mem-vec"


def _load(name, path):
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


mem_schema = _load("mem_schema", BIN / "mem_schema.py")

# Same text as LOG_SCHEMA in tests/test_mem.py and tests/test_mem_vec.py.
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

# Runs a script as `python3 <script> <args>` would, with sqlite3.connect patched
# so the child writes to MEM_TEST_SIGNAL_FD: "L" right before it asks for the
# write lock (it has already read table_info without finding `scope`), "A" if
# it ever runs ALTER TABLE.
SIGNAL_BEFORE_LOCK = r"""
import os, runpy, sqlite3, sys
fd = int(os.environ["MEM_TEST_SIGNAL_FD"])
_connect = sqlite3.connect

class SignallingConnection(sqlite3.Connection):
    def execute(self, sql, *args):
        statement = sql.lstrip().upper()
        if statement.startswith("BEGIN IMMEDIATE"):
            os.write(fd, b"L")
        elif statement.startswith("ALTER TABLE"):
            os.write(fd, b"A")
        return super().execute(sql, *args)

def connect(*args, **kwargs):
    kwargs.setdefault("factory", SignallingConnection)
    return _connect(*args, **kwargs)

sqlite3.connect = connect
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")
"""


def clean_env(**extra):
    env = dict(os.environ)
    env.pop("MEM_DB", None)
    env.pop("MEM_SCOPE", None)
    env.update(extra)
    return env


class LegacyDbCase(unittest.TestCase):
    """Fixture: temp db with the legacy log schema and three known rows."""

    def setUp(self):
        os.environ.pop("MEM_DB", None)
        os.environ.pop("MEM_SCOPE", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db = Path(self._tmp.name) / "legacy.db"
        con = sqlite3.connect(self.db)
        con.executescript(LOG_SCHEMA)
        con.executemany(
            "INSERT INTO log (id, date, title, type, status) VALUES (?,?,?,?,?)",
            [(3, "2026-01-01", "memoria", "memory", None),
             (7, "2026-02-01", "task aperto", "task", "todo"),
             (12, "2026-03-01", "idea", "idea", "open")])
        con.commit()
        con.close()

    def open(self, **kwargs):
        con = sqlite3.connect(self.db, **kwargs)
        self.addCleanup(con.close)
        return con

    def columns(self):
        con = sqlite3.connect(self.db)
        try:
            return [r[1] for r in con.execute("PRAGMA table_info(log)")]
        finally:
            con.close()

    def ids(self):
        con = sqlite3.connect(self.db)
        try:
            return [r[0] for r in con.execute("SELECT id FROM log ORDER BY id")]
        finally:
            con.close()


class TestEnsureScope(LegacyDbCase):
    def test_adds_scope_column_once_and_keeps_rows(self):
        con = self.open()
        mem_schema.ensure_scope(con)
        self.assertEqual(self.columns().count("scope"), 1)
        self.assertEqual(self.ids(), [3, 7, 12])
        nulls = con.execute("SELECT COUNT(*) FROM log WHERE scope IS NULL").fetchone()[0]
        self.assertEqual(nulls, 3)

    def test_creates_the_log_scope_index(self):
        con = self.open()
        mem_schema.ensure_scope(con)
        names = [r[1] for r in con.execute("PRAGMA index_list(log)")]
        self.assertIn("log_scope", names)

    def test_second_call_changes_nothing(self):
        con = self.open()
        mem_schema.ensure_scope(con)
        before = con.execute("PRAGMA schema_version").fetchone()[0]
        mem_schema.ensure_scope(con)
        after = con.execute("PRAGMA schema_version").fetchone()[0]
        self.assertEqual(before, after)
        self.assertFalse(con.in_transaction)

    def test_rechecks_columns_under_the_lock_and_skips_the_alter(self):
        """Another process adds `scope` between the first table_info read and
        BEGIN IMMEDIATE: the read repeated under the lock sees it, so the
        migrating connection never runs ALTER TABLE."""
        db = self.db
        executed = []

        class OtherProcessMigratesFirst(sqlite3.Connection):
            def execute(self, sql, *args):
                executed.append(sql)
                if sql.startswith("BEGIN IMMEDIATE"):
                    other = sqlite3.connect(db)
                    other.execute("ALTER TABLE log ADD COLUMN scope TEXT")
                    other.commit()
                    other.close()
                return super().execute(sql, *args)

        con = self.open(factory=OtherProcessMigratesFirst)
        mem_schema.ensure_scope(con)
        self.assertEqual([s for s in executed if s.startswith("ALTER")], [])
        self.assertFalse(con.in_transaction)
        self.assertEqual(self.columns().count("scope"), 1)

    def test_duplicate_column_from_a_stale_read_counts_as_done(self):
        """If table_info reports no `scope` although another process already
        added it, the ALTER fails with "duplicate column name": ensure_scope
        rolls back, raises nothing, and releases the lock."""
        self.open().execute("ALTER TABLE log ADD COLUMN scope TEXT")

        class StaleColumns(sqlite3.Connection):
            def execute(self, sql, *args):
                if sql.startswith("PRAGMA table_info"):
                    return super().execute("SELECT 0, 'id'")
                return super().execute(sql, *args)

        con = self.open(factory=StaleColumns)
        mem_schema.ensure_scope(con)
        self.assertFalse(con.in_transaction)
        self.assertEqual(self.columns().count("scope"), 1)

    def test_other_errors_propagate_and_release_the_lock(self):
        con = self.open()
        con.execute("DROP TABLE log")
        with self.assertRaises(sqlite3.OperationalError):
            mem_schema.ensure_scope(con)
        self.assertFalse(con.in_transaction)


class TestMemMigratesOnConnect(LegacyDbCase):
    def run_mem(self, *args):
        return subprocess.run(
            [sys.executable, str(MEM), *args],
            capture_output=True, text=True, env=clean_env(MEM_DB=str(self.db)))

    def test_any_command_migrates_a_legacy_db(self):
        r = self.run_mem("stats", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.columns().count("scope"), 1)
        self.assertEqual(self.ids(), [3, 7, 12])

    def test_process_waiting_on_the_lock_finds_the_column_added_meanwhile(self):
        holder = self.open(isolation_level=None)
        holder.execute("BEGIN IMMEDIATE")
        read_fd, write_fd = os.pipe()
        child = subprocess.Popen(
            [sys.executable, "-c", SIGNAL_BEFORE_LOCK, str(MEM), "stats", "--json"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            pass_fds=(write_fd,),
            env=clean_env(MEM_DB=str(self.db), MEM_TEST_SIGNAL_FD=str(write_fd)))
        os.close(write_fd)
        self.addCleanup(os.close, read_fd)
        ready, _, _ = select.select([read_fd], [], [], 30)
        signal = os.read(read_fd, 1) if ready else b""
        if signal != b"L":
            child.kill()
            _, err = child.communicate()
            self.fail(f"child never reached the lock: {err}")

        holder.execute("ALTER TABLE log ADD COLUMN scope TEXT")
        holder.execute("COMMIT")

        _, err = child.communicate(timeout=60)
        self.assertEqual(child.returncode, 0, err)
        self.assertEqual(self.columns().count("scope"), 1)
        # The child has exited, so the pipe is at EOF after whatever it wrote.
        self.assertEqual(os.read(read_fd, 16), b"", "child ran ALTER TABLE")


class TestMemVecMigratesOnConnect(LegacyDbCase):
    def test_connect_adds_the_scope_column(self):
        mem_vec = _load("mem_vec_for_schema_test", MEM_VEC)
        with mock.patch.dict(os.environ, {"MEM_DB": str(self.db)}):
            con = mem_vec.connect()
        self.addCleanup(con.close)
        self.assertEqual(self.columns().count("scope"), 1)


class TestMissingSchemaModule(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.bin = Path(self._tmp.name) / "bin"
        self.bin.mkdir()

    def run_copy(self, script, *args):
        copy = self.bin / script.name
        shutil.copy(script, copy)
        return subprocess.run(
            [sys.executable, str(copy), *args],
            capture_output=True, text=True, env=clean_env())

    def assert_missing_schema(self, r):
        self.assertEqual(r.returncode, 5, r.stderr)
        self.assertEqual(len(r.stderr.strip().splitlines()), 1, r.stderr)
        self.assertIn("bin/mem_schema.py", r.stderr)
        self.assertIn("~/.maestro/bin/mem_schema.py", r.stderr)

    def test_mem_without_the_module_exits_5_naming_it(self):
        self.assert_missing_schema(self.run_copy(MEM, "stats"))

    def test_mem_vec_without_the_module_exits_5_naming_it(self):
        self.assert_missing_schema(self.run_copy(MEM_VEC, "dupes"))


class TestSchemaApiMismatch(unittest.TestCase):
    """A newer bin/mem or bin/mem-vec next to an older (or newer)
    bin/mem_schema.py: the SCHEMA_API guard must catch it before any command
    runs, the same way the missing-module guard does."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.bin = Path(self._tmp.name) / "bin"
        self.bin.mkdir()

    def _schema_source(self, value):
        text = (BIN / "mem_schema.py").read_text()
        new_text, n = re.subn(r"(?m)^SCHEMA_API = \d+", f"SCHEMA_API = {value}", text)
        self.assertEqual(n, 1, "bin/mem_schema.py has no SCHEMA_API constant to rewrite")
        return new_text

    def _schema_source_without_api(self):
        text = (BIN / "mem_schema.py").read_text()
        new_text, n = re.subn(r"(?m)^SCHEMA_API = \d+\n", "", text)
        self.assertEqual(n, 1, "bin/mem_schema.py has no SCHEMA_API constant to remove")
        return new_text

    def run_with_schema(self, script, schema_source, *args):
        shutil.copy(script, self.bin / script.name)
        (self.bin / "mem_schema.py").write_text(schema_source)
        return subprocess.run(
            [sys.executable, str(self.bin / script.name), *args],
            capture_output=True, text=True, env=clean_env())

    def assert_api_mismatch(self, r):
        self.assertEqual(r.returncode, 5, r.stderr)
        self.assertEqual(len(r.stderr.strip().splitlines()), 1, r.stderr)
        self.assertIn("bin/mem_schema.py", r.stderr)
        self.assertIn("bin/mem, bin/mem-vec and bin/mem_schema.py", r.stderr)

    def test_mem_with_a_different_schema_api_exits_5(self):
        self.assert_api_mismatch(
            self.run_with_schema(MEM, self._schema_source(999), "stats"))

    def test_mem_with_a_schema_module_missing_the_attribute_exits_5(self):
        self.assert_api_mismatch(
            self.run_with_schema(MEM, self._schema_source_without_api(), "stats"))

    def test_mem_vec_with_a_different_schema_api_exits_5(self):
        self.assert_api_mismatch(
            self.run_with_schema(MEM_VEC, self._schema_source(999), "dupes"))

    def test_mem_vec_with_a_schema_module_missing_the_attribute_exits_5(self):
        self.assert_api_mismatch(
            self.run_with_schema(MEM_VEC, self._schema_source_without_api(), "dupes"))


class TestCurrentScope(unittest.TestCase):
    def scope_with(self, value):
        env = clean_env()
        if value is not None:
            env["MEM_SCOPE"] = value
        with mock.patch.dict(os.environ, env, clear=True):
            return mem_schema.current_scope()

    def test_unset_is_the_mother(self):
        self.assertIsNone(self.scope_with(None))

    def test_blank_is_the_mother(self):
        self.assertIsNone(self.scope_with("  "))

    def test_value_is_stripped(self):
        self.assertEqual(self.scope_with(" acme\n"), "acme")

    def test_digits_and_inner_hyphens_are_valid(self):
        self.assertEqual(self.scope_with("app-2"), "app-2")

    def test_invalid_values_exit_6_with_a_message(self):
        for value in ("Acme", "-acme", "ac me", "a_b", "../x"):
            with self.subTest(value=value):
                err = io.StringIO()
                with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
                    self.scope_with(value)
                self.assertEqual(cm.exception.code, mem_schema.EXIT_SCOPE_INVALID)
                self.assertIn("MEM_SCOPE", err.getvalue())

    def test_exit_codes_have_the_planned_values(self):
        self.assertEqual(mem_schema.EXIT_SCOPE_REFUSED, 4)
        self.assertEqual(mem_schema.EXIT_SCOPE_INVALID, 6)


class TestScopeClause(unittest.TestCase):
    def test_mother_filters_on_null(self):
        self.assertEqual(mem_schema.scope_clause(None), ("scope IS NULL", []))

    def test_satellite_filters_on_its_slug(self):
        self.assertEqual(mem_schema.scope_clause("acme"), ("scope = ?", ["acme"]))

    def test_all_scopes_filters_nothing(self):
        self.assertEqual(mem_schema.scope_clause(None, all_scopes=True), ("1=1", []))
        self.assertEqual(mem_schema.scope_clause("acme", all_scopes=True), ("1=1", []))

    def test_column_can_be_qualified(self):
        self.assertEqual(mem_schema.scope_clause(None, column="la.scope"),
                         ("la.scope IS NULL", []))
        self.assertEqual(mem_schema.scope_clause("acme", column="la.scope"),
                         ("la.scope = ?", ["acme"]))


class TestCheckScope(unittest.TestCase):
    def test_valid_slug_passes_through(self):
        self.assertEqual(mem_schema.check_scope("app-2", "--scope"), "app-2")

    def test_invalid_slug_exits_6_naming_its_source(self):
        for value in ("", "Acme", "-x", "a_b"):
            with self.subTest(value=value):
                err = io.StringIO()
                with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
                    mem_schema.check_scope(value, "--scope")
                self.assertEqual(cm.exception.code, mem_schema.EXIT_SCOPE_INVALID)
                self.assertIn("--scope", err.getvalue())

    def test_prog_defaults_to_mem(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit):
            mem_schema.check_scope("Bad!", "--scope")
        self.assertTrue(err.getvalue().startswith("mem:"))

    def test_prog_names_the_caller(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit):
            mem_schema.check_scope("Bad!", "--scope", prog="mem-vec")
        self.assertTrue(err.getvalue().startswith("mem-vec:"))


class TestCurrentScopeProg(unittest.TestCase):
    def test_prog_names_the_caller_in_invalid_scope_message(self):
        err = io.StringIO()
        with mock.patch.dict(os.environ, clean_env(MEM_SCOPE="Bad!"), clear=True):
            with contextlib.redirect_stderr(err), self.assertRaises(SystemExit):
                mem_schema.current_scope(prog="mem-vec")
        self.assertTrue(err.getvalue().startswith("mem-vec:"))


class TestReadClause(unittest.TestCase):
    def clause(self, *args, mem_scope=None, **kwargs):
        env = clean_env()
        if mem_scope is not None:
            env["MEM_SCOPE"] = mem_scope
        with mock.patch.dict(os.environ, env, clear=True):
            return mem_schema.read_clause(*args, **kwargs)

    def assert_exits(self, code, *args, **kwargs):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
            self.clause(*args, **kwargs)
        self.assertEqual(cm.exception.code, code)
        return err.getvalue()

    def test_mother_reads_null_by_default(self):
        self.assertEqual(self.clause(), ("scope IS NULL", []))

    def test_mother_all_default_reads_every_scope(self):
        self.assertEqual(self.clause(mother_all=True), ("1=1", []))

    def test_mother_scope_flag_reads_that_scope(self):
        self.assertEqual(self.clause("acme"), ("scope = ?", ["acme"]))
        self.assertEqual(self.clause("acme", mother_all=True), ("scope = ?", ["acme"]))

    def test_mother_all_scopes_flag_reads_every_scope(self):
        self.assertEqual(self.clause(None, True), ("1=1", []))

    def test_mother_invalid_scope_flag_exits_6(self):
        self.assertIn("--scope", self.assert_exits(mem_schema.EXIT_SCOPE_INVALID, "Bad!"))

    def test_satellite_reads_its_scope_even_where_the_mother_reads_all(self):
        self.assertEqual(self.clause(mem_scope="acme"), ("scope = ?", ["acme"]))
        self.assertEqual(self.clause(mem_scope="acme", mother_all=True),
                         ("scope = ?", ["acme"]))

    def test_satellite_refuses_both_flags_with_exit_4(self):
        for args in (("other",), (None, True)):
            with self.subTest(args=args):
                msg = self.assert_exits(mem_schema.EXIT_SCOPE_REFUSED, *args,
                                        mem_scope="acme")
                self.assertIn("acme", msg)

    def test_column_can_be_qualified(self):
        self.assertEqual(self.clause(column="la.scope"), ("la.scope IS NULL", []))

    def test_prog_names_the_caller_in_the_refusal_message(self):
        msg = self.assert_exits(mem_schema.EXIT_SCOPE_REFUSED, "other",
                                mem_scope="acme", prog="mem-vec")
        self.assertTrue(msg.startswith("mem-vec:"))

    def test_prog_names_the_caller_in_the_invalid_scope_message(self):
        msg = self.assert_exits(mem_schema.EXIT_SCOPE_INVALID, "Bad!", prog="mem-vec")
        self.assertTrue(msg.startswith("mem-vec:"))


class TestSchemaApiValue(unittest.TestCase):
    def test_schema_api_is_2(self):
        """T2 adds ensure_satellites and row_in_scope: the bump instances rely
        on to tell an old bin/mem_schema.py apart from this one."""
        self.assertEqual(mem_schema.SCHEMA_API, 2)


class TestEnsureSatellites(unittest.TestCase):
    """ensure_satellites is called only by `satellite add`: `list`/`show`
    must read the table as it is and never call it (see TestSatellite in
    tests/test_mem.py for the db-without-the-table case)."""

    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.addCleanup(self.con.close)

    def table_exists(self):
        return self.con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='satellites'"
        ).fetchone() is not None

    def columns(self):
        return [r[1] for r in self.con.execute("PRAGMA table_info(satellites)")]

    def insert(self, scope="acme", repo_path="/a", project_type="development"):
        self.con.execute(
            "INSERT INTO satellites (scope, repo_path, project_type, created) "
            "VALUES (?, ?, ?, '2026-09-14T08:00:00')",
            (scope, repo_path, project_type))

    def test_creates_the_table_with_the_planned_columns(self):
        mem_schema.ensure_satellites(self.con)
        self.assertTrue(self.table_exists())
        self.assertEqual(
            self.columns(),
            ["scope", "repo_path", "project_type", "mandate", "method",
             "constraints", "language", "vault_folder", "created"])

    def test_scope_is_the_primary_key(self):
        mem_schema.ensure_satellites(self.con)
        self.insert(scope="acme", repo_path="/a")
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert(scope="acme", repo_path="/b")

    def test_repo_path_is_unique(self):
        mem_schema.ensure_satellites(self.con)
        self.insert(scope="acme", repo_path="/a")
        with self.assertRaises(sqlite3.IntegrityError):
            self.insert(scope="other", repo_path="/a")

    def test_project_type_has_no_db_level_check(self):
        """SQLite can't ALTER a CHECK later, and no db has the table yet
        (unreleased): the CHECK constraint was dropped from the schema, so a
        value outside {ux,consulting,development} inserts cleanly here.
        --type argparse choices is the only validation now (tests/test_mem.py
        TestSatellite covers the CLI rejecting an invalid --type)."""
        mem_schema.ensure_satellites(self.con)
        self.insert(project_type="bogus")
        rows = [r[0] for r in self.con.execute("SELECT project_type FROM satellites")]
        self.assertEqual(rows, ["bogus"])

    def test_second_call_is_a_no_op_and_keeps_rows(self):
        mem_schema.ensure_satellites(self.con)
        self.insert()
        mem_schema.ensure_satellites(self.con)
        rows = [r[0] for r in self.con.execute("SELECT scope FROM satellites")]
        self.assertEqual(rows, ["acme"])


class TestRowInScope(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.addCleanup(self.con.close)
        self.con.executescript(LOG_SCHEMA)
        mem_schema.ensure_scope(self.con)
        self.mother_id = self.con.execute(
            "INSERT INTO log (date, title, type) VALUES "
            "('2026-09-14', 'nota madre', 'memory')").lastrowid
        self.sat_id = self.con.execute(
            "INSERT INTO log (date, title, type, scope) VALUES "
            "('2026-09-14', 'nota acme', 'memory', 'acme')").lastrowid
        self.con.commit()

    def test_none_scope_matches_a_row_in_any_scope(self):
        self.assertTrue(mem_schema.row_in_scope(self.con, self.mother_id, None))
        self.assertTrue(mem_schema.row_in_scope(self.con, self.sat_id, None))

    def test_none_scope_is_false_for_a_missing_id(self):
        self.assertFalse(mem_schema.row_in_scope(self.con, 9999, None))

    def test_a_slug_matches_only_its_own_rows(self):
        self.assertTrue(mem_schema.row_in_scope(self.con, self.sat_id, "acme"))
        self.assertFalse(mem_schema.row_in_scope(self.con, self.mother_id, "acme"))
        self.assertFalse(mem_schema.row_in_scope(self.con, self.sat_id, "other"))

    def test_a_slug_is_false_for_a_missing_id(self):
        self.assertFalse(mem_schema.row_in_scope(self.con, 9999, "acme"))


class TestEmbedRefused(unittest.TestCase):
    """The wording bin/mem and bin/mem-vec share for the embed refusal
    message, each prefixing its own prog name."""

    def test_template_names_the_scope_and_the_mother(self):
        msg = mem_schema.EMBED_REFUSED.format(scope="acme")
        self.assertIn("acme", msg)
        self.assertIn("mother", msg)


if __name__ == "__main__":
    unittest.main()
