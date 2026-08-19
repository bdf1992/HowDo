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
        self.assertIn('version: "0.7.1"', skill)
        self.assertIn("How Do v0.7.1", readme)
        self.assertIn('version = "0.7.1"', pyproject)
        self.assertIn('skill_version: "0.7.1"', context)
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## 0.7.1", changelog)

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
        self.assertIn("primarily informs **rendering and interaction**", context)
        self.assertIn("does not grant facts, capability, or authority", context)

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
