"""tests/test_claude_md_refs.py — every `CLAUDE.md` → `## …` reference in the
template points at a heading that exists.

Agents, skills and guides cite sections of `CLAUDE.md` by heading
(`CLAUDE.md` → `## Memory` → `### Task creation thresholds`). A heading renamed
or dropped leaves the reference dangling, and an agent told to read it finds
nothing. `CHANGELOG.md` and `docs/decisions-log/` are records of past versions
and keep the headings of their time, so they are not checked.

Run: python3 -m unittest tests.test_claude_md_refs -v
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORICAL = ("CHANGELOG.md", "docs/decisions-log/")
REF = re.compile(r"`CLAUDE\.md` → ((?:`#{2,3} [^`]+`(?: → )?)+)")
HEADING = re.compile(r"`(#{2,3}) ([^`]+)`")


def claude_md_sections() -> dict[str, set[str]]:
    """Map each `## ` heading of CLAUDE.md to the `### ` headings under it."""
    sections: dict[str, set[str]] = {}
    current = None
    in_fence = False
    for line in (ROOT / "CLAUDE.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        elif in_fence:
            continue
        elif line.startswith("## "):
            current = line[3:].strip()
            sections[current] = set()
        elif line.startswith("### ") and current is not None:
            sections[current].add(line[4:].strip())
    return sections


def references():
    files = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    for rel in files:
        if rel.startswith(HISTORICAL):
            continue
        for n, line in enumerate((ROOT / rel).read_text(encoding="utf-8").splitlines(), 1):
            for match in REF.finditer(line):
                yield f"{rel}:{n}", HEADING.findall(match.group(1))


def dangling(chain, sections) -> bool:
    parent = None
    for level, name in chain:
        if level == "##":
            if name not in sections:
                return True
            parent = name
        elif parent is not None:
            if name not in sections[parent]:
                return True
        elif not any(name in subs for subs in sections.values()):
            return True
    return False


class ClaudeMdRefsTest(unittest.TestCase):
    def test_every_reference_points_at_an_existing_heading(self):
        sections = claude_md_sections()
        broken = [
            f"{where}: {' → '.join(f'{lvl} {name}' for lvl, name in chain)}"
            for where, chain in references()
            if dangling(chain, sections)
        ]
        self.assertEqual(broken, [], "references to missing CLAUDE.md headings")


if __name__ == "__main__":
    unittest.main()
