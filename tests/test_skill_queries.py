"""tests/test_skill_queries.py — every `bin/mem` invocation documented in the
skills and agents that read or write `log` runs against a seeded fixture and
returns the rows its flags imply.

Extraction is text-only, no YAML/Markdown parser: fenced ```bash blocks in the
Markdown files, and `- "bin/mem ..."` list items in channels.yaml, filtered to
lines starting with `bin/mem` (a bare `sqlite3 ...` line is simply not
extracted — the separate TestNoRawSqlite3 below is what turns that into a
failure). Placeholders (`<start>`, `<end>`, `<name>`, …) are substituted from
the fixed PLACEHOLDERS map before each line runs; a relative date written
directly in a flag's value (`--since=-7d`) is resolved the same way bin/mem's
own parser resolves it. A new file joins SOURCE_FILES; a new placeholder
joins PLACEHOLDERS.

Run: python3 -m unittest tests.test_skill_queries -v
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "mem"

# Every file that reads or writes `log`, as required by the V2 slice packet's
# `rg` gate over `.claude/`. Task 4 adds `howto/01-skills.md`.
SOURCE_FILES = [
    ROOT / ".claude" / "skills" / "logbook" / "SKILL.md",
    ROOT / ".claude" / "agents" / "scheduler.md",
    ROOT / ".claude" / "agents" / "data" / "channels.yaml",
    ROOT / ".claude" / "skills" / "add-external-app" / "SKILL.md",
    ROOT / "howto" / "01-skills.md",
]

# The bin/mem subcommand each file is expected to document — the RED signal
# for "commands missing" (a file with no bin/mem lines yet fails here before
# it fails on row content). Order doesn't matter: the assertion below sorts
# both sides.
EXPECTED_SUBCOMMANDS = {
    ROOT / ".claude" / "skills" / "logbook" / "SKILL.md": ["today", "today", "today"],
    ROOT / ".claude" / "agents" / "scheduler.md": ["todo", "search", "search", "search"],
    ROOT / ".claude" / "agents" / "data" / "channels.yaml": ["todo", "search", "search", "search"],
    ROOT / ".claude" / "skills" / "add-external-app" / "SKILL.md": ["save"],
    ROOT / "howto" / "01-skills.md": ["search"],
}


# ---------------------------------------------------------------------------
# Fixture dates — relative to today, so the test is correct on whatever day it
# runs, with windows that never overlap.
# ---------------------------------------------------------------------------

TODAY_DATE = date.today()


def _d(days_ago: int) -> str:
    return (TODAY_DATE - timedelta(days=days_ago)).isoformat()


def _effective_today(now: datetime | None = None) -> str:
    """Mirrors bin/mem's effective_today(): the early-morning rule (00:00-06:00
    local counts as the previous day). Called at assertion time by default
    (`now=None` reads the live clock), like bin/mem's own default `today`
    does — not the fixed TODAY_DATE above, which a run started right before
    midnight and finished right after would already disagree with. A regression
    test passes an explicit `now` built from a chosen TZ offset instead of the
    live clock, so the early-morning branch is exercised deterministically."""
    if now is None:
        now = datetime.now()
    if now.hour < 6:
        return (now.date() - timedelta(days=1)).isoformat()
    return now.date().isoformat()


# Whole-hour Etc/GMT zones actually shipped by tzdata (Etc/GMT-14..Etc/GMT+12,
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


def _pick_early_morning_tz() -> tuple[str, int] | tuple[None, None]:
    """An (Etc/GMT zone, UTC offset in hours) whose local time is between
    00:00 and 06:00 right now, computed from the current UTC hour so the
    choice is deterministic at any time of day the gate happens to run —
    this is how the reviewer reproduced the bug, with TZ=Etc/GMT-12 at local
    01:16. Among the offsets that land in the window, the one closest to its
    middle (03:00) is preferred, to absorb the gap between picking the zone
    here and the subprocess under test reading its own clock a moment later.
    (None, None) when no whole-hour Etc/GMT offset lands in the window —
    doesn't happen in practice (every UTC hour has an exact 03:00 match
    within -12..+14), but callers skip rather than assume it can't."""
    utc_hour = datetime.now(timezone.utc).hour
    best: tuple[int, int] | None = None  # (distance from 03:00, offset)
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


TODAY = _d(0)
YESTERDAY = _d(1)
MID = _d(10)          # "inside the window" anchor for due/completed/date checks
END = _d(7)            # window end (closer to today)
START = _d(20)         # window start (further in the past)
BEFORE = _d(25)        # before the window
DAY = _d(30)           # the logbook's "a target day other than today"


PLACEHOLDERS = {
    "start": START,
    "end": END,
    "DAY": DAY,
    "name": "acme",
    "absolute-path": "/tmp/acme-project",
    "FROM_VERSION": "v2026.08.14.1",
    "TO_VERSION": "v2026.09.14.1",
    "N": "3",
    "M": "1",
    "list of updated/added files, comma-separated": "CLAUDE.md, howto/04-memory-and-integrations.md",
    "list": "none",
}

_PLACEHOLDER_RE = re.compile(r"<([^<>]+)>")


def substitute(line: str) -> str:
    """Replace every `<...>` token with PLACEHOLDERS[token]. An unknown token
    fails loudly instead of shipping a literal `<...>` into bin/mem's argv."""

    def repl(m: re.Match) -> str:
        key = m.group(1)
        if key not in PLACEHOLDERS:
            raise AssertionError(
                f"no fixture value for placeholder <{key}> in line: {line!r}; "
                "add it to PLACEHOLDERS"
            )
        return PLACEHOLDERS[key]

    return _PLACEHOLDER_RE.sub(repl, line)


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

_BASH_FENCE_RE = re.compile(r"```bash\n(.*?)```", re.DOTALL)
_YAML_COMMAND_RE = re.compile(r'^\s*-\s*"(bin/mem[^"]*)"\s*$')


def commands_in(path: Path) -> list[str]:
    """Every raw `bin/mem ...` line documented in `path` (pre-substitution)."""
    text = path.read_text()
    if path.suffix == ".yaml":
        return [m.group(1) for raw in text.splitlines()
                if (m := _YAML_COMMAND_RE.match(raw))]
    lines = []
    for block in _BASH_FENCE_RE.findall(text):
        for raw in block.splitlines():
            line = raw.strip()
            if line.startswith("bin/mem"):
                lines.append(line)
    return lines


def collect_commands() -> list[tuple[str, str]]:
    """[(relative file path, raw line), ...] across every file in SOURCE_FILES."""
    items = []
    for path in SOURCE_FILES:
        rel = str(path.relative_to(ROOT))
        for line in commands_in(path):
            items.append((rel, line))
    return items


# ---------------------------------------------------------------------------
# Fixture db: mother rows (scope NULL) and satellite rows (scope "acme"),
# spanning the windows above.
# ---------------------------------------------------------------------------

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
  priority TEXT DEFAULT 'normal',
  scope TEXT
);
CREATE INDEX log_scope ON log(scope);
"""

FIXTURE_ROWS = [
    dict(key="mother_task_in_window", date=MID, title="Mother task due inside the window",
         type="task", status="todo", due_date=START, scope=None),
    dict(key="mother_task_out_of_window", date=MID, title="Mother task due after the window",
         type="task", status="todo", due_date=TODAY, scope=None),
    dict(key="mother_task_no_due", date=MID, title="Mother task with no due date",
         type="task", status="todo", due_date=None, scope=None),
    dict(key="acme_task_in_window", date=MID, title="Acme task due inside the window",
         type="task", status="todo", due_date=MID, scope="acme"),
    dict(key="mother_done_in_window", date=MID, title="Mother task done inside the window",
         type="task", status="done", completed_date=MID, scope=None),
    dict(key="mother_done_before_window", date=MID, title="Mother task done before the window",
         type="task", status="done", completed_date=BEFORE, scope=None),
    dict(key="acme_done_in_window", date=MID, title="Acme task done inside the window",
         type="task", status="done", completed_date=MID, scope="acme"),
    dict(key="mother_memory_in_window", date=MID, title="Mother memory inside the window",
         type="memory", scope=None),
    dict(key="mother_memory_before_window", date=BEFORE, title="Mother memory before the window",
         type="memory", scope=None),
    dict(key="acme_memory_in_window", date=MID, title="Acme memory inside the window",
         type="memory", scope="acme"),
    dict(key="mother_idea_open", date=MID, title="Mother open idea",
         type="idea", status="open", scope=None),
    dict(key="mother_idea_dismissed", date=MID, title="Mother dismissed idea",
         type="idea", status="dismissed", scope=None),
    dict(key="acme_idea_open", date=MID, title="Acme open idea",
         type="idea", status="open", scope="acme"),
    dict(key="mother_today", date=TODAY, title="Mother row logged today",
         type="memory", scope=None),
    dict(key="acme_today", date=TODAY, title="Acme row logged today",
         type="memory", scope="acme"),
    dict(key="mother_yesterday", date=YESTERDAY, title="Mother row logged yesterday",
         type="memory", scope=None),
    dict(key="acme_yesterday", date=YESTERDAY, title="Acme row logged yesterday",
         type="memory", scope="acme"),
    dict(key="mother_day", date=DAY, title="Mother row on the target day",
         type="memory", scope=None),
    dict(key="acme_day", date=DAY, title="Acme row on the target day",
         type="memory", scope="acme"),
]


def seed_db(db_path: Path) -> dict[str, int]:
    """Fresh db with the current (scoped) log schema and FIXTURE_ROWS.
    Returns {fixture key: row id}."""
    con = sqlite3.connect(db_path)
    con.executescript(LOG_SCHEMA)
    ids = {}
    for row in FIXTURE_ROWS:
        cur = con.execute(
            "INSERT INTO log (date, title, type, status, due_date, completed_date, scope) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (row["date"], row["title"], row["type"], row.get("status"),
             row.get("due_date"), row.get("completed_date"), row.get("scope")),
        )
        ids[row["key"]] = cur.lastrowid
    con.commit()
    con.close()
    return ids


# ---------------------------------------------------------------------------
# Expected rows, computed from the parsed flags — independent of bin/mem's own
# implementation, so the test pins behaviour rather than mirroring code.
# ---------------------------------------------------------------------------

def parse_flags(tokens: list[str]) -> dict:
    """`--flag value` / `--flag=value` / `--flag` (boolean) pairs from a
    bin/mem argv tail — the `=` form is how a doc writes a negative relative
    date (`--since=-7d`), since a bare `-7d` reads as a flag to argparse."""
    flags: dict = {}
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("--"):
            body = tok[2:]
            if "=" in body:
                key, value = body.split("=", 1)
                flags[key.replace("-", "_")] = value
                i += 1
                continue
            key = body.replace("-", "_")
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                flags[key] = tokens[i + 1]
                i += 2
            else:
                flags[key] = True
                i += 1
        else:
            i += 1
    return flags


_REL_RE = re.compile(r"^([+-])(\d+)([dwm])$")


def _resolve_date(value: str) -> str:
    """Resolve a date flag's value the way bin/mem's own parser does:
    today/yesterday/tomorrow, ±Nd/±Nw/±Nm relative to today, or an absolute
    YYYY-MM-DD passed through unchanged."""
    kw = value.lower()
    if kw == "today":
        return TODAY
    if kw == "yesterday":
        return YESTERDAY
    if kw == "tomorrow":
        return _d(-1)
    m = _REL_RE.match(value)
    if m:
        sign, n, unit = m.group(1), int(m.group(2)), m.group(3)
        delta_days = {"d": n, "w": n * 7, "m": n * 30}[unit]
        return _d(delta_days if sign == "-" else -delta_days)
    return value


def _scope_ok(r: dict, flags: dict) -> bool:
    """Which fixture rows a command's scope flags admit, mirroring bin/mem's
    own defaults: --all-scopes opens every scope, --scope SLUG narrows to
    one, and with neither the mother's default read is the null scope."""
    if "all_scopes" in flags:
        return True
    if "scope" in flags:
        return r["scope"] == flags["scope"]
    return r["scope"] is None


def expected_today(flags: dict, *, now: datetime | None = None) -> set[str]:
    """`now` overrides the live clock used for the omitted-`--date` default,
    so a regression test can pin it to a specific TZ-derived instant instead
    of the process's own clock (see TestEarlyMorningDefault below)."""
    first = _resolve_date(flags["date"]) if "date" in flags else _effective_today(now)
    last = _resolve_date(flags["to"]) if "to" in flags else first
    return {r["key"] for r in FIXTURE_ROWS
            if first <= r["date"] <= last and _scope_ok(r, flags)}


def expected_todo(flags: dict) -> set[str]:
    due_until = flags.get("due_until")
    due_until = _resolve_date(due_until) if due_until is not None else None
    out = set()
    for r in FIXTURE_ROWS:
        if r["type"] != "task" or r.get("status") not in ("todo", "in_progress"):
            continue
        due = r.get("due_date")
        if due_until is None or due is None or due <= due_until:
            out.add(r["key"])
    return out


def expected_search(flags: dict) -> set[str]:
    out = set()
    cs = _resolve_date(flags["completed_since"]) if "completed_since" in flags else None
    cu = _resolve_date(flags["completed_until"]) if "completed_until" in flags else None
    for r in FIXTURE_ROWS:
        if not _scope_ok(r, flags):
            continue
        if "type" in flags and r["type"] != flags["type"]:
            continue
        if "status" in flags and r.get("status") != flags["status"]:
            continue
        if "since" in flags and r["date"] < _resolve_date(flags["since"]):
            continue
        if "until" in flags and r["date"] > _resolve_date(flags["until"]):
            continue
        if cs or cu:
            cd = r.get("completed_date")
            if cd is None or (cs and cd < cs) or (cu and cd > cu):
                continue
        out.add(r["key"])
    return out


EXPECTERS = {"today": expected_today, "todo": expected_todo, "search": expected_search}


# ---------------------------------------------------------------------------
# Raw sqlite3 gate — mirrors the packet's `rg` gate over just these files, so
# it fails (RED) on the current text before the rewrite.
# ---------------------------------------------------------------------------

_RAW_SQLITE_RE = re.compile(r"sqlite3.*\blog\b|INSERT INTO log|FROM log")

# finalize.sh (V4 Task 3: moved from `.claude/skills/setup/` into the
# plugin's own skill tree, under new-instance) used to write the first
# memory with a raw `sqlite3 INSERT INTO log`; it now calls the instance's
# own `bin/mem save`. The plugin tree is `export-ignore`d (see
# `.gitattributes`), so this path only exists inside the template repo
# itself — never inside a shipped instance, where this file (not
# export-ignored) still runs.
PLUGIN_SOURCE_FILES = [
    ROOT / "plugins" / "maestro" / "skills" / "new-instance" / "finalize.sh",
]


class TestNoRawSqlite3(unittest.TestCase):
    def test_no_source_file_touches_log_with_raw_sqlite3(self):
        for path in SOURCE_FILES:
            with self.subTest(file=path.relative_to(ROOT)):
                offenders = [ln for ln in path.read_text().splitlines()
                             if _RAW_SQLITE_RE.search(ln)]
                self.assertEqual(offenders, [])

    def test_moved_finalize_script_touches_no_raw_sqlite3(self):
        if not (ROOT / "plugins").is_dir():
            self.skipTest("the plugin tree is export-ignore'd: absent in a shipped instance")
        for path in PLUGIN_SOURCE_FILES:
            with self.subTest(file=path.relative_to(ROOT)):
                self.assertTrue(path.is_file(), f"{path} missing")
                offenders = [ln for ln in path.read_text().splitlines()
                             if _RAW_SQLITE_RE.search(ln)]
                self.assertEqual(offenders, [])


class TestDocumentedCommands(unittest.TestCase):
    """Each file documents at least the bin/mem subcommands the brief assigns
    it — fails on a file that still has no bin/mem lines at all."""

    def test_each_file_documents_its_expected_subcommands(self):
        for path, expected_cmds in EXPECTED_SUBCOMMANDS.items():
            with self.subTest(file=path.relative_to(ROOT)):
                got_cmds = [shlex.split(substitute(line))[1] for line in commands_in(path)]
                self.assertEqual(sorted(got_cmds), sorted(expected_cmds))


class TestSubstitute(unittest.TestCase):
    def test_replaces_a_known_placeholder(self):
        self.assertEqual(
            substitute("bin/mem todo --due-until <end>"),
            f"bin/mem todo --due-until {END}",
        )

    def test_raises_on_an_unknown_placeholder(self):
        with self.assertRaises(AssertionError):
            substitute("bin/mem todo --due-until <not-a-real-placeholder>")


class TestSkillQueriesRun(unittest.TestCase):
    """Every documented bin/mem command runs against a fresh fixture, exit 0;
    read commands (today/todo/search) return exactly the rows their flags
    imply. Write commands (save) are exit-0-only, per the brief."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._n = 0

    def _fresh_db(self) -> tuple[Path, dict[str, int]]:
        self._n += 1
        db = Path(self._tmp.name) / f"fixture-{self._n}.db"
        return db, seed_db(db)

    def run_mem(self, db: Path, argv: list[str]) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env.pop("MEM_SCOPE", None)
        env["MEM_DB"] = str(db)
        return subprocess.run(
            [sys.executable, str(SCRIPT), *argv],
            capture_output=True, text=True, env=env,
        )

    def test_every_documented_command(self):
        commands = collect_commands()
        self.assertTrue(commands, "no bin/mem commands found across SOURCE_FILES")
        for source, raw_line in commands:
            with self.subTest(source=source, command=raw_line):
                argv = shlex.split(substitute(raw_line))
                self.assertEqual(argv[0], "bin/mem")
                tail = argv[1:]
                cmd = tail[0]
                db, ids = self._fresh_db()
                r = self.run_mem(db, tail)
                self.assertEqual(r.returncode, 0, r.stderr)

                if cmd == "save":
                    continue

                expecter = EXPECTERS.get(cmd)
                if expecter is None:
                    self.fail(f"unhandled bin/mem subcommand in skill text: {cmd}")
                flags = parse_flags(tail[1:])
                rows = json.loads(r.stdout)
                id_to_key = {rid: key for key, rid in ids.items()}
                got_keys = {id_to_key[row["id"]] for row in rows}
                self.assertEqual(got_keys, expecter(flags))


class TestEarlyMorningDefault(unittest.TestCase):
    """Regression for the whole-branch review finding: plain `bin/mem today`
    (no --date) lives by the early-morning rule — effective_today(), not
    date.today() — and expected_today's default must apply the same rule, or
    the gate fails whenever a session (or the test run itself) lands between
    00:00 and 06:00 local. The reviewer reproduced it with TZ=Etc/GMT-12 at
    local 01:16; this test forces the same window deterministically instead
    of waiting for the clock to cross it."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def test_today_default_matches_expected_today_before_6am_in_a_chosen_tz(self):
        tz, offset = _pick_early_morning_tz()
        if tz is None:
            self.skipTest("no Etc/GMT offset puts local time in 00:00-06:00 right now")

        # The same wall-clock reading the subprocess will compute once TZ is
        # set in its environment: UTC now shifted by the chosen whole-hour
        # offset, not a real zoneinfo lookup, so it needs no tzdata of its own.
        local_now = (datetime.now(timezone.utc) + timedelta(hours=offset)).replace(tzinfo=None)
        self.assertLess(local_now.hour, 6,
                        "clock crossed the window while picking the TZ; rerun")

        db = Path(self._tmp.name) / "fixture.db"
        ids = seed_db(db)
        env = dict(os.environ)
        env.pop("MEM_SCOPE", None)
        env["MEM_DB"] = str(db)
        env["TZ"] = tz
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "today"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = json.loads(r.stdout)
        id_to_key = {rid: key for key, rid in ids.items()}
        got_keys = {id_to_key[row["id"]] for row in rows}
        self.assertEqual(got_keys, expected_today({}, now=local_now))


if __name__ == "__main__":
    unittest.main()
