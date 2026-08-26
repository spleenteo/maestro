"""Tests for user-skills/maestro-net/maestro-net — stdlib only, no network, no real instances."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "user-skills" / "maestro-net" / "maestro-net"

# Exit codes: the degradation contract of the channel.
OK = 0
E_USAGE = 2
E_NO_REGISTRY = 3
E_BAD_REGISTRY = 4
E_UNKNOWN_INSTANCE = 5
E_VERB_REFUSED = 6
E_DEAD_PATH = 7
E_REMOTE_FAILED = 8


def run(*args, env=None, cwd=None, stdin=None):
    base = dict(os.environ)
    base.pop("MEM_DB", None)
    base.pop("MAESTRO_INSTANCES", None)
    if env:
        base.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, env=base, cwd=cwd, input=stdin,
    )


def fake_instance(root, name, with_mem=True, with_prefs=True):
    """Create a directory that looks like a Maestro instance."""
    d = Path(root) / name
    (d / "bin").mkdir(parents=True, exist_ok=True)
    (d / "private").mkdir(parents=True, exist_ok=True)
    if with_mem:
        mem = d / "bin" / "mem"
        mem.write_text("#!/bin/sh\nexit 0\n")
        mem.chmod(0o755)
    if with_prefs:
        (d / "private" / "preferences.md").write_text(
            f"---\nsetup_completed: true\n---\n\n## Identity\n\n- **Name**: {name.capitalize()}\n"
        )
    return d


REGISTRY = """\
version: 1
instances:
  alfred:
    path: {alfred}
    domain: vita personale
    accepts: [recap, ask]
  pam:
    path: {pam}
    domain: lavoro DatoCMS
    accepts: [recap]
"""


class RegistryFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.alfred = fake_instance(self.root, "alfred")
        self.pam = fake_instance(self.root, "pam")
        self.registry = self.root / "maestro-instances.yaml"
        self.registry.write_text(REGISTRY.format(alfred=self.alfred, pam=self.pam))

    def tearDown(self):
        self.tmp.cleanup()

    def run_net(self, *args, **kw):
        return run("--registry", str(self.registry), *args, **kw)


class TestRegistryLoading(RegistryFixture):
    def test_lists_instances_from_registry(self):
        r = self.run_net("list")
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("alfred", r.stdout)
        self.assertIn("pam", r.stdout)

    def test_list_json_carries_path_domain_accepts(self):
        r = self.run_net("list", "--json")
        self.assertEqual(r.returncode, OK, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["instances"]["alfred"]["domain"], "vita personale")
        self.assertEqual(data["instances"]["alfred"]["accepts"], ["recap", "ask"])
        self.assertEqual(data["instances"]["pam"]["accepts"], ["recap"])

    def test_missing_registry_exits_3_and_names_the_scan_command(self):
        r = run("--registry", str(self.root / "nope.yaml"), "list")
        self.assertEqual(r.returncode, E_NO_REGISTRY)
        self.assertIn("scan", r.stderr)
        self.assertIn("nope.yaml", r.stderr)

    def test_malformed_yaml_exits_4_with_line_number(self):
        self.registry.write_text("version: 1\ninstances:\n  alfred:\n\tpath: /x\n")
        r = self.run_net("list")
        self.assertEqual(r.returncode, E_BAD_REGISTRY)
        self.assertIn("4", r.stderr)

    def test_registry_without_instances_key_exits_4(self):
        self.registry.write_text("version: 1\n")
        r = self.run_net("list")
        self.assertEqual(r.returncode, E_BAD_REGISTRY)
        self.assertIn("instances", r.stderr)

    def test_unsupported_version_exits_4(self):
        self.registry.write_text("version: 99\ninstances:\n  alfred:\n    path: /x\n")
        r = self.run_net("list")
        self.assertEqual(r.returncode, E_BAD_REGISTRY)
        self.assertIn("version", r.stderr)

    def test_instance_without_path_exits_4(self):
        self.registry.write_text("version: 1\ninstances:\n  alfred:\n    domain: x\n")
        r = self.run_net("list")
        self.assertEqual(r.returncode, E_BAD_REGISTRY)
        self.assertIn("path", r.stderr)

    def test_empty_registry_file_exits_4(self):
        self.registry.write_text("")
        r = self.run_net("list")
        self.assertEqual(r.returncode, E_BAD_REGISTRY)

    def test_env_var_supplies_the_registry_path(self):
        r = run("list", env={"MAESTRO_INSTANCES": str(self.registry)})
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("alfred", r.stdout)


class TestInstanceResolution(RegistryFixture):
    def test_exact_name_resolves(self):
        r = self.run_net("recap", "alfred", "ciao", "--dry-run")
        self.assertEqual(r.returncode, OK, r.stderr)

    def test_name_is_case_insensitive(self):
        r = self.run_net("recap", "Alfred", "ciao", "--dry-run")
        self.assertEqual(r.returncode, OK, r.stderr)

    def test_unique_prefix_resolves(self):
        r = self.run_net("recap", "alf", "ciao", "--dry-run")
        self.assertEqual(r.returncode, OK, r.stderr)

    def test_ambiguous_prefix_exits_5_and_lists_candidates(self):
        self.registry.write_text(
            self.registry.read_text()
            + f"  alfredo:\n    path: {self.alfred}\n    accepts: [recap]\n"
        )
        r = self.run_net("recap", "alf", "ciao", "--dry-run")
        self.assertEqual(r.returncode, E_UNKNOWN_INSTANCE)
        self.assertIn("alfred", r.stderr)
        self.assertIn("alfredo", r.stderr)

    def test_unknown_instance_exits_5_and_lists_known_names(self):
        r = self.run_net("recap", "zorro", "ciao", "--dry-run")
        self.assertEqual(r.returncode, E_UNKNOWN_INSTANCE)
        self.assertIn("zorro", r.stderr)
        self.assertIn("alfred", r.stderr)
        self.assertIn("pam", r.stderr)

    def test_vanished_path_exits_7(self):
        self.registry.write_text(
            f"version: 1\ninstances:\n  ghost:\n    path: {self.root}/gone\n    accepts: [recap]\n"
        )
        r = self.run_net("recap", "ghost", "ciao", "--dry-run")
        self.assertEqual(r.returncode, E_DEAD_PATH)
        self.assertIn("gone", r.stderr)

    def test_path_without_bin_mem_exits_7(self):
        naked = fake_instance(self.root, "naked", with_mem=False)
        self.registry.write_text(
            f"version: 1\ninstances:\n  naked:\n    path: {naked}\n    accepts: [recap]\n"
        )
        r = self.run_net("recap", "naked", "ciao", "--dry-run")
        self.assertEqual(r.returncode, E_DEAD_PATH)
        self.assertIn("bin/mem", r.stderr)


class TestAcceptsGate(RegistryFixture):
    def test_verb_outside_accepts_is_refused_with_6(self):
        r = self.run_net("ask", "pam", "che ore sono", "--dry-run")
        self.assertEqual(r.returncode, E_VERB_REFUSED)
        self.assertIn("ask", r.stderr)
        self.assertIn("pam", r.stderr)

    def test_verb_inside_accepts_passes(self):
        r = self.run_net("ask", "alfred", "che ore sono", "--dry-run")
        self.assertEqual(r.returncode, OK, r.stderr)

    def test_missing_accepts_field_refuses_every_verb(self):
        self.registry.write_text(
            f"version: 1\ninstances:\n  mute:\n    path: {self.alfred}\n"
        )
        r = self.run_net("recap", "mute", "ciao", "--dry-run")
        self.assertEqual(r.returncode, E_VERB_REFUSED)
        self.assertIn("accepts", r.stderr)

    def test_empty_accepts_list_refuses_every_verb(self):
        self.registry.write_text(
            f"version: 1\ninstances:\n  mute:\n    path: {self.alfred}\n    accepts: []\n"
        )
        r = self.run_net("recap", "mute", "ciao", "--dry-run")
        self.assertEqual(r.returncode, E_VERB_REFUSED)

    def test_unknown_verb_in_accepts_is_rejected_as_malformed(self):
        self.registry.write_text(
            f"version: 1\ninstances:\n  odd:\n    path: {self.alfred}\n    accepts: [recap, handoff]\n"
        )
        r = self.run_net("list")
        self.assertEqual(r.returncode, E_BAD_REGISTRY)
        self.assertIn("handoff", r.stderr)


MEM_RECORDER = """\
#!/bin/sh
{
  echo "MEM_DB=${MEM_DB:-<unset>}"
  echo "CWD=$(pwd)"
  for a in "$@"; do echo "ARG=$a"; done
} >> "$MEM_LOG"
exit ${MEM_EXIT:-0}
"""


def recording_mem(instance_dir):
    """Replace bin/mem with a recorder that appends its argv and env to $MEM_LOG."""
    mem = Path(instance_dir) / "bin" / "mem"
    mem.write_text(MEM_RECORDER)
    mem.chmod(0o755)
    return mem


class TestRecap(RegistryFixture):
    def setUp(self):
        super().setUp()
        recording_mem(self.alfred)
        self.log = self.root / "mem.log"

    def recap(self, *args, env=None):
        base = {"MEM_LOG": str(self.log)}
        base.update(env or {})
        return self.run_net("recap", *args, env=base)

    def logged(self):
        return self.log.read_text() if self.log.exists() else ""

    def test_calls_bin_mem_save_with_the_text(self):
        r = self.recap("alfred", "abbiamo finito maestro-net")
        self.assertEqual(r.returncode, OK, r.stderr)
        log = self.logged()
        self.assertIn("ARG=save", log)
        self.assertIn("ARG=abbiamo finito maestro-net", log)

    def test_tags_the_row_with_the_sender(self):
        self.recap("alfred", "ciao", "--from", "pam")
        self.assertIn("from:pam", self.logged())

    def test_sender_defaults_to_the_registry_name_of_the_current_directory(self):
        recording_mem(self.pam)
        r = run("--registry", str(self.registry), "recap", "alfred", "ciao",
                cwd=str(self.pam), env={"MEM_LOG": str(self.log)})
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("from:pam", self.logged())

    def test_sender_falls_back_to_the_directory_name_and_says_so(self):
        outside = self.root / "un-repo-qualunque"
        outside.mkdir()
        r = run("--registry", str(self.registry), "recap", "alfred", "ciao",
                cwd=str(outside), env={"MEM_LOG": str(self.log)})
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("from:un-repo-qualunque", self.logged())
        self.assertIn("un-repo-qualunque", r.stdout + r.stderr)

    def test_extra_tags_join_the_sender_tag(self):
        self.recap("alfred", "ciao", "-t", "maestro,net")
        log = self.logged()
        self.assertIn("maestro", log)
        self.assertIn("net", log)
        self.assertIn("from:", log)

    def test_description_is_forwarded(self):
        self.recap("alfred", "ciao", "-d", "il contesto lungo")
        self.assertIn("ARG=il contesto lungo", self.logged())

    def test_callers_mem_db_does_not_leak_into_the_recipient(self):
        self.recap("alfred", "ciao", env={"MEM_DB": "/tmp/wrong.db"})
        self.assertIn("MEM_DB=<unset>", self.logged())

    def test_runs_bin_mem_from_the_recipient_directory(self):
        self.recap("alfred", "ciao")
        self.assertIn(f"CWD={os.path.realpath(self.alfred)}", self.logged())

    def test_failing_bin_mem_exits_8_and_reports(self):
        r = self.recap("alfred", "ciao", env={"MEM_EXIT": "1"})
        self.assertEqual(r.returncode, E_REMOTE_FAILED)
        self.assertIn("alfred", r.stderr)

    def test_dry_run_executes_nothing(self):
        r = self.recap("alfred", "ciao", "--dry-run")
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertEqual(self.logged(), "")

    def test_confirmation_names_the_recipient(self):
        r = self.recap("alfred", "ciao")
        self.assertIn("alfred", r.stdout)


CLAUDE_RECORDER = """\
#!/bin/sh
{
  echo "MEM_DB=${MEM_DB:-<unset>}"
  echo "CWD=$(pwd)"
  for a in "$@"; do echo "ARG=$a"; done
} >> "$CLAUDE_LOG"
[ -n "$CLAUDE_SLEEP" ] && sleep "$CLAUDE_SLEEP"
echo "${CLAUDE_REPLY:-risposta headless}"
exit ${CLAUDE_EXIT:-0}
"""


class TestAsk(RegistryFixture):
    def setUp(self):
        super().setUp()
        self.bindir = self.root / "fakebin"
        self.bindir.mkdir()
        fake = self.bindir / "claude"
        fake.write_text(CLAUDE_RECORDER)
        fake.chmod(0o755)
        self.log = self.root / "claude.log"

    def ask(self, *args, env=None, path_with_claude=True):
        base = {"CLAUDE_LOG": str(self.log)}
        if path_with_claude:
            base["PATH"] = f"{self.bindir}:{os.environ['PATH']}"
        base.update(env or {})
        return self.run_net("ask", *args, env=base)

    def logged(self):
        return self.log.read_text() if self.log.exists() else ""

    def test_runs_claude_headless_in_the_recipient_directory(self):
        r = self.ask("alfred", "cosa sai delle biciclette")
        self.assertEqual(r.returncode, OK, r.stderr)
        log = self.logged()
        self.assertIn("ARG=-p", log)
        self.assertIn("cosa sai delle biciclette", log)
        self.assertIn(f"CWD={os.path.realpath(self.alfred)}", log)

    def test_prompt_declares_the_sender(self):
        self.ask("alfred", "domanda", "--from", "pam")
        self.assertIn("pam", self.logged())

    def test_prompt_forbids_writing(self):
        self.ask("alfred", "domanda")
        log = self.logged().lower()
        self.assertTrue(
            "non scrivere" in log or "sola lettura" in log,
            f"il prompt non porta il vincolo di sola lettura:\n{self.logged()}",
        )

    def test_reply_is_reported_to_the_caller(self):
        r = self.ask("alfred", "domanda", env={"CLAUDE_REPLY": "so tutto delle biciclette"})
        self.assertIn("so tutto delle biciclette", r.stdout)

    def test_callers_mem_db_does_not_leak(self):
        self.ask("alfred", "domanda", env={"MEM_DB": "/tmp/wrong.db"})
        self.assertIn("MEM_DB=<unset>", self.logged())

    def test_failing_claude_exits_8(self):
        r = self.ask("alfred", "domanda", env={"CLAUDE_EXIT": "1"})
        self.assertEqual(r.returncode, E_REMOTE_FAILED)
        self.assertIn("alfred", r.stderr)

    def test_missing_claude_binary_exits_8_and_names_it(self):
        r = self.ask("alfred", "domanda", env={"PATH": str(self.bindir / "empty")},
                     path_with_claude=False)
        self.assertEqual(r.returncode, E_REMOTE_FAILED)
        self.assertIn("claude", r.stderr)

    def test_timeout_exits_8_and_says_how_long_it_waited(self):
        r = self.ask("alfred", "domanda", "--timeout", "1", env={"CLAUDE_SLEEP": "5"})
        self.assertEqual(r.returncode, E_REMOTE_FAILED)
        self.assertIn("1", r.stderr)

    def test_dry_run_executes_nothing(self):
        r = self.ask("alfred", "domanda", "--dry-run")
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertEqual(self.logged(), "")


def transcript(projects_root, slug, cwd):
    """Fake Claude Code transcript directory: one jsonl carrying a cwd."""
    d = Path(projects_root) / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "session.jsonl").write_text(
        json.dumps({"type": "user", "cwd": str(cwd), "message": {"content": "ciao"}}) + "\n"
    )
    return d


class TestScan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.projects = self.root / "projects"
        self.projects.mkdir()
        self.registry = self.root / "maestro-instances.yaml"

    def tearDown(self):
        self.tmp.cleanup()

    def scan(self, *args):
        return run("--registry", str(self.registry), "scan", *args,
                   env={"CLAUDE_PROJECTS_ROOT": str(self.projects)})

    def test_finds_instance_reached_through_a_transcript_cwd(self):
        inst = fake_instance(self.root, "alfred")
        transcript(self.projects, "-Users-x-alfred", inst)
        r = self.scan()
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("alfred:", r.stdout)
        self.assertIn(str(inst), r.stdout)

    def test_skips_directory_without_preferences(self):
        inst = fake_instance(self.root, "notmaestro", with_prefs=False)
        transcript(self.projects, "-x-notmaestro", inst)
        r = self.scan()
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertNotIn("notmaestro:", r.stdout)

    def test_skips_directory_without_bin_mem(self):
        inst = fake_instance(self.root, "halfway", with_mem=False)
        transcript(self.projects, "-x-halfway", inst)
        r = self.scan()
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertNotIn("halfway:", r.stdout)

    def test_reads_the_name_from_a_bold_identity_line(self):
        inst = fake_instance(self.root, "dir-name-differs")
        (inst / "private" / "preferences.md").write_text(
            "## Identity (the orchestrator)\n\n- **Name**: Alfred\n- **Adjectives**: calmo\n"
        )
        transcript(self.projects, "-x-1", inst)
        r = self.scan()
        self.assertIn("alfred:", r.stdout)

    def test_reads_the_name_from_a_plain_identity_line(self):
        inst = fake_instance(self.root, "dir-name-differs")
        (inst / "private" / "preferences.md").write_text(
            "## Identity (the orchestrator)\n\n- Name: Claudio\n- Adjectives: preciso\n"
        )
        transcript(self.projects, "-x-1", inst)
        r = self.scan()
        self.assertIn("claudio:", r.stdout)

    def test_unreadable_name_falls_back_to_folder_and_warns(self):
        inst = fake_instance(self.root, "senzanome")
        (inst / "private" / "preferences.md").write_text("---\nsetup_completed: true\n---\n\nniente identity\n")
        transcript(self.projects, "-x-1", inst)
        r = self.scan()
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("senzanome:", r.stdout)
        self.assertIn("senzanome", r.stderr)
        self.assertIn("confermare", r.stderr.lower())

    def test_two_slugs_on_the_same_cwd_produce_one_entry(self):
        inst = fake_instance(self.root, "alfred")
        transcript(self.projects, "-slug-one", inst)
        transcript(self.projects, "-slug-two", inst)
        r = self.scan()
        self.assertEqual(r.stdout.count("alfred:"), 1, r.stdout)

    def test_two_instances_sharing_a_name_are_disambiguated(self):
        a = fake_instance(self.root, "first")
        b = fake_instance(self.root, "second")
        for d in (a, b):
            (d / "private" / "preferences.md").write_text("## Identity\n\n- **Name**: Alfred\n")
        transcript(self.projects, "-x-a", a)
        transcript(self.projects, "-x-b", b)
        r = self.scan()
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("alfred:", r.stdout)
        self.assertIn("alfred-2:", r.stdout)
        self.assertIn("omonim", r.stderr.lower())

    def test_scan_output_round_trips_through_the_parser(self):
        inst = fake_instance(self.root, "alfred")
        transcript(self.projects, "-x-1", inst)
        out = self.scan().stdout
        proposed = self.root / "proposed.yaml"
        proposed.write_text(out)
        r = run("--registry", str(proposed), "list", "--json")
        self.assertEqual(r.returncode, OK, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(data["instances"]["alfred"]["path"], str(inst))

    def test_default_accepts_can_be_narrowed_by_flag(self):
        inst = fake_instance(self.root, "alfred")
        transcript(self.projects, "-x-1", inst)
        out = self.scan("--accepts", "recap").stdout
        self.assertIn("accepts: [recap]", out)

    def test_write_creates_the_registry(self):
        inst = fake_instance(self.root, "alfred")
        transcript(self.projects, "-x-1", inst)
        r = self.scan("--write")
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertTrue(self.registry.is_file())
        self.assertIn("alfred:", self.registry.read_text())

    def test_write_refuses_to_overwrite_without_force(self):
        inst = fake_instance(self.root, "alfred")
        transcript(self.projects, "-x-1", inst)
        self.registry.write_text("version: 1\ninstances:\n")
        r = self.scan("--write")
        self.assertEqual(r.returncode, E_USAGE)
        self.assertIn("--force", r.stderr)
        self.assertEqual(self.registry.read_text(), "version: 1\ninstances:\n")

    def test_write_force_overwrites(self):
        inst = fake_instance(self.root, "alfred")
        transcript(self.projects, "-x-1", inst)
        self.registry.write_text("version: 1\ninstances:\n")
        r = self.scan("--write", "--force")
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("alfred:", self.registry.read_text())

    def test_missing_projects_root_is_explicit(self):
        r = run("--registry", str(self.registry), "scan",
                env={"CLAUDE_PROJECTS_ROOT": str(self.root / "nowhere")})
        self.assertNotEqual(r.returncode, OK)
        self.assertIn("nowhere", r.stderr)

    def test_no_instance_found_writes_nothing(self):
        r = self.scan("--write")
        self.assertFalse(self.registry.exists())
        self.assertIn("nessuna istanza", r.stderr.lower())


class TestCli(unittest.TestCase):
    def test_no_verb_exits_2(self):
        r = run()
        self.assertEqual(r.returncode, E_USAGE)

    def test_unknown_verb_exits_2(self):
        r = run("teleport", "alfred")
        self.assertEqual(r.returncode, E_USAGE)

    def test_help_exits_0(self):
        r = run("--help")
        self.assertEqual(r.returncode, OK)
        self.assertIn("recap", r.stdout)
        self.assertIn("ask", r.stdout)
        self.assertIn("scan", r.stdout)


if __name__ == "__main__":
    unittest.main()
