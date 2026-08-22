"""The schedule and the post-collection checks.

The schedule is the only evidence the arms were interleaved, and the checks are
the only thing standing between a log that looks like the planned study and one
that is it. Both are tested against the ways they can be quietly wrong.
"""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiment"))

from evidence import build_receipt  # noqa: E402
from harness import (  # noqa: E402
    ScheduleError,
    build_or_load,
    build_schedule,
    check_run,
    load_schedule,
    remaining,
    save_schedule,
)

D = lambda c: c * 64  # noqa: E731

TASKS = ("alpha", "beta", "gamma", "delta")


def schedule(**overrides):
    kwargs = dict(
        experiment_id="PILOT-0001", tasks=TASKS, trials_per_arm=3, seed=7
    )
    kwargs.update(overrides)
    return build_schedule(**kwargs)


def receipt_for(entry, *, result="pass", experiment_id="PILOT-0001", **patch):
    sections = {
        "experiment": {
            "experiment_id": experiment_id,
            "preregistration_digest": D("1"),
            "analysis_class": "confirmatory",
            "condition_label": f"{entry.arm}-label",
            "run_sequence_index": entry.index,
            "trial_id": f"t-{entry.index:04d}",
        },
        "benchmark": {
            "suite": "terminal-bench",
            "suite_version": "2.0",
            "task_id": entry.task_id,
            "task_version": "1",
            "task_qualification_digest": D("2"),
        },
        "environment": {
            "image_ref": "img", "image_digest": D("3"),
            "environment_context_digest": None if entry.arm == "h0" else D("4"),
        },
        "organism": {"organism_version": 1, "organism_fingerprint": D("5")},
        "treatment": {
            "arm": entry.arm, "skill_commit": "a" * 40, "skill_content_digest": D("6"),
            "recon_budget": 8000, "recon_used": 0 if entry.arm == "h0" else 3000,
            "recon_outcome": "not_applicable" if entry.arm == "h0" else "complete",
        },
        "resolution": {"resolution_version": 1, "resolution_digest": D("7")},
        "outcome": {
            "result": result, "verifier_kind": "deterministic",
            "verifier_exit_code": 0, "verifier_output_digest": D("8"),
        },
        "resources": {
            "wall_clock_seconds": 900.0, "prompt_tokens": 100,
            "completion_tokens": 50, "peak_vram_bytes": 1,
        },
        "custody": {"trajectory_digest": None, "artifact_digests": []},
    }
    if result in ("error", "excluded"):
        sections["outcome"]["failure_class"] = "harness_timeout"
    for name, values in patch.items():
        sections[name].update(values)
    return build_receipt(**sections)


class ShapeTests(unittest.TestCase):
    def test_every_pair_appears_the_planned_number_of_times(self):
        held = schedule()
        counts = {}
        for entry in held.entries:
            counts[(entry.task_id, entry.arm)] = counts.get((entry.task_id, entry.arm), 0) + 1
        self.assertEqual(len(counts), len(TASKS) * 2)
        self.assertEqual(set(counts.values()), {3})

    def test_indices_are_contiguous_from_zero(self):
        held = schedule()
        self.assertEqual([e.index for e in held.entries], list(range(len(held))))

    def test_arms_are_balanced_after_every_round(self):
        """The whole point: drift across the run has to hit both arms equally."""
        held = schedule()
        per_round = len(TASKS) * 2
        for boundary in range(per_round, len(held) + 1, per_round):
            prefix = held.entries[:boundary]
            h0 = sum(1 for e in prefix if e.arm == "h0")
            h1 = sum(1 for e in prefix if e.arm == "h1")
            with self.subTest(after=boundary):
                self.assertEqual(h0, h1)

    def test_a_round_contains_each_pair_exactly_once(self):
        held = schedule()
        per_round = len(TASKS) * 2
        first = held.entries[:per_round]
        self.assertEqual(len({(e.task_id, e.arm) for e in first}), per_round)

    def test_it_is_not_merely_task_ordered(self):
        """A schedule that runs h0 then h1 back to back per task is not
        interleaved, it is paired."""
        held = schedule()
        pairs = [
            (held.entries[i].task_id, held.entries[i + 1].task_id)
            for i in range(0, 8, 2)
        ]
        self.assertTrue(any(a != b for a, b in pairs))


class DeterminismTests(unittest.TestCase):
    def test_the_same_seed_gives_the_same_schedule(self):
        self.assertEqual(schedule().digest, schedule().digest)

    def test_a_different_seed_gives_a_different_schedule(self):
        self.assertNotEqual(schedule().digest, schedule(seed=8).digest)

    def test_the_task_set_is_inside_the_digest(self):
        self.assertNotEqual(
            schedule().digest, schedule(tasks=TASKS[:3]).digest
        )


class ValidationTests(unittest.TestCase):
    def test_no_tasks_is_refused(self):
        with self.assertRaises(ScheduleError):
            schedule(tasks=())

    def test_duplicate_tasks_are_refused(self):
        with self.assertRaises(ScheduleError):
            schedule(tasks=("a", "a"))

    def test_zero_trials_is_refused(self):
        with self.assertRaises(ScheduleError):
            schedule(trials_per_arm=0)

    def test_duplicate_arms_are_refused(self):
        with self.assertRaises(ScheduleError):
            schedule(arms=("h0", "h0"))


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "schedule.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_schedule_round_trips(self):
        held = schedule()
        save_schedule(self.path, held)
        self.assertEqual(load_schedule(self.path).digest, held.digest)

    def test_overwriting_is_refused(self):
        """A regenerated schedule is a different study under the same name."""
        save_schedule(self.path, schedule())
        with self.assertRaises(ScheduleError):
            save_schedule(self.path, schedule(seed=9))

    def test_an_edited_schedule_is_detected(self):
        save_schedule(self.path, schedule())
        document = json.loads(self.path.read_text())
        document["entries"][0]["arm"] = "h1"
        self.path.write_text(json.dumps(document))
        with self.assertRaises(ScheduleError) as caught:
            load_schedule(self.path)
        self.assertIn("edited", str(caught.exception))

    def test_build_or_load_creates_then_reuses(self):
        first = build_or_load(
            self.path, experiment_id="PILOT-0001", tasks=TASKS, trials_per_arm=3, seed=7
        )
        second = build_or_load(
            self.path, experiment_id="PILOT-0001", tasks=TASKS, trials_per_arm=3, seed=7
        )
        self.assertEqual(first.digest, second.digest)

    def test_resuming_under_different_parameters_is_refused(self):
        """Two studies in one receipt log is the failure this prevents."""
        build_or_load(
            self.path, experiment_id="PILOT-0001", tasks=TASKS, trials_per_arm=3, seed=7
        )
        for change in (
            {"seed": 8},
            {"trials_per_arm": 4},
            {"tasks": TASKS[:2]},
            {"experiment_id": "PILOT-0002"},
        ):
            with self.subTest(**change):
                kwargs = dict(
                    experiment_id="PILOT-0001", tasks=TASKS, trials_per_arm=3, seed=7
                )
                kwargs.update(change)
                with self.assertRaises(ScheduleError):
                    build_or_load(self.path, **kwargs)


class ResumeTests(unittest.TestCase):
    def test_nothing_run_means_everything_remains(self):
        held = schedule()
        self.assertEqual(len(remaining(held, [])), len(held))

    def test_the_remainder_is_what_has_no_receipt(self):
        held = schedule()
        done = [receipt_for(e) for e in held.entries[:5]]
        left = remaining(held, done)
        self.assertEqual(len(left), len(held) - 5)
        self.assertEqual(left[0].index, 5)

    def test_it_matches_on_index_not_on_task_and_arm(self):
        """Two entries in one round are otherwise indistinguishable, and a
        resume would re-run the wrong one."""
        held = schedule()
        target = held.entries[7]
        left = remaining(held, [receipt_for(target)])
        self.assertNotIn(target.index, [e.index for e in left])
        same_pair = [
            e for e in held.entries
            if (e.task_id, e.arm) == (target.task_id, target.arm) and e.index != target.index
        ]
        for entry in same_pair:
            self.assertIn(entry.index, [e.index for e in left])

    def test_another_experiments_receipts_are_ignored(self):
        held = schedule()
        stray = receipt_for(held.entries[0], experiment_id="PILOT-0002")
        self.assertEqual(len(remaining(held, [stray])), len(held))


class RunCheckTests(unittest.TestCase):
    def _complete(self, held=None, **kw):
        held = held or schedule()
        return held, [receipt_for(e, **kw) for e in held.entries]

    def test_a_faithful_run_is_clean(self):
        held, receipts = self._complete()
        report = check_run(receipts, schedule=held, committed_tasks=TASKS)
        self.assertTrue(report.clean, str(report))
        self.assertTrue(report.analysable)
        self.assertEqual(report.receipts, len(held))

    def test_an_empty_log_is_fatal(self):
        self.assertFalse(check_run([]).analysable)

    def test_a_tampered_receipt_is_caught(self):
        held, receipts = self._complete()
        receipts[3]["resources"]["prompt_tokens"] = 1
        report = check_run(receipts, schedule=held, committed_tasks=TASKS)
        self.assertFalse(report.analysable)
        self.assertTrue(any(f.check == "digests" for f in report.findings))

    def test_two_organisms_in_one_log_are_caught(self):
        held, receipts = self._complete()
        entry = held.entries[2]
        receipts[2] = receipt_for(entry, organism={"organism_fingerprint": D("b")})
        report = check_run(receipts, schedule=held, committed_tasks=TASKS)
        self.assertTrue(any(f.check == "organism" for f in report.findings))

    def test_two_preregistrations_are_caught(self):
        held, receipts = self._complete()
        receipts[1] = receipt_for(held.entries[1], experiment={"preregistration_digest": D("c")})
        report = check_run(receipts, schedule=held, committed_tasks=TASKS)
        self.assertTrue(any(f.check == "preregistration" for f in report.findings))

    def test_a_stray_rehearsal_receipt_is_caught(self):
        held, receipts = self._complete()
        receipts[0] = receipt_for(
            held.entries[0],
            experiment={"analysis_class": "rehearsal", "preregistration_digest": "none"},
        )
        report = check_run(receipts, schedule=held, committed_tasks=TASKS)
        self.assertTrue(any(f.check == "analysis_class" for f in report.findings))

    def test_excessive_exclusions_are_caught_per_arm(self):
        held = schedule()
        receipts = []
        for entry in held.entries:
            excluded = entry.arm == "h1" and entry.index % 4 == 1
            receipts.append(receipt_for(entry, result="error" if excluded else "pass"))
        report = check_run(receipts, schedule=held, committed_tasks=TASKS)
        self.assertTrue(any(f.check == "exclusions" for f in report.findings), str(report))

    def test_a_task_outside_the_committed_set_is_caught(self):
        held, receipts = self._complete()
        receipts[4] = receipt_for(held.entries[4], benchmark={"task_id": "epsilon"})
        report = check_run(receipts, schedule=held, committed_tasks=TASKS)
        self.assertTrue(any(f.check == "task set" for f in report.findings))

    def test_a_committed_task_with_no_trials_warns_but_is_not_fatal(self):
        held = schedule(tasks=TASKS[:3])
        receipts = [receipt_for(e) for e in held.entries]
        report = check_run(receipts, schedule=held, committed_tasks=TASKS)
        self.assertFalse(report.clean)
        self.assertTrue(report.analysable)

    def test_a_receipt_that_ran_the_wrong_arm_is_caught(self):
        """Structurally perfect, and not the trial that was scheduled."""
        held, receipts = self._complete()
        entry = held.entries[6]
        flipped = "h1" if entry.arm == "h0" else "h0"
        receipts[6] = receipt_for(
            type(entry)(entry.index, entry.task_id, flipped, entry.replicate)
        )
        report = check_run(receipts, schedule=held, committed_tasks=TASKS)
        self.assertTrue(any(f.check == "schedule" for f in report.findings), str(report))

    def test_a_partial_run_warns_rather_than_failing(self):
        held = schedule()
        report = check_run(
            [receipt_for(e) for e in held.entries[:10]], schedule=held, committed_tasks=TASKS
        )
        self.assertTrue(any(f.check == "coverage" for f in report.findings))
        self.assertTrue(report.analysable)

    def test_more_receipts_than_scheduled_is_fatal(self):
        held = schedule()
        receipts = [receipt_for(e) for e in held.entries]
        extra = copy.deepcopy(held.entries[0])
        receipts.append(receipt_for(type(extra)(999, "alpha", "h0", 0)))
        report = check_run(receipts, schedule=held, committed_tasks=TASKS)
        self.assertFalse(report.analysable)

    def test_checks_never_raise_on_a_malformed_log(self):
        for bad in ([{}], [{"experiment": None}], [{"outcome": []}], [None]):
            with self.subTest(log=bad):
                report = check_run(bad)
                self.assertFalse(report.clean)


if __name__ == "__main__":
    unittest.main()
