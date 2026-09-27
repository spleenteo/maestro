"""From a folder to the satellite that contains it, and to its role in the mother.

Used by `maestro-net` (`ask`, `request`, `satellite add/remove`) and by the
plugin's SessionStart hook: one recognition rule and one drift check for both.
The role of a satellite lives in the mother's `satellites` table, read through
the mother's own `bin/mem`; the machine registry only maps the repo to the
mother.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple

from maestro_registry import E_REMOTE_FAILED, NetError, inside

# The mother's bin/mem must know the satellites table: SCHEMA_API of bin/mem_schema.py.
MIN_SCHEMA_API = 2


def clean_env() -> Dict[str, str]:
    """The environment for a process run inside another instance.

    MEM_DB out: the recipient's `bin/mem` would write into the caller's db.
    MEM_SCOPE out: a recap or ask sent from a satellite would land in the
    caller's scope instead of the recipient's null scope. PWD and
    CLAUDE_PROJECT_DIR out: the remote session must recognise itself from its
    own folder, not from the caller's.
    """
    dropped = ("MEM_DB", "MEM_SCOPE", "PWD", "CLAUDE_PROJECT_DIR")
    return {k: v for k, v in os.environ.items() if k not in dropped}


def main_checkout(folder: str) -> Optional[str]:
    """Root of the main checkout when `folder` sits in a git worktree; None outside git."""
    try:
        out = subprocess.run(
            ["git", "-C", folder, "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    common = os.path.realpath(out.stdout.strip())
    return os.path.dirname(common) if os.path.basename(common) == ".git" else None


def match_satellite(registry: dict, folder: str) -> Tuple[Optional[str], Optional[dict]]:
    """(scope, entry) of the satellite whose repo contains `folder`, longest repo first.

    A folder inside a registered instance belongs to the instance, never to a satellite.
    """
    satellites = registry.get("satellites", {})
    if not satellites:
        return None, None
    real = os.path.realpath(folder)
    for entry in registry.get("instances", {}).values():
        if inside(real, os.path.realpath(os.path.expanduser(entry["path"]))):
            return None, None

    def repo_of(entry: dict) -> str:
        return os.path.realpath(os.path.expanduser(entry["repo"]))

    ranked = sorted(satellites.items(), key=lambda kv: len(repo_of(kv[1])), reverse=True)
    for scope, entry in ranked:
        if inside(real, repo_of(entry)):
            return scope, entry
    root = main_checkout(real)
    if root:
        for scope, entry in ranked:
            if repo_of(entry) == root:
                return scope, entry
    return None, None


def schema_api(mother: Path) -> int:
    """SCHEMA_API declared by the mother's bin/mem_schema.py; 0 when unreadable."""
    try:
        text = (mother / "bin" / "mem_schema.py").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    m = re.search(r"^SCHEMA_API\s*=\s*(\d+)", text, re.MULTILINE)
    return int(m.group(1)) if m else 0


def satellite_row(mother: str, path: Path, scope: str, entry: dict, timeout: int = 30) -> dict:
    """The satellite's row in the mother, which must point to the registry's repo.

    NetError 8 when the mother has no row, when `bin/mem` fails, or when the
    two stores disagree on the repo path.
    """
    mem = path / "bin" / "mem"
    detail = ""
    try:
        show = subprocess.run([str(mem), "satellite", "show", scope, "--json"],
                              capture_output=True, text=True, env=clean_env(), timeout=timeout,
                              stdin=subprocess.DEVNULL)
        detail = show.stderr.strip()
        row = json.loads(show.stdout) if show.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        detail, row = str(exc), None
    if not isinstance(row, dict):
        raise NetError(
            E_REMOTE_FAILED,
            f"`{mem} satellite show {scope}` returns no satellite row: `{mother}` has no role for it "
            f"(`{mem} satellite add`)." + (f"\n{detail}" if detail else ""))
    if os.path.realpath(row.get("repo_path") or "") != os.path.realpath(os.path.expanduser(entry["repo"])):
        raise NetError(
            E_REMOTE_FAILED,
            f"satellite `{scope}` points to {entry['repo']} in the registry and to "
            f"{row.get('repo_path')} in `{mother}`: align them first.")
    return row
