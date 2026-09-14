"""Tests for plugins/maestro/bin/maestro-net — stdlib only, no network, no real instances."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "plugins" / "maestro" / "bin" / "maestro-net"

# Exit codes: the degradation contract of the channel.
OK = 0
E_USAGE = 2
E_NO_REGISTRY = 3
E_BAD_REGISTRY = 4
E_UNKNOWN_INSTANCE = 5
E_VERB_REFUSED = 6
E_DEAD_PATH = 7
E_REMOTE_FAILED = 8
E_EXISTS = 9


def run(*args, env=None, cwd=None, stdin=None):
    base = dict(os.environ)
    base.pop("MEM_DB", None)
    base.pop("MEM_SCOPE", None)
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
  home:
    path: {home}
    domain: vita personale
    accepts: [recap, ask]
  work:
    path: {work}
    domain: lavoro in azienda SaaS
    accepts: [recap]
"""


class RegistryFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = fake_instance(self.root, "home")
        self.work = fake_instance(self.root, "work")
        self.registry = self.root / "maestro-instances.yaml"
        self.registry.write_text(REGISTRY.format(home=self.home, work=self.work))

    def tearDown(self):
        self.tmp.cleanup()

    def run_net(self, *args, **kw):
        return run("--registry", str(self.registry), *args, **kw)


class TestRegistryLoading(RegistryFixture):
    def test_lists_instances_from_registry(self):
        r = self.run_net("list")
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("home", r.stdout)
        self.assertIn("work", r.stdout)

    def test_list_json_carries_path_domain_accepts(self):
        r = self.run_net("list", "--json")
        self.assertEqual(r.returncode, OK, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["instances"]["home"]["domain"], "vita personale")
        self.assertEqual(data["instances"]["home"]["accepts"], ["recap", "ask"])
        self.assertEqual(data["instances"]["work"]["accepts"], ["recap"])

    def test_missing_registry_exits_3_and_names_the_scan_command(self):
        r = run("--registry", str(self.root / "nope.yaml"), "list")
        self.assertEqual(r.returncode, E_NO_REGISTRY)
        self.assertIn("scan", r.stderr)
        self.assertIn("nope.yaml", r.stderr)

    def test_malformed_yaml_exits_4_with_line_number(self):
        self.registry.write_text("version: 1\ninstances:\n  home:\n\tpath: /x\n")
        r = self.run_net("list")
        self.assertEqual(r.returncode, E_BAD_REGISTRY)
        self.assertIn("4", r.stderr)

    def test_registry_without_instances_key_exits_4(self):
        self.registry.write_text("version: 1\n")
        r = self.run_net("list")
        self.assertEqual(r.returncode, E_BAD_REGISTRY)
        self.assertIn("instances", r.stderr)

    def test_unsupported_version_exits_4(self):
        self.registry.write_text("version: 99\ninstances:\n  home:\n    path: /x\n")
        r = self.run_net("list")
        self.assertEqual(r.returncode, E_BAD_REGISTRY)
        self.assertIn("version", r.stderr)

    def test_instance_without_path_exits_4(self):
        self.registry.write_text("version: 1\ninstances:\n  home:\n    domain: x\n")
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
        self.assertIn("home", r.stdout)


class TestInstanceResolution(RegistryFixture):
    def test_exact_name_resolves(self):
        r = self.run_net("recap", "home", "ciao", "--dry-run")
        self.assertEqual(r.returncode, OK, r.stderr)

    def test_name_is_case_insensitive(self):
        r = self.run_net("recap", "Home", "ciao", "--dry-run")
        self.assertEqual(r.returncode, OK, r.stderr)

    def test_unique_prefix_resolves(self):
        r = self.run_net("recap", "hom", "ciao", "--dry-run")
        self.assertEqual(r.returncode, OK, r.stderr)

    def test_ambiguous_prefix_exits_5_and_lists_candidates(self):
        self.registry.write_text(
            self.registry.read_text()
            + f"  homer:\n    path: {self.home}\n    accepts: [recap]\n"
        )
        r = self.run_net("recap", "hom", "ciao", "--dry-run")
        self.assertEqual(r.returncode, E_UNKNOWN_INSTANCE)
        self.assertIn("home", r.stderr)
        self.assertIn("homer", r.stderr)

    def test_unknown_instance_exits_5_and_lists_known_names(self):
        r = self.run_net("recap", "zorro", "ciao", "--dry-run")
        self.assertEqual(r.returncode, E_UNKNOWN_INSTANCE)
        self.assertIn("zorro", r.stderr)
        self.assertIn("home", r.stderr)
        self.assertIn("work", r.stderr)

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
        r = self.run_net("ask", "work", "che ore sono", "--dry-run")
        self.assertEqual(r.returncode, E_VERB_REFUSED)
        self.assertIn("ask", r.stderr)
        self.assertIn("work", r.stderr)

    def test_verb_inside_accepts_passes(self):
        r = self.run_net("ask", "home", "che ore sono", "--dry-run")
        self.assertEqual(r.returncode, OK, r.stderr)

    def test_missing_accepts_field_refuses_every_verb(self):
        self.registry.write_text(
            f"version: 1\ninstances:\n  mute:\n    path: {self.home}\n"
        )
        r = self.run_net("recap", "mute", "ciao", "--dry-run")
        self.assertEqual(r.returncode, E_VERB_REFUSED)
        self.assertIn("accepts", r.stderr)

    def test_empty_accepts_list_refuses_every_verb(self):
        self.registry.write_text(
            f"version: 1\ninstances:\n  mute:\n    path: {self.home}\n    accepts: []\n"
        )
        r = self.run_net("recap", "mute", "ciao", "--dry-run")
        self.assertEqual(r.returncode, E_VERB_REFUSED)

    def test_unknown_verb_in_accepts_becomes_a_warning_and_is_dropped(self):
        self.registry.write_text(
            f"version: 1\ninstances:\n  odd:\n    path: {self.home}\n    accepts: [recap, handoff]\n"
        )
        r = self.run_net("list")
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("odd", r.stderr)
        self.assertIn("handoff", r.stderr)

        r = self.run_net("list", "--json")
        self.assertEqual(r.returncode, OK, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(data["instances"]["odd"]["accepts"], ["recap"])


MEM_RECORDER = """\
#!/bin/sh
{
  echo "MEM_DB=${MEM_DB:-<unset>}"
  echo "MEM_SCOPE=${MEM_SCOPE:-<unset>}"
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
        recording_mem(self.home)
        self.log = self.root / "mem.log"

    def recap(self, *args, env=None):
        base = {"MEM_LOG": str(self.log)}
        base.update(env or {})
        return self.run_net("recap", *args, env=base)

    def logged(self):
        return self.log.read_text() if self.log.exists() else ""

    def test_calls_bin_mem_save_with_the_text(self):
        r = self.recap("home", "abbiamo finito maestro-net")
        self.assertEqual(r.returncode, OK, r.stderr)
        log = self.logged()
        self.assertIn("ARG=save", log)
        self.assertIn("ARG=abbiamo finito maestro-net", log)

    def test_tags_the_row_with_the_sender(self):
        self.recap("home", "ciao", "--from", "work")
        self.assertIn("from:work", self.logged())

    def test_sender_defaults_to_the_registry_name_of_the_current_directory(self):
        recording_mem(self.work)
        r = run("--registry", str(self.registry), "recap", "home", "ciao",
                cwd=str(self.work), env={"MEM_LOG": str(self.log)})
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("from:work", self.logged())

    def test_sender_falls_back_to_the_directory_name_and_says_so(self):
        outside = self.root / "un-repo-qualunque"
        outside.mkdir()
        r = run("--registry", str(self.registry), "recap", "home", "ciao",
                cwd=str(outside), env={"MEM_LOG": str(self.log)})
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("from:un-repo-qualunque", self.logged())
        self.assertIn("un-repo-qualunque", r.stdout + r.stderr)

    def test_extra_tags_join_the_sender_tag(self):
        self.recap("home", "ciao", "-t", "maestro,net")
        log = self.logged()
        self.assertIn("maestro", log)
        self.assertIn("net", log)
        self.assertIn("from:", log)

    def test_description_is_forwarded(self):
        self.recap("home", "ciao", "-d", "il contesto lungo")
        self.assertIn("ARG=il contesto lungo", self.logged())

    def test_callers_mem_db_does_not_leak_into_the_recipient(self):
        self.recap("home", "ciao", env={"MEM_DB": "/tmp/wrong.db"})
        self.assertIn("MEM_DB=<unset>", self.logged())

    def test_callers_mem_scope_does_not_leak_into_the_recipient(self):
        self.recap("home", "ciao", env={"MEM_SCOPE": "acme"})
        self.assertIn("MEM_SCOPE=<unset>", self.logged())

    def test_unknown_verb_in_accepts_does_not_block_known_verbs(self):
        self.registry.write_text(
            f"version: 1\ninstances:\n  home:\n    path: {self.home}\n"
            f"    accepts: [recap, ask, request]\n"
        )
        r = self.recap("home", "ciao")
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("ARG=save", self.logged())
        self.assertIn("home", r.stderr)
        self.assertIn("request", r.stderr)

    def test_runs_bin_mem_from_the_recipient_directory(self):
        self.recap("home", "ciao")
        self.assertIn(f"CWD={os.path.realpath(self.home)}", self.logged())

    def test_failing_bin_mem_exits_8_and_reports(self):
        r = self.recap("home", "ciao", env={"MEM_EXIT": "1"})
        self.assertEqual(r.returncode, E_REMOTE_FAILED)
        self.assertIn("home", r.stderr)

    def test_dry_run_executes_nothing(self):
        r = self.recap("home", "ciao", "--dry-run")
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertEqual(self.logged(), "")

    def test_confirmation_names_the_recipient(self):
        r = self.recap("home", "ciao")
        self.assertIn("home", r.stdout)


CLAUDE_RECORDER = """\
#!/bin/sh
{
  echo "MEM_DB=${MEM_DB:-<unset>}"
  echo "MEM_SCOPE=${MEM_SCOPE:-<unset>}"
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
        r = self.ask("home", "cosa sai delle biciclette")
        self.assertEqual(r.returncode, OK, r.stderr)
        log = self.logged()
        self.assertIn("ARG=-p", log)
        self.assertIn("cosa sai delle biciclette", log)
        self.assertIn(f"CWD={os.path.realpath(self.home)}", log)

    def test_prompt_declares_the_sender(self):
        self.ask("home", "domanda", "--from", "work")
        self.assertIn("work", self.logged())

    def test_prompt_forbids_writing(self):
        self.ask("home", "domanda")
        log = self.logged().lower()
        self.assertTrue(
            "non scrivere" in log or "sola lettura" in log,
            f"il prompt non porta il vincolo di sola lettura:\n{self.logged()}",
        )

    def test_reply_is_reported_to_the_caller(self):
        r = self.ask("home", "domanda", env={"CLAUDE_REPLY": "so tutto delle biciclette"})
        self.assertIn("so tutto delle biciclette", r.stdout)

    def test_callers_mem_db_does_not_leak(self):
        self.ask("home", "domanda", env={"MEM_DB": "/tmp/wrong.db"})
        self.assertIn("MEM_DB=<unset>", self.logged())

    def test_callers_mem_scope_does_not_leak(self):
        self.ask("home", "domanda", env={"MEM_SCOPE": "acme"})
        self.assertIn("MEM_SCOPE=<unset>", self.logged())

    def test_failing_claude_exits_8(self):
        r = self.ask("home", "domanda", env={"CLAUDE_EXIT": "1"})
        self.assertEqual(r.returncode, E_REMOTE_FAILED)
        self.assertIn("home", r.stderr)

    def test_missing_claude_binary_exits_8_and_names_it(self):
        r = self.ask("home", "domanda", env={"PATH": str(self.bindir / "empty")},
                     path_with_claude=False)
        self.assertEqual(r.returncode, E_REMOTE_FAILED)
        self.assertIn("claude", r.stderr)

    def test_timeout_exits_8_and_says_how_long_it_waited(self):
        r = self.ask("home", "domanda", "--timeout", "1", env={"CLAUDE_SLEEP": "5"})
        self.assertEqual(r.returncode, E_REMOTE_FAILED)
        self.assertIn("1", r.stderr)

    def test_dry_run_executes_nothing(self):
        r = self.ask("home", "domanda", "--dry-run")
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
        inst = fake_instance(self.root, "home")
        transcript(self.projects, "-Users-x-home", inst)
        r = self.scan()
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("home:", r.stdout)
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
            "## Identity (the orchestrator)\n\n- **Name**: Home\n- **Adjectives**: calmo\n"
        )
        transcript(self.projects, "-x-1", inst)
        r = self.scan()
        self.assertIn("home:", r.stdout)

    def test_reads_the_name_from_a_plain_identity_line(self):
        inst = fake_instance(self.root, "dir-name-differs")
        (inst / "private" / "preferences.md").write_text(
            "## Identity (the orchestrator)\n\n- Name: Side\n- Adjectives: preciso\n"
        )
        transcript(self.projects, "-x-1", inst)
        r = self.scan()
        self.assertIn("side:", r.stdout)

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
        inst = fake_instance(self.root, "home")
        transcript(self.projects, "-slug-one", inst)
        transcript(self.projects, "-slug-two", inst)
        r = self.scan()
        self.assertEqual(r.stdout.count("home:"), 1, r.stdout)

    def test_two_instances_sharing_a_name_are_disambiguated(self):
        a = fake_instance(self.root, "first")
        b = fake_instance(self.root, "second")
        for d in (a, b):
            (d / "private" / "preferences.md").write_text("## Identity\n\n- **Name**: Home\n")
        transcript(self.projects, "-x-a", a)
        transcript(self.projects, "-x-b", b)
        r = self.scan()
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("home:", r.stdout)
        self.assertIn("home-2:", r.stdout)
        self.assertIn("omonim", r.stderr.lower())

    def test_scan_output_round_trips_through_the_parser(self):
        inst = fake_instance(self.root, "home")
        transcript(self.projects, "-x-1", inst)
        out = self.scan().stdout
        proposed = self.root / "proposed.yaml"
        proposed.write_text(out)
        r = run("--registry", str(proposed), "list", "--json")
        self.assertEqual(r.returncode, OK, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(data["instances"]["home"]["path"], str(inst))

    def test_default_accepts_can_be_narrowed_by_flag(self):
        inst = fake_instance(self.root, "home")
        transcript(self.projects, "-x-1", inst)
        out = self.scan("--accepts", "recap").stdout
        self.assertIn("accepts: [recap]", out)

    def test_write_creates_the_registry(self):
        inst = fake_instance(self.root, "home")
        transcript(self.projects, "-x-1", inst)
        r = self.scan("--write")
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertTrue(self.registry.is_file())
        self.assertIn("home:", self.registry.read_text())

    def test_write_refuses_to_overwrite_without_force(self):
        inst = fake_instance(self.root, "home")
        transcript(self.projects, "-x-1", inst)
        self.registry.write_text("version: 1\ninstances:\n")
        r = self.scan("--write")
        self.assertEqual(r.returncode, E_USAGE)
        self.assertIn("--force", r.stderr)
        self.assertEqual(self.registry.read_text(), "version: 1\ninstances:\n")

    def test_write_force_overwrites(self):
        inst = fake_instance(self.root, "home")
        transcript(self.projects, "-x-1", inst)
        self.registry.write_text("version: 1\ninstances:\n")
        r = self.scan("--write", "--force")
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("home:", self.registry.read_text())

    def test_missing_projects_root_is_explicit(self):
        r = run("--registry", str(self.registry), "scan",
                env={"CLAUDE_PROJECTS_ROOT": str(self.root / "nowhere")})
        self.assertNotEqual(r.returncode, OK)
        self.assertIn("nowhere", r.stderr)

    def test_no_instance_found_writes_nothing(self):
        r = self.scan("--write")
        self.assertFalse(self.registry.exists())
        self.assertIn("nessuna istanza", r.stderr.lower())


class TestRegister(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.registry = self.root / "maestro-instances.yaml"

    def tearDown(self):
        self.tmp.cleanup()

    def register(self, *args, **kw):
        return run("--registry", str(self.registry), "register", *args, **kw)

    def make_instance(self, name):
        return fake_instance(self.root, name)

    def test_creates_registry_from_nothing(self):
        inst = self.make_instance("home")
        r = self.register("home", "--path", str(inst))
        self.assertEqual(r.returncode, OK, r.stderr)
        text = self.registry.read_text()
        self.assertIn("version: 1", text)
        self.assertIn("instances:", text)
        self.assertIn("  home:", text)
        self.assertIn(f"path: {os.path.realpath(inst)}", text)
        self.assertIn('domain: ""', text)
        self.assertIn("accepts: [recap, ask]", text)

    def test_confirmation_names_instance_and_path(self):
        inst = self.make_instance("home")
        r = self.register("home", "--path", str(inst))
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("home", r.stdout)
        self.assertIn(str(os.path.realpath(inst)), r.stdout)

    def test_append_keeps_other_entries_domain_accepts_and_comments(self):
        home = self.make_instance("home")
        work = self.make_instance("work")
        self.registry.write_text(
            "# nota personale sul registry\n"
            "version: 1\n"
            "instances:\n"
            "  home:\n"
            f"    path: {home}\n"
            '    domain: "vita personale"\n'
            "    accepts: [recap, ask]\n"
        )
        r = self.register("work", "--path", str(work), "--domain", "lavoro")
        self.assertEqual(r.returncode, OK, r.stderr)
        text = self.registry.read_text()
        self.assertIn("# nota personale sul registry", text)
        self.assertIn('domain: "vita personale"', text)
        self.assertIn("accepts: [recap, ask]", text)
        self.assertIn("  work:", text)
        self.assertIn('domain: "lavoro"', text)

    def test_registry_with_version_after_instances_stays_valid(self):
        home = self.make_instance("home")
        work = self.make_instance("work")
        self.registry.write_text(f"instances:\n  home:\n    path: {home}\nversion: 1\n")
        r = self.register("work", "--path", str(work))
        self.assertEqual(r.returncode, OK, r.stderr)
        lr = run("--registry", str(self.registry), "list", "--json")
        self.assertEqual(lr.returncode, OK, lr.stderr)
        data = json.loads(lr.stdout)
        self.assertIn("home", data["instances"])
        self.assertIn("work", data["instances"])

    def test_registry_without_trailing_newline_stays_valid(self):
        home = self.make_instance("home")
        work = self.make_instance("work")
        self.registry.write_text(f"version: 1\ninstances:\n  home:\n    path: {home}")
        r = self.register("work", "--path", str(work))
        self.assertEqual(r.returncode, OK, r.stderr)
        lr = run("--registry", str(self.registry), "list", "--json")
        self.assertEqual(lr.returncode, OK, lr.stderr)
        data = json.loads(lr.stdout)
        self.assertIn("home", data["instances"])
        self.assertIn("work", data["instances"])

    def test_duplicate_name_different_case_exits_9(self):
        home = self.make_instance("home")
        other = self.make_instance("other")
        self.registry.write_text(f"version: 1\ninstances:\n  Home:\n    path: {home}\n")
        r = self.register("home", "--path", str(other))
        self.assertEqual(r.returncode, E_EXISTS)
        self.assertIn("home", r.stderr.lower())

    def test_duplicate_path_via_symlink_exits_9(self):
        home = self.make_instance("home")
        self.registry.write_text(f"version: 1\ninstances:\n  home:\n    path: {home}\n")
        link = self.root / "home-link"
        link.symlink_to(home)
        r = self.register("home2", "--path", str(link))
        self.assertEqual(r.returncode, E_EXISTS)

    def test_missing_dir_exits_7(self):
        r = self.register("ghost", "--path", str(self.root / "nope"))
        self.assertEqual(r.returncode, E_DEAD_PATH)
        self.assertFalse(self.registry.exists())

    def test_dir_without_signature_exits_7(self):
        naked = self.root / "naked"
        naked.mkdir()
        r = self.register("naked", "--path", str(naked))
        self.assertEqual(r.returncode, E_DEAD_PATH)
        self.assertIn("bin/mem", r.stderr + " " + str(r.stderr))

    def test_domain_with_quote_is_refused(self):
        inst = self.make_instance("home")
        r = self.register("home", "--path", str(inst), "--domain", 'ha "virgolette"')
        self.assertEqual(r.returncode, E_USAGE)
        self.assertFalse(self.registry.exists())

    def test_domain_with_newline_is_refused(self):
        inst = self.make_instance("home")
        r = self.register("home", "--path", str(inst), "--domain", "riga1\nriga2")
        self.assertEqual(r.returncode, E_USAGE)

    def test_uppercase_name_refused(self):
        inst = self.make_instance("Home")
        r = self.register("Home", "--path", str(inst))
        self.assertEqual(r.returncode, E_USAGE)
        self.assertFalse(self.registry.exists())

    def test_relative_path_refused(self):
        inst = self.make_instance("home")
        r = self.register("home", "--path", "relative/path")
        self.assertEqual(r.returncode, E_USAGE)

    def test_unknown_verb_in_accepts_refused(self):
        inst = self.make_instance("home")
        r = self.register("home", "--path", str(inst), "--accepts", "recap,handoff")
        self.assertEqual(r.returncode, E_USAGE)
        self.assertIn("handoff", r.stderr)

    def test_accepts_defaults_to_recap_ask(self):
        inst = self.make_instance("home")
        r = self.register("home", "--path", str(inst))
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("accepts: [recap, ask]", self.registry.read_text())

    def test_accepts_can_be_narrowed(self):
        inst = self.make_instance("home")
        r = self.register("home", "--path", str(inst), "--accepts", "recap")
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("accepts: [recap]", self.registry.read_text())

    def test_registered_instance_is_reachable_by_recap(self):
        inst = self.make_instance("home")
        recording_mem(inst)
        r = self.register("home", "--path", str(inst))
        self.assertEqual(r.returncode, OK, r.stderr)
        r2 = run("--registry", str(self.registry), "recap", "home", "ciao", "--dry-run")
        self.assertEqual(r2.returncode, OK, r2.stderr)

    def test_missing_path_flag_exits_2(self):
        r = self.register("home")
        self.assertEqual(r.returncode, E_USAGE)

    def test_appends_after_trailing_comments_of_the_last_entry(self):
        home = self.make_instance("home")
        work = self.make_instance("work")
        self.registry.write_text(
            "version: 1\ninstances:\n"
            f"  home:\n    path: {home}\n"
            "  # fine istanze, non aggiungere a mano qui sotto\n"
        )
        r = self.register("work", "--path", str(work))
        self.assertEqual(r.returncode, OK, r.stderr)
        text = self.registry.read_text()
        self.assertIn("# fine istanze, non aggiungere a mano qui sotto", text)
        self.assertLess(
            text.index("# fine istanze"), text.index("  work:"),
            "il commento di coda deve restare prima della nuova istanza appesa",
        )


class TestUnregister(RegistryFixture):
    def test_removes_existing_instance(self):
        r = self.run_net("unregister", "work")
        self.assertEqual(r.returncode, OK, r.stderr)
        text = self.registry.read_text()
        self.assertNotIn("work:", text)
        self.assertIn("home:", text)

    def test_confirmation_names_instance_and_path(self):
        r = self.run_net("unregister", "work")
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertIn("work", r.stdout)
        self.assertIn(str(self.work), r.stdout)

    def test_keeps_other_entries_intact(self):
        r = self.run_net("unregister", "work")
        self.assertEqual(r.returncode, OK, r.stderr)
        text = self.registry.read_text()
        self.assertIn("domain: vita personale", text)
        self.assertIn("accepts: [recap, ask]", text)

    def test_unregistered_instance_disappears_from_list(self):
        r = self.run_net("unregister", "work")
        self.assertEqual(r.returncode, OK, r.stderr)
        lr = self.run_net("list", "--json")
        data = json.loads(lr.stdout)
        self.assertNotIn("work", data["instances"])
        self.assertIn("home", data["instances"])

    def test_unknown_name_exits_5(self):
        r = self.run_net("unregister", "zorro")
        self.assertEqual(r.returncode, E_UNKNOWN_INSTANCE)
        self.assertIn("zorro", r.stderr)
        self.assertIn("home", r.stderr)

    def test_case_insensitive_match(self):
        r = self.run_net("unregister", "Work")
        self.assertEqual(r.returncode, OK, r.stderr)
        self.assertNotIn("work:", self.registry.read_text())

    def test_missing_registry_exits_3(self):
        r = run("--registry", str(self.root / "nope.yaml"), "unregister", "home")
        self.assertEqual(r.returncode, E_NO_REGISTRY)

    def test_comment_between_two_instances_survives_unregister_of_the_first(self):
        self.registry.write_text(
            "version: 1\ninstances:\n"
            f"  home:\n    path: {self.home}\n"
            "  # a note describing work below\n"
            f"  work:\n    path: {self.work}\n"
        )
        r = self.run_net("unregister", "home")
        self.assertEqual(r.returncode, OK, r.stderr)
        text = self.registry.read_text()
        self.assertIn("# a note describing work below", text)
        self.assertNotIn("home:", text)
        self.assertIn("work:", text)

    def test_comment_inside_the_removed_block_goes_with_it(self):
        self.registry.write_text(
            "version: 1\ninstances:\n"
            f"  home:\n    path: {self.home}\n"
            "    # nota interna su home\n"
            "    accepts: [recap]\n"
            f"  work:\n    path: {self.work}\n"
        )
        r = self.run_net("unregister", "home")
        self.assertEqual(r.returncode, OK, r.stderr)
        text = self.registry.read_text()
        self.assertNotIn("nota interna su home", text)
        self.assertIn("work:", text)


class TestCli(unittest.TestCase):
    def test_no_verb_exits_2(self):
        r = run()
        self.assertEqual(r.returncode, E_USAGE)

    def test_unknown_verb_exits_2(self):
        r = run("teleport", "home")
        self.assertEqual(r.returncode, E_USAGE)

    def test_help_exits_0(self):
        r = run("--help")
        self.assertEqual(r.returncode, OK)
        self.assertIn("recap", r.stdout)
        self.assertIn("ask", r.stdout)
        self.assertIn("scan", r.stdout)
        self.assertIn("register", r.stdout)
        self.assertIn("unregister", r.stdout)


if __name__ == "__main__":
    unittest.main()
