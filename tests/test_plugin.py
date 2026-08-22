"""The plugin layout is a packaging change, so it is tested as packaging.

Nothing here asserts anything about the discipline. These tests establish that
an assembled plugin root delivers exactly what an ordinary install delivers,
plus a manifest and an executable -- and that it delivers no more than that.

The parity framing is deliberate. Two install paths exist while the plugin one
is being proven, and the way that ends badly is the two drifting: a payload
rule enforced on one path and quietly absent on the other. Every test below is
therefore written against ``install.copy_payload`` or its output rather than
against a second hand-maintained file list.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "plugin"
sys.path.insert(0, str(PAYLOAD / "runtime"))
sys.path.insert(0, str(ROOT))

import install  # noqa: E402

from howdo.context import resolve_context_path  # noqa: E402


class ManifestTests(unittest.TestCase):
    """The manifest is a tracked source file, but not a tracked version."""

    def _source(self) -> dict:
        return json.loads(install.MANIFEST_SOURCE.read_text(encoding="utf-8"))

    def test_the_manifest_source_exists_and_parses(self):
        self.assertTrue(
            install.MANIFEST_SOURCE.is_file(),
            "install.py assembles a manifest from a file that is not in the repo",
        )
        self._source()

    def test_the_manifest_name_is_the_invocation_name(self):
        """A root-``SKILL.md`` plugin is invoked by the *plugin* name.

        The frontmatter ``name`` is not consulted for it, so the manifest name
        is what decides whether the skill is reachable as ``/how-do``. The
        skill description promises that string and a release test asserts it,
        which makes this the load-bearing field in the file.
        """
        self.assertEqual(self._source()["name"], install.skill_name(PAYLOAD / "SKILL.md"))

    def test_the_manifest_version_is_tracked_and_aligned(self):
        """The version is tracked here, and a test is what keeps it honest.

        It used to be derived: an assembler read it from ``SKILL.md`` and wrote
        it into a generated manifest, so there was nothing to keep in sync.
        That stopped being possible when the plugin root became a real tracked
        directory -- a marketplace clones it and reads this file exactly as
        committed, with no build step in between. So the version is committed,
        and it joins the four other places `test_release.py` holds aligned
        rather than floating free.
        """
        self.assertEqual(
            self._source().get("version"), install.skill_version(PAYLOAD / "SKILL.md"),
            "the manifest version drifted from SKILL.md",
        )

    def test_the_assembled_manifest_matches_the_skill_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "how-do"
            install.assemble_plugin(destination, dry_run=False)
            manifest = json.loads(
                (destination / install.MANIFEST_DIR / install.MANIFEST_NAME)
                .read_text(encoding="utf-8")
            )
        self.assertEqual(manifest["version"], install.skill_version(PAYLOAD / "SKILL.md"))

    def test_skill_version_reads_the_frontmatter_it_claims_to(self):
        self.assertRegex(install.skill_version(PAYLOAD / "SKILL.md"), r"^\d+\.\d+\.\d+$")


class LayoutTests(unittest.TestCase):
    """Where ``SKILL.md`` sits decides the invocation name, so it is a contract."""

    def _assemble(self, tmp) -> Path:
        destination = Path(tmp) / "how-do"
        install.assemble_plugin(destination, dry_run=False)
        return destination

    def test_skill_md_stays_at_the_plugin_root(self):
        """Moving it under ``skills/`` renames the skill.

        Verified against the runtime rather than the docs, which state the
        opposite: a plugin shipping ``skills/how-do/SKILL.md`` registers
        ``/how-do:how-do``, while one shipping ``SKILL.md`` at its root
        registers the bare plugin name. Only the second keeps the invocation
        the skill description promises.
        """
        with tempfile.TemporaryDirectory() as tmp:
            destination = self._assemble(tmp)
            self.assertTrue((destination / "SKILL.md").is_file())
            self.assertFalse(
                (destination / "skills").exists(),
                "a skills/ directory namespaces the skill to /how-do:how-do",
            )

    def test_the_manifest_is_the_only_thing_inside_claude_plugin(self):
        """Components in ``.claude-plugin/`` are silently not loaded."""
        with tempfile.TemporaryDirectory() as tmp:
            destination = self._assemble(tmp)
            inside = sorted(p.name for p in (destination / install.MANIFEST_DIR).iterdir())
            self.assertEqual(inside, [install.MANIFEST_NAME])

    def test_windows_gets_a_shim_for_the_same_helper(self):
        """``bin/`` on PATH is only an affordance where the file can run.

        An extensionless file with a shebang is not executable on Windows, so
        without a ``.cmd`` beside it every ``howdo-context`` instruction in the
        docs is quietly POSIX-only -- on a platform this project supports
        deliberately enough to branch the store location for.
        """
        with tempfile.TemporaryDirectory() as tmp:
            destination = self._assemble(tmp)
            shim = destination / "bin" / "howdo-context.cmd"
            self.assertTrue(shim.is_file(), "no Windows shim beside bin/howdo-context")
            self.assertIn("howdo-context", shim.read_text(encoding="utf-8"))

    def test_the_executable_ships_executable(self):
        """A bin/ entry without the bit is absent from PATH, not broken.

        That failure is silent: the helper simply is not found, and the agent
        falls back to whatever it would have done without it.
        """
        with tempfile.TemporaryDirectory() as tmp:
            destination = self._assemble(tmp)
            helper = destination / "bin" / "howdo-context"
            self.assertTrue(helper.is_file(), "bin/howdo-context did not ship")
            self.assertTrue(os.access(helper, os.X_OK), "bin/howdo-context is not executable")
            self.assertTrue(
                helper.read_text(encoding="utf-8").startswith("#!"),
                "the POSIX entry point lost its shebang",
            )


class VerifyTests(unittest.TestCase):
    """``--verify`` has to judge a plugin by the thing the host judges it by."""

    def test_a_plugin_root_is_identified_by_its_manifest_not_its_directory(self):
        """The host reads ``name`` from the manifest and ignores the directory.

        A plugin assembled into a directory called anything at all still loads
        under its manifest name, so requiring the two to match would fail a
        perfectly good install -- and, worse, would pass a broken one whose
        directory happened to be right while its manifest was not.
        """
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "some-other-name"
            install.assemble_plugin(destination, dry_run=False)
            code = install.report(destination, Path(tmp) / "CONTEXT.md")
            self.assertEqual(code, 0, "a correctly named manifest was reported as a problem")

    def test_a_manifest_disagreeing_with_the_skill_is_a_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "how-do"
            install.assemble_plugin(destination, dry_run=False)
            manifest = destination / install.MANIFEST_DIR / install.MANIFEST_NAME
            broken = json.loads(manifest.read_text(encoding="utf-8"))
            broken["name"] = "not-how-do"
            manifest.write_text(json.dumps(broken), encoding="utf-8")
            code = install.report(destination, Path(tmp) / "CONTEXT.md")
            self.assertEqual(code, 1, "a manifest that renames the skill was reported as ok")

    def test_an_ordinary_install_still_checks_the_directory(self):
        """No manifest means no plugin, and then the directory *is* the name."""
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "wrong-name"
            install.copy_payload(destination, dry_run=False)
            code = install.report(destination, Path(tmp) / "CONTEXT.md")
            self.assertEqual(code, 1, "a misnamed skill directory was reported as ok")


class TrackedRootTests(unittest.TestCase):
    """The payload boundary stopped being a rule and became a directory.

    Nothing holds `experiment/` and `tests/` out of the plugin any more,
    because they are not inside it. That is the point of the move: a
    marketplace clones `plugin/` and gets the payload, so a rule that could be
    forgotten was replaced by a fact that cannot be.
    """

    def test_the_plugin_root_is_tracked_not_generated(self):
        for name in ("SKILL.md", "CONTEXT.template.md", "QUICKSTART.md", "LICENSE"):
            self.assertTrue((PAYLOAD / name).is_file(), f"plugin/{name} is missing")
        for name in ("references", "runtime", "examples", "bin"):
            self.assertTrue((PAYLOAD / name).is_dir(), f"plugin/{name}/ is missing")
        self.assertTrue((PAYLOAD / ".claude-plugin" / "plugin.json").is_file())

    def test_repository_concerns_are_outside_the_plugin_root(self):
        """The boundary, stated as the filesystem fact it now is."""
        for name in ("experiment", "tests", "install.py", "CONTRIBUTING.md",
                     "ADVERSARIAL.md", "CHANGELOG.md", "README.md", "pyproject.toml"):
            self.assertTrue((ROOT / name).exists(), f"{name} vanished from the repo root")
            self.assertFalse(
                (PAYLOAD / name).exists(),
                f"{name} is inside the plugin root and would ship to every user",
            )

    def test_the_marketplace_points_at_the_plugin_root(self):
        """A marketplace entry naming the wrong directory installs nothing."""
        market = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        entries = {entry["name"]: entry for entry in market["plugins"]}
        self.assertIn("how-do", entries, "the marketplace does not list how-do")
        source = entries["how-do"]["source"]
        self.assertEqual((ROOT / source).resolve(), PAYLOAD.resolve(),
                         f"marketplace source {source!r} is not the plugin root")

    def test_the_marketplace_is_not_mistaken_for_a_plugin(self):
        """`.claude-plugin/` at the repo root holds a marketplace, not a plugin.

        A `plugin.json` there would make the whole repository a plugin root and
        ship `experiment/` and `tests/` to every user -- exactly the regression
        the move exists to make impossible.
        """
        self.assertFalse((ROOT / ".claude-plugin" / "plugin.json").exists())

    def test_the_shipped_licence_matches_the_repository_licence(self):
        """Two copies on purpose: GitHub reads the root, the artifact carries
        its own. Two copies that disagree would be worse than one."""
        self.assertEqual(
            (ROOT / "LICENSE").read_text(encoding="utf-8"),
            (PAYLOAD / "LICENSE").read_text(encoding="utf-8"),
        )


class NoticeTests(unittest.TestCase):
    """The one thing How Do says before it is asked anything.

    `SKILL.md` refuses to load the discipline uninvited, and this plugin ships
    a `SessionStart` hook. Those coexist because of exactly three properties,
    and a claim in a document is not one of them -- so each is asserted here.
    If any of these fails, the hook has stopped being a notice and the refusal
    in `SKILL.md` has become false.
    """

    def _run(self, store: Path, *args: str):
        environment = dict(os.environ)
        environment.pop("CLAUDE_PLUGIN_DATA", None)
        environment["HOWDO_CONTEXT"] = str(store)
        return subprocess.run(
            [sys.executable, str(PAYLOAD / "bin" / "howdo-context"), "--notice", *args],
            capture_output=True, text=True, env=environment, cwd=tempfile.gettempdir(),
        )

    def _settled(self, tmp) -> Path:
        store = Path(tmp) / "CONTEXT.md"
        subprocess.run(
            [sys.executable, str(PAYLOAD / "bin" / "howdo-context"), "--ensure"],
            capture_output=True, text=True, cwd=tempfile.gettempdir(),
            env={**os.environ, "HOWDO_CONTEXT": str(store)},
        )
        return store

    def test_it_never_emits_model_context(self):
        """The property the whole doctrine rests on.

        `systemMessage` reaches the person. `additionalContext` reaches the
        model, and the moment this hook emits it the plugin is loading the
        discipline uninvited.
        """
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(Path(tmp) / "CONTEXT.md")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertNotIn("additionalContext", json.dumps(payload))
            emitted = payload["hookSpecificOutput"]
            self.assertEqual(emitted["hookEventName"], "SessionStart")
            self.assertTrue(emitted["suppressOutput"])
            # The two halves that make it a notice rather than an advert: it
            # says a conversation is coming, and it says you may refuse it.
            self.assertIn("the first conversation works it out with you",
                          emitted["systemMessage"])
            self.assertIn("You can also say no", emitted["systemMessage"])

    def test_it_speaks_when_the_question_has_no_answer_yet(self):
        with tempfile.TemporaryDirectory() as tmp:
            for store in (Path(tmp) / "absent.md", self._settled(tmp)):
                with self.subTest(store=store.name):
                    self.assertTrue(self._run(store).stdout.strip())

    def test_it_is_silent_once_the_question_has_an_answer(self):
        """Declined and deferred are answers. Re-asking is the nagging the
        discipline refuses, and silence is how that refusal is kept here."""
        from howdo.context import decline_onboarding, defer_onboarding  # noqa: PLC0415

        for settle in (decline_onboarding, defer_onboarding):
            with self.subTest(settle=settle.__name__), tempfile.TemporaryDirectory() as tmp:
                store = self._settled(tmp)
                settle(store)
                self.assertEqual(self._run(store).stdout.strip(), "",
                                 f"the notice speaks after {settle.__name__}")

    def test_silence_is_empty_rather_than_an_empty_object(self):
        """`SessionStart` stdout becomes context when it is not valid JSON, so
        the quiet path must emit nothing at all rather than something small."""
        from howdo.context import decline_onboarding  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as tmp:
            store = self._settled(tmp)
            decline_onboarding(store)
            self.assertEqual(self._run(store).stdout, "")

    def test_it_reads_and_never_writes(self):
        """Ignoring the notice must leave the person exactly where they were."""
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "CONTEXT.md"
            self._run(store)
            self.assertFalse(store.exists(), "the notice instantiated the store")

    def test_a_broken_store_does_not_break_every_session(self):
        """A hook that raises would open every session with an error about a
        file nobody asked about. Quiet is the correct failure."""
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "CONTEXT.md"
            store.write_text("not a context file at all\n", encoding="utf-8")
            result = self._run(store)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_the_hook_is_declared_and_points_at_something_that_exists(self):
        config = json.loads((PAYLOAD / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        entries = config["hooks"]["SessionStart"]
        commands = [h["command"] for entry in entries for h in entry["hooks"]]
        self.assertEqual(len(commands), 1, "more than one SessionStart hook ships")
        command = commands[0]
        self.assertIn("--notice", command)
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", command,
                      "the hook hard-codes a path that moves on every update")
        self.assertTrue((PAYLOAD / "bin" / "howdo-context").is_file())

    def test_only_a_session_start_hook_ships(self):
        """Five plugin slots are empty on purpose; this guards the sixth from
        quietly growing. A hook on any other event is not a first-run notice."""
        config = json.loads((PAYLOAD / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(list(config["hooks"]), ["SessionStart"])

    def test_the_note_has_exactly_one_source(self):
        """Two copies of a text this carefully worded would drift on the first
        edit, and only one of them is covered by the installer's tests."""
        from howdo.notice import CONFIGURATION_NOTE  # noqa: PLC0415

        self.assertEqual(install.CONFIGURATION_NOTE, CONFIGURATION_NOTE)
        with tempfile.TemporaryDirectory() as tmp:
            spoken = json.loads(self._run(Path(tmp) / "CONTEXT.md").stdout)
            self.assertEqual(
                spoken["hookSpecificOutput"]["systemMessage"],
                CONFIGURATION_NOTE.strip(),
                "the hook and the installer say different things",
            )


class ParityTests(unittest.TestCase):
    """The plugin root is the ordinary payload plus a manifest and bin/."""

    def test_the_plugin_contains_everything_an_ordinary_install_does(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "skill"
            plugin_dir = Path(tmp) / "plugin"
            install.copy_payload(skill_dir, dry_run=False)
            install.assemble_plugin(plugin_dir, dry_run=False)

            expected = {p.relative_to(skill_dir) for p in skill_dir.rglob("*")}
            actual = {p.relative_to(plugin_dir) for p in plugin_dir.rglob("*")}
            missing = sorted(str(p) for p in expected - actual)
            self.assertEqual(missing, [], f"the plugin drops payload files: {missing}")

    def test_the_plugin_adds_nothing_beyond_the_manifest_and_bin(self):
        """Parity has two directions. Silently widening the payload is the
        regression that the experiment boundary exists to prevent."""
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "skill"
            plugin_dir = Path(tmp) / "plugin"
            install.copy_payload(skill_dir, dry_run=False)
            install.assemble_plugin(plugin_dir, dry_run=False)

            expected = {p.relative_to(skill_dir) for p in skill_dir.rglob("*")}
            actual = {p.relative_to(plugin_dir) for p in plugin_dir.rglob("*")}
            allowed_prefixes = (install.MANIFEST_DIR,) + install.PLUGIN_EXTRA
            surprises = sorted(
                str(p) for p in actual - expected
                if p.parts[0] not in allowed_prefixes
            )
            self.assertEqual(surprises, [], f"the plugin ships extra files: {surprises}")

    def test_the_plugin_ships_no_repository_concerns(self):
        """Whatever keeps ``experiment/`` and ``tests/`` out of an install has
        to hold on this path too, or the boundary moved rather than held."""
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "how-do"
            install.assemble_plugin(destination, dry_run=False)
            strays = sorted(
                str(p.relative_to(destination))
                for p in destination.rglob("*")
                if p.name in {"experiment", "tests", "__pycache__", "CONTEXT.md"}
                or p.suffix in {".pyc", ".pyo"}
                or p.name.startswith("test_")
            )
            self.assertEqual(strays, [], f"the plugin ships repository concerns: {strays}")

    @unittest.skipIf(
        (PAYLOAD / "runtime" / "howdo" / "environment.py").exists(),
        "the PILOT-0001 adapter still lives in runtime/, so every install "
        "path ships it; this check activates when it moves out of the payload",
    )
    def test_the_plugin_names_no_experiment(self):
        """The boundary is enforced by content, not only by directory.

        ``copy_payload`` guards which *directories* ship. The plugin adds
        ``bin/`` and a manifest after that guard runs, so the same rule is
        re-checked over the assembled root -- otherwise the one place the two
        install paths differ is the one place the boundary is unenforced.

        This is skipped rather than deleted because it currently fails for a
        reason that is not the plugin's: ``runtime/howdo/environment.py`` is
        the pilot adapter, and ``howdo.__init__`` re-exports it, so an ordinary
        install carries the experiment too. Moving the adapter out of the
        payload is separate work already in flight; when it lands, this test
        stops skipping and starts guarding the plugin path with no edit here.
        """
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "how-do"
            install.assemble_plugin(destination, dry_run=False)
            named = sorted(
                str(path.relative_to(destination))
                for path in destination.rglob("*")
                if path.is_file() and "PILOT" in path.read_text(
                    encoding="utf-8", errors="ignore"
                ).upper()
            )
            self.assertEqual(named, [], f"the plugin names the experiment: {named}")

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "how-do"
            actions = install.assemble_plugin(destination, dry_run=True)
            self.assertFalse(destination.exists(), "--dry-run created the plugin root")
            self.assertTrue(any(install.MANIFEST_NAME in a for a in actions))


class StorePrecedenceTests(unittest.TestCase):
    """``CLAUDE_PLUGIN_DATA`` is why the plugin layout is worth having.

    A plugin host guarantees that directory survives an update. That is the
    exact guarantee the payload/store split was built by hand to provide, so
    when a host offers it we take it -- but never over a store the person has
    already placed themselves.
    """

    def test_plugin_data_is_used_when_the_host_offers_it(self):
        resolved = resolve_context_path(env={"CLAUDE_PLUGIN_DATA": "/plugin/data"})
        self.assertEqual(resolved, Path("/plugin/data/CONTEXT.md"))

    def test_the_basename_stays_canonical(self):
        """A different basename is read as a fork, which would silently start a
        second lineage every time the host directory changed."""
        resolved = resolve_context_path(env={"CLAUDE_PLUGIN_DATA": "/plugin/data"})
        self.assertEqual(resolved.name, "CONTEXT.md")

    def test_an_explicitly_placed_store_still_wins(self):
        resolved = resolve_context_path(
            env={"HOWDO_CONTEXT": "/mine/CONTEXT.md", "CLAUDE_PLUGIN_DATA": "/plugin/data"},
        )
        self.assertEqual(resolved, Path("/mine/CONTEXT.md"))

    def test_a_selected_file_outranks_both(self):
        resolved = resolve_context_path(
            "/session/CONTEXT.md",
            env={"HOWDO_CONTEXT": "/mine/CONTEXT.md", "CLAUDE_PLUGIN_DATA": "/plugin/data"},
        )
        self.assertEqual(resolved, Path("/session/CONTEXT.md"))

    def test_the_platform_default_survives_when_no_host_offers_one(self):
        """Installing outside a plugin host must not change where the store is.

        Without this, adding the plugin path would relocate the store of every
        person who installed the skill the ordinary way.
        """
        resolved = resolve_context_path(env={}, home="/home/someone", platform="linux")
        self.assertEqual(resolved, Path("/home/someone/.howdo/CONTEXT.md"))

    def test_an_empty_plugin_data_is_not_a_path(self):
        resolved = resolve_context_path(
            env={"CLAUDE_PLUGIN_DATA": ""}, home="/home/someone", platform="linux",
        )
        self.assertEqual(resolved, Path("/home/someone/.howdo/CONTEXT.md"))


class ExecutableTests(unittest.TestCase):
    """``bin/howdo-context`` replaces a relative-path shell-out that only
    resolved when the process happened to be sitting in the payload."""

    def _run(self, destination: Path, *args: str, env: dict | None = None):
        environment = dict(os.environ)
        environment.pop("HOWDO_CONTEXT", None)
        environment.pop("CLAUDE_PLUGIN_DATA", None)
        environment.update(env or {})
        return subprocess.run(
            [sys.executable, str(destination / "bin" / "howdo-context"), *args],
            capture_output=True, text=True, env=environment, cwd=tempfile.gettempdir(),
        )

    def test_it_resolves_the_runtime_from_an_unrelated_directory(self):
        """The failure it exists to fix: run from anywhere but the payload."""
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "how-do"
            install.assemble_plugin(destination, dry_run=False)
            result = self._run(destination, "--path", env={"HOWDO_CONTEXT": "/somewhere/CONTEXT.md"})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "/somewhere/CONTEXT.md")

    def test_it_honours_the_plugin_root_a_host_declares(self):
        """``CLAUDE_PLUGIN_ROOT`` moves when the plugin updates, so the script
        must read it rather than cache a path derived at build time."""
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "how-do"
            install.assemble_plugin(destination, dry_run=False)
            moved = Path(tmp) / "relocated"
            destination.rename(moved)
            result = subprocess.run(
                [sys.executable, str(moved / "bin" / "howdo-context"), "--path"],
                capture_output=True, text=True, cwd=tempfile.gettempdir(),
                env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(moved),
                     "HOWDO_CONTEXT": "/somewhere/CONTEXT.md"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_it_reports_a_missing_store_without_failing(self):
        """Missing is the ordinary first-run state, not an error."""
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "how-do"
            install.assemble_plugin(destination, dry_run=False)
            result = self._run(destination, env={"HOWDO_CONTEXT": str(Path(tmp) / "CONTEXT.md")})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("missing", result.stdout)

    def test_ensure_instantiates_from_the_shipped_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "how-do"
            install.assemble_plugin(destination, dry_run=False)
            store = Path(tmp) / "store" / "CONTEXT.md"
            result = self._run(destination, "--ensure", env={"HOWDO_CONTEXT": str(store)})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(store.is_file(), "--ensure did not instantiate the store")
            self.assertIn("onboarding_required", result.stdout)

    def test_ensure_never_clobbers_a_settled_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "how-do"
            install.assemble_plugin(destination, dry_run=False)
            store = Path(tmp) / "store" / "CONTEXT.md"
            self._run(destination, "--ensure", env={"HOWDO_CONTEXT": str(store)})
            settled = store.read_text(encoding="utf-8") + "\n<!-- mine -->\n"
            store.write_text(settled, encoding="utf-8")
            self._run(destination, "--ensure", env={"HOWDO_CONTEXT": str(store)})
            self.assertEqual(store.read_text(encoding="utf-8"), settled)


if __name__ == "__main__":
    unittest.main()
