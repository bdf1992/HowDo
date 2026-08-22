import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from howdo.context import inspect_context  # noqa: E402


def _flatten(text: str) -> str:
    """Lowercase and collapse whitespace.

    These are contracts about meaning, not layout. Asserting against raw text
    makes a paragraph rewrap look like a broken promise.
    """
    return re.sub(r"\s+", " ", text).lower()



class ReleaseContractTests(unittest.TestCase):
    def test_release_versions_are_aligned(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        context = (ROOT / "CONTEXT.template.md").read_text(encoding="utf-8")
        self.assertIn('version: "0.9.0"', skill)
        self.assertIn("How Do v0.9.0", readme)
        self.assertIn('version = "0.9.0"', pyproject)
        self.assertIn('skill_version: "0.9.0"', context)
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## 0.9.0", changelog)

    def test_tracked_context_is_the_template_not_a_settled_context(self):
        # Personal contexts are never committed; only the template is tracked.
        status = inspect_context(ROOT / "CONTEXT.template.md")
        self.assertEqual(status.state, "template", status.reason)
        self.assertFalse((ROOT / "CONTEXT.md").exists(), "a personal store is tracked")

    def test_first_run_contract_is_not_lazy(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        # The gate is a guarantee, so it stays in SKILL.md even though the
        # interview it triggers moved to a reference.
        self.assertIn("before the first substantive howdo", skill.lower())
        self.assertIn("never bypassed silently", skill.lower())
        self.assertNotIn("onboarding is not a gate on work", skill.lower())
        self.assertNotIn("onboard it lazily", skill.lower())

    def test_look_is_defined_as_running_the_test_check_wrote(self):
        """The word stays; the definition has to carry the testing weight."""
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Check writes the test", skill)
        self.assertIn("Check wrote the test; Look runs it", skill)
        self.assertIn("test it against what you predicted", skill)
        self.assertIn("cannot test a thing by asking it whether it worked", skill.lower())

    def test_onboarding_settings_are_tied_to_loop_stages(self):
        """The pedagogy is the loop; onboarding tunes it, so say which stage."""
        reference = (ROOT / "references" / "onboarding.md").read_text(encoding="utf-8")
        for stage in ("tunes `Map`", "tunes `Path`", "tunes `Check` and `Look`", "tunes `Update`"):
            self.assertIn(stage, reference)

    def test_agency_modifier_keeps_one_loop(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("How[actor] : Map → Path → Check → Do → Look → Update", skill)
        for form in ("How do I", "How do you", "How do we", "How do they"):
            self.assertIn(form, skill)

    def test_context_separates_rendering_from_actor_capability(self):
        context = (ROOT / "CONTEXT.template.md").read_text(encoding="utf-8")
        # The invariant is the separation, not the wording: durable context
        # shapes how you teach and present, never what the actor can do.
        self.assertIn("does not grant facts, capability, or authority", context)
        self.assertIn("primarily informs", context)

    def test_deferral_is_documented_as_distinct_from_decline(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        reference = (ROOT / "references" / "onboarding.md").read_text(encoding="utf-8")
        self.assertIn("onboarding: deferred", skill)
        self.assertIn("offer stays open", skill.lower())
        self.assertIn("deferral is not a decline", skill.lower())
        self.assertIn("never record", reference.lower())

    def test_decline_semantics_are_durable(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        reference = (ROOT / "references" / "onboarding.md").read_text(encoding="utf-8")
        self.assertIn("onboarding: declined", skill)
        self.assertIn("do not ask again", skill.lower())
        # The README names the persisted state a user can see; the runtime
        # helper that writes it is documented where the helpers live.
        self.assertIn("onboarding: declined", readme)
        self.assertIn("decline_onboarding", reference)

    def test_completion_claim_is_structural_not_truth_claim(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("structural completeness only", skill)
        self.assertIn("does not prove", skill)


class IssuerGuaranteeTests(unittest.TestCase):
    """0.9.0 was a deliberate goalpost move; CONTRIBUTING asks a release test to hold it.

    The runtime enforces these. What this checks is that the shipped documents
    still *say* so, because an issuer whose refusals are undocumented reads as a
    way to manufacture ground.
    """

    def test_the_skill_says_an_artifact_is_issued_from_a_run(self):
        skill = _flatten((ROOT / "SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("issued rather than described", skill)
        self.assertIn("from a completed howdo rather than from a plan", skill)

    def test_the_skill_keeps_untested_separate_from_grounded(self):
        skill = _flatten((ROOT / "SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("untested", skill)
        self.assertIn("residual that *matched* grounds it".replace("*", ""), skill.replace("*", ""))
        self.assertIn("drops the grounding its predecessor earned", skill)

    def test_the_skill_states_where_the_kernels_staleness_check_stops(self):
        """The one guarantee a persisted artifact cannot inherit from admit()."""
        skill = _flatten((ROOT / "SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("ends at the process boundary", skill)
        self.assertIn("revision it was observed against", skill)

    def test_the_boundaries_of_grounding_are_declared_not_implied(self):
        adversarial = _flatten((ROOT / "ADVERSARIAL.md").read_text(encoding="utf-8"))
        self.assertIn("structurally grounded, not correct", adversarial)
        self.assertIn("staleness is reported, not enforced", adversarial)

    def test_the_goalpost_move_is_recorded(self):
        changelog = _flatten((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))
        self.assertIn("deliberate goalpost move", changelog)


class PedagogyIntentTests(unittest.TestCase):
    """Onboarding establishes a pedagogy. Preference language invites a narrower read."""

    def _reference(self) -> str:
        return (ROOT / "references" / "onboarding.md").read_text(encoding="utf-8")

    def test_the_target_is_pedagogy_not_presentation(self):
        for text in (self._reference(), (ROOT / "CONTEXT.template.md").read_text(encoding="utf-8")):
            self.assertIn("pedagogy", text.lower())
        reference = self._reference().lower()
        for dimension in ("anchor", "build direction", "counts as understood", "correction"):
            self.assertIn(dimension, reference, f"pedagogy dimension missing: {dimension}")

    def test_the_agent_is_given_latitude_over_route(self):
        """Objectives with latitude, not a script. A numbered procedure is the old shape."""
        reference = self._reference()
        self.assertIn("How you get there is yours", reference)
        self.assertIn("The route is free", reference)
        section = reference[reference.index("## Establishing the pedagogy"):reference.index("## Decline versus deferral")]
        self.assertNotIn("\n1. ", section, "the pedagogy section is a numbered script again")

    def test_a_reading_must_be_tested_before_it_settles(self):
        """A preference stated is a hypothesis. The test is what makes it evidence."""
        reference = self._reference()
        self.assertIn("Stop when you have **tested** a reading, not when you have formed one", reference)
        self.assertIn("makes it evident", reference)
        self.assertNotIn("Stop as soon as you can name", reference)

    def test_the_register_stays_conversational(self):
        reference = self._reference().lower()
        self.assertIn("not an intake form", reference)
        self.assertIn("one question at a time", reference)
        self.assertIn("i don't know", reference)

    def test_identity_labels_are_still_refused(self):
        """Pedagogy is about how understanding builds, never what type someone is."""
        for text in (self._reference(), (ROOT / "CONTEXT.template.md").read_text(encoding="utf-8")):
            self.assertIn("visual learner", text, "the anti-label guard went missing")
        self.assertIn("observations, not identities", self._reference())

    def test_skill_carries_the_latitude_so_a_reference_miss_does_not_lose_it(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("pedagogy", skill.lower())
        self.assertIn("yours to choose", skill.lower())
        self.assertIn("never an intake form", skill.lower())

    def test_the_shell_is_fixed_and_its_internals_are_personal(self):
        """Both halves, wherever the term is introduced.

        Drop the first and onboarding reads as an agent inventing a pedagogy
        per reader. Drop the second and it reads as an impersonal config step
        with nothing a person could supply. Stating the join in one file, on
        the line a reader reaches last, is what let both readings stand.
        """
        for name in ("SKILL.md", "CONTEXT.template.md", "references/onboarding.md"):
            flat = _flatten((ROOT / name).read_text(encoding="utf-8"))
            with self.subTest(document=name):
                self.assertIn("fixed shell", flat, "the shell half is missing")
                self.assertIn("internals are personal", flat, "the personal half is missing")
                self.assertIn(
                    "no source but the person", flat, "nothing says where the internals come from"
                )

    def test_onboarding_states_why_it_needs_a_person(self):
        """A reason, not an assertion: settings with no other source."""
        flat = _flatten(self._reference())
        self.assertIn("which is why onboarding needs one", flat)
        self.assertIn("cannot be inferred", flat)


class VocabularyTests(unittest.TestCase):
    """The glossary maps local terms to established practice. Gaps are where readers trip."""

    LOAD_BEARING = (
        "paradigm",
        "map",
        "path",
        "residual",
        "settlement",
        "trace",
        "handle",
        "pedagogy",
        "shell",
        "internals",
        "onboarding",
        "exemplar",
        "payload",
        "store",
    )

    def _defined_terms(self) -> set[str]:
        text = (ROOT / "references" / "vocabulary.md").read_text(encoding="utf-8")
        terms = set()
        for line in text.splitlines():
            if not line.startswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and cells[0] not in ("here", "---"):
                terms.add(cells[0].lower())
        return terms

    def test_load_bearing_terms_are_defined(self):
        defined = self._defined_terms()
        for term in self.LOAD_BEARING:
            with self.subTest(term=term):
                self.assertIn(
                    term, defined, f"the skill leans on '{term}' but the glossary omits it"
                )


class ReaderFacingOutputTests(unittest.TestCase):
    """The local terms are equipment. Nothing forbade emitting them at the person."""

    def _skill(self) -> str:
        return (ROOT / "SKILL.md").read_text(encoding="utf-8")

    def _rule(self) -> str:
        for line in self._skill().splitlines():
            if line.startswith("- **The vocabulary is working equipment"):
                return _flatten(line)
        self.fail("SKILL.md no longer states the reader-facing output rule")

    def test_the_rule_withholds_rather_than_permits_skipping(self):
        """'Does not need it' is permission to skip; this has to be an instruction."""
        rule = self._rule()
        self.assertIn("not what the person reads back", rule)
        self.assertIn("do not say", rule)
        vocabulary = _flatten((ROOT / "references" / "vocabulary.md").read_text(encoding="utf-8"))
        self.assertIn("withholds these words", vocabulary)
        self.assertNotIn("does not need it", vocabulary)

    def test_the_rule_names_the_machinery_that_leaks_most_readily(self):
        rule = self._rule()
        for term in ("pedagogy", "paradigm", "residual", "exemplar", "settlement", "payload", "store"):
            with self.subTest(term=term):
                self.assertIn(term, rule, f"the rule does not name '{term}'")
        self.assertIn("state names", rule)
        self.assertIn("frontmatter keys", rule)
        self.assertIn("store paths", rule)

    def test_the_rule_carries_its_two_exceptions_and_reaches_onboarding(self):
        """Structure may show through; wording may not. Two narrow exceptions."""
        rule = self._rule()
        self.assertIn("inspect mode", rule)
        self.assertIn("working on how do itself", rule)
        self.assertIn("never its wording", rule)
        onboarding = _flatten((ROOT / "references" / "onboarding.md").read_text(encoding="utf-8"))
        self.assertIn("never say the machinery at them", onboarding)


class InvocationIntentTests(unittest.TestCase):
    """How Do is requested. A broad description makes it ambient by accident."""

    def _description(self) -> str:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        front = text[3 : text.index("\n---", 3)]
        line = next(l for l in front.splitlines() if l.startswith("description:"))
        return line.split(":", 1)[1].strip()

    def test_description_asks_to_be_invoked(self):
        description = self._description().lower()
        self.assertIn("requested, not ambient", description)
        self.assertIn("/how-do", description)

    def test_description_does_not_advertise_bare_handles_as_triggers(self):
        """Handles are moves inside a HowDo; as triggers they fire on everything."""
        description = self._description().lower()
        for bait in ('"help me"', '"say more"', '"do work"', '"what now"', '"why that"'):
            self.assertNotIn(bait, description, f"{bait} makes the skill ambient")

    def test_description_states_what_is_not_a_trigger(self):
        description = self._description().lower()
        self.assertIn("not by itself a request", description)

    def test_description_stays_within_the_frontmatter_budget(self):
        self.assertLessEqual(len(self._description()), 700)

    def test_body_keeps_handles_separate_from_triggers(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("requested, not ambient", skill.lower())
        self.assertIn("moves within a HowDo already underway", skill)


class InstallerNoteTests(unittest.TestCase):
    """A fresh install told the person what an agent should do, in words nothing defined."""

    def _note(self) -> str:
        sys.path.insert(0, str(ROOT))
        import install  # noqa: PLC0415

        return install.CONFIGURATION_NOTE

    def test_it_carries_every_setting_and_both_opt_outs(self):
        """Four settings and two answers. A partial note is a misleading one."""
        note = _flatten(self._note())
        settings = {
            "anchor": "subject you already know well",
            "build direction": "before the general rule",
            "what counts as understood": "convinces you",
            "how correction lands": "corrected when you are wrong",
        }
        for setting, phrase in settings.items():
            with self.subTest(setting=setting):
                self.assertIn(phrase, note, f"the note does not explain {setting}")
        self.assertIn("not be asked again", note, "declining is not offered")
        self.assertIn("offer stays open", note, "deferring is not offered")

    def test_it_avoids_the_vocabulary_the_reader_has_no_definition_for(self):
        """It is addressed to a person, on a path where nothing defined these."""
        note = _flatten(self._note())
        for term in (
            "pedagogy",
            "onboarding",
            "paradigm",
            "residual",
            "exemplar",
            "settlement",
            "payload",
            "howdo",
            "context.md",
        ):
            with self.subTest(term=term):
                self.assertNotIn(term, note, f"the note says '{term}' at the person")

    def test_it_is_ascii(self):
        """A contract, not a style preference.

        The note prints to whatever console the user has. A legacy codepage
        with no em dash turns an install into a UnicodeEncodeError.
        """
        note = self._note()
        try:
            note.encode("ascii")
        except UnicodeEncodeError as exc:
            self.fail(f"non-ASCII in the installer note: {note[exc.start:exc.end]!r}")
        note.encode("cp437")


class ContinuousIntegrationTests(unittest.TestCase):
    """CONTRIBUTING claimed CI ran on push and PR while no workflow existed."""

    WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"

    def test_the_workflow_exists(self):
        self.assertTrue(self.WORKFLOW.is_file(), "CONTRIBUTING promises CI; nothing runs it")

    def test_it_runs_the_documented_commands(self):
        text = self.WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("unittest discover -s tests", text)
        self.assertIn("examples/jira_workflow.py", text)
        self.assertIn("install.py --verify", text)

    def test_it_covers_every_python_the_package_claims(self):
        """A matrix narrower than requires-python is a claim nothing checks."""
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        floor = re.search(r'requires-python\s*=\s*"[><=]*(\d+)\.(\d+)"', pyproject)
        self.assertIsNotNone(floor, "pyproject has no requires-python floor")
        text = self.WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(f'"{floor.group(1)}.{floor.group(2)}"', text)

    def test_it_installs_on_every_platform_the_store_branches_on(self):
        """default_store_path() branches on Windows, so Windows must be tested."""
        text = self.WORKFLOW.read_text(encoding="utf-8")
        for runner in ("ubuntu-latest", "macos-latest", "windows-latest"):
            self.assertIn(runner, text)

    def test_contributing_does_not_promise_more_than_the_workflow_runs(self):
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        self.assertIn("tests.yml", contributing)
        self.assertIn("push and pull request", contributing)


class ReferenceSplitTests(unittest.TestCase):
    """Detail loads on demand; the guarantees it backs stay in SKILL.md."""

    def test_references_are_pointed_to_and_exist(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for name in ("references/onboarding.md", "references/vocabulary.md"):
            self.assertIn(name, skill, f"SKILL.md never tells anyone to read {name}")
            self.assertTrue((ROOT / name).is_file(), f"{name} is missing")

    def test_references_ship_with_the_payload(self):
        sys.path.insert(0, str(ROOT))
        import install  # noqa: E402

        self.assertIn("references", install.PAYLOAD)
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "how-do"
            install.copy_payload(destination, dry_run=False)
            for name in ("onboarding.md", "vocabulary.md"):
                self.assertTrue((destination / "references" / name).is_file())

    def test_skill_keeps_the_guarantees_the_reference_details(self):
        """A reference that is never read must not take a guarantee with it."""
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
        self.assertIn("onboarding: declined", skill)
        self.assertIn("do not ask again", skill)
        self.assertIn("structural completeness only", skill)
        self.assertIn("does not prove", skill)

    def test_skill_has_no_dangling_section_pointers(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        headings = {line[3:].strip() for line in skill.splitlines() if line.startswith("## ")}
        for pointer in re.findall(r"as in \*\*([^*]+)\*\*", skill):
            self.assertIn(pointer, headings, f"SKILL.md points at a section it lost: {pointer}")


class PayloadHygieneTests(unittest.TestCase):
    """What ships is the skill, not whatever the working tree accumulated."""

    def test_install_copies_no_build_noise(self):
        sys.path.insert(0, str(ROOT))
        import install  # noqa: E402

        with tempfile.TemporaryDirectory() as tmp:
            # The README tells contributors to run the tests before installing,
            # so bytecode is present in a realistic working tree.
            junk = ROOT / "runtime" / "howdo" / "__pycache__"
            junk.mkdir(parents=True, exist_ok=True)
            (junk / "context.cpython-311.pyc").write_bytes(b"stale")

            destination = Path(tmp) / "how-do"
            install.copy_payload(destination, dry_run=False)

            strays = [
                path.relative_to(destination)
                for path in destination.rglob("*")
                if path.name == "__pycache__" or path.suffix in {".pyc", ".pyo", ".pyd"}
            ]
            self.assertEqual(strays, [], f"install shipped build noise: {strays}")


if __name__ == "__main__":
    unittest.main()
