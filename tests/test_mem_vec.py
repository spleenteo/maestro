"""Test per bin/mem-vec (strato semantico di memories.db).

Unit test stdlib-only + integration test che si auto-skippano se
sqlite-vec o Ollama non sono disponibili nell'interprete corrente.

The scope tests stub `vec_distance_cosine` with a plain SQLite function
instead of loading the real extension, so they run stdlib-only: only
visibility (which ids come back) is under test, never real distance.

Run (unit, stdlib):  python3 -m unittest tests.test_mem_vec -v
Run (integration):   uv run --with sqlite-vec python -m unittest tests.test_mem_vec -v
"""
import argparse
import contextlib
import importlib.util
import io
import itertools
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
_mem_vec_path = ROOT / "bin" / "mem-vec"
_spec = importlib.util.spec_from_file_location("mem_vec", _mem_vec_path)
if _spec is None:
    # Fallback for Python 3.9 where files without .py extension may not work
    from importlib.machinery import SourceFileLoader
    _loader = SourceFileLoader("mem_vec", str(_mem_vec_path))
    _spec = importlib.util.spec_from_loader("mem_vec", _loader)
mem_vec = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mem_vec)

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


def _has_sqlite_vec() -> bool:
    if not hasattr(sqlite3.Connection, "enable_load_extension"):
        return False
    try:
        import sqlite_vec  # noqa: F401
        return True
    except ImportError:
        return False


def _ollama_up() -> bool:
    try:
        urllib.request.urlopen(f"{mem_vec.OLLAMA_URL}/api/version", timeout=1)
        return True
    except OSError:
        return False


class TempDbCase(unittest.TestCase):
    """Fixture: db temporaneo con schema log reale e 2 righe note."""

    def setUp(self):
        os.environ.pop("MEM_DB", None)
        os.environ.pop("MEM_SCOPE", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "test.db"
        con = sqlite3.connect(self.db)
        con.executescript(LOG_SCHEMA)
        con.execute(
            "INSERT INTO log (date,title,description,tags,type) VALUES "
            "('2026-07-15','lavatrice rumorosa','vibrazione oblò in centrifuga',"
            "'casa,elettrodomestici','memory')")
        con.execute(
            "INSERT INTO log (date,title,type,status) VALUES "
            "('2026-07-15','chiamare tecnico caldaia','task','todo')")
        con.commit()
        con.close()
        os.environ["MEM_DB"] = str(self.db)

    def tearDown(self):
        os.environ.pop("MEM_DB", None)
        os.environ.pop("MEM_SCOPE", None)
        self._tmp.cleanup()


class TestCore(TempDbCase):
    def test_content_text_skips_missing_parts(self):
        self.assertEqual(mem_vec.content_text("t", None, "a,b"), "t\na,b")
        self.assertEqual(mem_vec.content_text("t", "d", None), "t\nd")

    def test_content_hash_varies_with_text_and_model(self):
        h1 = mem_vec.content_hash("m1", "ciao")
        self.assertEqual(h1, mem_vec.content_hash("m1", "ciao"))
        self.assertNotEqual(h1, mem_vec.content_hash("m2", "ciao"))
        self.assertNotEqual(h1, mem_vec.content_hash("m1", "ciào"))

    def test_two_vault_roots_sharing_a_relative_path_get_distinct_chunk_ids(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a"
            b = Path(tmp) / "b"
            for root in (a, b):
                root.mkdir()
                (root / "note.md").write_text("---\ntags: [x]\ndescription: d\n---\n\n## Same\n\ntext\n")
            ids_a = {c["chunk_id"] for c in mem_vec.chunk_file(a / "note.md", a)}
            ids_b = {c["chunk_id"] for c in mem_vec.chunk_file(b / "note.md", b)}
            self.assertTrue(ids_a and ids_b)
            self.assertEqual(ids_a & ids_b, set())
            self.assertEqual({c["root"] for c in mem_vec.chunk_file(a / "note.md", a)},
                             {mem_vec.root_key(a)})

    def test_walk_vault_does_not_follow_symlinks(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vault"
            outside = Path(tmp) / "outside"
            (root / "in").mkdir(parents=True)
            outside.mkdir()
            (root / "in" / "here.md").write_text("here\n")
            (outside / "secret.md").write_text("secret\n")
            (root / "linked").symlink_to(outside, target_is_directory=True)
            (root / "alias.md").symlink_to(outside / "secret.md")
            rels = sorted(str(p.relative_to(r)) for p, r in mem_vec.walk_vault([root]))
            self.assertEqual(rels, ["in/here.md"])

    def test_pack_unpack_roundtrip(self):
        v = [0.25, -1.5, 3.0]
        out = mem_vec.unpack(mem_vec.pack(v))
        for a, b in zip(v, out):
            self.assertAlmostEqual(a, b, places=6)

    def test_connect_creates_log_vec_idempotently(self):
        con = mem_vec.connect()
        row = con.execute(
            "SELECT name FROM sqlite_master WHERE name='log_vec'").fetchone()
        self.assertIsNotNone(row)
        con.close()
        con = mem_vec.connect()  # seconda volta: nessun errore
        con.close()

    def test_scan_state_lifecycle(self):
        con = mem_vec.connect()
        pending, stale, ok = mem_vec.scan_state(con, "m1")
        self.assertEqual((len(pending), len(stale), len(ok)), (2, 0, 0))
        item = pending[0]
        con.execute(
            "INSERT INTO log_vec VALUES (?,?,?,?,?,?)",
            (item["id"], "m1", 2, item["hash"],
             mem_vec.pack([1.0, 0.0]), "2026-07-15T12:00:00"))
        con.commit()
        pending, stale, ok = mem_vec.scan_state(con, "m1")
        self.assertEqual((len(pending), len(stale), len(ok)), (1, 0, 1))
        # modifica del testo → la riga diventa stale
        con.execute("UPDATE log SET title='lavatrice MOLTO rumorosa' WHERE id=?",
                    (item["id"],))
        con.commit()
        pending, stale, ok = mem_vec.scan_state(con, "m1")
        self.assertEqual((len(pending), len(stale), len(ok)), (1, 1, 0))
        con.close()


class TestChunker(unittest.TestCase):
    def test_parse_frontmatter_extracts_description_and_tags(self):
        text = ("---\n"
                "tags: [casa, persiane, preventivo]\n"
                "description: \"nota sul preventivo\"\n"
                "---\n\n"
                "# Titolo\ncorpo qui")
        meta, body = mem_vec.parse_frontmatter(text)
        self.assertEqual(meta["description"], "nota sul preventivo")
        self.assertEqual(meta["tags"], "casa, persiane, preventivo")
        self.assertTrue(body.startswith("# Titolo"))

    def test_parse_frontmatter_absent(self):
        meta, body = mem_vec.parse_frontmatter("nessun frontmatter\n")
        self.assertEqual(meta, {})
        self.assertEqual(body, "nessun frontmatter\n")

    def test_split_sections_by_heading(self):
        body = "preambolo\n\n## Persiane\ntesto A\n\n### Dettaglio\ntesto B\n\n## Fisco\ntesto C"
        secs = mem_vec.split_sections(body)
        headings = [s["heading"] for s in secs]
        self.assertEqual(headings, ["", "Persiane", "Dettaglio", "Fisco"])
        dettaglio = next(s for s in secs if s["heading"] == "Dettaglio")
        self.assertEqual(dettaglio["heading_path"], ["Persiane", "Dettaglio"])
        self.assertEqual(dettaglio["text"], "testo B")

    def test_split_sections_ignores_headings_in_code_fence(self):
        body = "## Reale\n```\n## finto dentro codice\n```\ncorpo"
        secs = mem_vec.split_sections(body)
        self.assertEqual([s["heading"] for s in secs], ["Reale"])

    def test_slugify(self):
        self.assertEqual(mem_vec.slugify("Persiane terrazza"), "persiane-terrazza")
        self.assertEqual(mem_vec.slugify("RMN & acufene!"), "rmn-acufene")

    def test_subsplit_short_returns_single(self):
        self.assertEqual(mem_vec.subsplit("a b c", 10, 2), ["a b c"])

    def test_subsplit_long_overlaps(self):
        text = " ".join(str(i) for i in range(10))
        parts = mem_vec.subsplit(text, 4, 1)
        self.assertGreater(len(parts), 1)
        self.assertTrue(parts[0].startswith("0 1 2 3"))
        # overlap: l'ultima parola di un chunk riappare nel successivo
        self.assertIn("3", parts[1].split())

    def test_build_embed_text_prepends_context(self):
        out = mem_vec.build_embed_text("descr file", ["Persiane", "Costi"],
                                       "casa, persiane", "1000 euro")
        self.assertTrue(out.startswith("descr file"))
        self.assertIn("Persiane › Costi", out)
        self.assertTrue(out.rstrip().endswith("1000 euro"))

    def test_chunk_file_produces_context_and_ids(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            f = root / "Logbook" / "2026-07-09.md"
            f.parent.mkdir(parents=True)
            f.write_text("---\ndescription: diario\ntags: [casa]\n---\n\n"
                         "## Persiane terrazza\npreventivo Mannino 1000 euro\n",
                         encoding="utf-8")
            chunks = mem_vec.chunk_file(f, root)
            self.assertEqual(len(chunks), 1)
            c = chunks[0]
            self.assertEqual(c["rel_path"], "Logbook/2026-07-09.md")
            self.assertEqual(c["heading"], "Persiane terrazza")
            self.assertEqual(c["anchor"], "persiane-terrazza")
            self.assertIn("diario", c["embed_text"])
            self.assertIn("Mannino", c["snippet"])
            self.assertEqual(len(c["chunk_id"]), 64)  # sha256 hex


class TestIgnoreWalk(unittest.TestCase):
    def _vault(self, d):
        root = Path(d)
        (root / "Logbook").mkdir(parents=True)
        (root / "Diario").mkdir()
        (root / "Logbook" / "a.md").write_text("# a\nx", encoding="utf-8")
        (root / "Diario" / "segreto.md").write_text("# s\ny", encoding="utf-8")
        (root / "note.md").write_text("# n\nz", encoding="utf-8")
        return root

    def test_walk_respects_mem_ignore(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = self._vault(d)
            (root / ".mem-ignore").write_text("Diario/\n", encoding="utf-8")
            rels = sorted(str(p.relative_to(r)) for p, r in mem_vec.walk_vault([root]))
            self.assertIn("Logbook/a.md", rels)
            self.assertIn("note.md", rels)
            self.assertNotIn("Diario/segreto.md", rels)

    def test_walk_skips_dot_dirs_always(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".obsidian").mkdir()
            (root / ".obsidian" / "x.md").write_text("# x", encoding="utf-8")
            (root / "ok.md").write_text("# ok", encoding="utf-8")
            rels = [str(p.relative_to(r)) for p, r in mem_vec.walk_vault([root])]
            self.assertEqual(rels, ["ok.md"])

    def test_load_ignore_glob_and_negation(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".mem-ignore").write_text(
                "*.excalidraw\nTemplate/\n", encoding="utf-8")
            ig = mem_vec.load_ignore(root)
            self.assertTrue(ig("disegno.excalidraw"))
            self.assertTrue(ig("Template/base.md"))
            self.assertFalse(ig("Logbook/a.md"))


@unittest.skipUnless(_has_sqlite_vec(), "sqlite-vec non disponibile in questo interprete")
class TestDistance(TempDbCase):
    def test_cosine_distance_via_sql(self):
        con = mem_vec.connect()
        mem_vec.load_vec(con)
        a = mem_vec.pack([1.0, 0.0])
        b = mem_vec.pack([0.0, 1.0])
        d_same = con.execute("SELECT vec_distance_cosine(?, ?)", (a, a)).fetchone()[0]
        d_orth = con.execute("SELECT vec_distance_cosine(?, ?)", (a, b)).fetchone()[0]
        self.assertAlmostEqual(d_same, 0.0, places=5)
        self.assertAlmostEqual(d_orth, 1.0, places=5)
        con.close()


@unittest.skipUnless(_ollama_up(), "Ollama non raggiungibile")
class TestOllamaEmbed(TempDbCase):
    def test_embed_pipeline_end_to_end(self):
        model = mem_vec.DEFAULT_MODEL
        con = mem_vec.connect()
        pending, _, _ = mem_vec.scan_state(con, model)
        self.assertEqual(len(pending), 2)
        con.close()
        rc = mem_vec.main(["embed"])
        self.assertEqual(rc, 0)
        con = mem_vec.connect()
        pending, stale, ok = mem_vec.scan_state(con, model)
        self.assertEqual((len(pending), len(stale), len(ok)), (0, 0, 2))
        dims = con.execute("SELECT dims FROM log_vec LIMIT 1").fetchone()[0]
        self.assertGreater(dims, 100)
        con.close()


@unittest.skipUnless(_has_sqlite_vec() and _ollama_up(), "servono sqlite-vec + Ollama")
class TestSemanticQueries(TempDbCase):
    def test_search_ranks_relevant_row_first(self):
        mem_vec.main(["embed"])
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mem_vec.main(["search", "elettrodomestico che fa rumore", "--limit", "2"])
        self.assertEqual(rc, 0)
        rows = json.loads(buf.getvalue().strip())
        self.assertEqual(rows[0]["title"], "lavatrice rumorosa")
        self.assertIn("score", rows[0])

    def test_similar_and_dupes_find_near_duplicate(self):
        con = mem_vec.connect()
        con.execute(
            "INSERT INTO log (date,title,description,tags,type) VALUES "
            "('2026-07-15','lavatrice fa rumore','oblò che vibra in centrifuga',"
            "'casa','memory')")
        con.commit()
        con.close()
        mem_vec.main(["embed"])
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(mem_vec.main(["similar", "1", "--limit", "2"]), 0)
        rows = json.loads(buf.getvalue().strip())
        self.assertEqual(rows[0]["id"], 3)  # il quasi-duplicato della lavatrice
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(mem_vec.main(["dupes", "--min-score", "0.7"]), 0)
        pairs = json.loads(buf.getvalue().strip())
        self.assertTrue(any({p["id_a"], p["id_b"]} == {1, 3} for p in pairs))


@unittest.skipUnless(_ollama_up(), "Ollama non raggiungibile")
class TestVaultEmbed(TempDbCase):
    def _vault(self):
        import tempfile
        self._vtmp = tempfile.TemporaryDirectory()
        root = Path(self._vtmp.name)
        (root / "Logbook").mkdir()
        (root / "Logbook" / "2026-07-09.md").write_text(
            "---\ndescription: diario del giorno\ntags: [casa]\n---\n\n"
            "## Persiane\npreventivo Mannino mille euro una mano\n\n"
            "## Karate\nallenamento kata Heian\n", encoding="utf-8")
        return root

    def test_embed_populates_vault_vec_incrementally(self):
        root = self._vault()
        rc = mem_vec.main(["embed", "--root", str(root)])
        self.assertEqual(rc, 0)
        con = mem_vec.connect()
        n = con.execute("SELECT COUNT(*) FROM vault_vec").fetchone()[0]
        self.assertEqual(n, 2)  # due sezioni
        # ri-eseguire senza modifiche → nessun nuovo embed (tutti ok)
        p, s, ok, orph = mem_vec.scan_vault_state(con, [root], mem_vec.DEFAULT_MODEL)
        self.assertEqual((len(p), len(s)), (0, 0))
        con.close()

    def test_modifying_one_section_reembeds_only_that(self):
        root = self._vault()
        mem_vec.main(["embed", "--root", str(root)])
        f = root / "Logbook" / "2026-07-09.md"
        f.write_text(f.read_text(encoding="utf-8").replace(
            "kata Heian", "kata Bassai"), encoding="utf-8")
        con = mem_vec.connect()
        p, s, ok, orph = mem_vec.scan_vault_state(
            con, [root], mem_vec.DEFAULT_MODEL, use_mtime_skip=False)
        self.assertEqual((len(p), len(s), len(ok)), (0, 1, 1))
        con.close()

    def test_deleting_file_orphans_its_chunks(self):
        root = self._vault()
        mem_vec.main(["embed", "--root", str(root)])
        (root / "Logbook" / "2026-07-09.md").unlink()
        con = mem_vec.connect()
        p, s, ok, orph = mem_vec.scan_vault_state(con, [root], mem_vec.DEFAULT_MODEL)
        self.assertEqual(len(orph), 2)
        con.close()
        mem_vec.main(["embed", "--root", str(root)])
        con = mem_vec.connect()
        self.assertEqual(con.execute("SELECT COUNT(*) FROM vault_vec").fetchone()[0], 0)
        con.close()

    def tearDown(self):
        super().tearDown()
        if hasattr(self, "_vtmp"):
            self._vtmp.cleanup()


@unittest.skipUnless(_has_sqlite_vec() and _ollama_up(), "servono sqlite-vec + Ollama")
class TestFusedSearch(TempDbCase):
    def test_search_fuses_memory_and_vault_with_refs(self):
        import contextlib, io, tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Logbook").mkdir()
            (root / "Logbook" / "2026-07-09.md").write_text(
                "---\ndescription: diario\ntags: [casa]\n---\n\n"
                "## Persiane terrazza\npreventivo Mannino mille euro\n",
                encoding="utf-8")
            mem_vec.main(["embed", "--root", str(root)])
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = mem_vec.main(["search", "verniciare le persiane",
                                   "--limit", "5", "--min-score", "0.2"])
            self.assertEqual(rc, 0)
            rows = json.loads(buf.getvalue().strip())
            sources = {r["source"] for r in rows}
            self.assertIn("vault", sources)
            vhit = next(r for r in rows if r["source"] == "vault")
            self.assertEqual(vhit["ref"], "Logbook/2026-07-09.md#Persiane terrazza")
            self.assertIn("score", vhit)

    def test_only_memory_excludes_vault(self):
        import contextlib, io, tempfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "n.md").write_text("## S\ntesto persiane\n", encoding="utf-8")
            mem_vec.main(["embed", "--root", str(root)])
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                mem_vec.main(["search", "persiane", "--only", "memory", "--min-score", "0"])
            rows = json.loads(buf.getvalue().strip())
            self.assertTrue(all(r["source"] == "memory" for r in rows))


def _stub_distance(a, b):
    """Stands in for vec_distance_cosine in the scope tests: only visibility
    (which ids come back) is under test here, never a real distance."""
    return 0.0


def _stub_load_vec(con):
    """Stands in for load_vec in command-level scope tests: registers the stub
    distance, so no sqlite-vec extension is needed."""
    con.create_function("vec_distance_cosine", 2, _stub_distance)


_UNIT_VEC = [1.0, 0.0]


def _sem_args(**kw):
    defaults = dict(type=None, status=None, since=None, until=None, tag=None,
                    model="m1", limit=50, min_score=0.0, scope=None, all_scopes=False)
    defaults.update(kw)
    return argparse.Namespace(**defaults)


def _assert_exit(testcase, code, fn, *args, **kwargs):
    """Run fn with stderr captured, assert it exits with `code`, return the
    captured message."""
    err = io.StringIO()
    with contextlib.redirect_stderr(err), testcase.assertRaises(SystemExit) as cm:
        fn(*args, **kwargs)
    testcase.assertEqual(cm.exception.code, code)
    return err.getvalue()


class ScopedRowsCase(TempDbCase):
    """Fixture: a migrated db (mem_vec.connect()), a stubbed
    vec_distance_cosine, and one embedded memory per (title, scope) in ROWS.
    The two legacy rows of TempDbCase have no embedding, so they never match."""

    ROWS = (("mother-a", None), ("acme-a", "acme"), ("other-a", "other"))

    def setUp(self):
        super().setUp()
        self.con = mem_vec.connect()
        _stub_load_vec(self.con)
        self.ids = {}
        for title, scope in self.ROWS:
            log_id = self.con.execute(
                "INSERT INTO log (date, title, type, scope) VALUES (?,?,?,?)",
                ("2026-09-14", title, "memory", scope)).lastrowid
            self.con.execute(
                "INSERT INTO log_vec (log_id, model, dims, content_hash, embedding, embedded_at) "
                "VALUES (?, 'm1', 2, 'h', ?, '2026-09-14T00:00:00')",
                (log_id, mem_vec.pack(_UNIT_VEC)))
            self.ids[title] = log_id
        self.con.commit()

    def tearDown(self):
        self.con.close()
        super().tearDown()

    def id_list(self, *titles):
        return sorted(self.ids[t] for t in titles)


class TestMemHitRowsScope(ScopedRowsCase):
    def hit_ids(self, **kw):
        rows = mem_vec._mem_hit_rows(self.con, mem_vec.pack(_UNIT_VEC), _sem_args(**kw))
        return sorted(r["id"] for r in rows)

    def test_mother_default_sees_only_the_null_scope(self):
        self.assertEqual(self.hit_ids(), self.id_list("mother-a"))

    def test_mother_scope_flag_narrows_to_that_scope(self):
        self.assertEqual(self.hit_ids(scope="acme"), self.id_list("acme-a"))

    def test_mother_all_scopes_sees_every_row(self):
        self.assertEqual(self.hit_ids(all_scopes=True), sorted(self.ids.values()))

    def test_other_filters_still_apply_inside_the_scope(self):
        self.assertEqual(self.hit_ids(all_scopes=True, type="task"), [])

    def test_satellite_sees_only_its_own_scope(self):
        with mock.patch.dict(os.environ, {"MEM_SCOPE": "acme"}):
            self.assertEqual(self.hit_ids(), self.id_list("acme-a"))

    def test_satellite_refuses_both_flags_with_exit_4(self):
        for flag in ({"scope": "other"}, {"all_scopes": True}):
            with self.subTest(flag=flag), \
                    mock.patch.dict(os.environ, {"MEM_SCOPE": "acme"}):
                msg = _assert_exit(self, mem_vec.mem_schema.EXIT_SCOPE_REFUSED,
                                   self.hit_ids, **flag)
                self.assertTrue(msg.startswith("mem-vec:"), msg)


class TestSimilarRowsScope(ScopedRowsCase):
    def similar_ids(self, anchor, **kw):
        rows = mem_vec._similar_rows(self.con, mem_vec.pack(_UNIT_VEC), "m1",
                                     self.ids[anchor], _sem_args(**kw))
        return sorted(r["id"] for r in rows)

    def test_mother_default_sees_only_the_null_scope(self):
        self.assertEqual(self.similar_ids("acme-a"), self.id_list("mother-a"))

    def test_mother_all_scopes_sees_every_row_but_the_anchor(self):
        self.assertEqual(self.similar_ids("mother-a", all_scopes=True),
                         self.id_list("acme-a", "other-a"))

    def test_mother_scope_flag_narrows_to_that_scope(self):
        self.assertEqual(self.similar_ids("mother-a", scope="other"),
                         self.id_list("other-a"))

    def test_satellite_sees_only_its_own_scope(self):
        with mock.patch.dict(os.environ, {"MEM_SCOPE": "acme"}):
            self.assertEqual(self.similar_ids("mother-a"), self.id_list("acme-a"))

    def test_satellite_refuses_scope_flag_with_exit_4(self):
        with mock.patch.dict(os.environ, {"MEM_SCOPE": "acme"}):
            msg = _assert_exit(self, mem_vec.mem_schema.EXIT_SCOPE_REFUSED,
                               self.similar_ids, "acme-a", scope="other")
        self.assertTrue(msg.startswith("mem-vec:"), msg)


class TestDupesRowsScope(ScopedRowsCase):
    ROWS = (("mother-a", None), ("mother-b", None), ("acme-a", "acme"),
            ("other-a", "other"))

    def pairs(self, **kw):
        rows = mem_vec._dupes_rows(self.con, _sem_args(**kw))
        return sorted(tuple(sorted((r["id_a"], r["id_b"]))) for r in rows)

    def test_mother_default_pairs_only_rows_of_the_null_scope(self):
        self.assertEqual(self.pairs(), [tuple(self.id_list("mother-a", "mother-b"))])

    def test_a_pair_needs_both_rows_in_scope(self):
        self.assertEqual(self.pairs(scope="acme"), [])

    def test_mother_all_scopes_pairs_every_combination(self):
        expected = sorted(itertools.combinations(sorted(self.ids.values()), 2))
        self.assertEqual(self.pairs(all_scopes=True), expected)

    def test_satellite_pairs_only_rows_of_its_own_scope(self):
        with mock.patch.dict(os.environ, {"MEM_SCOPE": "acme"}):
            self.assertEqual(self.pairs(), [])

    def test_satellite_refuses_scope_flag_with_exit_4(self):
        with mock.patch.dict(os.environ, {"MEM_SCOPE": "acme"}):
            msg = _assert_exit(self, mem_vec.mem_schema.EXIT_SCOPE_REFUSED,
                               self.pairs, scope="other")
        self.assertTrue(msg.startswith("mem-vec:"), msg)


class TestCmdSimilarAnchorScope(ScopedRowsCase):
    """cmd_similar end to end in process, with load_vec replaced by the stub."""

    ROWS = (("mother-a", None), ("acme-a", "acme"), ("acme-b", "acme"),
            ("other-a", "other"))

    def run_similar(self, anchor, *flags, env=None):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, env or {}), \
                mock.patch.object(mem_vec, "load_vec", _stub_load_vec), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = mem_vec.main(["similar", str(self.ids[anchor]), *flags])
        ids = sorted(h["id"] for h in json.loads(out.getvalue())) if rc == 0 else None
        return rc, ids, err.getvalue()

    def test_satellite_refuses_an_anchor_of_another_scope_with_exit_1(self):
        rc, ids, err = self.run_similar("mother-a", env={"MEM_SCOPE": "acme"})
        self.assertEqual(rc, 1)
        self.assertEqual(
            err, f"mem-vec: no row with id {self.ids['mother-a']} in scope acme\n")

    def test_satellite_anchors_on_its_own_rows(self):
        rc, ids, err = self.run_similar("acme-a", env={"MEM_SCOPE": "acme"})
        self.assertEqual(rc, 0, err)
        self.assertEqual(ids, self.id_list("acme-b"))

    def test_mother_accepts_an_anchor_of_any_scope_and_hits_follow_the_flags(self):
        self.assertEqual(self.run_similar("acme-a")[1], self.id_list("mother-a"))
        self.assertEqual(self.run_similar("acme-a", "--all-scopes")[1],
                         self.id_list("mother-a", "acme-b", "other-a"))
        self.assertEqual(self.run_similar("acme-a", "--scope", "other")[1],
                         self.id_list("other-a"))

    def test_satellite_flag_refusal_comes_before_the_anchor_check(self):
        with mock.patch.dict(os.environ, {"MEM_SCOPE": "acme"}):
            msg = _assert_exit(self, mem_vec.mem_schema.EXIT_SCOPE_REFUSED, mem_vec.main,
                               ["similar", str(self.ids["mother-a"]), "--all-scopes"])
        self.assertIn("--all-scopes", msg)


class TestAnchorInScope(ScopedRowsCase):
    """_anchor_in_scope now delegates to mem_schema.row_in_scope for a
    satellite, keeping its own mother-always-True shortcut (T2)."""

    def test_mother_accepts_any_row_including_a_nonexistent_id(self):
        self.assertTrue(mem_vec._anchor_in_scope(self.con, self.ids["acme-a"], None))
        self.assertTrue(mem_vec._anchor_in_scope(self.con, 999999, None))

    def test_satellite_accepts_only_its_own_scope(self):
        self.assertTrue(mem_vec._anchor_in_scope(self.con, self.ids["acme-a"], "acme"))
        self.assertFalse(mem_vec._anchor_in_scope(self.con, self.ids["mother-a"], "acme"))
        self.assertFalse(mem_vec._anchor_in_scope(self.con, self.ids["other-a"], "acme"))

    def test_satellite_rejects_a_nonexistent_id(self):
        self.assertFalse(mem_vec._anchor_in_scope(self.con, 999999, "acme"))


class TestScopeRefusalLeavesTheDbUntouched(TempDbCase):
    """TempDbCase's db has the legacy schema: connect() would add the scope
    column and the vec tables, so an identical file means no connect ran."""

    def assert_untouched(self, code, argv, env):
        before = self.db.read_bytes()
        with mock.patch.dict(os.environ, env), \
                mock.patch.object(mem_vec, "ollama_embed") as embed:
            msg = _assert_exit(self, code, mem_vec.main, argv)
        embed.assert_not_called()
        self.assertEqual(self.db.read_bytes(), before)
        return msg

    def test_embed_is_refused_in_a_satellite_with_exit_4(self):
        before = self.db.read_bytes()
        err = io.StringIO()
        with mock.patch.dict(os.environ, {"MEM_SCOPE": "acme"}), \
                contextlib.redirect_stderr(err):
            rc = mem_vec.main(["embed"])
        self.assertEqual(rc, mem_vec.mem_schema.EXIT_SCOPE_REFUSED)
        self.assertTrue(err.getvalue().startswith("mem-vec:"), err.getvalue())
        self.assertIn("acme", err.getvalue())
        self.assertEqual(self.db.read_bytes(), before)

    def test_embed_with_an_invalid_mem_scope_exits_6(self):
        msg = self.assert_untouched(mem_vec.mem_schema.EXIT_SCOPE_INVALID,
                                    ["embed"], {"MEM_SCOPE": "Bad!"})
        self.assertTrue(msg.startswith("mem-vec:"), msg)

    def test_read_commands_refuse_scope_flags_before_connecting(self):
        for argv in (["search", "q", "--scope", "other"],
                     ["search", "q", "--only", "vault", "--all-scopes"],
                     ["similar", "1", "--all-scopes"],
                     ["dupes", "--scope", "other"]):
            with self.subTest(argv=argv):
                msg = self.assert_untouched(mem_vec.mem_schema.EXIT_SCOPE_REFUSED,
                                            argv, {"MEM_SCOPE": "acme"})
                self.assertTrue(msg.startswith("mem-vec:"), msg)

    def test_embed_runs_in_the_mother(self):
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"MEM_VAULT_ROOTS": ""}), \
                contextlib.redirect_stdout(out):
            rc = mem_vec.main(["embed", "--status"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out.getvalue())["memory"]["total"], 2)


class TestParserScopeFlags(unittest.TestCase):
    def parse(self, args):
        with contextlib.redirect_stderr(io.StringIO()):
            return mem_vec.build_parser().parse_args(args)

    def test_search_similar_dupes_accept_scope_flags(self):
        self.assertEqual(self.parse(["search", "q", "--scope", "acme"]).scope, "acme")
        self.assertTrue(self.parse(["similar", "1", "--all-scopes"]).all_scopes)
        self.assertEqual(self.parse(["dupes", "--scope", "acme"]).scope, "acme")

    def test_scope_and_all_scopes_are_mutually_exclusive(self):
        for args in (["search", "q", "--scope", "acme", "--all-scopes"],
                     ["similar", "1", "--scope", "acme", "--all-scopes"],
                     ["dupes", "--scope", "acme", "--all-scopes"]):
            with self.subTest(args=args), self.assertRaises(SystemExit) as cm:
                self.parse(args)
            self.assertEqual(cm.exception.code, 2)

    def test_embed_does_not_accept_scope_flags(self):
        with self.assertRaises(SystemExit) as cm:
            self.parse(["embed", "--scope", "acme"])
        self.assertEqual(cm.exception.code, 2)

    def test_help_documents_scope_rules_and_exit_codes(self):
        text = mem_vec.build_parser().format_help()
        for needle in ("MEM_SCOPE", "--scope", "--all-scopes", "embed",
                       "Exit code 3", "Exit code 4", "Exit code 5", "Exit code 6"):
            with self.subTest(needle=needle):
                self.assertIn(needle, text)


@unittest.skipUnless(_has_sqlite_vec() and _ollama_up() and shutil.which("uv"),
                     "servono uv, sqlite-vec + Ollama")
class TestSemanticProbeRespectsScope(unittest.TestCase):
    """The V1 Done probe through bin/mem: a row saved by a satellite stays out
    of the mother's --semantic search until --scope opens it, and the
    satellite finds it."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.db = Path(cls._tmp.name) / "probe.db"
        con = sqlite3.connect(cls.db)
        con.executescript(LOG_SCHEMA)
        con.commit()
        con.close()
        cls.sat_ref = "#" + str(cls.saved("probe", "acme"))
        cls.mother_ref = "#" + str(cls.saved("probe", None))
        r = cls.run_mem("embed")
        if r.returncode != 0:
            raise AssertionError(f"bin/mem embed failed: {r.stderr}")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    @classmethod
    def run_mem(cls, *args, scope=None):
        env = {k: v for k, v in os.environ.items()
               if k not in ("MEM_DB", "MEM_SCOPE", "MEM_VAULT_ROOTS")}
        env["MEM_DB"] = str(cls.db)
        if scope:
            env["MEM_SCOPE"] = scope
        return subprocess.run([sys.executable, str(ROOT / "bin" / "mem"), *args],
                              capture_output=True, text=True, env=env)

    @classmethod
    def saved(cls, title, scope):
        r = cls.run_mem("save", title, "--json", scope=scope)
        if r.returncode != 0:
            raise AssertionError(f"bin/mem save failed: {r.stderr}")
        return json.loads(r.stdout)["id"]

    def refs(self, *flags, scope=None):
        r = self.run_mem("search", "probe", "--semantic", "--only", "memory",
                         *flags, scope=scope)
        self.assertEqual(r.returncode, 0, r.stderr)
        return {h["ref"] for h in json.loads(r.stdout)}

    def test_mother_search_finds_only_the_null_scope(self):
        self.assertEqual(self.refs(), {self.mother_ref})

    def test_mother_scope_flag_finds_the_satellite_row(self):
        self.assertEqual(self.refs("--scope", "acme"), {self.sat_ref})

    def test_satellite_search_finds_its_own_row(self):
        self.assertEqual(self.refs(scope="acme"), {self.sat_ref})


if __name__ == "__main__":
    unittest.main()
