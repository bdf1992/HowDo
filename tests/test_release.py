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
        self.assertIn("Before the first substantive HowDo", skill)
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

    def test_reinstall_prunes_noise_an_earlier_install_left(self):
        sys.path.insert(0, str(ROOT))
        import install  # noqa: E402

        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "how-do"
            install.copy_payload(destination, dry_run=False)
            stale = destination / "runtime" / "howdo" / "__pycache__"
            stale.mkdir(parents=True, exist_ok=True)
            (stale / "context.cpython-311.pyc").write_bytes(b"stale")

            install.copy_payload(destination, dry_run=False)
            self.assertFalse(stale.exists(), "reinstall left an earlier install's bytecode")


if __name__ == "__main__":
    unittest.main()
