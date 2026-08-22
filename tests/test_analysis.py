"""The committed analysis, validated before it ever sees a real trial.

The preregistration requires this module to recover an effect it was told about
in advance. These tests are that requirement.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiment"))

from analysis import analyse, decide, per_task_rates, synthetic_trials  # noqa: E402

SIZING = ROOT / "experiment" / "PILOT-0001" / "SIZING.md"

FAST = dict(permutations=300, resamples=500)


class RecoveryTests(unittest.TestCase):
    def test_it_recovers_a_known_effect(self):
        rows = synthetic_trials(tasks=20, trials_per_arm=8, h0_rate=0.35, lift=0.25, seed=1)
        result = analyse(rows, seed=1, **FAST)
        self.assertGreater(result.effect, 0.15)
        self.assertLess(result.ci_low, result.effect)
        self.assertGreater(result.ci_high, result.effect)
        self.assertEqual(decide(result, delta_star=0.10, harm_ceiling=0.20)[0], "GO")

    def test_it_does_not_invent_an_effect(self):
        rows = synthetic_trials(tasks=20, trials_per_arm=8, h0_rate=0.35, lift=0.0, seed=2)
        result = analyse(rows, seed=2, **FAST)
        self.assertNotEqual(decide(result, delta_star=0.10, harm_ceiling=1.0)[0], "GO")
        self.assertGreater(result.p_value, 0.05)

    def test_a_null_gives_a_large_p_value_and_a_lift_a_small_one(self):
        null = analyse(
            synthetic_trials(tasks=20, trials_per_arm=8, h0_rate=0.35, lift=0.0, seed=3),
            seed=3, **FAST,
        )
        lift = analyse(
            synthetic_trials(tasks=20, trials_per_arm=8, h0_rate=0.35, lift=0.3, seed=3),
            seed=3, **FAST,
        )
        self.assertGreater(null.p_value, lift.p_value)

    def test_the_p_value_is_never_zero(self):
        """10,000 permutations cannot license a claim stronger than 1/10,001."""
        rows = synthetic_trials(tasks=20, trials_per_arm=8, h0_rate=0.2, lift=0.7, seed=4)
        result = analyse(rows, seed=4, **FAST)
        self.assertGreater(result.p_value, 0)

    def test_it_is_deterministic_under_a_seed(self):
        rows = synthetic_trials(tasks=12, trials_per_arm=6, h0_rate=0.4, lift=0.2, seed=5)
        one = analyse(rows, seed=9, **FAST)
        two = analyse(rows, seed=9, **FAST)
        self.assertEqual(one.as_dict(), two.as_dict())


class UnitOfAnalysisTests(unittest.TestCase):
    def test_the_task_is_the_unit(self):
        """A task with many trials must not outvote a task with few."""
        rows = []
        for index in range(40):
            rows.append(_row("loud", "h0", "fail", index))
            rows.append(_row("loud", "h1", "pass", index))
        for index in range(2):
            rows.append(_row("quiet", "h0", "pass", 100 + index))
            rows.append(_row("quiet", "h1", "fail", 100 + index))
        result = analyse(rows, seed=1, permutations=50, resamples=200)
        # Two tasks, +1 and -1: the mean is zero despite 40:2 trial counts.
        self.assertAlmostEqual(result.effect, 0.0)

    def test_a_task_present_in_only_one_arm_is_dropped(self):
        rows = [
            _row("paired", "h0", "fail", 0),
            _row("paired", "h1", "pass", 1),
            _row("orphan", "h1", "pass", 2),
        ]
        result = analyse(rows, seed=1, permutations=20, resamples=100)
        self.assertEqual(result.tasks, ("paired",))


class ExclusionTests(unittest.TestCase):
    def test_errors_do_not_count_as_failures(self):
        rows = [
            _row("t", "h0", "fail", 0),
            _row("t", "h1", "pass", 1),
            _row("t", "h1", "error", 2),
        ]
        rates = per_task_rates(
            [(r["benchmark"]["task_id"], r["treatment"]["arm"],
              None if r["outcome"]["result"] in ("error", "excluded")
              else int(r["outcome"]["result"] == "pass")) for r in rows]
        )
        self.assertEqual(rates["t"]["h1"], 1.0)

    def test_a_run_over_the_exclusion_ceiling_is_void(self):
        rows = [_row("t", "h0", "fail", 0), _row("t", "h1", "pass", 1)]
        rows += [_row("t", "h1", "error", 2 + i) for i in range(3)]
        result = analyse(rows, seed=1, permutations=20, resamples=100)
        outcome, reason = decide(result, delta_star=0.10, harm_ceiling=1.0)
        self.assertEqual(outcome, "INCONCLUSIVE")
        self.assertIn("selected one", reason)

    def test_exploratory_receipts_are_not_analysed(self):
        rows = [_row("t", "h0", "fail", 0), _row("t", "h1", "pass", 1)]
        stray = _row("t", "h1", "pass", 2)
        stray["experiment"]["analysis_class"] = "exploratory"
        with self.assertRaises(ValueError):
            analyse([stray], seed=1, permutations=10, resamples=10)


class DecisionRuleTests(unittest.TestCase):
    def _analysis(self, low, high, harm=0.0, tasks=10):
        from analysis.pilot0001 import PilotAnalysis

        harmed = int(harm * tasks)
        differences = tuple([-0.5] * harmed + [0.5] * (tasks - harmed))
        return PilotAnalysis(
            tasks=tuple(f"t{i}" for i in range(tasks)),
            differences=differences,
            effect=(low + high) / 2,
            ci_low=low, ci_high=high, p_value=0.01,
            wins=tasks - harmed, losses=harmed, ties=0,
            excluded_rate_h0=0.0, excluded_rate_h1=0.0,
            permutations=1, resamples=1, seed=0,
        )

    def test_an_interval_above_delta_star_is_go(self):
        self.assertEqual(decide(self._analysis(0.12, 0.30), delta_star=0.10,
                                harm_ceiling=1.0)[0], "GO")

    def test_an_interval_below_delta_star_is_stop_even_without_zero(self):
        """A real but too-small effect is conclusive, not indeterminate. The
        first draft of this rule sent it to INCONCLUSIVE."""
        outcome, reason = decide(self._analysis(0.02, 0.06), delta_star=0.10,
                                 harm_ceiling=1.0)
        self.assertEqual(outcome, "STOP")
        self.assertIn("too small to act on", reason)

    def test_an_interval_spanning_delta_star_is_inconclusive(self):
        self.assertEqual(decide(self._analysis(0.04, 0.22), delta_star=0.10,
                                harm_ceiling=1.0)[0], "INCONCLUSIVE")

    def test_a_flat_null_is_stop(self):
        self.assertEqual(decide(self._analysis(-0.04, 0.05), delta_star=0.10,
                                harm_ceiling=1.0)[0], "STOP")

    def test_harm_flags_but_does_not_overturn_a_go(self):
        """Drafted as a gate; demoted because it fires on noise at pilot n."""
        outcome, reason = decide(self._analysis(0.12, 0.30, harm=0.5),
                                 delta_star=0.10, harm_ceiling=0.20)
        self.assertEqual(outcome, "GO")
        self.assertIn("Flag:", reason)
        self.assertIn("do not read this as a gate", reason)

    def test_harm_is_thresholded_at_delta_star_not_at_zero(self):
        from analysis.pilot0001 import PilotAnalysis

        held = PilotAnalysis(
            tasks=("a", "b", "c", "d"),
            differences=(-0.01, -0.02, -0.30, 0.4),
            effect=0.0, ci_low=-0.1, ci_high=0.1, p_value=0.5,
            wins=1, losses=3, ties=0,
            excluded_rate_h0=0.0, excluded_rate_h1=0.0,
            permutations=1, resamples=1, seed=0,
        )
        self.assertEqual(held.losses, 3)
        self.assertEqual(held.harm_rate(0.10), 0.25)


class SizingNoteTests(unittest.TestCase):
    def _text(self) -> str:
        return " ".join(SIZING.read_text(encoding="utf-8").split())

    def test_it_says_it_is_not_the_power_gate(self):
        self.assertIn("Do not use this table as the power gate", self._text())

    def test_it_declares_why_it_is_optimistic(self):
        text = self._text()
        self.assertIn("Why these numbers are optimistic", text)
        self.assertIn("correlated failures inflate variance", text)

    def test_it_records_that_tasks_buy_more_than_trials(self):
        self.assertIn("Tasks buy more than trials do", self._text())


def _row(task, arm, result, index):
    return {
        "experiment": {"analysis_class": "confirmatory", "run_sequence_index": index},
        "benchmark": {"task_id": task},
        "treatment": {"arm": arm},
        "outcome": {"result": result},
    }


if __name__ == "__main__":
    unittest.main()
