"""The evidence receipt: the promises a trial record makes to a later reader.

Every test here corresponds to a way a receipt can look correct and be false.
Nothing in this file checks that recorded values are *true* -- see the "What
review enforces" section of RECEIPT.md for that boundary.
"""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiment"))

from evidence import (  # noqa: E402
    RECEIPT_VERSION,
    ReceiptError,
    append_receipt,
    build_receipt,
    correct_receipt,
    corrections_for,
    read_receipts,
    verify_receipt,
)

CONTRACT = ROOT / "experiment" / "evidence" / "RECEIPT.md"

D = lambda char: char * 64  # noqa: E731 - a readable stand-in digest

SECTIONS = {
    "experiment": {
        "experiment_id": "PILOT-0001",
        "preregistration_digest": D("1"),
        "analysis_class": "confirmatory",
        "condition_label": "h1-howdo-recon",
        "run_sequence_index": 0,
        "trial_id": "t-0001",
    },
    "benchmark": {
        "suite": "terminal-bench",
        "suite_version": "2.0",
        "task_id": "hb-0042",
        "task_version": "3",
        "task_qualification_digest": D("2"),
    },
    "environment": {
        "image_ref": "ghcr.io/example/task:1",
        "image_digest": D("3"),
        "environment_context_digest": D("4"),
    },
    "organism": {"organism_version": 1, "organism_fingerprint": D("5")},
    "treatment": {
        "arm": "h1",
        "skill_commit": "a" * 40,
        "skill_content_digest": D("6"),
        "recon_budget": 4000,
        "recon_used": 3120,
        "recon_outcome": "complete",
    },
    "resolution": {"resolution_version": 1, "resolution_digest": D("7")},
    "outcome": {
        "result": "pass",
        "verifier_kind": "deterministic",
        "verifier_exit_code": 0,
        "verifier_output_digest": D("8"),
    },
    "resources": {
        "wall_clock_seconds": 214.5,
        "prompt_tokens": 8100,
        "completion_tokens": 1450,
        "peak_vram_bytes": 21000000000,
    },
    "custody": {"trajectory_digest": D("9"), "artifact_digests": [D("a")]},
}


def sections(**overrides):
    built = copy.deepcopy(SECTIONS)
    for name, patch in overrides.items():
        built[name].update(patch)
    return built


def receipt(**overrides):
    return build_receipt(**sections(**overrides))


class ShapeTests(unittest.TestCase):
    def test_a_complete_receipt_builds_and_verifies(self):
        record = receipt()
        self.assertEqual(record["receipt_version"], RECEIPT_VERSION)
        self.assertTrue(verify_receipt(record))

    def test_every_required_field_is_actually_required(self):
        for name, fields in SECTIONS.items():
            for key in fields:
                with self.subTest(field=f"{name}.{key}"):
                    built = copy.deepcopy(SECTIONS)
                    del built[name][key]
                    with self.assertRaises(ReceiptError):
                        build_receipt(**built)

    def test_an_unknown_section_is_refused(self):
        built = copy.deepcopy(SECTIONS)
        with self.assertRaises(TypeError):
            build_receipt(**built, notes={"anything": 1})


class ClosedSetTests(unittest.TestCase):
    """Free-text categories become uncountable the moment two writers exist."""

    def test_result_is_a_closed_set(self):
        with self.assertRaises(ReceiptError):
            receipt(outcome={"result": "mostly_passed"})

    def test_arm_is_a_closed_set(self):
        with self.assertRaises(ReceiptError):
            receipt(treatment={"arm": "h1-variant"})

    def test_analysis_class_is_a_closed_set(self):
        with self.assertRaises(ReceiptError):
            receipt(experiment={"analysis_class": "final"})

    def test_verifier_kind_is_a_closed_set(self):
        with self.assertRaises(ReceiptError):
            receipt(outcome={"verifier_kind": "human"})


class FailureClassTests(unittest.TestCase):
    def test_an_error_must_be_typed(self):
        with self.assertRaises(ReceiptError):
            receipt(outcome={"result": "error"})

    def test_an_excluded_trial_must_be_typed(self):
        with self.assertRaises(ReceiptError):
            receipt(outcome={"result": "excluded"})

    def test_a_typed_error_is_accepted(self):
        record = receipt(outcome={"result": "error", "failure_class": "harness_timeout"})
        self.assertTrue(verify_receipt(record))

    def test_a_pass_may_not_carry_a_failure_class(self):
        """Otherwise a trial that measured the treatment can be filed as
        infrastructure noise after the fact."""
        with self.assertRaises(ReceiptError):
            receipt(outcome={"result": "pass", "failure_class": "oom"})

    def test_a_fail_may_not_carry_a_failure_class(self):
        with self.assertRaises(ReceiptError):
            receipt(outcome={"result": "fail", "failure_class": "runtime_crash"})

    def test_the_failure_class_itself_is_a_closed_set(self):
        with self.assertRaises(ReceiptError):
            receipt(outcome={"result": "error", "failure_class": "weird"})


class CertificationTests(unittest.TestCase):
    """Deterministic verifiers only. A rule a writer can assert is a convention."""

    def test_certification_cannot_be_written(self):
        with self.assertRaises(ReceiptError):
            receipt(outcome={"certifies": True})

    def test_a_deterministic_confirmatory_pass_certifies(self):
        self.assertTrue(receipt()["outcome"]["certifies"])

    def test_a_judged_pass_does_not_certify(self):
        record = receipt(outcome={"verifier_kind": "judge"})
        self.assertFalse(record["outcome"]["certifies"])

    def test_an_exploratory_pass_does_not_certify(self):
        record = receipt(experiment={"analysis_class": "exploratory"})
        self.assertFalse(record["outcome"]["certifies"])

    def test_a_fail_does_not_certify(self):
        record = receipt(outcome={"result": "fail"})
        self.assertFalse(record["outcome"]["certifies"])

    def test_a_hand_edited_certification_fails_verification(self):
        """Even with the digest recomputed to match, the derived value is
        rechecked -- so forging certification takes forging the rule, not the
        hash."""
        import hashlib

        record = receipt(outcome={"verifier_kind": "judge"})
        record["outcome"]["certifies"] = True
        payload = {k: v for k, v in record.items() if k != "receipt_digest"}
        record["receipt_digest"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        self.assertFalse(verify_receipt(record))


class PreregistrationTests(unittest.TestCase):
    def test_a_confirmatory_trial_needs_a_preregistration_in_force(self):
        with self.assertRaises(ReceiptError):
            receipt(experiment={"preregistration_digest": "none"})

    def test_an_exploratory_trial_does_not(self):
        record = build_receipt(
            **sections(
                experiment={"analysis_class": "exploratory", "preregistration_digest": "none"}
            )
        )
        self.assertTrue(verify_receipt(record))

    def test_a_rehearsal_does_not(self):
        record = build_receipt(
            **sections(
                experiment={"analysis_class": "rehearsal", "preregistration_digest": "none"}
            )
        )
        self.assertTrue(verify_receipt(record))


class ArmConsistencyTests(unittest.TestCase):
    """The control arm has no reconnaissance; the treatment arms always do."""

    def test_h0_cannot_report_reconnaissance(self):
        with self.assertRaises(ReceiptError):
            receipt(treatment={"arm": "h0", "recon_outcome": "complete"})

    def test_h0_with_no_reconnaissance_is_accepted(self):
        record = receipt(
            treatment={"arm": "h0", "recon_outcome": "not_applicable"},
            experiment={"condition_label": "h0-raw"},
        )
        self.assertTrue(verify_receipt(record))

    def test_a_treatment_arm_cannot_report_no_reconnaissance(self):
        with self.assertRaises(ReceiptError):
            receipt(treatment={"arm": "h2", "recon_outcome": "not_applicable"})

    def test_reconnaissance_failure_is_recorded_not_hidden(self):
        """Treatment failure, not an excluded trial: the arm still ran."""
        record = receipt(treatment={"recon_outcome": "failed"})
        self.assertEqual(record["treatment"]["recon_outcome"], "failed")
        self.assertTrue(verify_receipt(record))


class CustodyTests(unittest.TestCase):
    def test_a_filesystem_path_is_refused(self):
        with self.assertRaises(ReceiptError):
            receipt(custody={"trajectory_digest": "/var/runs/trial-1.jsonl"})

    def test_an_inline_payload_is_refused(self):
        with self.assertRaises(ReceiptError):
            receipt(custody={"trajectory_digest": "user: hello\nassistant: hi"})

    def test_artifact_references_are_addresses_too(self):
        with self.assertRaises(ReceiptError):
            receipt(custody={"artifact_digests": [D("a"), "./out.txt"]})

    def test_a_trial_with_no_trajectory_is_allowed(self):
        record = receipt(custody={"trajectory_digest": None})
        self.assertTrue(verify_receipt(record))

    def test_an_uppercase_digest_is_refused(self):
        """Two spellings of one address split a blob store in half."""
        with self.assertRaises(ReceiptError):
            receipt(custody={"trajectory_digest": "A" * 64})


class DigestTests(unittest.TestCase):
    def test_any_edit_breaks_the_digest(self):
        record = receipt()
        record["resources"]["prompt_tokens"] = 1
        self.assertFalse(verify_receipt(record))

    def test_verification_never_raises(self):
        for bad in ({}, {"receipt_digest": "x"}, {"outcome": None}, []):
            with self.subTest(record=bad):
                self.assertFalse(verify_receipt(bad))

    def test_two_receipts_differing_only_in_arm_differ_in_digest(self):
        one = receipt()
        two = receipt(
            treatment={"arm": "h2"}, experiment={"condition_label": "h2-howdo-frozen"}
        )
        self.assertNotEqual(one["receipt_digest"], two["receipt_digest"])


class AppendOnlyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / "receipts.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_receipts_accumulate_in_written_order(self):
        for index in range(3):
            append_receipt(self.log, receipt(experiment={"run_sequence_index": index}))
        stored = read_receipts(self.log)
        self.assertEqual([r["experiment"]["run_sequence_index"] for r in stored], [0, 1, 2])

    def test_an_out_of_order_index_is_refused(self):
        append_receipt(self.log, receipt(experiment={"run_sequence_index": 5}))
        with self.assertRaises(ReceiptError):
            append_receipt(self.log, receipt(experiment={"run_sequence_index": 4}))

    def test_a_repeated_index_is_refused(self):
        append_receipt(self.log, receipt(experiment={"run_sequence_index": 2}))
        with self.assertRaises(ReceiptError):
            append_receipt(self.log, receipt(experiment={"run_sequence_index": 2}))

    def test_ordering_is_per_experiment(self):
        append_receipt(self.log, receipt(experiment={"run_sequence_index": 9}))
        other = receipt(
            experiment={"experiment_id": "PILOT-0002", "run_sequence_index": 0}
        )
        self.assertTrue(append_receipt(self.log, other))

    def test_a_receipt_that_does_not_verify_is_never_written(self):
        record = receipt()
        record["resources"]["prompt_tokens"] = 1
        with self.assertRaises(ReceiptError):
            append_receipt(self.log, record)
        self.assertEqual(read_receipts(self.log), [])


class CorrectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / "receipts.jsonl"
        self.original = append_receipt(self.log, receipt())

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_correction_leaves_the_original_in_place(self):
        correct_receipt(
            self.log,
            corrects_digest=self.original["receipt_digest"],
            reason="verifier output digest addressed the wrong blob",
            corrected_fields={"outcome.verifier_output_digest": D("b")},
        )
        stored = read_receipts(self.log)
        self.assertEqual(len(stored), 2)
        self.assertEqual(stored[0], self.original)
        self.assertTrue(verify_receipt(stored[0]))

    def test_a_correction_must_name_an_existing_receipt(self):
        with self.assertRaises(ReceiptError):
            correct_receipt(
                self.log,
                corrects_digest=D("f"),
                reason="typo",
                corrected_fields={},
            )

    def test_a_correction_must_say_why(self):
        with self.assertRaises(ReceiptError):
            correct_receipt(
                self.log,
                corrects_digest=self.original["receipt_digest"],
                reason="   ",
                corrected_fields={"outcome.result": "fail"},
            )

    def test_corrections_are_findable_from_the_receipt_they_correct(self):
        correct_receipt(
            self.log,
            corrects_digest=self.original["receipt_digest"],
            reason="wrong task version recorded",
            corrected_fields={"benchmark.task_version": "4"},
        )
        found = list(corrections_for(self.log, self.original["receipt_digest"]))
        self.assertEqual(len(found), 1)
        self.assertIn("wrong task version", found[0]["correction"]["reason"])


class ContractTests(unittest.TestCase):
    """The document and the code have to agree, and the gap has to be stated."""

    def _contract(self) -> str:
        return CONTRACT.read_text(encoding="utf-8")

    def test_the_contract_exists_and_states_the_design_rule(self):
        text = self._contract()
        self.assertIn("Freeze what cannot be recovered", text)

    def test_it_names_every_section_the_code_requires(self):
        text = self._contract()
        for section in SECTIONS:
            with self.subTest(section=section):
                self.assertIn(f"### `{section}`", text)

    def test_it_says_certification_is_derived(self):
        self.assertIn("derived, not written", self._contract())

    def test_it_states_what_the_code_does_not_enforce(self):
        """A contract that lists only its guarantees reads as if it has no gaps."""
        text = self._contract()
        self.assertIn("## What review enforces", text)
        self.assertIn("structurally perfect", text)


if __name__ == "__main__":
    unittest.main()
