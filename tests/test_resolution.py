"""The resolution block: the part of a crossing that cannot be recomputed.

These tests exist because the digest is a commitment. If two materially
different resolutions can produce the same digest, the receipt is asserting
something it cannot back.
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiment"))

from evidence import (  # noqa: E402
    RESOLUTION_VERSION,
    Resolution,
    ResolutionOperand,
    resolution_fields,
    verify_resolution,
)
from evidence.resolution import ResolutionError  # noqa: E402

ENVIRONMENT = ResolutionOperand("environment", "environment_context", "img:abc", "e" * 64)
TRIAL = ResolutionOperand("trial", "trial", "trial-a", "t" * 64)
SKILL = ResolutionOperand("skill", "skill_node", "how-do@0.8.0", "s" * 64)


def _resolution(*operands, builder_id="harbor-adapter", builder_digest="d" * 64):
    return Resolution(
        builder_id=builder_id, builder_digest=builder_digest, operands=operands
    )


class CommitmentTests(unittest.TestCase):
    def test_the_same_resolution_digests_the_same_way(self):
        self.assertEqual(
            _resolution(ENVIRONMENT, TRIAL).digest, _resolution(ENVIRONMENT, TRIAL).digest
        )

    def test_order_is_part_of_the_commitment(self):
        self.assertNotEqual(
            _resolution(ENVIRONMENT, TRIAL).digest, _resolution(TRIAL, ENVIRONMENT).digest
        )

    def test_role_and_kind_cannot_be_swapped_without_notice(self):
        """Skill(foo) + Environment(bar) must not collide with the reverse."""
        one = _resolution(
            ResolutionOperand("skill", "skill_node", "foo", "1" * 64),
            ResolutionOperand("environment", "environment_context", "bar", "2" * 64),
        )
        other = _resolution(
            ResolutionOperand("environment", "environment_context", "foo", "1" * 64),
            ResolutionOperand("skill", "skill_node", "bar", "2" * 64),
        )
        self.assertNotEqual(one.digest, other.digest)

    def test_arity_is_part_of_the_commitment(self):
        self.assertNotEqual(
            _resolution(ENVIRONMENT, TRIAL).digest,
            _resolution(ENVIRONMENT, TRIAL, SKILL).digest,
        )

    def test_the_resolver_is_part_of_the_commitment(self):
        """Same operands, different resolver, is a different resolution."""
        self.assertNotEqual(
            _resolution(ENVIRONMENT, TRIAL, builder_id="resolver-a").digest,
            _resolution(ENVIRONMENT, TRIAL, builder_id="resolver-b").digest,
        )

    def test_the_resolver_version_is_part_of_the_commitment(self):
        self.assertNotEqual(
            _resolution(ENVIRONMENT, TRIAL, builder_digest="a" * 64).digest,
            _resolution(ENVIRONMENT, TRIAL, builder_digest="b" * 64).digest,
        )

    def test_the_canonicalization_version_is_inside_the_digest(self):
        base = _resolution(ENVIRONMENT, TRIAL)
        bumped = Resolution(
            builder_id=base.builder_id,
            builder_digest=base.builder_digest,
            operands=base.operands,
            version=RESOLUTION_VERSION + 1,
        )
        self.assertNotEqual(base.digest, bumped.digest)

    def test_a_crafted_identity_cannot_impersonate_the_structure(self):
        """Concatenating digests would be forgeable; a typed encoding is not."""
        honest = _resolution(
            ResolutionOperand("environment", "environment_context", "img:abc", "e" * 64),
            ResolutionOperand("trial", "trial", "trial-a", "t" * 64),
        )
        forged = _resolution(
            ResolutionOperand(
                "environment",
                "environment_context",
                'img:abc","digest":"' + "e" * 64 + '"},{"role":"trial"',
                "e" * 64,
            ),
            ResolutionOperand("trial", "trial", "trial-a", "t" * 64),
        )
        self.assertNotEqual(honest.digest, forged.digest)

    def test_the_canonical_form_is_inspectable_and_ordered(self):
        payload = json.loads(_resolution(ENVIRONMENT, TRIAL).canonical_bytes())
        self.assertEqual(
            [operand["role"] for operand in payload["operands"]], ["environment", "trial"]
        )
        self.assertEqual(payload["resolution_version"], RESOLUTION_VERSION)


class ReceiptBlockTests(unittest.TestCase):
    def test_the_block_carries_only_the_irreversible_fields(self):
        block = _resolution(ENVIRONMENT, TRIAL).as_receipt_block()
        self.assertEqual(
            set(block),
            {
                "resolution_version",
                "resolution_builder_id",
                "resolution_builder_digest",
                "resolution_operands",
                "resolution_digest",
            },
        )

    def test_a_stored_block_verifies_against_its_own_digest(self):
        self.assertTrue(verify_resolution(_resolution(ENVIRONMENT, TRIAL).as_receipt_block()))

    def test_a_tampered_operand_fails_verification(self):
        block = _resolution(ENVIRONMENT, TRIAL).as_receipt_block()
        block["resolution_operands"][0]["identity"] = "img:zzz"
        self.assertFalse(verify_resolution(block))

    def test_a_reordered_block_fails_verification(self):
        block = _resolution(ENVIRONMENT, TRIAL).as_receipt_block()
        block["resolution_operands"].reverse()
        self.assertFalse(verify_resolution(block))

    def test_a_malformed_block_is_false_not_an_exception(self):
        self.assertFalse(verify_resolution({}))
        self.assertFalse(verify_resolution({"resolution_operands": [{}]}))

    def test_the_helper_accepts_plain_records(self):
        block = resolution_fields(
            builder_id="harbor-adapter",
            builder_digest="d" * 64,
            operands=[
                {
                    "role": "environment",
                    "kind": "environment_context",
                    "identity": "img:abc",
                    "digest": "e" * 64,
                },
                {"role": "trial", "kind": "trial", "identity": "trial-a", "digest": "t" * 64},
            ],
        )
        self.assertEqual(block["resolution_digest"], _resolution(ENVIRONMENT, TRIAL).digest)


class RefusalTests(unittest.TestCase):
    def test_casing_cannot_silently_fork_a_role(self):
        with self.assertRaises(ResolutionError):
            ResolutionOperand("Environment", "environment_context", "img:abc", "e" * 64)

    def test_empty_fields_are_refused(self):
        for bad in ("", "   "):
            with self.assertRaises(ResolutionError):
                ResolutionOperand("environment", "environment_context", bad, "e" * 64)

    def test_a_resolution_needs_an_operand(self):
        with self.assertRaises(ResolutionError):
            _resolution()

    def test_operands_must_be_typed(self):
        with self.assertRaises(ResolutionError):
            Resolution(
                builder_id="harbor-adapter",
                builder_digest="d" * 64,
                operands=({"role": "environment"},),
            )

    def test_the_resolver_must_be_named(self):
        with self.assertRaises(ResolutionError):
            _resolution(ENVIRONMENT, builder_id="")


class CrossingRuleTests(unittest.TestCase):
    """The rule has to keep saying that crossings are not stored."""

    DOCUMENT = ROOT / "experiment" / "CROSSINGS.md"

    def _text(self) -> str:
        return " ".join(self.DOCUMENT.read_text(encoding="utf-8").lower().split())

    def test_crossings_are_declared_projections_not_objects(self):
        text = self._text()
        self.assertIn("crossings are evidence projections", text)
        self.assertIn("not persisted as an independent entity", text)

    def test_the_interaction_vocabulary_is_marked_as_analysis_not_schema(self):
        self.assertIn("analysis vocabulary — not schema", self._text())

    def test_it_says_why_ordering_is_recorded_before_it_is_used(self):
        text = self._text()
        self.assertIn("ordered, not a set", text)
        self.assertIn("recovering it afterwards is impossible", text)

    def test_it_keeps_interpretation_downstream(self):
        self.assertIn("what stays downstream", self._text())


if __name__ == "__main__":
    unittest.main()
