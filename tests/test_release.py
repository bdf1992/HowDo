import sys
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
        self.assertIn('version: "0.7.0"', skill)
        self.assertIn("How Do v0.7.0", readme)
        self.assertIn('version = "0.7.0"', pyproject)
        self.assertIn('skill_version: "0.7.0"', context)
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## 0.7.0", changelog)

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


if __name__ == "__main__":
    unittest.main()
