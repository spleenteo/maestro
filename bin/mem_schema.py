# origin: maestro
# maestro_version: v2026.09.14.1
"""mem_schema: the scope migration and the scope rules of memories.db.

Imported by bin/mem and bin/mem-vec from their own directory; stdlib only, so
it runs on the system python3 and under `uv run --script` alike.

- ensure_scope(con): adds `log.scope TEXT` and the `log_scope` index once,
  safe when several processes open a legacy db at the same time.
- SCHEMA_API: bumped whenever this module's interface changes; bin/mem and
  bin/mem-vec check it against the value they expect right after import.
- current_scope(prog=): the scope of this session, read from MEM_SCOPE; None is
  the mother instance (rows with `scope IS NULL`).
- scope_clause(scope, all_scopes=, column=): the SQL filter for that scope.
- read_clause(scope_flag, all_scopes, mother_all=, column=, prog=): the filter
  of a read command, applying the session scope and the mother-only flags.
- check_scope(value, source, prog=): validates a slug, EXIT_SCOPE_INVALID
  otherwise.
- ensure_satellites(con): creates the `satellites` table once, if missing.
  Call it only from `satellite add`: `list` and `show` read the table as it
  stands and must leave a db without one alone.
- row_in_scope(con, rid, scope): whether a `log` row with id `rid` exists —
  in any scope when `scope` is None, in exactly `scope` otherwise.
- EMBED_REFUSED: the wording bin/mem and bin/mem-vec share for the embed
  refusal message, formatted with `scope=`.

`prog` names the caller at the start of every stderr message of
`current_scope`, `read_clause` and `check_scope`: "mem" by default, and
`bin/mem-vec` passes "mem-vec".
"""

from __future__ import annotations

import os
import re
import sqlite3
import sys

EXIT_SCOPE_REFUSED = 4
EXIT_SCOPE_INVALID = 6

# Bumped whenever this module's interface changes; bin/mem and bin/mem-vec
# each carry the value they expect and check it right after import, so an
# instance that copied a newer script next to an older mem_schema.py (or the
# reverse) fails with a named message instead of a vague error mid-command.
SCHEMA_API = 2

_SCOPE_RE = re.compile(r"[a-z0-9][a-z0-9-]*")


def _log_columns(con: sqlite3.Connection) -> list[str]:
    return [row[1] for row in con.execute("PRAGMA table_info(log)")]


def ensure_scope(con: sqlite3.Connection) -> None:
    """Add `log.scope` and its index if missing. Call it on a connection with
    no open transaction, before any statement on `log`.

    ALTER TABLE ADD COLUMN has no IF NOT EXISTS: the column check is repeated
    under the write lock, and "duplicate column name" (another process added
    it after our read) counts as done."""
    if "scope" in _log_columns(con):
        return
    con.execute("BEGIN IMMEDIATE")
    try:
        if "scope" in _log_columns(con):
            con.rollback()
            return
        con.execute("ALTER TABLE log ADD COLUMN scope TEXT")
        con.execute("CREATE INDEX IF NOT EXISTS log_scope ON log(scope)")
        con.commit()
    except sqlite3.OperationalError as e:
        con.rollback()
        if "duplicate column name" not in str(e):
            raise


def check_scope(value: str, source: str, *, prog: str = "mem") -> str:
    """`value` when it matches `^[a-z0-9][a-z0-9-]*$`; otherwise a stderr
    message naming `source` (MEM_SCOPE, --scope) and EXIT_SCOPE_INVALID.
    `prog` names the caller in the message (bin/mem-vec passes "mem-vec")."""
    if not _SCOPE_RE.fullmatch(value):
        sys.stderr.write(
            f"{prog}: invalid {source} {value!r}: use lowercase letters, digits "
            "and hyphens, starting with a letter or a digit\n")
        sys.exit(EXIT_SCOPE_INVALID)
    return value


def current_scope(*, prog: str = "mem") -> str | None:
    """MEM_SCOPE stripped; None when unset or blank. A value outside
    `^[a-z0-9][a-z0-9-]*$` ends the process with EXIT_SCOPE_INVALID.
    `prog` names the caller in that message (bin/mem-vec passes "mem-vec")."""
    value = os.environ.get("MEM_SCOPE", "").strip()
    if not value:
        return None
    return check_scope(value, "MEM_SCOPE", prog=prog)


def scope_clause(scope: str | None, *, all_scopes: bool = False,
                 column: str = "scope") -> tuple[str, list]:
    """SQL condition and parameters selecting the rows of `scope`:
    every row with all_scopes, `column IS NULL` for the mother."""
    if all_scopes:
        return "1=1", []
    if scope is None:
        return f"{column} IS NULL", []
    return f"{column} = ?", [scope]


def read_clause(scope_flag: str | None = None, all_scopes: bool = False, *,
                mother_all: bool = False, column: str = "scope",
                prog: str = "mem") -> tuple[str, list]:
    """The scope filter of a read command, given its --scope/--all-scopes.

    A satellite reads its own scope and refuses both flags with
    EXIT_SCOPE_REFUSED. The mother reads null, or every scope when the
    command defaults to it (`mother_all`); --scope narrows to one valid slug
    and --all-scopes opens every scope. `prog` names the caller in stderr
    messages (bin/mem-vec passes "mem-vec")."""
    scope = current_scope(prog=prog)
    if scope is not None:
        if scope_flag is not None or all_scopes:
            sys.stderr.write(
                f"{prog}: --scope and --all-scopes are refused in scope {scope}: "
                "only the mother instance (MEM_SCOPE unset) reads other scopes\n")
            sys.exit(EXIT_SCOPE_REFUSED)
        return scope_clause(scope, column=column)
    if scope_flag is not None:
        return scope_clause(check_scope(scope_flag, "--scope", prog=prog), column=column)
    return scope_clause(None, all_scopes=all_scopes or mother_all, column=column)


# ---------------------------------------------------------------------------
# Satellites: the mother's registry of the repos it lends its memory to.
# ---------------------------------------------------------------------------

SATELLITES_SCHEMA = """
CREATE TABLE IF NOT EXISTS satellites (
  scope TEXT PRIMARY KEY,
  repo_path TEXT NOT NULL UNIQUE,
  project_type TEXT NOT NULL,
  mandate TEXT,
  method TEXT,
  constraints TEXT,
  language TEXT,
  vault_folder TEXT,
  created TEXT NOT NULL
);
"""


def ensure_satellites(con: sqlite3.Connection) -> None:
    """Create the `satellites` table if missing. `CREATE TABLE IF NOT EXISTS`
    needs no lock dance: called only from `satellite add`, so `list` and
    `show` never bring the table into being on a db that lacks it."""
    con.executescript(SATELLITES_SCHEMA)


def row_in_scope(con: sqlite3.Connection, rid: int, scope: str | None) -> bool:
    """Whether a `log` row with id `rid` exists: in any scope when `scope`
    is None, in exactly `scope` otherwise."""
    if scope is None:
        return con.execute(
            "SELECT 1 FROM log WHERE id=?", (rid,)).fetchone() is not None
    return con.execute(
        "SELECT 1 FROM log WHERE id=? AND scope=?", (rid, scope)).fetchone() is not None


# The literal wording of the embed refusal, shared by bin/mem and
# bin/mem-vec: each writes f"{prog}: {EMBED_REFUSED.format(scope=scope)}\n".
EMBED_REFUSED = ("embed is refused in scope {scope}: only the mother instance "
                 "vectorizes memories and prunes vault_vec")
