"""Task qualification: the two unqualified tasks that bias rather than blur.

A task nothing can solve shrinks the effective sample while the task count says
otherwise. A task that passes without being solved dilutes any real effect
toward zero. Both look ordinary in an aggregate score.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiment"))

from evidence import (  # noqa: E402
    MAX_INFRASTRUCTURE_ERROR_RATE,
    NOOP_ATTEMPTS,
    ORACLE_ATTEMPTS,
    Qualification,
    QualificationError,
    qualification_fields,
    verify_qualification,
)

PROCEDURE = ROOT / "experiment" / "TASK-QUALIFICATION.md"

BASE = dict(
    suite="harbor-index",
    suite_version="2026.03",
    task_id="hb-0042",
    task_version="3",
    task_definition_digest="a" * 64,
    harbor_version="0.4.2",
    image_digest="b" * 64,
    verifier_kind="deterministic",
    oracle_attempts=ORACLE_ATTEMPTS,
    oracle_passes=ORACLE_ATTEMPTS,
    noop_attempts=NOOP_ATTEMPTS,
    noop_failures=NOOP_ATTEMPTS,
    infrastructure_errors=0,
)


def qualification(**overrides) -> Qualification:
    return Qualification(**{**BASE, **overrides})


class OutcomeTests(unittest.TestCase):
    def test_a_clean_deterministic_task_qualifies(self):
        held = qualification()
        self.assertEqual(held.outcome, "qualified")
        self.assertIsNone(held.rejection_reason)
        self.assertTrue(held.certifies)

    def test_a_judge_scored_task_informs_research_but_never_certifies(self):
        held = qualification(verifier_kind="judge")
        self.assertEqual(held.outcome, "research_only")
        self.assertFalse(held.certifies)

    def test_an_unsolvable_task_is_rejected(self):
        held = qualification(oracle_passes=0)
        self.assertEqual(held.outcome, "rejected")
        self.assertIn("oracle passed 0/5", held.rejection_reason)

    def test_a_task_solvable_four_times_in_five_is_rejected(self):
        """4/5 under a known-good solution indicts the fixture, not the solution."""
        held = qualification(oracle_passes=4)
        self.assertEqual(held.outcome, "rejected")

    def test_a_single_noop_pass_disqualifies(self):
        held = qualification(noop_failures=NOOP_ATTEMPTS - 1)
        self.assertEqual(held.outcome, "rejected")
        self.assertIn("accepts the initial state", held.rejection_reason)

    def test_too_few_oracle_runs_is_rejected_not_accepted_on_faith(self):
        held = qualification(oracle_attempts=1, oracle_passes=1)
        self.assertEqual(held.outcome, "rejected")

    def test_too_few_noop_runs_is_rejected(self):
        held = qualification(noop_attempts=1, noop_failures=1)
        self.assertEqual(held.outcome, "rejected")

    def test_a_flaky_task_is_rejected(self):
        held = qualification(infrastructure_errors=10)
        self.assertEqual(held.outcome, "rejected")
        self.assertIn("infrastructure error rate", held.rejection_reason)

    def test_a_few_flakes_are_tolerated(self):
        held = qualification(infrastructure_errors=1)
        self.assertLessEqual(held.infrastructure_error_rate, MAX_INFRASTRUCTURE_ERROR_RATE)
        self.assertEqual(held.outcome, "qualified")

    def test_rejection_reasons_are_checked_in_a_fixed_order(self):
        """Two readers of one record must give the same reason."""
        held = qualification(oracle_passes=0, noop_failures=0, infrastructure_errors=99)
        self.assertIn("oracle passed", held.rejection_reason)


class RecordTests(unittest.TestCase):
    def test_impossible_counts_are_refused(self):
        with self.assertRaises(QualificationError):
            qualification(oracle_passes=ORACLE_ATTEMPTS + 1)
        with self.assertRaises(QualificationError):
            qualification(noop_failures=NOOP_ATTEMPTS + 1)

    def test_an_unknown_verifier_kind_is_refused(self):
        with self.assertRaises(QualificationError):
            qualification(verifier_kind="vibes")

    def test_a_blank_task_identity_is_refused(self):
        for field in ("suite", "task_id", "task_version", "task_definition_digest"):
            with self.subTest(field=field):
                with self.assertRaises(QualificationError):
                    qualification(**{field: "  "})

    def test_the_digest_commits_to_the_counts(self):
        """A receipt cites the evidence that granted authority, not the claim
        that qualification happened."""
        one = qualification().digest
        two = qualification(oracle_passes=ORACLE_ATTEMPTS - 1).digest
        self.assertNotEqual(one, two)

    def test_the_digest_distinguishes_task_versions(self):
        self.assertNotEqual(qualification().digest, qualification(task_version="4").digest)

    def test_the_record_carries_the_derived_outcome(self):
        record = qualification_fields(**BASE)
        self.assertEqual(record["outcome"], "qualified")
        self.assertEqual(record["task_qualification_digest"], qualification().digest)


class VerificationTests(unittest.TestCase):
    def test_an_untouched_record_verifies(self):
        self.assertTrue(verify_qualification(qualification_fields(**BASE)))

    def test_a_record_edited_to_promote_a_rejected_task_fails(self):
        """Even with the digest recomputed: the outcome is rechecked, so
        promoting a rejection takes forging the rule rather than the hash."""
        record = qualification_fields(**{**BASE, "noop_failures": 0})
        self.assertEqual(record["outcome"], "rejected")
        record["outcome"] = "qualified"
        record["certifies"] = True
        self.assertFalse(verify_qualification(record))

    def test_a_record_edited_to_certify_a_judged_task_fails(self):
        record = qualification_fields(**{**BASE, "verifier_kind": "judge"})
        record["certifies"] = True
        self.assertFalse(verify_qualification(record))

    def test_verification_never_raises(self):
        for bad in ({}, [], None, {"suite": "x"}, {"oracle_passes": "five"}):
            with self.subTest(record=bad):
                self.assertFalse(verify_qualification(bad))


class ProcedureTests(unittest.TestCase):
    def _text(self) -> str:
        return PROCEDURE.read_text(encoding="utf-8")

    def test_the_procedure_exists_and_names_both_failure_modes(self):
        text = self._text()
        self.assertIn("cannot be solved at all", text)
        self.assertIn("passes without being solved", text)

    def test_the_counts_in_the_document_match_the_code(self):
        """A procedure saying 5 while the code enforces 3 is worse than neither."""
        text = self._text()
        self.assertIn(f"**{ORACLE_ATTEMPTS} times**", text)
        self.assertIn(f"**{NOOP_ATTEMPTS} times**", text)
        self.assertIn(f"**{MAX_INFRASTRUCTURE_ERROR_RATE:.0%}**", text)

    def test_it_keeps_judged_tasks_out_of_certification(self):
        text = self._text()
        self.assertIn("research_only", text)
        self.assertIn("never certify", text)

    def test_rejections_stay_in_the_record(self):
        """Deleting rejections turns a committed set into a selected set."""
        self.assertIn("deleting rejections", self._text())

    def test_it_states_what_qualification_does_not_establish(self):
        text = self._text()
        self.assertIn("## What this does not establish", text)
        self.assertIn("qualified and useless", text)


if __name__ == "__main__":
    unittest.main()
