import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "plugin"
sys.path.insert(0, str(PAYLOAD / "runtime"))

from howdo import complete_onboarding, decline_onboarding, fork_context, inspect_context


TEMPLATE = """---
howdo_context: "2"
context_id: pending
context_file: CONTEXT.md
skill: how-do
skill_version: "0.6.1"
onboarding: required
parent_context_id: none
---
# How Do Context

## Calibration domains

- pending

## Representation observations

- pending

## Structures that landed

- pending

## Structures that did not land

- pending

## Interaction observations

- pending

## LongHow settlements

- none yet
"""


def settle(path: Path) -> None:
    complete_onboarding(
        path,
        calibration_domain="incident response — can critique triage explanations",
        representation_observation="relation first, then rule, then executable step",
        landed_example="small boundary diagram exposed the missing handoff",
        rejected_example="taxonomy-first prose hid the concrete object",
        interaction_observation="show one useful object before expanding the model",
    )


class ContextContractTests(unittest.TestCase):
    def test_shipped_file_is_a_template_not_a_context(self):
        status = inspect_context(PAYLOAD / "CONTEXT.template.md")
        self.assertEqual(status.state, "template", status.reason)

    def test_template_is_never_ready_and_never_settleable(self):
        from howdo import TemplateContextError
        with self.assertRaises(TemplateContextError):
            complete_onboarding(
                PAYLOAD / "CONTEXT.template.md",
                calibration_domain="d",
                representation_observation="r",
                landed_example="l",
                rejected_example="x",
                allow_payload=True,
            )
        with self.assertRaises(TemplateContextError):
            decline_onboarding(PAYLOAD / "CONTEXT.template.md", allow_payload=True)

    def test_missing_context_requires_creation(self):
        with tempfile.TemporaryDirectory() as td:
            status = inspect_context(Path(td) / "CONTEXT.md")
            self.assertEqual(status.state, "missing")

    def test_installed_template_requires_onboarding(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "CONTEXT.md"
            path.write_text(TEMPLATE, encoding="utf-8")
            self.assertEqual(inspect_context(path).state, "onboarding_required")

    def test_flipping_metadata_does_not_fake_completion(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "CONTEXT.md"
            fake = TEMPLATE.replace("context_id: pending", "context_id: context_fake").replace(
                "onboarding: required", "onboarding: complete"
            )
            path.write_text(fake, encoding="utf-8")
            status = inspect_context(path)
            self.assertEqual(status.state, "onboarding_required")
            self.assertIn("missing evidence", status.reason)

    def test_shipped_template_cannot_be_faked_by_metadata_only(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "CONTEXT.md"
            shipped = (PAYLOAD / "CONTEXT.template.md").read_text(encoding="utf-8")
            fake = shipped.replace("template: true\n", "").replace(
                "context_file: CONTEXT.template.md", "context_file: CONTEXT.md"
            ).replace("context_id: template", "context_id: context_fake").replace(
                "onboarding: required", "onboarding: complete"
            )
            path.write_text(fake, encoding="utf-8")
            status = inspect_context(path)
            self.assertEqual(status.state, "onboarding_required")
            self.assertIn("missing evidence", status.reason)

    def test_completion_helper_requires_comparative_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "CONTEXT.md"
            path.write_text(TEMPLATE, encoding="utf-8")
            with self.assertRaises(ValueError):
                complete_onboarding(
                    path,
                    calibration_domain="pending",
                    representation_observation="diagram first",
                    landed_example="diagram",
                    rejected_example="taxonomy",
                )

    def test_decline_is_persisted_and_not_reasked(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "CONTEXT.md"
            path.write_text(TEMPLATE, encoding="utf-8")
            decline_onboarding(path)
            status = inspect_context(path)
            self.assertEqual(status.state, "declined")
            self.assertEqual(status.metadata["onboarding"], "declined")
            self.assertNotEqual(status.metadata["context_id"], "pending")

    def test_decline_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "CONTEXT.md"
            path.write_text(TEMPLATE, encoding="utf-8")
            decline_onboarding(path)
            first_id = inspect_context(path).metadata["context_id"]
            decline_onboarding(path)
            self.assertEqual(inspect_context(path).metadata["context_id"], first_id)

    def test_ready_context_cannot_be_recompleted_or_reidentified(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "CONTEXT.md"
            path.write_text(TEMPLATE, encoding="utf-8")
            settle(path)
            first_id = inspect_context(path).metadata["context_id"]
            with self.assertRaises(ValueError):
                settle(path)
            self.assertEqual(inspect_context(path).metadata["context_id"], first_id)

    def test_declined_context_can_later_complete_without_identity_churn(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "CONTEXT.md"
            path.write_text(TEMPLATE, encoding="utf-8")
            decline_onboarding(path)
            first_id = inspect_context(path).metadata["context_id"]
            settle(path)
            status = inspect_context(path)
            self.assertEqual(status.state, "ready")
            self.assertEqual(status.metadata["context_id"], first_id)

    def test_onboarding_evidence_is_flattened_to_one_line(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "CONTEXT.md"
            path.write_text(TEMPLATE, encoding="utf-8")
            complete_onboarding(
                path,
                calibration_domain="incident response\nwith production triage",
                representation_observation="relation first\r\nthen rule",
                landed_example="small diagram\nthen example",
                rejected_example="taxonomy\nfirst",
            )
            text = path.read_text(encoding="utf-8")
            self.assertIn("- incident response with production triage", text)
            self.assertIn("- relation first then rule", text)
            self.assertIn("- small diagram then example", text)
            self.assertIn("- taxonomy first", text)

    def test_one_nonplaceholder_bullet_is_structurally_sufficient(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "CONTEXT.md"
            fake = TEMPLATE.replace("context_id: pending", "context_id: context_min").replace(
                "onboarding: required", "onboarding: complete"
            ).replace("- pending", "- x")
            path.write_text(fake, encoding="utf-8")
            self.assertEqual(inspect_context(path).state, "ready")

    def test_obvious_placeholder_prefix_is_not_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "CONTEXT.md"
            fake = TEMPLATE.replace("context_id: pending", "context_id: context_fake").replace(
                "onboarding: required", "onboarding: complete"
            ).replace("- pending", "- pending (see instructions)")
            path.write_text(fake, encoding="utf-8")
            self.assertEqual(inspect_context(path).state, "onboarding_required")

    def test_completed_matching_context_is_ready(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "CONTEXT.md"
            path.write_text(TEMPLATE, encoding="utf-8")
            settle(path)
            status = inspect_context(path)
            self.assertEqual(status.state, "ready")
            self.assertNotEqual(status.metadata["context_id"], "pending")

    def test_missing_lineage_marker_is_invalid_not_ready(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "CONTEXT.md"
            broken = TEMPLATE.replace("context_file: CONTEXT.md\n", "")
            path.write_text(broken, encoding="utf-8")
            self.assertEqual(inspect_context(path).state, "invalid")

    def test_manual_copy_to_new_name_is_detected_as_fork(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "CONTEXT.md"
            source.write_text(TEMPLATE, encoding="utf-8")
            settle(source)
            copied = Path(td) / "CONTEXT.visual.md"
            copied.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            self.assertEqual(inspect_context(copied).state, "fork_required")
            self.assertEqual(inspect_context(source).state, "ready")

    def test_fork_helper_preserves_source_and_requires_new_onboarding(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "CONTEXT.md"
            source.write_text(TEMPLATE, encoding="utf-8")
            settle(source)
            parent_id = inspect_context(source).metadata["context_id"]
            before = source.read_text(encoding="utf-8")
            fork = Path(td) / "CONTEXT.code.md"
            fork_context(source, fork)

            self.assertEqual(source.read_text(encoding="utf-8"), before)
            status = inspect_context(fork)
            self.assertEqual(status.state, "onboarding_required")
            self.assertEqual(status.metadata["parent_context_id"], parent_id)
            self.assertEqual(status.metadata["context_file"], "CONTEXT.code.md")

    def test_fork_helper_inserts_missing_required_markers(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "legacy.md"
            legacy = """---
howdo_context: "1"
context_id: context_old
context_file: legacy.md
skill: how-do
skill_version: "0.5.0"
---
# How Do Context

## Calibration domains
- operations
## Representation observations
- examples first
## Structures that landed
- worked example
## Structures that did not land
- dense taxonomy
"""
            source.write_text(legacy, encoding="utf-8")
            fork = Path(td) / "CONTEXT.new.md"
            fork_context(source, fork)
            status = inspect_context(fork)
            self.assertEqual(status.state, "onboarding_required")
            self.assertEqual(status.metadata["parent_context_id"], "context_old")
            self.assertEqual(status.metadata["onboarding"], "required")

    def test_existing_fork_destination_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "CONTEXT.md"
            source.write_text(TEMPLATE, encoding="utf-8")
            target = Path(td) / "CONTEXT.other.md"
            target.write_text("keep me", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                fork_context(source, target)
            self.assertEqual(target.read_text(encoding="utf-8"), "keep me")


if __name__ == "__main__":
    unittest.main()
