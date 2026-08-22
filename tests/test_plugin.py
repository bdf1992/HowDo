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

    def test_the_manifest_source_pins_no_version(self):
        """Six places to edit on release is five too many.

        The assembled manifest derives its version from the skill. If a version
        is ever written into the source file it becomes authoritative, drifts
        on the first release nobody thinks about, and pins the plugin to a
        stale version for every user.
        """
        self.assertNotIn(
            "version", self._source(),
            "packaging/plugin.json pins a version; it is derived from SKILL.md",
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


class DistributionTests(unittest.TestCase):
    """A marketplace clones a repository; it cannot run the assembler first.

    ``plugin/`` is therefore a real plugin root in the tree, manifest and all,
    and the repository root carries a marketplace entry pointing at it. That
    makes the payload boundary a filesystem fact: what ships is what is in one
    directory, rather than what a function remembered to copy.

    A committed derived file is the risk this trades for, so the derivation is
    still the authority and these tests are what stop the copy going stale.
    """

    def _committed(self) -> Path:
        return install.PAYLOAD_ROOT / install.MANIFEST_DIR / install.MANIFEST_NAME

    def _marketplace(self) -> dict:
        return json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )

    def test_the_committed_manifest_is_byte_identical_to_the_derived_one(self):
        """Not merely equivalent. Byte-identical, so refreshing it is mechanical.

        ``install.manifest_bytes()`` is the single authority. Comparing parsed
        dictionaries would pass while the file drifted in key order or
        indentation, and then the fix for a failure here would be a judgement
        call instead of overwriting the file with what this function returns.
        """
        self.assertEqual(
            self._committed().read_text(encoding="utf-8"),
            install.manifest_bytes(),
            "plugin/.claude-plugin/plugin.json is stale; rewrite it from "
            "install.manifest_bytes()",
        )

    def test_the_committed_manifest_carries_the_skill_version(self):
        """The version is still derived; committing the result does not pin it."""
        manifest = json.loads(self._committed().read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], install.skill_version(PAYLOAD / "SKILL.md"))

    def test_the_payload_root_holds_nothing_an_install_would_leave_behind(self):
        """The directory is the boundary now, so the directory is what is checked.

        Anything added to ``plugin/`` that is not in ``PAYLOAD`` ships to a
        marketplace user and is silently missing from an ordinary install --
        exactly the two-paths drift the parity tests exist to catch, arriving
        by a new route.
        """
        allowed = set(install.PAYLOAD) | set(install.PLUGIN_EXTRA) | {install.MANIFEST_DIR}
        present = {
            entry.name for entry in install.PAYLOAD_ROOT.iterdir()
            if entry.name != "__pycache__"
        }
        self.assertEqual(
            present - allowed, set(),
            "plugin/ holds files no install path ships; add them to PAYLOAD or move them out",
        )

    def test_the_shipped_license_is_the_repository_license(self):
        """The payload ships a licence, and a repository root needs one too.

        Two copies is the cost of the payload being a subdirectory: a licence
        outside ``plugin/`` never reaches an installed skill, and one only
        inside it is invisible to anything reading the repository. They are
        checked equal rather than trusted equal, and a symlink is not an option
        because a Windows checkout would ship the link text as the licence.
        """
        self.assertEqual(
            (PAYLOAD / "LICENSE").read_text(encoding="utf-8"),
            (ROOT / "LICENSE").read_text(encoding="utf-8"),
            "plugin/LICENSE has drifted from the repository LICENSE",
        )

    def test_no_shipped_document_tells_the_reader_to_run_the_installer(self):
        """The payload cannot instruct someone to run a file it does not ship.

        `QUICKSTART.md` and `references/onboarding.md` both told the reader to
        run `python install.py --shared` to opt into a generic store. A
        marketplace user has no `install.py`, and the advice was worse than
        unreachable: a plugin payload is version-scoped, so a shared store
        settled inside it is discarded by the next release rather than merely
        replaced -- the exact loss the store design exists to prevent.

        Naming the other install route in prose is fine and sometimes
        necessary. A runnable command is not, because that is the form a reader
        copies.
        """
        offenders = []
        for path in sorted(install.PAYLOAD_ROOT.rglob("*.md")):
            if "python install.py" in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(install.PAYLOAD_ROOT)))
        self.assertEqual(
            offenders, [],
            "shipped documents tell the reader to run install.py, which the payload does not ship",
        )

    def test_the_marketplace_points_at_the_committed_plugin_root(self):
        entries = self._marketplace()["plugins"]
        sources = {entry["name"]: entry["source"] for entry in entries}
        manifest = json.loads(self._committed().read_text(encoding="utf-8"))
        self.assertIn(
            manifest["name"], sources,
            "the marketplace lists no plugin under the manifest's own name",
        )
        target = (ROOT / sources[manifest["name"]]).resolve()
        self.assertEqual(target, install.PAYLOAD_ROOT.resolve())

    def test_the_marketplace_source_is_a_plugin_root(self):
        """A source that does not resolve to a manifest installs nothing."""
        for entry in self._marketplace()["plugins"]:
            with self.subTest(plugin=entry["name"]):
                root = (ROOT / entry["source"]).resolve()
                self.assertTrue(
                    (root / install.MANIFEST_DIR / install.MANIFEST_NAME).is_file(),
                    f"{entry['source']} has no {install.MANIFEST_DIR}/{install.MANIFEST_NAME}",
                )


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
