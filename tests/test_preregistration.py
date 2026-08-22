"""The preregistration: the commitments a confirmatory trial cites.

The document is the gate. These tests check the two things that make citing it
mean something -- that an unfilled one cannot be digested, and that the
document actually contains the commitments it claims to.
"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiment"))

from evidence import (  # noqa: E402
    PreregistrationError,
    preregistration_digest,
    undeclared_markers,
)

PREREG = ROOT / "experiment" / "PILOT-0001" / "PREREGISTRATION.md"
RUNBOOK = ROOT / "experiment" / "PILOT-0001" / "RUNBOOK.md"


def _flat(text: str) -> str:
    """Line wrapping is a formatting choice; these tests are about content."""
    return " ".join(text.split())


class DigestTests(unittest.TestCase):
    def test_the_current_document_is_not_yet_frozen(self):
        """It ships unfrozen on purpose: the open values are decisions a person
        makes, not defaults a script picks."""
        self.assertTrue(undeclared_markers(PREREG))
        with self.assertRaises(PreregistrationError):
            preregistration_digest(PREREG)

    def test_the_refusal_names_what_is_missing(self):
        with self.assertRaises(PreregistrationError) as caught:
            preregistration_digest(PREREG)
        message = str(caught.exception)
        self.assertIn("undeclared", message)
        self.assertIn("proposed 0.10", message)

    def test_stage_a_may_be_frozen_while_stage_b_is_open(self):
        import re

        # Fill only the Stage A commitments; leave Stage B open.
        settled = PREREG.read_text(encoding="utf-8")
        settled = re.sub(r"<<DECLARE[^>]*>>", "0.10", settled, flags=re.DOTALL)
        settled = re.sub(r"<<STAGE-A[^>]*>>", "2026-09-01", settled, flags=re.DOTALL)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "PREREGISTRATION.md"
            path.write_text(settled, encoding="utf-8")
            digest = preregistration_digest(path, stage="A")
            self.assertEqual(len(digest), 64)
            with self.assertRaises(PreregistrationError):
                preregistration_digest(path, stage="B")

    def test_a_fully_settled_document_digests(self):
        import re

        settled = re.sub(r"<<[^>]*>>", "settled", PREREG.read_text(encoding="utf-8"),
                         flags=re.DOTALL)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "PREREGISTRATION.md"
            path.write_text(settled, encoding="utf-8")
            self.assertEqual(len(preregistration_digest(path)), 64)

    def test_any_edit_changes_the_digest(self):
        """A commitment changed after freezing must not be able to hide."""
        import re

        settled = re.sub(r"<<[^>]*>>", "settled", PREREG.read_text(encoding="utf-8"),
                         flags=re.DOTALL)
        with tempfile.TemporaryDirectory() as tmp:
            one = Path(tmp) / "a.md"
            two = Path(tmp) / "b.md"
            one.write_text(settled, encoding="utf-8")
            two.write_text(settled.replace("Exclusion ceiling", "Exclusion allowance"),
                           encoding="utf-8")
            self.assertNotEqual(preregistration_digest(one), preregistration_digest(two))

    def test_an_unknown_stage_is_refused(self):
        with self.assertRaises(PreregistrationError):
            preregistration_digest(PREREG, stage="C")


class CommitmentTests(unittest.TestCase):
    """The document has to actually contain what the gate depends on."""

    def _text(self) -> str:
        return _flat(PREREG.read_text(encoding="utf-8"))

    def test_it_declares_all_three_outcomes(self):
        text = self._text()
        for outcome in ("**GO.**", "**STOP.**", "**INCONCLUSIVE.**"):
            with self.subTest(outcome=outcome):
                self.assertIn(outcome, text)

    def test_inconclusive_is_not_a_soft_go(self):
        self.assertIn("Not a soft GO", self._text())

    def test_stop_is_an_accepted_result(self):
        text = self._text()
        self.assertIn("A clean null is an accepted result", text)
        self.assertIn("return to How Do itself", text)

    def test_it_carries_the_qualifier_on_what_a_null_falsifies(self):
        """A null falsifies the treatment; the person-derived half is in no arm."""
        text = self._text()
        self.assertIn("It does not falsify How Do.", text)
        self.assertIn("absent from every arm", text)

    def test_the_primary_endpoint_is_singular_and_named(self):
        text = self._text()
        self.assertIn("## Primary endpoint", text)
        self.assertIn("one primary endpoint, one test", text)

    def test_secondary_endpoints_are_fixed_in_advance(self):
        self.assertIn("## Secondary endpoints", self._text())

    def test_exploratory_analysis_is_separated_by_name(self):
        text = self._text()
        self.assertIn("## Explicitly exploratory", text)
        self.assertIn("cannot convert a null into a positive", text)

    def test_the_power_gate_refuses_to_lower_the_threshold(self):
        text = self._text()
        self.assertIn("MDE > δ\\*, PILOT-0001 does not run", text)
        self.assertIn("not to lower δ\\*", text)

    def test_the_screening_bias_is_declared_rather_than_discovered(self):
        text = self._text()
        self.assertIn("Screening bias, declared", text)
        self.assertIn("neither trivial nor impossible", text)

    def test_control_trials_are_fresh(self):
        self.assertIn("Fresh trials only", self._text())

    def test_no_interim_analysis(self):
        self.assertIn("No interim analysis", self._text())

    def test_exclusions_have_a_ceiling(self):
        self.assertIn("Exclusion ceiling", self._text())

    def test_there_is_a_deviations_register(self):
        text = self._text()
        self.assertIn("## Deviations register", text)
        self.assertIn("an unrecorded deviation is", text)


class RunbookTests(unittest.TestCase):
    """The runbook exists so that nobody decides anything mid-study."""

    def _text(self) -> str:
        return _flat(RUNBOOK.read_text(encoding="utf-8"))

    def test_it_states_its_own_purpose(self):
        self.assertIn("nobody makes a decision while the study is running", self._text())

    def test_it_gates_on_the_frozen_artifacts_before_running(self):
        text = self._text()
        for gate in ("Organism frozen?", "Preregistration frozen at Stage B?",
                     "Every committed task qualified?", "Power gate passed?"):
            with self.subTest(gate=gate):
                self.assertIn(gate, text)

    def test_analysis_code_precedes_the_data(self):
        self.assertIn("before any real trial exists", self._text())

    def test_the_trial_lifecycle_ends_in_destruction(self):
        text = self._text()
        self.assertIn("destroy the container and the context", text)
        self.assertIn("Destruction is not cleanup, it is the treatment", text)

    def test_recon_failure_is_not_an_exclusion(self):
        self.assertIn("reconnaissance failure is **treatment failure.**", self._text().lower())

    def test_integrity_checks_run_before_the_difference_is_looked_at(self):
        self.assertIn("Do not look at the difference yet", self._text())

    def test_failures_are_looked_up_rather_than_decided(self):
        self.assertIn("Look up the disposition; do not decide it.", self._text())


if __name__ == "__main__":
    unittest.main()
