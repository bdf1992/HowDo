import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from howdo.context import inspect_context  # noqa: E402


class ReleaseContractTests(unittest.TestCase):
    def test_release_versions_are_aligned(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        context = (ROOT / "CONTEXT.template.md").read_text(encoding="utf-8")
        self.assertIn('version: "0.8.0"', skill)
        self.assertIn("How Do v0.8.0", readme)
        self.assertIn('version = "0.8.0"', pyproject)
        self.assertIn('skill_version: "0.8.0"', context)
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## 0.8.0", changelog)

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
        self.assertIn("onboarding: declined", skill)
        self.assertIn("do not ask again", skill.lower())
        self.assertIn("decline_onboarding", readme)

    def test_completion_claim_is_structural_not_truth_claim(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("structural completeness only", skill)
        self.assertIn("does not prove", skill)


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
