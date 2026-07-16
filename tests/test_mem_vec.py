"""Test per bin/mem-vec (strato semantico di memories.db).

Unit test stdlib-only + integration test che si auto-skippano se
sqlite-vec o Ollama non sono disponibili nell'interprete corrente.

Run (unit, stdlib):  python3 -m unittest tests.test_mem_vec -v
Run (integration):   uv run --with sqlite-vec python -m unittest tests.test_mem_vec -v
"""
import importlib.util
import json
import os
import sqlite3
import tempfile
import unittest
import urllib.request
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
