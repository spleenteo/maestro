"""maestro_versions.py — the vYYYY.MM.DD.N version scheme, the changelog's
top version, and the file-marker rules shared by maestro-sync and, in V3,
by the update-check hook.

Marker rules (docs/work/2026-09-27-sync-script/slices.md, V1): a markdown
file is marked when its first line is `---`, the frontmatter ends at the
next `---`, and a line inside it is exactly `origin: maestro`; a script is
marked when one of its first three lines is exactly `# origin: maestro` or
`// origin: maestro`. A mention anywhere else in the body is never a mark.
A marked file with no `maestro_version:` of its own reads as None here; a
caller that needs a floor falls back to BASELINE_VERSION.

Pure text and path handling: no subprocess, no network.
"""

from __future__ import annotations

import re
from pathlib import Path

VERSION_RE = re.compile(r"^v(\d{4})\.(\d{2})\.(\d{2})\.(\d+)$")
CHANGELOG_HEADING_RE = re.compile(r"^##\s+(v\d{4}\.\d{2}\.\d{2}\.\d+)\b", re.MULTILINE)
MAESTRO_VERSION_LINE_RE = re.compile(r"^\s*maestro_version:\s*(.+?)\s*$")
SCRIPT_MARKER_LINES = ("# origin: maestro", "// origin: maestro")

# A marked file with no `maestro_version:` of its own reads as this floor:
# the version in force before the marker convention existed.
BASELINE_VERSION = "v2026.04.29.1"

# The four globs the instance scan walks: no recursion beyond one level of
# skill/agent folders, no symlink following.
MARKDOWN_GLOBS = ("CLAUDE.md", ".claude/skills/*/SKILL.md", ".claude/agents/*.md", "howto/*.md")


def parse_version(text: str) -> tuple[int, int, int, int]:
    """`vYYYY.MM.DD.N` as a tuple of integers, compared as numbers never as
    text (`.10` sorts after `.9`, not before it as a string). Raises
    ValueError on anything that doesn't match the scheme exactly."""
    m = VERSION_RE.match(text.strip())
    if not m:
        raise ValueError(f"not a maestro version (expected vYYYY.MM.DD.N): {text!r}")
    year, month, day, n = m.groups()
    return (int(year), int(month), int(day), int(n))


def is_newer(a: str, b: str) -> bool:
    """Whether version `a` is strictly newer than version `b`."""
    return parse_version(a) > parse_version(b)


def changelog_top_version(path: str | Path) -> str | None:
    """The version carried by the first `## vYYYY.MM.DD.N` heading of a
    CHANGELOG.md, or None when the file has no such heading. Never looks a
    version up as a commit: some versions in the changelog have no release
    commit at all."""
    text = Path(path).read_text(encoding="utf-8")
    m = CHANGELOG_HEADING_RE.search(text)
    return m.group(1) if m else None


def _strip_bom(text: str) -> str:
    return text[1:] if text.startswith("﻿") else text


def _frontmatter_lines(lines: list[str]) -> list[str] | None:
    """Lines between the opening `---` (line 1) and the next `---`, or None
    when line 1 isn't `---` or no closing `---` follows."""
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i]
    return None


def _markdown_marker(text: str) -> tuple[bool, str | None]:
    lines = _strip_bom(text).splitlines()
    frontmatter = _frontmatter_lines(lines)
    if frontmatter is None:
        return False, None
    if not any(line.strip() == "origin: maestro" for line in frontmatter):
        return False, None
    version = None
    for line in frontmatter:
        m = MAESTRO_VERSION_LINE_RE.match(line)
        if m:
            version = m.group(1).strip().strip("\"'")
            break
    return True, version


def _script_marker(text: str) -> tuple[bool, str | None]:
    first_three = text.splitlines()[:3]
    marked = any(line.strip() in SCRIPT_MARKER_LINES for line in first_three)
    return marked, None


def read_marker(path: str | Path) -> tuple[bool, str | None]:
    """(marked, version) for one file, per the marker rules above. A
    markdown file (`.md`) is checked in its frontmatter only; any other
    file, in its first three lines only. A mention in the body is never a
    mark, so a script that names the marker strings by necessity — this
    module, maestro-sync itself — reads as unmarked."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".md":
        return _markdown_marker(text)
    return _script_marker(text)
