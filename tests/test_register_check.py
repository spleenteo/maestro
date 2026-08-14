"""Test per bin/register-check (divieti meccanici del writing register).

Stdlib-only, nessuna dipendenza esterna: il checker non tocca db né rete.

Run: python3 -m unittest tests.test_register_check -v
"""
import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_path = ROOT / "bin" / "register-check"
_spec = importlib.util.spec_from_file_location("register_check", _path)
if _spec is None:
    from importlib.machinery import SourceFileLoader
    _loader = SourceFileLoader("register_check", str(_path))
    _spec = importlib.util.spec_from_loader("register_check", _loader)
rc = importlib.util.module_from_spec(_spec)
# @dataclass risolve le annotazioni via sys.modules[cls.__module__]: senza
# registrazione il modulo caricato da file non è raggiungibile.
sys.modules["register_check"] = rc
_spec.loader.exec_module(rc)


def rules(text, **kw):
    """Insieme dei numeri di divieto rilevati in text."""
    return {f.rule for f in rc.analyze(text, **kw)}


def findings(text, rule, **kw):
    return [f for f in rc.analyze(text, **kw) if f.rule == rule]


# ---------------------------------------------------------------------------
# Divieto 4 — em dash come pausa
# ---------------------------------------------------------------------------

class TestRule4EmDash(unittest.TestCase):

    def test_flags_em_dash_in_prose(self):
        self.assertIn(4, rules("The parser is slow — it reparses every call."))

    def test_reports_line_and_match(self):
        f = findings("ok line\nsecond — here\n", 4)[0]
        self.assertEqual(f.line, 2)
        self.assertEqual(f.kind, "violation")

    def test_ignores_fenced_code(self):
        text = "clean prose here\n\n```\nx = 1  # note — inline\n```\n"
        self.assertNotIn(4, rules(text))

    def test_ignores_tilde_fenced_code(self):
        text = "clean prose\n\n~~~python\nfoo()  # — dash\n~~~\n"
        self.assertNotIn(4, rules(text))

    def test_ignores_frontmatter(self):
        text = '---\ndescription: "a — b"\n---\n\nclean prose here.\n'
        self.assertNotIn(4, rules(text))

    def test_ignores_blockquote(self):
        self.assertNotIn(4, rules("> quoted text — from someone else\n"))

    def test_ignores_inline_code(self):
        self.assertNotIn(4, rules("run `mem save — x` to save.\n"))

    def test_ignores_heading_separator(self):
        self.assertNotIn(4, rules("## Context — what the audit found\n"))

    def test_line_numbers_survive_frontmatter(self):
        text = "---\ntags: [a]\n---\n\nprose — here\n"
        self.assertEqual(findings(text, 4)[0].line, 5)


# ---------------------------------------------------------------------------
# Divieto 5 — grassetto come enfasi
# ---------------------------------------------------------------------------

class TestRule5Bold(unittest.TestCase):

    def test_flags_bold_mid_sentence(self):
        self.assertIn(5, rules("You must **never** write to that path.\n"))

    def test_allows_label_with_colon(self):
        self.assertNotIn(5, rules("**Why**: the reader decides without opening.\n"))

    def test_allows_label_with_colon_inside_line(self):
        self.assertNotIn(5, rules("- **Rules**: never install agents directly.\n"))

    def test_allows_bold_opening_a_list_item(self):
        self.assertNotIn(5, rules("- **Identity** your name and adjectives\n"))

    def test_allows_bold_opening_a_line(self):
        self.assertNotIn(5, rules("**Session start** happens once per session.\n"))

    def test_allows_bold_in_table_cell(self):
        self.assertNotIn(5, rules("| 4 | em dash | **violation** |\n"))

    def test_ignores_fenced_code(self):
        self.assertNotIn(5, rules("prose\n\n```\nfoo(**kwargs)\n```\n"))


# ---------------------------------------------------------------------------
# Divieto 3 — parallelismo negativo
# ---------------------------------------------------------------------------

class TestRule3NegativeParallelism(unittest.TestCase):

    def test_en_its_not_x_its_y(self):
        self.assertIn(3, rules("It's not a bug, it's a missing guard.\n"))

    def test_en_not_just_x_but_y(self):
        self.assertIn(3, rules("The pass is not just cosmetic, but structural.\n"))

    def test_en_not_so_much_x_as_y(self):
        self.assertIn(3, rules("It is not so much slow as unpredictable.\n"))

    def test_it_non_e_x_e_y(self):
        self.assertIn(3, rules("Non è un bug, è una guardia mancante.\n"))

    def test_it_non_solo_x_ma_y(self):
        self.assertIn(3, rules("Non solo cosmetico, ma strutturale.\n"))

    def test_it_non_si_tratta_di(self):
        self.assertIn(3, rules("Non si tratta di stile, ma di leggibilità.\n"))

    def test_it_non_tanto_x_quanto_y(self):
        self.assertIn(3, rules("Non tanto lento quanto imprevedibile.\n"))

    def test_en_tailing_negation(self):
        # La forma invertita: "Y, not just X". È quella che compare in howto/09.
        self.assertIn(3, rules("It searches by meaning, not just keywords.\n"))

    def test_it_tailing_negation(self):
        self.assertIn(3, rules("Cerca per significato, non solo per parole.\n"))

    def test_en_tailing_negation_with_article(self):
        self.assertIn(3, rules("A model reads them, not a reader.\n"))

    def test_it_tailing_negation_with_article(self):
        self.assertIn(3, rules("Le legge un modello, non un lettore.\n"))

    def test_tailing_negation_needs_a_noun_phrase(self):
        # ", not yet" non è un parallelismo: nessun secondo termine opposto.
        self.assertNotIn(3, rules("The guard exists, not yet enforced.\n"))

    def test_plain_negation_is_clean(self):
        self.assertNotIn(3, rules("The module does not have permission tests.\n"))

    def test_plain_italian_negation_is_clean(self):
        self.assertNotIn(3, rules("Il modulo non ha test sui permessi.\n"))

    def test_kind_is_candidate(self):
        self.assertEqual(findings("It's not X, it's Y.\n", 3)[0].kind, "candidate")


# ---------------------------------------------------------------------------
# Divieto 6 — triadi
# ---------------------------------------------------------------------------

class TestRule6Triads(unittest.TestCase):

    def test_en_triad_with_and(self):
        self.assertIn(6, rules("The tool is fast, cheap, and reliable.\n"))

    def test_en_triad_without_oxford_comma(self):
        self.assertIn(6, rules("The tool is fast, cheap and reliable.\n"))

    def test_it_triad(self):
        self.assertIn(6, rules("Lo strumento è veloce, economico e affidabile.\n"))

    def test_pair_is_clean(self):
        self.assertNotIn(6, rules("The tool is fast and cheap.\n"))

    def test_four_item_list_is_clean(self):
        # Una triade è un elenco DI TRE, non tre voci consecutive dentro
        # un elenco più lungo.
        self.assertNotIn(6, rules("Covers logbook, TIL, documents and howto.\n"))

    def test_six_item_list_is_clean(self):
        text = ("Quotations, code, paths, wikilinks, numbers and proper "
                "nouns are off limits.\n")
        self.assertNotIn(6, rules(text))

    def test_italian_four_item_list_is_clean(self):
        self.assertNotIn(6, rules("Copre vault, logbook, canali e chat.\n"))

    def test_kind_is_candidate(self):
        self.assertEqual(findings("fast, cheap, and reliable.\n", 6)[0].kind, "candidate")

    def test_ignores_fenced_code(self):
        self.assertNotIn(6, rules("prose\n\n```\na, b, and c\n```\n"))


# ---------------------------------------------------------------------------
# Masking e regioni saltate
# ---------------------------------------------------------------------------

class TestMasking(unittest.TestCase):

    def test_wikilink_is_masked(self):
        self.assertNotIn(4, rules("see [[Nota — lunga]] for details\n"))

    def test_url_is_masked(self):
        self.assertNotIn(4, rules("see https://example.com/a—b for details\n"))

    def test_link_target_is_masked(self):
        self.assertNotIn(4, rules("see [the doc](./a—b.md) for details\n"))

    def test_frontmatter_only_at_top(self):
        # Un '---' a metà file è una regola orizzontale, non frontmatter.
        text = "prose here\n\n---\n\nmore prose — flagged\n"
        self.assertIn(4, rules(text))


# ---------------------------------------------------------------------------
# --skip e CLI
# ---------------------------------------------------------------------------

class TestSkip(unittest.TestCase):

    def test_skip_removes_rule(self):
        text = "It is slow — really. Not a bug, it's a guard.\n"
        self.assertNotIn(4, rules(text, skip={4}))

    def test_skip_leaves_others(self):
        text = "prose — here and fast, cheap, and reliable.\n"
        self.assertIn(6, rules(text, skip={4}))

    def test_parse_skip_accepts_comma_list(self):
        self.assertEqual(rc.parse_skip("4,6"), {4, 6})

    def test_parse_skip_empty(self):
        self.assertEqual(rc.parse_skip(None), set())

    def test_parse_skip_rejects_unknown_rule(self):
        with self.assertRaises(ValueError):
            rc.parse_skip("9")


class TestCli(unittest.TestCase):

    def _run(self, argv, stdin_text=""):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = rc.main(argv, stdin=io.StringIO(stdin_text))
        return code, buf.getvalue()

    def test_clean_stdin_exits_zero(self):
        code, out = self._run(["-"], "A clean sentence with no violations.\n")
        self.assertEqual(code, 0)

    def test_dirty_stdin_exits_one(self):
        code, out = self._run(["-"], "Slow — and wrong.\n")
        self.assertEqual(code, 1)
        self.assertIn("4", out)

    def test_json_output_is_parseable(self):
        import json
        code, out = self._run(["-", "--json"], "Slow — and wrong.\n")
        payload = json.loads(out)
        self.assertEqual(payload["findings"][0]["rule"], 4)
        self.assertEqual(payload["counts"]["4"], 1)

    def test_skip_flag_from_cli(self):
        code, out = self._run(["-", "--skip", "4"], "Slow — and wrong.\n")
        self.assertEqual(code, 0)

    def test_missing_file_exits_two(self):
        code, out = self._run(["/nonexistent/path/xyz.md"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
