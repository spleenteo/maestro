"""tests/test_new_instance.py — the command blocks of the `new-instance`
skill (V4 plan, Task 4), run as the skill writes them.

The skill is Markdown a model copies into Bash calls, so its fenced
```bash blocks are code: this file extracts them by section heading, fills
the placeholders the model fills (`<destination>`, `<sha>`, ...) and the
variables Claude Code substitutes in plugin skill content
(`${CLAUDE_SKILL_DIR}`, `${CLAUDE_PLUGIN_ROOT}`), and runs them in order
the way a session would: destination, plugin commit, template mirror,
extract, the internal-vault commands of the interview, finalize, register.
A block with a placeholder this file doesn't know fails the run.

Stand-ins, never the real thing:
- GitHub is a temp bare repo cloned from this repo, reached through a
  `file://` URL written as `repository` in a stub plugin root's
  `plugin.json`.
- `claude` is a stub script printing a `plugin list --json` with an
  unrelated plugin, a `maestro@maestro` row at `project` scope with a wrong
  SHA, and the `user` row with the real one.
- `HOME` is a temp dir (the mirror lands in its `.maestro`), and
  `MAESTRO_INSTANCES` a temp registry. `maestro-net` resolves from this
  repo's plugin `bin/`.
- `PATH` is built explicitly: stub bin, plugin bin, /usr/bin:/bin and the
  directories of git, tar, python3 and sqlite3.

The Bash tool runs commands in the owner's shell, so the flow and the
failure cases run under bash and, when present, zsh.

This file needs the template's `.git` and its plugin tree, neither of which
an archived instance has: it is `export-ignore`d.

Run: python3 -m unittest tests.test_new_instance -v
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "plugins" / "maestro" / "skills" / "new-instance"
SKILL = SKILL_DIR / "SKILL.md"
PLUGIN_BIN = ROOT / "plugins" / "maestro" / "bin"
REGISTER_CHECK = ROOT / "bin" / "register-check"

# Section headings the blocks are read from. A renamed heading fails here.
STEP_DESTINATION = "## 2. Destination"
STEP_COMMIT = "## 3. Plugin commit"
STEP_MIRROR = "## 4. Template mirror"
STEP_EXTRACT = "## 5. Extract"
QUESTION_TERRITORIES = "### Question 10/10"
TERRITORY_FOLDERS = "## Territory folders"
FINALIZE = "## Finalize"
REGISTER = "## Register"
LOGBOOK = "## Day-zero logbook"
TIL = "## Day-zero TIL"

TEMPLATE_ONLY_PATHS = ("docs", "plugins", ".claude-plugin", ".devflow.yml", ".gitattributes")

# Values the model would fill in. The Finalize example in the skill uses
# the `acme-partnership` project slug, so the internal vault matches it.
PROJECT_SLUG = "acme-partnership"
ORCHESTRATOR_SLUG = "jarvis"
DOMAIN = "Acme partnership work"
MISSING_SHA = "deadbeef" * 5

_FENCE_RE = re.compile(r"^([ \t]*)```bash\n(.*?)^[ \t]*```", re.DOTALL | re.MULTILINE)
_HEADING_RE = re.compile(r"#{1,6} ")
_LEFTOVER_RE = re.compile(r"<[a-z][a-z0-9_ -]*>|\$\{CLAUDE_[A-Z_]+\}")


# ---------------------------------------------------------------------------
# Machine
# ---------------------------------------------------------------------------

def _tool_dir(name: str) -> str:
    found = shutil.which(name)
    if found is None:
        raise RuntimeError(f"{name} not found on this machine")
    return str(Path(found).resolve().parent)


def _base_path() -> str:
    dirs = ["/usr/bin", "/bin"]
    for tool in ("git", "tar", "python3", "sqlite3"):
        d = _tool_dir(tool)
        if d not in dirs:
            dirs.append(d)
    return ":".join(dirs)


BASE_PATH = _base_path()

SHELLS = [("bash", ("/bin/bash", "-c"))]
_ZSH = shutil.which("zsh")
if _ZSH:
    SHELLS.append(("zsh", (_ZSH, "-f", "-c")))


def _git(*args: str, env: dict | None = None) -> str:
    r = subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True,
        env=env or {"PATH": BASE_PATH, "HOME": tempfile.gettempdir()},
    )
    return r.stdout.strip()


# ---------------------------------------------------------------------------
# Skill text
# ---------------------------------------------------------------------------

def _sections(text: str) -> dict:
    """Heading line -> section body, with headings inside fences ignored
    (a `# comment` in a bash block or a heading in a Markdown template
    never splits a section)."""
    sections: dict = {}
    current = None
    buf: list = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and _HEADING_RE.match(line):
            if current is not None:
                sections[current] = "".join(buf)
            current, buf = line.strip(), []
            continue
        buf.append(line)
    if current is not None:
        sections[current] = "".join(buf)
    return sections


def _section(prefix: str) -> str:
    sections = _sections(SKILL.read_text(encoding="utf-8"))
    matches = [body for heading, body in sections.items() if heading.startswith(prefix)]
    if len(matches) != 1:
        raise AssertionError(f"expected one section starting with {prefix!r}, found {len(matches)}")
    return matches[0]


def _bash_blocks(body: str) -> list:
    """Fenced bash blocks, dedented: a block nested in a list item is
    indented in the Markdown and runs without that indentation."""
    return [textwrap.dedent(block) for _, block in _FENCE_RE.findall(body)]


def _only_bash_block(prefix: str) -> str:
    blocks = _bash_blocks(_section(prefix))
    if len(blocks) != 1:
        raise AssertionError(f"expected one bash block under {prefix!r}, found {len(blocks)}")
    return blocks[0]


def _internal_vault_blocks() -> list:
    blocks = _bash_blocks(_section(TERRITORY_FOLDERS))
    if len(blocks) != 2:
        raise AssertionError(f"expected two bash blocks for the internal vault, found {len(blocks)}")
    return blocks


def _markdown_template(prefix: str) -> str:
    m = re.search(r"```markdown\n(.*?)```", _section(prefix), re.DOTALL)
    if m is None:
        raise AssertionError(f"no markdown template under {prefix!r}")
    return m.group(1)


def _escape_for_double_quotes(value: str) -> str:
    """The skill's rule for a free-text value inside double quotes on the
    command line: a backslash before `\\`, `"`, `$` and a backtick; an
    apostrophe and a line break stay as they are."""
    for ch in ("\\", '"', "$", "`"):
        value = value.replace(ch, "\\" + ch)
    return value


def _fill(block: str, values: dict) -> str:
    for key, value in values.items():
        block = block.replace(key, value)
    leftover = _LEFTOVER_RE.findall(block)
    if leftover:
        raise AssertionError(f"unfilled placeholders {leftover} in block:\n{block}")
    return block


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

def _plugin_rows(user_version: str) -> list:
    return [
        {"id": "superpowers@claude-plugins-official", "version": "6.3.0",
         "scope": "user", "enabled": True},
        {"id": "maestro@maestro", "version": "0123456789ab",
         "scope": "project", "enabled": True},
        {"id": "maestro@maestro", "version": user_version,
         "scope": "user", "enabled": True},
    ]


class _Remote:
    """A bare clone of this repo standing in for GitHub."""

    def __init__(self, tmp: Path):
        self.path = tmp / "remote.git"
        _git("clone", "--bare", "--quiet", str(ROOT), str(self.path))
        self.sha = _git("-C", str(self.path), "rev-parse", "HEAD")

    @property
    def url(self) -> str:
        return self.path.as_uri()

    def push_new_commit(self, tmp: Path, label: str) -> str:
        work = tmp / f"work-{label}"
        _git("clone", "--quiet", self.url, str(work))
        _git("-C", str(work), "-c", "user.name=New Instance Test",
             "-c", "user.email=new-instance-test@example.com",
             "-c", "commit.gpgsign=false",
             "commit", "--allow-empty", "--quiet", "-m", f"fetch test {label}")
        sha = _git("-C", str(work), "rev-parse", "HEAD")
        _git("-C", str(work), "push", "--quiet", "origin", f"HEAD:refs/heads/fetch-test-{label}")
        return sha


class _Session:
    """What one Claude Code session sees: HOME, a stub `claude`, the plugin
    root holding `plugin.json`, a registry, a working directory."""

    def __init__(self, tmp: Path, remote: _Remote, rows: list):
        self.tmp = Path(tempfile.mkdtemp(prefix="session-", dir=tmp))
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.cwd = self.tmp / "cwd"
        self.cwd.mkdir()
        self.registry = self.tmp / "maestro-instances.yaml"

        self.plugin_root = self.tmp / "plugin-root"
        (self.plugin_root / ".claude-plugin").mkdir(parents=True)
        (self.plugin_root / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "maestro", "repository": remote.url}), encoding="utf-8",
        )

        self.stub_bin = self.tmp / "stub-bin"
        self.stub_bin.mkdir()
        self.plugin_list = self.tmp / "plugin-list.json"
        self.plugin_list.write_text(json.dumps(rows), encoding="utf-8")
        self.claude_argv = self.tmp / "claude-argv"
        stub = self.stub_bin / "claude"
        stub.write_text(
            "#!/bin/sh\n"
            f"printf '%s\\n' \"$*\" > '{self.claude_argv}'\n"
            f"cat '{self.plugin_list}'\n",
            encoding="utf-8",
        )
        stub.chmod(0o755)

    @property
    def mirror(self) -> Path:
        return self.home / ".maestro"

    def env(self, plugin_bin_on_path: bool = True) -> dict:
        path = f"{self.stub_bin}:{PLUGIN_BIN}:{BASE_PATH}" if plugin_bin_on_path \
            else f"{self.stub_bin}:{BASE_PATH}"
        return {
            "PATH": path,
            "HOME": str(self.home),
            "MAESTRO_INSTANCES": str(self.registry),
        }

    def values(self, destination: str = "", sha: str = "") -> dict:
        return {
            "<destination>": destination,
            "<sha>": sha,
            "<project_slug>": PROJECT_SLUG,
            "<orchestrator-slug>": ORCHESTRATOR_SLUG,
            "<domain>": DOMAIN,
            "${CLAUDE_SKILL_DIR}": str(SKILL_DIR),
            "${CLAUDE_PLUGIN_ROOT}": str(self.plugin_root),
        }

    def run(self, shell: tuple, block: str, values: dict, *, prelude: str = "",
            plugin_bin_on_path: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            [*shell, prelude + _fill(block, values)], cwd=str(self.cwd),
            env=self.env(plugin_bin_on_path), capture_output=True, text=True, timeout=120,
        )


def _require_ok(name: str, r: subprocess.CompletedProcess) -> None:
    if r.returncode != 0:
        raise AssertionError(
            f"{name} exited {r.returncode}\n--- stdout\n{r.stdout}\n--- stderr\n{r.stderr}"
        )


# ---------------------------------------------------------------------------
# The whole flow
# ---------------------------------------------------------------------------

class _FlowBase:
    SHELL: tuple = ()

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="maestro-new-instance-test-"))
        cls.addClassCleanup(shutil.rmtree, cls.tmp, True)
        cls.remote = _Remote(cls.tmp)
        cls.short_sha = cls.remote.sha[:12]
        cls.session = _Session(cls.tmp, cls.remote, _plugin_rows(cls.short_sha))
        cls.destination = cls.tmp / "instances" / "acme"
        dest = str(cls.destination)
        s = cls.session

        _require_ok("step 2", s.run(cls.SHELL, _only_bash_block(STEP_DESTINATION), s.values(dest)))

        step3 = s.run(cls.SHELL, _only_bash_block(STEP_COMMIT), s.values(dest))
        _require_ok("step 3", step3)
        cls.resolved_sha = step3.stdout.strip()
        values = s.values(dest, cls.resolved_sha)

        _require_ok("step 4", s.run(cls.SHELL, _only_bash_block(STEP_MIRROR), values))
        _require_ok("step 5", s.run(cls.SHELL, _only_bash_block(STEP_EXTRACT), values))

        mkdir_block, gitignore_block = _internal_vault_blocks()
        _require_ok("internal vault folders", s.run(cls.SHELL, mkdir_block, values))
        _require_ok("gitignore append", s.run(cls.SHELL, gitignore_block, values))
        _require_ok("gitignore append, again", s.run(cls.SHELL, gitignore_block, values))

        _require_ok("finalize", s.run(cls.SHELL, _only_bash_block(FINALIZE), values))
        _require_ok("register", s.run(cls.SHELL, _only_bash_block(REGISTER), values))

    def test_step_3_resolves_the_user_scope_sha(self):
        self.assertEqual(self.resolved_sha, self.short_sha)
        self.assertEqual(self.session.claude_argv.read_text().strip(), "plugin list --json")

    def test_mirror_is_cloned_from_the_plugin_repository(self):
        origin = _git("-C", str(self.session.mirror), "remote", "get-url", "origin")
        self.assertEqual(origin, self.remote.url)

    def test_destination_has_no_template_only_paths(self):
        for rel in TEMPLATE_ONLY_PATHS:
            with self.subTest(path=rel):
                self.assertFalse((self.destination / rel).exists(), f"{rel} leaked")

    def test_destination_is_an_instance_skeleton(self):
        self.assertTrue((self.destination / "CLAUDE.md").is_file())
        self.assertTrue(os.access(self.destination / "bin" / "mem", os.X_OK))
        self.assertFalse((self.destination / ".git").exists())

    def test_internal_vault_folders_exist(self):
        for sub in ("logbook", "til", "documents"):
            with self.subTest(sub=sub):
                self.assertTrue((self.destination / PROJECT_SLUG / sub).is_dir())

    def test_gitignore_lists_the_vault_once(self):
        lines = (self.destination / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines.count(f"{PROJECT_SLUG}/"), 1)

    def test_instance_is_finalized(self):
        prefs = (self.destination / "private" / "preferences.md").read_text(encoding="utf-8")
        self.assertIn("setup_completed: true", prefs)
        self.assertIn(f"vault_path: {self.destination}/{PROJECT_SLUG}", prefs)
        self.assertTrue((self.destination / "private" / "routines.yaml").is_file())
        con = sqlite3.connect(str(self.destination / "private" / "memories.db"))
        try:
            cols = {row[1] for row in con.execute("PRAGMA table_info(log)")}
            titles = [row[0] for row in con.execute("SELECT title FROM log")]
        finally:
            con.close()
        self.assertIn("scope", cols)
        self.assertEqual(titles, ["Orchestrator setup completed"])

    def test_registry_lists_the_instance(self):
        r = subprocess.run(
            [str(PLUGIN_BIN / "maestro-net"), "list", "--json"],
            env=self.session.env(), capture_output=True, text=True,
        )
        _require_ok("maestro-net list", r)
        entry = json.loads(r.stdout)["instances"][ORCHESTRATOR_SLUG]
        self.assertEqual(entry["path"], os.path.realpath(self.destination))
        self.assertEqual(entry["domain"], DOMAIN)
        self.assertEqual(entry["accepts"], ["recap", "ask"])


class TestFlowBash(_FlowBase, unittest.TestCase):
    SHELL = SHELLS[0][1]


@unittest.skipUnless(_ZSH, "zsh not installed")
class TestFlowZsh(_FlowBase, unittest.TestCase):
    SHELL = SHELLS[-1][1]


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------

class TestRefusals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="maestro-new-instance-refusals-"))
        cls.addClassCleanup(shutil.rmtree, cls.tmp, True)
        cls.remote = _Remote(cls.tmp)

    def _session(self, user_version: str | None = None) -> _Session:
        version = user_version if user_version is not None else self.remote.sha[:12]
        return _Session(self.tmp, self.remote, _plugin_rows(version))

    def test_step_2_refuses_a_non_empty_destination(self):
        for name, shell in SHELLS:
            with self.subTest(shell=name):
                s = self._session()
                dest = s.tmp / "taken"
                dest.mkdir()
                (dest / "notes.txt").write_text("keep me", encoding="utf-8")

                r = s.run(shell, _only_bash_block(STEP_DESTINATION), s.values(str(dest)))

                self.assertNotEqual(r.returncode, 0)
                self.assertIn(str(dest), r.stderr)
                self.assertEqual(sorted(p.name for p in dest.iterdir()), ["notes.txt"])

    def test_step_2_accepts_an_empty_existing_destination(self):
        for name, shell in SHELLS:
            with self.subTest(shell=name):
                s = self._session()
                dest = s.tmp / "empty"
                dest.mkdir()

                r = s.run(shell, _only_bash_block(STEP_DESTINATION), s.values(str(dest)))

                self.assertEqual(r.returncode, 0, r.stderr)

    def test_step_2_accepts_the_empty_session_folder(self):
        for name, shell in SHELLS:
            with self.subTest(shell=name):
                s = self._session()

                r = s.run(shell, _only_bash_block(STEP_DESTINATION), s.values(str(s.cwd)))

                self.assertEqual(r.returncode, 0, r.stderr)

    def test_step_2_refuses_a_non_empty_destination_when_ls_is_shadowed(self):
        # Claude Code applies the owner's aliases and functions to every
        # Bash call: an `ls` that prints nothing must not pass the check.
        for name, shell in SHELLS:
            with self.subTest(shell=name):
                s = self._session()
                dest = s.tmp / "taken"
                dest.mkdir()
                (dest / "notes.txt").write_text("keep me", encoding="utf-8")

                r = s.run(shell, _only_bash_block(STEP_DESTINATION), s.values(str(dest)),
                          prelude="ls() { :; }\n")

                self.assertNotEqual(r.returncode, 0)
                self.assertEqual(sorted(p.name for p in dest.iterdir()), ["notes.txt"])

    def test_step_2_refuses_a_relative_destination(self):
        for name, shell in SHELLS:
            with self.subTest(shell=name):
                s = self._session()

                r = s.run(shell, _only_bash_block(STEP_DESTINATION), s.values("instances/acme"))

                self.assertEqual(r.returncode, 2)
                self.assertEqual(list(s.cwd.iterdir()), [])

    def test_step_3_refuses_a_version_that_is_not_a_sha(self):
        for name, shell in SHELLS:
            with self.subTest(shell=name):
                s = self._session(user_version="1.2.0")

                r = s.run(shell, _only_bash_block(STEP_COMMIT), s.values())

                self.assertNotEqual(r.returncode, 0)
                self.assertEqual(r.stdout.strip(), "")
                self.assertIn("1.2.0", r.stderr)

    def test_step_3_refuses_when_no_user_scope_row_exists(self):
        for name, shell in SHELLS:
            with self.subTest(shell=name):
                s = self._session()
                rows = [row for row in _plugin_rows("unused") if row["scope"] != "user"
                        or row["id"] != "maestro@maestro"]
                s.plugin_list.write_text(json.dumps(rows), encoding="utf-8")

                r = s.run(shell, _only_bash_block(STEP_COMMIT), s.values())

                self.assertNotEqual(r.returncode, 0)
                self.assertEqual(r.stdout.strip(), "")
                self.assertIn("maestro@maestro", r.stderr)

    def test_step_4_stops_when_the_commit_is_missing_from_the_mirror(self):
        for name, shell in SHELLS:
            with self.subTest(shell=name):
                s = self._session()

                r = s.run(shell, _only_bash_block(STEP_MIRROR), s.values(sha=MISSING_SHA))

                self.assertNotEqual(r.returncode, 0)
                self.assertIn("claude plugin update maestro@maestro", r.stderr)

    def test_step_4_fetches_a_commit_pushed_after_the_mirror_was_cloned(self):
        for name, shell in SHELLS:
            with self.subTest(shell=name):
                s = self._session()
                block = _only_bash_block(STEP_MIRROR)
                _require_ok("first step 4", s.run(shell, block, s.values(sha=self.remote.sha)))

                new_sha = self.remote.push_new_commit(s.tmp, name)
                missing = subprocess.run(
                    ["git", "-C", str(s.mirror), "cat-file", "-e", f"{new_sha}^{{commit}}"],
                    env={"PATH": BASE_PATH, "HOME": str(s.home)}, capture_output=True,
                )
                self.assertNotEqual(missing.returncode, 0, "commit already in the mirror")

                r = s.run(shell, block, s.values(sha=new_sha))

                self.assertEqual(r.returncode, 0, r.stderr)


# ---------------------------------------------------------------------------
# Free-text values and the register fallback
# ---------------------------------------------------------------------------

FREE_TEXT = 'He said "hi", it\'s $HOME and `echo INJECTED` with a \\ backslash\nand a second line'
FREE_DOMAIN = "Costs in $HOME and `echo INJECTED`"


class TestFinalizeAndRegisterValues(unittest.TestCase):
    """Values written the way the skill says reach preferences and the
    registry verbatim, under each shell the Bash tool may use."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="maestro-new-instance-values-"))
        cls.addClassCleanup(shutil.rmtree, cls.tmp, True)
        cls.remote = _Remote(cls.tmp)

    def _instance(self, s: _Session) -> Path:
        dest = s.tmp / "instance"
        dest.mkdir()
        archive = subprocess.run(
            ["git", "-C", str(self.remote.path), "archive", "HEAD"],
            stdout=subprocess.PIPE, check=True, env={"PATH": BASE_PATH, "HOME": str(s.home)},
        )
        subprocess.run(["tar", "-x", "-C", str(dest)], input=archive.stdout, check=True,
                       env={"PATH": BASE_PATH})
        return dest

    def _finalize(self, s: _Session, shell: tuple, dest: Path, context: str):
        block, n = re.subn(
            r'MAESTRO_CONTEXT="[^"\n]*"',
            lambda _m: 'MAESTRO_CONTEXT="' + _escape_for_double_quotes(context) + '"',
            _only_bash_block(FINALIZE),
        )
        self.assertEqual(n, 1, "the Finalize block has no single MAESTRO_CONTEXT value")
        return s.run(shell, block, s.values(str(dest)))

    def _registry_entry(self, s: _Session) -> dict:
        r = subprocess.run([str(PLUGIN_BIN / "maestro-net"), "list", "--json"],
                           env=s.env(), capture_output=True, text=True)
        _require_ok("maestro-net list", r)
        return json.loads(r.stdout)["instances"][ORCHESTRATOR_SLUG]

    def test_finalize_keeps_special_characters_verbatim(self):
        for name, shell in SHELLS:
            with self.subTest(shell=name):
                s = _Session(self.tmp, self.remote, _plugin_rows(self.remote.sha[:12]))
                dest = self._instance(s)

                _require_ok("finalize", self._finalize(s, shell, dest, FREE_TEXT))

                prefs = (dest / "private" / "preferences.md").read_text(encoding="utf-8")
                self.assertIn(FREE_TEXT, prefs)

    def test_register_keeps_dollar_and_backtick_verbatim(self):
        for name, shell in SHELLS:
            with self.subTest(shell=name):
                s = _Session(self.tmp, self.remote, _plugin_rows(self.remote.sha[:12]))
                dest = self._instance(s)
                _require_ok("finalize", self._finalize(s, shell, dest, "Plain context."))
                values = s.values(str(dest))
                values["<domain>"] = _escape_for_double_quotes(FREE_DOMAIN)

                _require_ok("register", s.run(shell, _only_bash_block(REGISTER), values))

                self.assertEqual(self._registry_entry(s)["domain"], FREE_DOMAIN)

    def test_register_falls_back_to_the_plugin_copy_when_not_on_path(self):
        for name, shell in SHELLS:
            with self.subTest(shell=name):
                s = _Session(self.tmp, self.remote, _plugin_rows(self.remote.sha[:12]))
                dest = self._instance(s)
                _require_ok("finalize", self._finalize(s, shell, dest, "Plain context."))
                self.assertIsNone(shutil.which("maestro-net", path=s.env(False)["PATH"]))
                values = s.values(str(dest))
                values["${CLAUDE_PLUGIN_ROOT}"] = str(PLUGIN_BIN.parent)

                r = s.run(shell, _only_bash_block(REGISTER), values, plugin_bin_on_path=False)

                _require_ok("register", r)
                self.assertEqual(self._registry_entry(s)["path"], os.path.realpath(dest))


# ---------------------------------------------------------------------------
# Static checks on the skill text
# ---------------------------------------------------------------------------

class TestCommandBlockHygiene(unittest.TestCase):
    def setUp(self):
        self.blocks = _bash_blocks(SKILL.read_text(encoding="utf-8"))

    def test_skill_has_command_blocks(self):
        self.assertGreaterEqual(len(self.blocks), 8)

    def test_every_block_starts_with_pipefail(self):
        for block in self.blocks:
            with self.subTest(block=block.splitlines()[0]):
                first = block.splitlines()[0]
                self.assertRegex(first, r"^set -e?o pipefail$")

    def test_no_block_uses_a_tilde_path_or_rg(self):
        for block in self.blocks:
            with self.subTest(block=block.splitlines()[0]):
                self.assertNotIn("~", block)
                self.assertNotRegex(block, r"(^|[\s|;&(])rg\s")


class TestSkillText(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_frontmatter_values_with_a_colon_are_quoted(self):
        # An unquoted `: ` inside a plain scalar makes the whole frontmatter
        # invalid YAML, and `disable-model-invocation` goes with it.
        frontmatter = self.text.split("---\n")[1]
        for line in frontmatter.splitlines():
            key, _, value = line.partition(": ")
            with self.subTest(key=key):
                if ": " in value:
                    self.assertRegex(value, r'^".*"$')

    def test_territory_question_writes_nothing(self):
        # Folders are created after the summary is confirmed, so a corrected
        # project name leaves nothing stale behind.
        self.assertEqual(_bash_blocks(_section(QUESTION_TERRITORIES)), [])

    def test_finalize_states_the_escaping_rule_and_never_rephrases(self):
        body = _section(FINALIZE)
        self.assertNotIn("ephrase", body)
        for escaped in ("`\\\\`", '`\\"`', "`\\$`"):
            with self.subTest(escaped=escaped):
                self.assertIn(escaped, body)

    def test_title_is_new_instance(self):
        self.assertIn("\n# New instance\n", self.text)

    def test_no_trace_of_the_old_setup_skill(self):
        self.assertNotIn(".disabled", self.text)
        self.assertNotIn(".claude/skills/setup", self.text)

    def test_hand_off_tells_the_owner_how_to_open_the_instance(self):
        self.assertIn('cd "<destination>" && claude', _section("## Hand-off"))


class TestDayZeroTemplates(unittest.TestCase):
    """The day-zero notes follow the writing register: their templates pass
    `bin/register-check` before a model fills them in."""

    def _check(self, prefix: str) -> subprocess.CompletedProcess:
        tmp = Path(tempfile.mkdtemp(prefix="maestro-day-zero-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        note = tmp / "note.md"
        note.write_text(_markdown_template(prefix), encoding="utf-8")
        return subprocess.run(
            [str(REGISTER_CHECK), str(note)], env={"PATH": BASE_PATH},
            capture_output=True, text=True,
        )

    def test_logbook_template_passes_register_check(self):
        r = self._check(LOGBOOK)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_til_template_passes_register_check(self):
        r = self._check(TIL)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
