import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime"))

from howdo import (  # noqa: E402
    PayloadContextError,
    complete_onboarding,
    decline_onboarding,
    ensure_context,
    inspect_context,
    payload_root,
    resolve_context_path,
)

SHIPPED_TEMPLATE = ROOT / "CONTEXT.md"

EVIDENCE = {
    "calibration_domain": "distributed queues; runs incident review",
    "representation_observation": "diagram before terminology landed for relational systems",
    "landed_example": "state diagram then one worked failure, then names",
    "rejected_example": "definitions-first prose; reader could not locate the failure",
}


def make_payload(root: Path) -> Path:
    """Build a directory that looks like an installed skill payload."""
    payload = root / "skills" / "how-do"
    (payload / "runtime" / "howdo").mkdir(parents=True)
    (payload / "SKILL.md").write_text("# How Do\n", encoding="utf-8")
    (payload / "CONTEXT.md").write_text(
        SHIPPED_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return payload


class PayloadBoundaryTests(unittest.TestCase):
    def test_payload_is_detected_from_the_skill_file_it_ships(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = make_payload(Path(tmp))
            self.assertEqual(payload_root(payload / "CONTEXT.md"), payload)
            self.assertEqual(payload_root(payload / "runtime" / "howdo"), payload)

    def test_store_outside_the_payload_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_payload(Path(tmp))
            store = Path(tmp) / "home" / ".howdo" / "CONTEXT.md"
            store.parent.mkdir(parents=True)
            store.write_text(SHIPPED_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")
            self.assertIsNone(payload_root(store))

    def test_completion_refuses_to_settle_inside_the_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = make_payload(Path(tmp))
            with self.assertRaises(PayloadContextError):
                complete_onboarding(payload / "CONTEXT.md", **EVIDENCE)
            # The refusal must leave the shipped template untouched.
            self.assertEqual(
                inspect_context(payload / "CONTEXT.md").state, "onboarding_required"
            )

    def test_decline_refuses_to_settle_inside_the_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = make_payload(Path(tmp))
            with self.assertRaises(PayloadContextError):
                decline_onboarding(payload / "CONTEXT.md")

    def test_payload_settlement_requires_an_explicit_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = make_payload(Path(tmp))
            settled = complete_onboarding(
                payload / "CONTEXT.md", allow_payload=True, **EVIDENCE
            )
            self.assertEqual(inspect_context(settled).state, "ready")


class StoreResolutionTests(unittest.TestCase):
    def test_explicit_selection_wins_over_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            chosen = Path(tmp) / "chosen" / "CONTEXT.md"
            resolved = resolve_context_path(
                chosen, env={"HOWDO_CONTEXT": str(Path(tmp) / "env" / "CONTEXT.md")}
            )
            self.assertEqual(resolved, chosen)

    def test_environment_wins_over_home_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            configured = Path(tmp) / "env" / "CONTEXT.md"
            resolved = resolve_context_path(
                env={"HOWDO_CONTEXT": str(configured)}, home=Path(tmp) / "home"
            )
            self.assertEqual(resolved, configured)

    def test_default_store_is_user_scoped_and_keeps_the_canonical_basename(self):
        with tempfile.TemporaryDirectory() as tmp:
            resolved = resolve_context_path(env={}, home=Path(tmp))
            self.assertEqual(resolved, Path(tmp) / ".howdo" / "CONTEXT.md")
            # A different basename would be read as a fork by inspect_context.
            self.assertEqual(resolved.name, "CONTEXT.md")


class EnsureContextTests(unittest.TestCase):
    def test_first_run_instantiates_the_store_and_requires_onboarding(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = make_payload(Path(tmp))
            status = ensure_context(
                template=payload / "CONTEXT.md", env={}, home=Path(tmp) / "home"
            )
            self.assertEqual(status.state, "onboarding_required")
            self.assertTrue(status.path.exists())
            self.assertIsNone(payload_root(status.path))

    def test_reinstall_never_clobbers_a_settled_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = make_payload(Path(tmp))
            home = Path(tmp) / "home"
            first = ensure_context(template=payload / "CONTEXT.md", env={}, home=home)
            complete_onboarding(first.path, **EVIDENCE)
            settled_id = inspect_context(first.path).metadata["context_id"]

            # Payload is replaced wholesale, exactly as an update would do.
            (payload / "CONTEXT.md").write_text(
                SHIPPED_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8"
            )
            second = ensure_context(template=payload / "CONTEXT.md", env={}, home=home)

            self.assertEqual(second.state, "ready")
            self.assertEqual(second.metadata["context_id"], settled_id)

    def test_instantiated_store_is_settleable_where_the_payload_copy_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = make_payload(Path(tmp))
            status = ensure_context(
                template=payload / "CONTEXT.md", env={}, home=Path(tmp) / "home"
            )
            complete_onboarding(status.path, **EVIDENCE)
            self.assertEqual(inspect_context(status.path).state, "ready")


if __name__ == "__main__":
    unittest.main()
